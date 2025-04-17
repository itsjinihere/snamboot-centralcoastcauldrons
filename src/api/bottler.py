from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, root_validator
from typing import List, Optional
import sqlalchemy
import random

from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)


class PotionMixes(BaseModel):
    potion_type: List[int] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Must contain exactly 4 elements: [r, g, b, d]",
    )
    quantity: int = Field(
        ..., ge=1, le=10000, description="Quantity must be between 1 and 10,000"
    )

    @root_validator(pre=True)
    @classmethod
    def validate_potion_type(cls, values):
        potion_type = values.get('potion_type')
        if len(potion_type) != 4:
            raise ValueError("Potion type must have exactly 4 elements: [r, g, b, d]")
        if sum(potion_type) != 100:
            raise ValueError("Sum of potion_type values must be exactly 100")
        return values


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_bottles(potions_delivered: List[PotionMixes], order_id: int):
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")

    ml_used: dict[str, float] = {
        "red_ml": 0.0,
        "green_ml": 0.0,
        "blue_ml": 0.0,
    }

    potions_made: dict[str, int] = {
        "red_potions": 0,
        "green_potions": 0,
        "blue_potions": 0,
    }

    for mix in potions_delivered:
        ml_total_per_bottle = 50
        ml_total = mix.quantity * ml_total_per_bottle

        ml_used["red_ml"] += ml_total * (mix.potion_type[0] / 100)
        ml_used["green_ml"] += ml_total * (mix.potion_type[1] / 100)
        ml_used["blue_ml"] += ml_total * (mix.potion_type[2] / 100)

        if mix.potion_type == [100, 0, 0, 0]:
            potions_made["red_potions"] += mix.quantity
        elif mix.potion_type == [0, 100, 0, 0]:
            potions_made["green_potions"] += mix.quantity
        elif mix.potion_type == [0, 0, 100, 0]:
            potions_made["blue_potions"] += mix.quantity

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory
                SET
                    red_ml = red_ml - :red_ml,
                    green_ml = green_ml - :green_ml,
                    blue_ml = blue_ml - :blue_ml,
                    red_potions = red_potions + :red_potions,
                    green_potions = green_potions + :green_potions,
                    blue_potions = blue_potions + :blue_potions
                """
            ),
            {
                "red_ml": int(ml_used["red_ml"]),
                "green_ml": int(ml_used["green_ml"]),
                "blue_ml": int(ml_used["blue_ml"]),
                "red_potions": potions_made["red_potions"],
                "green_potions": potions_made["green_potions"],
                "blue_potions": potions_made["blue_potions"],
            },
        )


def create_bottle_plan(
    red_ml: Optional[int] = None,
    green_ml: Optional[int] = None,
    blue_ml: Optional[int] = None,
    red_potions: Optional[int] = None,
    green_potions: Optional[int] = None,
    blue_potions: Optional[int] = None,
    maximum_potion_capacity: int = 50,
    current_potion_inventory: List[PotionMixes] = [],
) -> List[PotionMixes]:
    # Fetch potion mixes from database instead of hardcoding
    with db.engine.begin() as connection:
        potion_rows = connection.execute(
            sqlalchemy.text("""
                SELECT potion_type, quantity
                FROM potions
            """)
        ).fetchall()

    potion_plan = []
    for row in potion_rows:
        potion_type = row[0]
        quantity = row[1]
        potion_plan.append(PotionMixes(potion_type=potion_type, quantity=quantity))

    return potion_plan


@router.post("/plan", response_model=List[PotionMixes])
def get_bottle_plan():
    # You can adjust this if needed based on other variables
    return create_bottle_plan(
        red_ml=100,
        green_ml=0,
        blue_ml=0,
        red_potions=0,
        green_potions=0,
        blue_potions=0,
        maximum_potion_capacity=50,
    )
