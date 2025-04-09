CREATE TABLE IF NOT EXISTS global_inventory (
    gold INTEGER DEFAULT 100,
    red_ml INTEGER DEFAULT 0,
    green_ml INTEGER DEFAULT 0,
    blue_ml INTEGER DEFAULT 0,
    red_potions INTEGER DEFAULT 0,
    green_potions INTEGER DEFAULT 0,
    blue_potions INTEGER DEFAULT 0
);

DELETE FROM global_inventory;

INSERT INTO global_inventory (
    gold, red_ml, green_ml, blue_ml,
    red_potions, green_potions, blue_potions
) VALUES (
    1000, 1000, 1000, 1000,
    10, 10, 10
);
