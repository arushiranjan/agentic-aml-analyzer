"""
generate_sample_data.py
------------------------
Creates sample_data/transactions.csv: a synthetic banking transaction
dataset with normal traffic PLUS deliberately injected suspicious
patterns so every rule in tools/rule_engine.py and tools/graph_intelligence.py
has something to find.

Includes two OPTIONAL columns (device_id, merchant_category) to
demonstrate the optional device_anomaly / merchant_anomaly rules, which
only activate when those columns are present in the uploaded CSV.

Run:  python sample_data/generate_sample_data.py
"""

import os
import random
import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

COUNTRIES = ["India", "UAE", "Singapore", "UK", "USA", "Nigeria"]
CHANNELS = ["NEFT", "IMPS", "UPI", "SWIFT", "RTGS", "Cash Deposit"]
MERCHANT_CATEGORIES = ["Groceries", "Utilities", "Travel", "Electronics", "Dining",
                        "Fuel", "Healthcare", "Entertainment", "Jewelry", "Crypto Exchange"]

START = pd.Timestamp("2025-01-01")
END = pd.Timestamp("2025-03-31")

rows = []
txn_counter = 1


def add_txn(customer_id, beneficiary_id, amount, timestamp, country=None, channel=None,
            device_id=None, merchant_category=None):
    global txn_counter
    rows.append({
        "transaction_id": f"T{txn_counter:06d}",
        "customer_id": customer_id,
        "beneficiary_id": beneficiary_id,
        "amount": round(amount, 2),
        "timestamp": timestamp,
        "country": country or random.choice(COUNTRIES),
        "channel": channel or random.choice(CHANNELS),
        "device_id": device_id or f"DEV-{random.randint(1, 3):02d}-{customer_id}",
        "merchant_category": merchant_category or random.choice(MERCHANT_CATEGORIES),
    })
    txn_counter += 1


def random_timestamp():
    delta = END - START
    return START + pd.Timedelta(seconds=random.randint(0, int(delta.total_seconds())))


# ---------------------------------------------------------------- 1. Normal customers (C001-C150)
normal_customers = [f"C{i:03d}" for i in range(1, 151)]
for cust in normal_customers:
    n_txns = random.randint(3, 25)
    for _ in range(n_txns):
        beneficiary = f"B{random.randint(1, 300):03d}"
        amount = np.random.gamma(shape=2.0, scale=8000)
        add_txn(cust, beneficiary, amount, random_timestamp())

# ---------------------------------------------------------------- 2. Structuring (C901, C902)
for cust in ["C901", "C902"]:
    base_time = random_timestamp()
    for i in range(18):
        beneficiary = f"B{random.randint(400, 407):03d}"
        amount = random.uniform(8500, 9950)  # just under 10,000 threshold
        ts = base_time + pd.Timedelta(minutes=i)
        add_txn(cust, beneficiary, amount, ts)

# ---------------------------------------------------------------- 3. High velocity / rapid P2P (C903)
base_time = random_timestamp()
for i in range(9):
    beneficiary = f"B{random.randint(500, 510):03d}"
    amount = random.uniform(2000, 6000)
    ts = base_time + pd.Timedelta(minutes=i * 5)
    add_txn("C903", beneficiary, amount, ts)

# ---------------------------------------------------------------- 4. Layering + money mule (C904 -> C905 -> C906)
base_time = random_timestamp()
add_txn("C800", "C904", 500000, base_time)
add_txn("C904", "C905", 480000, base_time + pd.Timedelta(minutes=20))
add_txn("C905", "C906", 460000, base_time + pd.Timedelta(minutes=45))
add_txn("C904", "C907", 15000, base_time + pd.Timedelta(minutes=30))
add_txn("C904", "C908", 12000, base_time + pd.Timedelta(minutes=50))

# ---------------------------------------------------------------- 5. Circular transfers (C910 -> C911 -> C912 -> C910)
base_time = random_timestamp()
add_txn("C910", "C911", 250000, base_time)
add_txn("C911", "C912", 240000, base_time + pd.Timedelta(hours=1))
add_txn("C912", "C910", 230000, base_time + pd.Timedelta(hours=2))

# ---------------------------------------------------------------- 6. Dormant then active (C920)
add_txn("C920", "B600", 5000, pd.Timestamp("2025-01-05"))
base_time = pd.Timestamp("2025-03-20")
for i in range(6):
    add_txn("C920", f"B60{i}", random.uniform(20000, 90000), base_time + pd.Timedelta(hours=i))

# ---------------------------------------------------------------- 7. Large amount anomaly (C930)
for _ in range(10):
    add_txn("C930", f"B{random.randint(700, 710):03d}", random.uniform(3000, 9000), random_timestamp())
add_txn("C930", "B999", 950000, random_timestamp())  # sudden huge outlier

# ---------------------------------------------------------------- 8. Unusual recipient count / hub account (C940)
base_time = random_timestamp()
for i in range(12):
    add_txn("C940", f"B{800+i:03d}", random.uniform(5000, 15000), base_time + pd.Timedelta(hours=i))

# ---------------------------------------------------------------- 9. Transaction burst at an odd hour (C950)
base_time = pd.Timestamp("2025-02-10 02:00:00")  # 2 AM
for i in range(7):
    add_txn("C950", f"B{random.randint(900, 910):03d}", random.uniform(1000, 4000),
            base_time + pd.Timedelta(seconds=i * 40))

# ---------------------------------------------------------------- 10. Geo anomaly (C960): 4 countries in <2 hours
base_time = random_timestamp()
geo_sequence = ["India", "UAE", "Singapore", "Nigeria"]
for i, country in enumerate(geo_sequence):
    add_txn("C960", f"B{950+i:03d}", random.uniform(20000, 60000),
            base_time + pd.Timedelta(minutes=i * 30), country=country)

# ---------------------------------------------------------------- 11. Device anomaly (C970): 5 distinct devices
base_time = random_timestamp()
for i in range(6):
    add_txn("C970", f"B{960+i:03d}", random.uniform(5000, 15000),
            base_time + pd.Timedelta(hours=i), device_id=f"DEV-{i:02d}-C970")

# ---------------------------------------------------------------- 12. Merchant anomaly (C980): 6 unrelated categories fast
base_time = random_timestamp()
for i, cat in enumerate(["Jewelry", "Crypto Exchange", "Electronics", "Travel", "Fuel", "Healthcare"]):
    add_txn("C980", f"B{970+i:03d}", random.uniform(8000, 20000),
            base_time + pd.Timedelta(hours=i), merchant_category=cat)

df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)

os.makedirs(os.path.dirname(__file__), exist_ok=True)
out_path = os.path.join(os.path.dirname(__file__), "transactions.csv")
df.to_csv(out_path, index=False)
print(f"Wrote {len(df)} transactions to {out_path}")
