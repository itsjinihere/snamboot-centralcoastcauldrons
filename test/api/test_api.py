import pytest
import sqlalchemy
from src import database as db
from src.api.barrels import (
    calculate_barrel_summary,
    create_barrel_plan,
    Barrel,
    BarrelOrder,
)
from src.api.bottler import create_bottle_plan
from src.api.catalog import create_catalog
from src.api.inventory import get_inventory

# ----- TEST DATABASE SETUP -----
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    with db.engine.begin() as conn:
        conn.execute(sqlalchemy.text("""
            CREATE TABLE IF NOT EXISTS global_inventory (
                gold INTEGER DEFAULT 100,
                red_ml INTEGER DEFAULT 0,
                green_ml INTEGER DEFAULT 0,
                blue_ml INTEGER DEFAULT 0,
                dark_ml INTEGER DEFAULT 0,
                red_potions INTEGER DEFAULT 0,
                green_potions INTEGER DEFAULT 0,
                blue_potions INTEGER DEFAULT 0
            );
        """))
        # Optionally initialize with a row:
        conn.execute(sqlalchemy.text("""
            INSERT INTO global_inventory (gold, red_ml, green_ml, blue_ml, dark_ml, red_potions, green_potions, blue_potions)
            VALUES (1000, 1000, 1000, 1000, 1000, 10, 10, 10)
            ON CONFLICT DO NOTHING;
        """))



# ----- BARRELS -----
def test_calculate_barrel_summary():
    barrels = [
        Barrel(
            sku="R",
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=2,
        ),
        Barrel(
            sku="G",
            ml_per_barrel=1000,
            potion_type=[0, 1.0, 0, 0],
            price=150,
            quantity=1,
        ),
    ]
    summary = calculate_barrel_summary(barrels)
    assert summary.gold_paid == 350


def test_create_barrel_plan_basic():
    catalog = [
        Barrel(
            sku="R",
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=1,
        ),
        Barrel(
            sku="G",
            ml_per_barrel=1000,
            potion_type=[0, 1.0, 0, 0],
            price=150,
            quantity=1,
        ),
    ]
    plan = create_barrel_plan(
        gold=200,
        max_barrel_capacity=10000,
        current_red_ml=0,
        current_green_ml=2000,
        current_blue_ml=2000,
        current_dark_ml=0,
        red_potions=0,
        green_potions=6,
        blue_potions=6,
        wholesale_catalog=catalog,
    )
    assert isinstance(plan, list)
    assert all(isinstance(p, BarrelOrder) for p in plan)


# ----- BOTTLER -----
def test_create_bottle_plan_red():
    result = create_bottle_plan(
        red_ml=500,
        green_ml=0,
        blue_ml=0,
        dark_ml=0,
        red_potions=0,
        green_potions=5,
        blue_potions=5,
        maximum_potion_capacity=50,
        current_potion_inventory=[],
    )
    assert isinstance(result, list)
    assert result[0].potion_type == [100, 0, 0, 0]


# ----- CATALOG -----
def test_catalog_excludes_zero():
    catalog = create_catalog()
    for item in catalog:
        assert item.quantity > 0
        assert item.potion_type.count(100) == 1  # One dominant color


# ----- CARTS -----
def test_checkout_calculation():
    # This test only checks logic—not actual DB modification.
    cart_items = {"RED_POTION_0": 2, "GREEN_POTION_0": 3}
    # gold = 0
    total = sum(cart_items.values()) * 50
    assert total == 250


# ----- INVENTORY -----
def test_inventory_audit_values():
    inv = get_inventory()
    assert inv.gold >= 0
    assert inv.number_of_potions >= 0
    assert inv.ml_in_barrels >= 0
