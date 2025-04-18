from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import sqlalchemy
from enum import Enum
from typing import List, Optional
from datetime import datetime
from src import database as db
from src.api import auth

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

# ----- ENUMS -----
class SearchSortOptions(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"


class SearchSortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


# ----- MODELS -----
class LineItem(BaseModel):
    line_item_id: int
    item_sku: str
    customer_name: str
    line_item_total: int
    timestamp: str


class SearchResponse(BaseModel):
    previous: Optional[str] = None
    next: Optional[str] = None
    results: List[LineItem]


@router.get("/search/", response_model=SearchResponse, tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: SearchSortOptions = SearchSortOptions.timestamp,
    sort_order: SearchSortOrder = SearchSortOrder.desc,
):
    with db.engine.begin() as connection:
        results = connection.execute(
            sqlalchemy.text(f"""
                SELECT ci.id, c.customer_name, ci.item_sku, ci.quantity * ci.unit_price AS line_item_total, ci.timestamp
                FROM cart_items ci
                JOIN carts c ON ci.cart_id = c.customer_id  -- Changed to customer_id
                WHERE c.customer_name ILIKE :customer_name
                AND ci.item_sku ILIKE :potion_sku
                ORDER BY {sort_col.value} {sort_order.value.upper()}
                LIMIT 50
            """),
            {"customer_name": f"%{customer_name}%", "potion_sku": f"%{potion_sku}%"},
        ).fetchall()

        # Handling the case where no results are found gracefully
        if not results:
            return SearchResponse(previous=None, next=None, results=[])

        return SearchResponse(
            previous=None,
            next=None,
            results=[
                LineItem(
                    line_item_id=row.id,
                    item_sku=row.item_sku,
                    customer_name=row.customer_name,
                    line_item_total=row.line_item_total,
                    timestamp=row.timestamp.isoformat(),
                )
                for row in results
            ],
        )


class Customer(BaseModel):
    customer_id: str
    customer_name: str
    character_class: str
    level: int = Field(ge=1, le=20)


class CartCreateResponse(BaseModel):
    customer_id: int


@router.post("/", response_model=CartCreateResponse)
def create_cart(new_cart: Customer):
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("""
                INSERT INTO carts (customer_id, customer_name, character_class, level)
                VALUES (:cid, :cname, :cclass, :level)
                RETURNING customer_id
            """),
            {
                "cid": new_cart.customer_id,
                "cname": new_cart.customer_name,
                "cclass": new_cart.character_class,
                "level": new_cart.level,
            },
        )

        customer_id = result.scalar_one_or_none()

    if customer_id is None:
        raise HTTPException(status_code=500, detail="Failed to create cart")

    return CartCreateResponse(customer_id=customer_id)


class CartItem(BaseModel):
    quantity: int = Field(ge=1, description="Quantity must be at least 1")


@router.post("/{cart_id}/items/{item_sku}", status_code=status.HTTP_204_NO_CONTENT)
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("""
                INSERT INTO cart_items (cart_id, item_sku, quantity, timestamp)
                SELECT :cid, :sku, :qty, :now
                FROM carts c WHERE c.customer_id = :cid  -- Change to use customer_id instead of cart_id
                ON CONFLICT (cart_id, item_sku) DO UPDATE
                SET quantity = EXCLUDED.quantity,
                    timestamp = EXCLUDED.timestamp
            """),
            {
                "cid": cart_id,
                "sku": item_sku,
                "qty": cart_item.quantity,
                "now": datetime.utcnow(),  # Ensure this gets set properly
            },
        )


class CheckoutResponse(BaseModel):
    total_potions_bought: int
    total_gold_paid: int


class CartCheckout(BaseModel):
    payment: str


@router.post("/{cart_id}/checkout", response_model=CheckoutResponse)
def checkout(cart_id: int, cart_checkout: CartCheckout):
    with db.engine.begin() as connection:
        items = connection.execute(
            sqlalchemy.text("""
                SELECT item_sku, quantity, quantity * unit_price AS line_item_total
                FROM cart_items
                WHERE cart_id = :cart_id
            """),
            {"cart_id": cart_id},
        ).fetchall()

        if not items:
            raise HTTPException(status_code=404, detail="Cart not found or empty")

        total_potions = sum(item.quantity for item in items)
        total_gold = sum(item.line_item_total for item in items)

        connection.execute(
            sqlalchemy.text("""
                UPDATE global_inventory
                SET gold = gold + :total_gold
            """),
            {"total_gold": total_gold},
        )

        for item in items:
            # Adjust potion type handling here based on the item_sku
            if item.item_sku.startswith("RED"):
                connection.execute(
                    sqlalchemy.text("""
                        UPDATE global_inventory
                        SET red_potions = red_potions - :qty
                    """),
                    {"qty": item.quantity},
                )
            elif item.item_sku.startswith("GREEN"):
                connection.execute(
                    sqlalchemy.text("""
                        UPDATE global_inventory
                        SET green_potions = green_potions - :qty
                    """),
                    {"qty": item.quantity},
                )
            elif item.item_sku.startswith("BLUE"):
                connection.execute(
                    sqlalchemy.text("""
                        UPDATE global_inventory
                        SET blue_potions = blue_potions - :qty
                    """),
                    {"qty": item.quantity},
                )

    return CheckoutResponse(
        total_potions_bought=total_potions,
        total_gold_paid=total_gold,
    )
