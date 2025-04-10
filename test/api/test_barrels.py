from unittest.mock import patch
from src.api.barrels import (
    calculate_barrel_summary,
    create_barrel_plan,
    Barrel,
    BarrelOrder,
)
from typing import List


def test_barrel_delivery() -> None:
    delivery: List[Barrel] = [
        Barrel(
            item_sku="SMALL_RED_BARREL",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0],
            price=100,
            quantity=10,
        ),
        Barrel(
            item_sku="SMALL_GREEN_BARREL",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[0, 1.0, 0],
            price=150,
            quantity=5,
        ),
    ]

    delivery_summary = calculate_barrel_summary(delivery)
    assert delivery_summary.gold_paid == 1750


@patch("src.api.barrels.random.choice", return_value="red")  # 👈 This is the patch
def test_buy_small_red_barrel_plan(mock_choice) -> None:
    wholesale_catalog: List[Barrel] = [
        Barrel(
            item_sku="SMALL_RED_BARREL",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0],
            price=100,
            quantity=10,
        ),
        Barrel(
            item_sku="SMALL_GREEN_BARREL",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[0, 1.0, 0],
            price=150,
            quantity=5,
        ),
        Barrel(
            item_sku="SMALL_BLUE_BARREL",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[0, 0, 1.0],
            price=500,
            quantity=2,
        ),
    ]

    gold = 100
    max_barrel_capacity = 10000
    current_red_ml = 0
    current_green_ml = 1000
    current_blue_ml = 1000
    red_potions = 0
    green_potions = 0
    blue_potions = 0

    barrel_orders = create_barrel_plan(
        gold,
        max_barrel_capacity,
        current_red_ml,
        current_green_ml,
        current_blue_ml,
        red_potions,
        green_potions,
        blue_potions,
        wholesale_catalog,
    )

    assert isinstance(barrel_orders, list)
    assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
    assert len(barrel_orders) > 0
    assert barrel_orders[0].item_sku == "SMALL_RED_BARREL"  # Changed from sku to item_sku
    assert barrel_orders[0].quantity == 1


def test_cant_afford_barrel_plan() -> None:
    wholesale_catalog: List[Barrel] = [
        Barrel(
            item_sku="SMALL_RED_BARREL",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0],
            price=100,
            quantity=10,
        ),
        Barrel(
            item_sku="SMALL_GREEN_BARREL",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[0, 1.0, 0],
            price=150,
            quantity=5,
        ),
        Barrel(
            item_sku="SMALL_BLUE_BARREL",  # Changed from sku to item_sku
            ml_per_barrel=1000,
            potion_type=[0, 0, 1.0],
            price=500,
            quantity=2,
        ),
    ]

    gold = 50
    max_barrel_capacity = 10000
    current_red_ml = 0
    current_green_ml = 1000
    current_blue_ml = 1000
    red_potions = 0
    green_potions = 0
    blue_potions = 0

    barrel_orders = create_barrel_plan(
        gold,
        max_barrel_capacity,
        current_red_ml,
        current_green_ml,
        current_blue_ml,
        red_potions,
        green_potions,
        blue_potions,
        wholesale_catalog,
    )

    assert isinstance(barrel_orders, list)
    assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
    assert len(barrel_orders) == 0
