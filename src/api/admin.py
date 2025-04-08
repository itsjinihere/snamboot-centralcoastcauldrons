from fastapi import APIRouter, Depends, status
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset():
    """
    Reset the game state. Gold goes to 100, all potion and ml quantities 
    are reset to 0, and all carts and cart items are deleted.
    """
    with db.engine.begin() as connection:
        # Reset inventory
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory
                SET
                    gold = 100,
                    red_ml = 0,
                    green_ml = 0,
                    blue_ml = 0,
                    dark_ml = 0,
                    red_potions = 0,
                    green_potions = 0,
                    blue_potions = 0
                """
            )
        )

        # Clear cart-related data
        connection.execute(sqlalchemy.text("DELETE FROM cart_items"))
        connection.execute(sqlalchemy.text("DELETE FROM carts"))