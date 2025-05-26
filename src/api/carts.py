from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from uuid import UUID
import sqlalchemy
from typing import List
from datetime import datetime
from src import database as db
from src.api import auth
from enum import Enum
from typing import Optional

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class CartItem(BaseModel):
    sku: str
    quantity: int = Field(ge=1)

class CartCheckout(BaseModel):
    order_id: UUID
    payment: str

class CheckoutResponse(BaseModel):
    total_potions_bought: int
    total_gold_paid: int

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_cart():
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("""
                INSERT INTO carts DEFAULT VALUES
                RETURNING cart_id
            """)
        ).mappings().first()
    return {"cart_id": result["cart_id"]}

@router.post("/{cart_id}/items", status_code=status.HTTP_204_NO_CONTENT)
def add_cart_items(cart_id: int, items: List[CartItem]):
    with db.engine.begin() as connection:
        for item in items:
            connection.execute(
                sqlalchemy.text("""
                    INSERT INTO cart_items (cart_id, item_sku, quantity, timestamp)
                    VALUES (:cart_id, :sku, :qty, :now)
                    ON CONFLICT (cart_id, item_sku) DO UPDATE
                    SET quantity = cart_items.quantity + EXCLUDED.quantity,
                        timestamp = EXCLUDED.timestamp
                """),
                {"cart_id": cart_id, "sku": item.sku, "qty": item.quantity, "now": datetime.utcnow()}
            )

@router.post("/{cart_id}/checkout", response_model=CheckoutResponse)
def checkout(cart_id: int, cart_checkout: CartCheckout):
    with db.engine.begin() as connection:
        # Check if this order_id was already processed
        existing = connection.execute(
            sqlalchemy.text("""
                SELECT response FROM executed_orders WHERE order_id = :oid
            """),
            {"oid": str(cart_checkout.order_id)}
        ).scalar_one_or_none()

        if existing:
            return CheckoutResponse(**existing)

        items = connection.execute(
            sqlalchemy.text("""
                SELECT item_sku, quantity
                FROM cart_items
                WHERE cart_id = :cid
            """),
            {"cid": cart_id}
        ).mappings().all()

        if not items:
            raise HTTPException(status_code=400, detail="Cart is empty or does not exist.")

        sku_to_price = {
            "RED_POTION_0": 50,
            "GREEN_POTION_0": 60,
            "BLUE_POTION_0": 70,
            "DARK_POTION_0": 80,
        }

        ledger_entries = []
        total_gold = 0
        total_potions = 0

        for item in items:
            price = sku_to_price.get(item["item_sku"])
            if price is None:
                raise HTTPException(status_code=400, detail=f"Invalid SKU {item['item_sku']}")

            total_gold += price * item["quantity"]
            total_potions += item["quantity"]

            ledger_entries.append({
                "resource": item["item_sku"].replace("_POTION_0", "_potion").lower(),
                "change": -item["quantity"],
                "context": f"checkout {cart_id}"
            })

        # Get current gold
        gold = connection.execute(
            sqlalchemy.text("""
                SELECT COALESCE(SUM(change), 0)
                FROM ledger_entries
                WHERE resource = 'gold'
            """)
        ).scalar_one()

        if gold < total_gold:
            raise HTTPException(status_code=400, detail="Not enough gold.")

        ledger_entries.append({
            "resource": "gold",
            "change": -total_gold,
            "context": f"checkout {cart_id}"
        })

        for entry in ledger_entries:
            connection.execute(
                sqlalchemy.text("""
                    INSERT INTO ledger_entries (resource, change, context)
                    VALUES (:resource, :change, :context)
                """),
                entry
            )

    # Log to checkout_logs
        connection.execute(
            sqlalchemy.text("""
                INSERT INTO checkout_logs (total_potions, total_gold, timestamp)
                VALUES (:total_potions, :total_gold, NOW())
            """),
            {
                "total_potions": total_potions,
                "total_gold": total_gold,
            }
        )


        response = {
            "total_potions_bought": total_potions,
            "total_gold_paid": total_gold
        }

        connection.execute(
            sqlalchemy.text("""
                INSERT INTO executed_orders (order_id, response)
                VALUES (:oid, :response::jsonb)
            """),
            {"oid": str(cart_checkout.order_id), "response": json.dumps(response)}
        )

        connection.execute(
            sqlalchemy.text("DELETE FROM cart_items WHERE cart_id = :cid"),
            {"cid": cart_id}
        )

        connection.execute(
            sqlalchemy.text("DELETE FROM carts WHERE cart_id = :cid"),
            {"cid": cart_id}
        )

    return CheckoutResponse(**response)

class SearchSortOptions(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class SearchSortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

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

@router.get("/search/", response_model=SearchResponse)
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
                SELECT ci.id AS line_item_id,
                       ci.item_sku,
                       c.customer_name,
                       (ci.quantity * ci.unit_price) AS line_item_total,
                       ci.timestamp
                FROM cart_items ci
                JOIN carts c ON ci.cart_id = c.cart_id
                WHERE c.customer_name ILIKE :customer_name
                  AND ci.item_sku ILIKE :potion_sku
                ORDER BY {sort_col.value} {sort_order.value}
                LIMIT 50
            """),
            {
                "customer_name": f"%{customer_name}%",
                "potion_sku": f"%{potion_sku}%",
            }
        ).mappings().all()

    return SearchResponse(
        previous=None,
        next=None,
        results=[
            LineItem(
                line_item_id=row["line_item_id"],
                item_sku=row["item_sku"],
                customer_name=row["customer_name"],
                line_item_total=row["line_item_total"],
                timestamp=row["timestamp"].isoformat()
            )
            for row in results
        ]
    )
