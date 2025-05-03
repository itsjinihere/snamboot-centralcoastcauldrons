from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from uuid import UUID
import sqlalchemy

from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionMix(BaseModel):
    order_id: Optional[UUID] = None
    potion_type: List[int] = Field(..., min_length=4, max_length=4)
    quantity: int = Field(..., ge=1)

    @model_validator(mode="before")
    @classmethod
    def validate_mixture(cls, values):
        potion_type = values.get("potion_type")
        if potion_type is None or len(potion_type) != 4:
            raise ValueError("potion_type must have exactly 4 elements [r, g, b, d]")
        if sum(potion_type) != 100:
            raise ValueError("potion_type values must sum to 100")
        return values

@router.post("/deliver", status_code=status.HTTP_204_NO_CONTENT)
def deliver_bottled_potions(potions: List[PotionMix]):
    with db.engine.begin() as connection:
        for potion in potions:
            # Idempotency check
            if potion.order_id:
                existing = connection.execute(
                    sqlalchemy.text("""
                        SELECT 1 FROM executed_orders WHERE order_id = :oid
                    """),
                    {"oid": str(potion.order_id)}
                ).first()
                if existing:
                    continue

            potion_types = ["red", "green", "blue", "dark"]
            ml_resources = [f"{color}_ml" for color in potion_types]
            potion_resources = [f"{color}_potion" for color in potion_types]

            ml_needed = {
                ml: 50 * potion.quantity * (potion.potion_type[i] / 100)
                for i, ml in enumerate(ml_resources)
            }

            ledger_entries = []
            for i, ml_resource in enumerate(ml_resources):
                used = int(ml_needed[ml_resource])
                if used > 0:
                    ledger_entries.append((ml_resource, -used, "Used for bottling"))

            for i, potion_resource in enumerate(potion_resources):
                if potion.potion_type[i] == 100:
                    ledger_entries.append((potion_resource, potion.quantity, "Potion bottled"))
                    break

            for resource, change, context in ledger_entries:
                connection.execute(
                    sqlalchemy.text("""
                        INSERT INTO ledger_entries (resource, change, context)
                        VALUES (:resource, :change, :context)
                    """),
                    {"resource": resource, "change": change, "context": context}
                )

            if potion.order_id:
                connection.execute(
                    sqlalchemy.text("""
                        INSERT INTO executed_orders (order_id)
                        VALUES (:oid)
                    """),
                    {"oid": str(potion.order_id)}
                )

@router.post("/plan", response_model=List[PotionMix])
def get_bottle_plan():
    with db.engine.begin() as connection:
        inventory = connection.execute(
            sqlalchemy.text("""
                SELECT 
                    COALESCE(SUM(CASE WHEN resource = 'red_ml' THEN change ELSE 0 END), 0) AS red_ml,
                    COALESCE(SUM(CASE WHEN resource = 'green_ml' THEN change ELSE 0 END), 0) AS green_ml,
                    COALESCE(SUM(CASE WHEN resource = 'blue_ml' THEN change ELSE 0 END), 0) AS blue_ml,
                    COALESCE(SUM(CASE WHEN resource = 'dark_ml' THEN change ELSE 0 END), 0) AS dark_ml
                FROM ledger_entries
            """)
        ).mappings().one()

    mixes = []
    for i, color in enumerate(["red", "green", "blue", "dark"]):
        ml_key = f"{color}_ml"
        quantity = inventory[ml_key] // 50
        if quantity > 0:
            mix = [0, 0, 0, 0]
            mix[i] = 100
            mixes.append(PotionMix(potion_type=mix, quantity=int(quantity)))

    return mixes
