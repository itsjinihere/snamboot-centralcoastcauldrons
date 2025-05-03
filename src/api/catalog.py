from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Annotated
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/catalog",
    tags=["catalog"]
)

class CatalogItem(BaseModel):
    sku: Annotated[str, Field(pattern=r"^[A-Z_0-9]{1,20}$")]
    name: str
    quantity: Annotated[int, Field(ge=1, le=10000)]
    price: Annotated[int, Field(ge=1, le=500)]
    potion_type: List[int] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Must contain exactly 4 elements: [r, g, b, d]",
    )

POTION_DEFINITIONS = {
    "RED_POTION_0": {
        "name": "Red Potion",
        "base_price": 50,
        "type": [100, 0, 0, 0],
        "resource": "red_potions",
    },
    "GREEN_POTION_0": {
        "name": "Green Potion",
        "base_price": 60,
        "type": [0, 100, 0, 0],
        "resource": "green_potions",
    },
    "BLUE_POTION_0": {
        "name": "Blue Potion",
        "base_price": 70,
        "type": [0, 0, 100, 0],
        "resource": "blue_potions",
    },
    "DARK_POTION_0": {
        "name": "Dark Potion",
        "base_price": 90,
        "type": [0, 0, 0, 100],
        "resource": "dark_potions",
    },
}

def fetch_potion_balances():
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT
                resource,
                SUM(change) AS total
            FROM ledger_entries
            WHERE resource IN ('red_potions', 'green_potions', 'blue_potions', 'dark_potions')
            GROUP BY resource
        """)).mappings().all()

    return {row["resource"]: row["total"] or 0 for row in result}

def determine_price(base: int, quantity: int) -> int:
    return min(base + 10, 500) if quantity < 4 else base

@router.get("/", response_model=List[CatalogItem])
def get_catalog():
    potion_balances = fetch_potion_balances()
    catalog: List[CatalogItem] = []

    for sku, info in POTION_DEFINITIONS.items():
        qty = potion_balances.get(info["resource"], 0)
        if qty > 0:
            catalog.append(CatalogItem(
                sku=sku,
                name=info["name"],
                quantity=qty,
                price=determine_price(info["base_price"], qty),
                potion_type=info["type"]
            ))

    return catalog[:6]
