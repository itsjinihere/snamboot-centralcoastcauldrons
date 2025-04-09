from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from src.api import auth
import sqlalchemy
from src import database as db
import random
from typing import List, Optional

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

    @field_validator("potion_type")
    @classmethod
    def validate_potion_type(cls, potion_type: List[int]) -> List[int]:
        if sum(potion_type) != 100:
            raise ValueError("Sum of potion_type values must be exactly 100")
        return potion_type


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_bottles(potions_delivered: List[PotionMixes], order_id: int):
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")

    ml_used: dict[str, float] = {
        "red_ml": 0.0,
        "green_ml": 0.0,
        "blue_ml": 0.0,
        "dark_ml": 0.0,
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
        ml_used["dark_ml"] += ml_total * (mix.potion_type[3] / 100)

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
                    dark_ml = dark_ml - :dark_ml,
                    red_potions = red_potions + :red_potions,
                    green_potions = green_potions + :green_potions,
                    blue_potions = blue_potions + :blue_potions
                """
            ),
            {
                "red_ml": int(ml_used["red_ml"]),
                "green_ml": int(ml_used["green_ml"]),
                "blue_ml": int(ml_used["blue_ml"]),
                "dark_ml": int(ml_used["dark_ml"]),
                "red_potions": potions_made["red_potions"],
                "green_potions": potions_made["green_potions"],
                "blue_potions": potions_made["blue_potions"],
            },
        )


def create_bottle_plan(
    red_ml: Optional[int] = None,
    green_ml: Optional[int] = None,
    blue_ml: Optional[int] = None,
    dark_ml: Optional[int] = None,
    red_potions: Optional[int] = None,
    green_potions: Optional[int] = None,
    blue_potions: Optional[int] = None,
    maximum_potion_capacity: int = 50,
    current_potion_inventory: List[PotionMixes] = [],
) -> List[PotionMixes]:
    # If values not provided, fetch from database
    if None in [
        red_ml,
        green_ml,
        blue_ml,
        dark_ml,
        red_potions,
        green_potions,
        blue_potions,
    ]:
        with db.engine.begin() as connection:
            row = connection.execute(
                sqlalchemy.text("""
                    SELECT red_ml, green_ml, blue_ml, dark_ml,
                           red_potions, green_potions, blue_potions
                    FROM global_inventory
                    LIMIT 1
                """)
            ).first()

        if not row:
            return []

        red_ml = row.red_ml
        green_ml = row.green_ml
        blue_ml = row.blue_ml
        dark_ml = row.dark_ml
        red_potions = row.red_potions
        green_potions = row.green_potions
        blue_potions = row.blue_potions

    # Mypy-safe asserts
    assert red_ml is not None
    assert green_ml is not None
    assert blue_ml is not None
    assert dark_ml is not None
    assert red_potions is not None
    assert green_potions is not None
    assert blue_potions is not None

    potion_plan = []
    bottle_volume = 50
    low_stock = []

    if red_potions < 5 and red_ml >= bottle_volume:
        low_stock.append(("red", [100, 0, 0, 0], red_ml))
    if green_potions < 5 and green_ml >= bottle_volume:
        low_stock.append(("green", [0, 100, 0, 0], green_ml))
    if blue_potions < 5 and blue_ml >= bottle_volume:
        low_stock.append(("blue", [0, 0, 100, 0], blue_ml))

    if not low_stock and dark_ml >= bottle_volume:
        potion_plan.append(PotionMixes(potion_type=[0, 0, 0, 100], quantity=1))
    elif low_stock:
        color, potion_type, available_ml = random.choice(low_stock)
        max_quantity = min(available_ml // bottle_volume, 10)
        if max_quantity >= 1:
            potion_plan.append(
                PotionMixes(potion_type=potion_type, quantity=int(max_quantity))
            )

    return potion_plan


@router.post("/plan", response_model=List[PotionMixes])
def get_bottle_plan():
    with db.engine.begin() as connection:
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT red_ml, green_ml, blue_ml, dark_ml,
                       red_potions, green_potions, blue_potions
                FROM global_inventory
                """
            )
        ).one()

    return create_bottle_plan(
        red_ml=row.red_ml,
        green_ml=row.green_ml,
        blue_ml=row.blue_ml,
        dark_ml=row.dark_ml,
        red_potions=row.red_potions,
        green_potions=row.green_potions,
        blue_potions=row.blue_potions,
        maximum_potion_capacity=50,
        current_potion_inventory=[],
    )
