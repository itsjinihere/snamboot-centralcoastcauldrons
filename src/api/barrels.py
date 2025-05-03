from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from uuid import UUID
import random
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

# ---- Models ----

class Barrel(BaseModel):
    order_id: Optional[UUID] = None
    sku: str
    potion_type: List[float] = Field(..., min_length=4, max_length=4)
    price: int = Field(ge=0)
    quantity: int = Field(ge=0)

    @field_validator("potion_type")
    @classmethod
    def validate_sum(cls, values: List[float]) -> List[float]:
        if not abs(sum(values) - 1.0) < 1e-6:
            raise ValueError("Potion type fractions must sum to 1.0")
        return values

class BarrelOrder(BaseModel):
    sku: str
    quantity: int = Field(gt=0)

# ---- Utilities ----

def get_current_inventory(connection):
    query = """
        SELECT 
            COALESCE(SUM(CASE WHEN resource = 'gold' THEN change ELSE 0 END), 0) AS gold,
            COALESCE(SUM(CASE WHEN resource = 'red_ml' THEN change ELSE 0 END), 0) AS red_ml,
            COALESCE(SUM(CASE WHEN resource = 'green_ml' THEN change ELSE 0 END), 0) AS green_ml,
            COALESCE(SUM(CASE WHEN resource = 'blue_ml' THEN change ELSE 0 END), 0) AS blue_ml,
            COALESCE(SUM(CASE WHEN resource = 'dark_ml' THEN change ELSE 0 END), 0) AS dark_ml
        FROM ledger_entries
    """
    return connection.execute(sqlalchemy.text(query)).mappings().one()

# ---- Endpoint: /barrels/deliver/{order_id} ----

@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def deliver_barrels(barrels: List[Barrel], order_id: UUID):
    with db.engine.begin() as connection:
        # Check for duplicate order
        existing = connection.execute(
            sqlalchemy.text("SELECT 1 FROM executed_orders WHERE order_id = :oid"),
            {"oid": str(order_id)}
        ).first()
        if existing:
            return  # Idempotent: do nothing if already processed

        total_gold = sum(barrel.price * barrel.quantity for barrel in barrels)

        # Compute total ml per color
        color_map = ["red_ml", "green_ml", "blue_ml", "dark_ml"]
        ml_totals = {color: 0 for color in color_map}

        for barrel in barrels:
            ml_per_barrel = 1000  # Fixed amount
            total_ml = barrel.quantity * ml_per_barrel
            for i, color in enumerate(color_map):
                ml_totals[color] += int(total_ml * barrel.potion_type[i])

        # Insert ledger entries for ml and gold
        for color, amount in ml_totals.items():
            if amount > 0:
                connection.execute(
                    sqlalchemy.text(
                        "INSERT INTO ledger_entries (resource, change, context) VALUES (:resource, :change, 'barrel delivery')"
                    ),
                    {"resource": color, "change": amount}
                )

        connection.execute(
            sqlalchemy.text(
                "INSERT INTO ledger_entries (resource, change, context) VALUES ('gold', :change, 'barrel delivery')"
            ),
            {"change": -total_gold}
        )

        # Record order ID for idempotency
        connection.execute(
            sqlalchemy.text("INSERT INTO executed_orders (order_id) VALUES (:oid)"),
            {"oid": str(order_id)}
        )

# ---- Endpoint: /barrels/plan ----

@router.post("/plan", response_model=List[BarrelOrder])
def plan_barrels(catalog: List[Barrel]):
    with db.engine.begin() as connection:
        inventory = get_current_inventory(connection)

        # Get potion counts
        potions = connection.execute(
            sqlalchemy.text("""
                SELECT 
                    COALESCE(SUM(CASE WHEN resource = 'red_potions' THEN change ELSE 0 END), 0) AS red_potions,
                    COALESCE(SUM(CASE WHEN resource = 'green_potions' THEN change ELSE 0 END), 0) AS green_potions,
                    COALESCE(SUM(CASE WHEN resource = 'blue_potions' THEN change ELSE 0 END), 0) AS blue_potions
                FROM ledger_entries
            """)
        ).mappings().one()

        # Choose a color with < 5 potions
        potion_counts = {
            "red": potions.red_potions,
            "green": potions.green_potions,
            "blue": potions.blue_potions,
        }
        candidates = [color for color, count in potion_counts.items() if count < 5]
        if not candidates:
            return []

        chosen_color = random.choice(candidates)
        color_index = {"red": 0, "green": 1, "blue": 2}[chosen_color]

        # Find matching barrels
        eligible = [
            b for b in catalog
            if b.potion_type[color_index] == 1.0 and b.price <= inventory.gold
        ]

        if not eligible:
            return []

        best_barrel = min(eligible, key=lambda b: b.price)
        return [BarrelOrder(sku=best_barrel.sku, quantity=1)]
