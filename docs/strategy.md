# Strategy for a Profitable Potion Shop - Version 4

## Step 1: Define Your Strategy

To develop the most profitable potion shop, we propose the following three hypotheses based on observed customer behavior and operational bottlenecks:

### Hypothesis 1: Customers Prefer Red Potions, But We Are Often Out of Stock
Red potions are consistently the most purchased item, but we frequently run out of inventory. We hypothesize that increasing red potion production during low-inventory periods and prioritizing red barrels in our `/plan` endpoint will boost total revenue.

### Hypothesis 2: Bottling Efficiency Can Be Improved by Avoiding ML Waste
Currently, partial leftover ml amounts (e.g., 45 ml of blue) go unused if they can’t make a full potion. We hypothesize that tracking and minimizing leftover ml through smarter potion planning will reduce waste and increase the number of potions bottled, thereby boosting profit.

### Hypothesis 3: Customers Buy More Potions When the Catalog Has More Variety
We hypothesize that having at least 3 different potion types in stock (e.g., red, green, and blue) correlates with higher average cart totals. If the catalog only contains 1–2 potion types, we suspect customers purchase fewer items overall.

---

## Step 2: Design Your Experiments

### Hypothesis 1: Prioritizing Red Potions

- **Metric**: Daily revenue from red potions
- **Method**:
  - Log how many red potions are sold each day.
  - Compare revenue during periods when red potions are frequently stocked vs. frequently out of stock.
  - Use a moving average to track trends.

### Hypothesis 2: Reducing ML Waste

- **Metric**: Average leftover ml after bottling events
- **Method**:
  - Track the ml used and leftover for each color in every bottling run.
  - Calculate leftover-to-used ratio per bottling event.
  - Aim to reduce the average leftover ml per event over time.

### Hypothesis 3: Catalog Variety Impact

- **Metric**: Average cart value based on catalog potion variety
- **Method**:
  - Track how many potion types were listed in the catalog at checkout time.
  - Group checkouts by potion variety and calculate the average cart total.
  - Look for a correlation between higher variety and higher spending.

---

## Step 3: Instrumentation Added

To track the above hypotheses, we added the following tables and logs:

### 1. `bottling_logs`
```sql
CREATE TABLE bottling_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    red_ml_used INTEGER DEFAULT 0,
    green_ml_used INTEGER DEFAULT 0,
    blue_ml_used INTEGER DEFAULT 0,
    dark_ml_used INTEGER DEFAULT 0,
    total_potions_bottled INTEGER NOT NULL,
    potion_type TEXT NOT NULL
);

- Used in /bottler/deliver to log each bottling event.
- Helps us calculate ml efficiency and potion output.

### 2. `checkout_logs`
```sql
CREATE TABLE checkout_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cart_id INTEGER NOT NULL,
    gold_spent INTEGER NOT NULL,
    red_qty INTEGER DEFAULT 0,
    green_qty INTEGER DEFAULT 0,
    blue_qty INTEGER DEFAULT 0,
    dark_qty INTEGER DEFAULT 0,
    catalog_variety INTEGER NOT NULL
);

- Logged at /checkout time.
- Stores the number of potion types available in the catalog at checkout and quantities bought.
- Helps us correlate catalog variety with gold spent.

### 3. `catalog_snapshots`
```sql
CREATE TABLE catalog_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    red_available BOOLEAN,
    green_available BOOLEAN,
    blue_available BOOLEAN,
    dark_available BOOLEAN
);

## Step 4: Analytics Queries

### Query 1: Red Potion Revenue Trend
```sql
SELECT
    DATE(timestamp) AS day,
    SUM(red_qty * 50) AS red_revenue
FROM checkout_logs
GROUP BY day
ORDER BY day;

### Query 2: Average ML Leftover per Bottling
```sql
SELECT
    AVG((red_ml_used + green_ml_used + blue_ml_used + dark_ml_used) % 50) AS avg_leftover_ml
FROM bottling_logs;

### Query 2: Average Cart Value by Catalog Variety
```sql
SELECT
    catalog_variety,
    AVG(gold_spent) AS avg_cart_value
FROM checkout_logs
GROUP BY catalog_variety
ORDER BY catalog_variety;
