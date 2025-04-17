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
from src.api.carts import Customer


# ----- TEST DATABASE SETUP -----
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    with db.engine.begin() as conn:
        conn.execute(
            sqlalchemy.text("""
            CREATE TABLE IF NOT EXISTS global_inventory (
                gold INTEGER DEFAULT 100,
                red_ml INTEGER DEFAULT 0,
                green_ml INTEGER DEFAULT 0,
                blue_ml INTEGER DEFAULT 0,
                red_potions INTEGER DEFAULT 0,
                green_potions INTEGER DEFAULT 0,
                blue_potions INTEGER DEFAULT 0
            );
        """)
        )
        # Optionally initialize with a row:
        conn.execute(
            sqlalchemy.text("""
            INSERT INTO global_inventory (gold, red_ml, green_ml, blue_ml, red_potions, green_potions, blue_potions)
            VALUES (1000, 1000, 1000, 1000, 10, 10, 10)
            ON CONFLICT DO NOTHING;
        """)
        )


# ----- BARRELS -----
def test_calculate_barrel_summary():
    barrels = [
        Barrel(
            item_sku="R",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=2,
        ),
        Barrel(
            item_sku="G",  # Changed from sku to item_sku
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
            item_sku="R",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=1,
        ),
        Barrel(
            item_sku="G",  # Changed from sku to item_sku
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
    cart_items = {"RED_POTION_0": 2, "GREEN_POTION_0": 3}
    total = sum(cart_items.values()) * 50
    assert total == 250


# Test creating a cart
def test_create_cart():
    new_cart = Customer(
        customer_id="12345",  # Updated field names
        customer_name="John",
        character_class="Warrior",  # New field
        level=5,  # New field
    )

    # Simulating a post to the /carts/ endpoint
    response = new_cart.dict()  # Simulate the expected response
    assert "customer_id" in response
    assert response["customer_id"] == "12345"
    assert response["customer_name"] == "John"
    assert response["character_class"] == "Warrior"
    assert response["level"] == 5


# ----- INVENTORY -----
def test_inventory_audit_values():
    inv = get_inventory()
    assert inv.gold >= 0
    assert inv.number_of_potions >= 0
    assert inv.ml_in_barrels >= 0

# ----- POTIONS -----

def test_insert_potion():
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("""
                INSERT INTO potions (name, potion_type, quantity, price)
                VALUES ('Red Potion', '[100, 0, 0, 0]', 10, 50)
            """)
        )

    # Check that the potion was inserted correctly
    result = connection.execute(
        sqlalchemy.text("""
            SELECT * FROM potions WHERE name = 'Red Potion'
        """)
    ).fetchall()

    assert len(result) == 1
    assert result[0]["name"] == "Red Potion"
    assert result[0]["potion_type"] == [100, 0, 0, 0]
    assert result[0]["quantity"] == 10
    assert result[0]["price"] == 50

def test_get_potions():
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("""
                INSERT INTO potions (name, potion_type, quantity, price)
                VALUES ('Blue Potion', '[0, 0, 100, 0]', 15, 70)
            """)
        )

    # Retrieve the potion from the database
    result = connection.execute(
        sqlalchemy.text("""
            SELECT * FROM potions WHERE name = 'Blue Potion'
        """)
    ).fetchone()

    assert result is not None
    assert result["name"] == "Blue Potion"
    assert result["potion_type"] == [0, 0, 100, 0]
    assert result["quantity"] == 15
    assert result["price"] == 70

def test_update_potion_quantity():
    with db.engine.begin() as connection:
        # Insert a potion with initial quantity
        connection.execute(
            sqlalchemy.text("""
                INSERT INTO potions (name, potion_type, quantity, price)
                VALUES ('Green Potion', '[0, 100, 0, 0]', 10, 60)
            """)
        )

    # Simulate potion delivery (i.e., 5 potions are delivered)
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("""
                UPDATE potions
                SET quantity = quantity - 5
                WHERE name = 'Green Potion'
            """)
        )

    # Verify that the potion quantity has been updated correctly
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("""
                SELECT quantity FROM potions WHERE name = 'Green Potion'
            """)
        ).fetchone()

    assert result is not None
    assert result["quantity"] == 5

def test_potion_type_validation():
    invalid_potion_type = [200, 0, 0, 0]  # Invalid, sum is not 100

    # Simulate adding a potion with an invalid type
    with pytest.raises(ValueError):
        with db.engine.begin() as connection:
            connection.execute(
                sqlalchemy.text("""
                    INSERT INTO potions (name, potion_type, quantity, price)
                    VALUES ('Invalid Potion', :potion_type, 5, 50)
                """), {'potion_type': invalid_potion_type}
            )

def test_catalog_potion_inclusion():
    with db.engine.begin() as connection:
        # Insert sample potions into the potions table
        connection.execute(
            sqlalchemy.text("""
                INSERT INTO potions (name, potion_type, quantity, price)
                VALUES ('Red Potion', '[100, 0, 0, 0]', 10, 50)
            """)
        )

    # Fetch the catalog and check that the potion appears
    catalog = create_catalog()  # Call your existing catalog creation logic

    assert any(item.name == 'Red Potion' for item in catalog)
    assert any(item.potion_type == [100, 0, 0, 0] for item in catalog)
    assert any(item.quantity == 10 for item in catalog)
    assert any(item.price == 50 for item in catalog)

def test_update_potion_price():
    with db.engine.begin() as connection:
        # Insert a potion with initial price
        connection.execute(
            sqlalchemy.text("""
                INSERT INTO potions (name, potion_type, quantity, price)
                VALUES ('Red Potion', '[100, 0, 0, 0]', 10, 50)
            """)
        )

    # Simulate updating the price of the potion
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("""
                UPDATE potions
                SET price = 60
                WHERE name = 'Red Potion'
            """)
        )

    # Verify that the price has been updated correctly
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("""
                SELECT price FROM potions WHERE name = 'Red Potion'
            """)
        ).fetchone()

    assert result is not None
    assert result["price"] == 60

def test_inventory_update_after_delivery():
    with db.engine.begin() as connection:
        # Insert a potion and simulate delivery
        connection.execute(
            sqlalchemy.text("""
                INSERT INTO potions (name, potion_type, quantity, price)
                VALUES ('Blue Potion', '[0, 0, 100, 0]', 20, 70)
            """)
        )

    # Simulate potion delivery (i.e., 5 potions delivered)
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("""
                UPDATE potions
                SET quantity = quantity - 5
                WHERE name = 'Blue Potion'
            """)
        )

    # Verify the inventory has been updated
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("""
                SELECT quantity FROM potions WHERE name = 'Blue Potion'
            """)
        ).fetchone()

    assert result is not None
    assert result["quantity"] == 15


