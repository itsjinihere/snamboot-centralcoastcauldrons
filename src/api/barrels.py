from dataclasses import dataclass
from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List
import random
import sqlalchemy
from src.api import auth
from src import database as db
from datetime import datetime

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)


class Barrel(BaseModel):
    item_sku: str  # Changed from 'sku' to 'item_sku'
    ml_per_barrel: int = Field(gt=0, description="Must be greater than 0")
    potion_type: List[float] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Must contain exactly 3 elements: [r, g, b] that sum to 1.0",
    )
    price: int = Field(ge=0, description="Price must be non-negative")
    quantity: int = Field(ge=0, description="Quantity must be non-negative")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )  # Added timestamp field

    @field_validator("potion_type")
    @classmethod
    def validate_potion_type(cls, potion_type: List[float]) -> List[float]:
        if len(potion_type) != 3:
            raise ValueError("potion_type must have exactly 3 elements: [r, g, b]")
        if not abs(sum(potion_type) - 1.0) < 1e-6:
            raise ValueError("Sum of potion_type values must be exactly 1.0")
        return potion_type


class BarrelOrder(BaseModel):
    item_sku: str  # Changed from 'sku' to 'item_sku'
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


@dataclass
class BarrelSummary:
    gold_paid: int


def calculate_barrel_summary(barrels: List[Barrel]) -> BarrelSummary:
    return BarrelSummary(gold_paid=sum(b.price * b.quantity for b in barrels))


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_barrels(barrels_delivered: List[Barrel], order_id: int):
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    delivery = calculate_barrel_summary(barrels_delivered)

    ml_totals: dict[str, float] = {
        "red_ml": 0.0,
        "green_ml": 0.0,
        "blue_ml": 0.0,
    }

    for barrel in barrels_delivered:
        total_ml = barrel.ml_per_barrel * barrel.quantity
        ml_totals["red_ml"] += total_ml * barrel.potion_type[0]
        ml_totals["green_ml"] += total_ml * barrel.potion_type[1]
        ml_totals["blue_ml"] += total_ml * barrel.potion_type[2]

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory
                SET
                    gold = gold - :gold_paid,
                    red_ml = red_ml + :red_ml,
                    green_ml = green_ml + :green_ml,
                    blue_ml = blue_ml + :blue_ml
                """
            ),
            {
                "gold_paid": delivery.gold_paid,
                "red_ml": int(ml_totals["red_ml"]),
                "green_ml": int(ml_totals["green_ml"]),
                "blue_ml": int(ml_totals["blue_ml"]),
            },
        )


def create_barrel_plan(
    gold: int,
    max_barrel_capacity: int,
    current_red_ml: int,
    current_green_ml: int,
    current_blue_ml: int,
    red_potions: int,
    green_potions: int,
    blue_potions: int,
    wholesale_catalog: List[Barrel],
) -> List[BarrelOrder]:
    print(
        f"gold: {gold}, max_barrel_capacity: {max_barrel_capacity}, "
        f"current_red_ml: {current_red_ml}, current_green_ml: {current_green_ml}, "
        f"current_blue_ml: {current_blue_ml}, "
        f"red_potions: {red_potions}, green_potions: {green_potions}, blue_potions: {blue_potions}, "
        f"wholesale_catalog: {wholesale_catalog}"
    )

    color_index_map = {"red": 0, "green": 1, "blue": 2}
    potion_counts = {"red": red_potions, "green": green_potions, "blue": blue_potions}
    eligible_colors = [color for color, count in potion_counts.items() if count < 5]

    if not eligible_colors:
        return []

    chosen_color = random.choice(eligible_colors)
    idx = color_index_map[chosen_color]

    matching_barrels = [
        barrel for barrel in wholesale_catalog if barrel.potion_type[idx] == 1.0
    ]

    cheapest_barrel = min(matching_barrels, key=lambda b: b.price, default=None)

    current_capacity = current_red_ml + current_green_ml + current_blue_ml

    if (
        cheapest_barrel
        and cheapest_barrel.price <= gold
        and current_capacity + cheapest_barrel.ml_per_barrel <= max_barrel_capacity
    ):
        return [
            BarrelOrder(item_sku=cheapest_barrel.item_sku, quantity=1)
        ]  # Updated to item_sku

    return []


def get_wholesale_purchase_plan(wholesale_catalog: List[Barrel]):
    print(f"barrel catalog: {wholesale_catalog}")

    with db.engine.begin() as connection:
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT gold, red_ml, green_ml, blue_ml,
                       red_potions, green_potions, blue_potions
                FROM global_inventory
                """
            )
        ).first()  # Changed to .first()

    if not row:
        raise HTTPException(status_code=404, detail="No inventory row found")

    return create_barrel_plan(
        gold=row.gold,
        max_barrel_capacity=10000,
        current_red_ml=row.red_ml,
        current_green_ml=row.green_ml,
        current_blue_ml=row.blue_ml,
        red_potions=row.red_potions,
        green_potions=row.green_potions,
        blue_potions=row.blue_potions,
        wholesale_catalog=wholesale_catalog,
    )
