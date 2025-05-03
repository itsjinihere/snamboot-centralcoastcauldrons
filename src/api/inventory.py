from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import sqlalchemy
from src.api import auth
from src import database as db
from typing import Optional
from uuid import UUID

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

class InventoryAudit(BaseModel):
    number_of_potions: int
    ml_in_barrels: int
    gold: int

class CapacityPlan(BaseModel):
    potion_capacity: int = Field(ge=0, le=10, description="Potion capacity units, max 10")
    ml_capacity: int = Field(ge=0, le=10, description="ML capacity units, max 10")

@router.get("/audit", response_model=InventoryAudit)
def get_inventory():
    """
    Returns an audit of the current inventory using the ledger.
    """
    with db.engine.begin() as connection:
        gold = connection.execute(
            sqlalchemy.text("""
                SELECT COALESCE(SUM(change), 0) FROM ledger_entries
                WHERE resource = 'gold'
            """)
        ).scalar_one()

        ml_in_barrels = connection.execute(
            sqlalchemy.text("""
                SELECT COALESCE(SUM(change), 0) FROM ledger_entries
                WHERE resource IN ('red_ml', 'green_ml', 'blue_ml', 'dark_ml')
            """)
        ).scalar_one()

        potions = connection.execute(
            sqlalchemy.text("""
                SELECT COALESCE(SUM(change), 0) FROM ledger_entries
                WHERE resource IN ('red_potion', 'green_potion', 'blue_potion', 'dark_potion')
            """)
        ).scalar_one()

        return InventoryAudit(
            number_of_potions=potions,
            ml_in_barrels=ml_in_barrels,
            gold=gold
        )

@router.post("/plan", response_model=CapacityPlan)
def get_capacity_plan():
    """
    Hardcoded plan: start with 1 unit of each. More costs gold.
    """
    return CapacityPlan(potion_capacity=1, ml_capacity=1)

@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def deliver_capacity_plan(capacity_purchase: CapacityPlan, order_id: UUID):
    """
    Processes the delivery of a capacity purchase using a ledger-based and idempotent design.
    """
    with db.engine.begin() as connection:
        # Check for duplicate execution
        existing = connection.execute(
            sqlalchemy.text("""
                SELECT 1 FROM executed_orders WHERE order_id = :oid
            """),
            {"oid": str(order_id)}
        ).first()

        if existing:
            return  # Already processed

        # Determine how many extra capacity units were purchased
        extra_potion_capacity = max(capacity_purchase.potion_capacity - 1, 0)
        extra_ml_capacity = max(capacity_purchase.ml_capacity - 1, 0)

        total_cost = (extra_potion_capacity + extra_ml_capacity) * 1000

        current_gold = connection.execute(
            sqlalchemy.text("""
                SELECT COALESCE(SUM(change), 0) FROM ledger_entries
                WHERE resource = 'gold'
            """)
        ).scalar_one()

        if total_cost > current_gold:
            raise HTTPException(status_code=400, detail="Insufficient gold")

        if total_cost > 0:
            connection.execute(
                sqlalchemy.text("""
                    INSERT INTO ledger_entries (resource, change, context)
                    VALUES ('gold', :change, 'Capacity upgrade')
                """),
                {"change": -total_cost}
            )

        connection.execute(
            sqlalchemy.text("""
                INSERT INTO executed_orders (order_id)
                VALUES (:oid)
            """),
            {"oid": str(order_id)}
        )

    return
