"""
Purpose:
    Generate realistic synthetic CSV see data for the FactoryMind OLTP schema.
    These CSVs are intended to be bulk-loaded into Azure SQL using data/seed_database.py.

What this script creates:
    - users.csv
    - equipment.csv
    - work_orders.csv
    - parts_usage.csv
    - sensor_events.csv
    - query_logs.csv

Why this script matters:
    - Gives the ASP.NET Core application realistic data to render in dashboards/tables.
    - Creates enough maintenance history for analytics and ML experimentation.
    - Preserves chronological work order timestamps so you can later do a proper time-base train/test split for predictive maintenance modeling.
"""

import os
import random
from datetime import datetime, timedelta
from sre_constants import FAILURE

import numpy as np
import pandas as pd
from faker import Faker

# ==============================================================
# Global Setup
# ==============================================================

# Faker generates realistic names, emails, short text, and timestamps.
fake = Faker()

# NumPy has a modern random generator used for reproducible numeric simulation.
rand_num_gen = np.random.default_rng(seed=42)

# Seed Python's built-in random module so random.choice/random.choices
# Produce the same results on each run
random.seed(42)


# ===============================================================
# Output Location
# ===============================================================

# Exports folder is created automatically if it does not exist.
EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)


# ===============================================================
# Project-Specific Constants
# ===============================================================

# Roles are repeated to infuence the distribution toward Operators and Technicians, with fewer Supervisors.
ROLES = ["Operator", "Operator", "Technician", "Technician", "Supervisor"]

# Approximate row counts

N_USERS = 30
N_EQUIPMENT = 30
TOTAL_WO = 6500

# Work orders and sensor data are generated across a multi-year window to create historical depth for analytics, time-series features, and ML.
WO_START = datetime(2023, 1, 1)
WO_END = datetime(2025, 12, 31)

# Failure categories are designed to feel realistic for an automotive plant or industrial maintenance environment.
FAILURE_TYPES = [
    "Mechanical Wear",
    "Electrical Fault",
    "Hydraulic Leak",
    "Overheating",
    "Sensor Malfunction",
    "Software Error",
    "Vibration Damage",
    "Corrosion",
    "Lubrication Failure",
    ]

# Priority levels commonly used in maintenance systems.
PRIORITIES = ["Low", "Medium", "High", "Critical"]

# Weighted distribution so Medium/High are most common and Critical is rarer.
PRIORITY_WEIGHTS = [0.20, 0.45, 0.25, 0.10]

# Machine/equipment types for manufacturing floor setting
EQUIPMENT_TYPES = [
    "CNC Milling Machine",
    "Robotic Welding Arm",
    "Hydraulic Press",
    "Paint Booth Conveyor",
    "Body Assembly Robot",
    "Stamping Press",
    "Engine Mounting Station",
    "Axle Assembly Line",
    "Torque Wrench System",
    "Quality Inspection Camera",
    "Overhead Crane",
    "Parts Conveyor Belt",
    "Laser Cutting Machine",
    "Spot Welder",
    "Chassis Frame Jig",
]

# Common industrial manufacturers/brands to make the equipment table feel less generic.
MANUFACTURERS = [
    "KUKA",
    "Fanuc",
    "ABB",
    "Siemens",
    "Bosch",
    "Atlas Copco",
    "Trumpf",
    "Kawasaki",
    ]

# Parts used during work orders. These support dowstream spend calculations, parts-cost analytics, and feature engineering such as total_parts_cost_ytd.
PART_NAMES = [
    "Drive Belt",
    "Hydraulic Seal Kit",
    "Motor Bearing",
    "Servo Drive Unit",
    "Coolant Pump",
    "Pressure Sensor",
    "Encoder Module",
    "Power Supply Unit",
    "Relay Switch",
    "Pneumatic Valve",
    "Gear Assembly",
    "Filter Cartridge",
    "Control Board",
    "Proximity Sensor",
    "Actuator Rod",
]

# Simulated user interaction / audit log actions for the Query_Logs table.
QUERY_ACTIONS = [
    "VIEW_EQUIPMENT_LIST",
    "VIEW_WORK_ORDER",
    "RUN_ANALYTICS_REPORT",
    "SEARCH_PARTS",
    "EXPORT_CSV",
    "VIEW_SENSOR_FEED",
    "RUN_ML_PREDICTION",
    "UPDATE_WORK_ORDER",
    "VIEW_OEE_DASHBOARD",
    "SEARCH_DOCUMENT",
]

# ==============================================================
# 1. Users
# ==============================================================

def generate_users(n:int) -> pd.DataFrame:
    """
    Create synthetic user records for the Users table.

    Design notes:
        - User_ID is explicityl included so the CSV is easy to inspect and bulk-load.
        - Emails use an internal-looking domain
        - Create_At is placed 2-4 years in the past to avoid every account looking newly created.
        - Is_Active is mostly 1 so the app has a realistic majority of active users.
    """

    records = []

    for i in range (1, n + 1):
        role = random.choice(ROLES)
        fname = fake.first_name()
        lname = fake.last_name()

        records.append({
            "User_ID": i,
            "First_Name": fname,
            "Last_Name": lname,
            "Email": f"{fname.lower()}.{lname.lower()}{i}@factory.com",
            "Role": role,
            "Created_At": fake.date_time_between(
                start_date="-4y",
                end_date="-2y"
                ).strftime("%Y-%m-%d %H:%M:%S"),
            "Is_Active": random.choices([1,0], weights = [0.90, 0.10])[0],
            })
    return pd.DataFrame(records)


# ==============================================================
# 2. Equipment
# ==============================================================

def generate_equipment(n:int) -> pd.DataFrame:
    """
    Create synthetic equipment records for the Equipment table.

    Design notes:
        - Equipment names are unique and human-readable.
        - Install dates span several years so you can derive equipment_age_days later.
        - Status is biased toward Active because most plant assets are operational.
        - BlobUrl is intentionally left null becuase Azure Blob Storage image uploads are a later concern, not part of initial data seeding.
    """
    
    records = []
    used_names = set()

    for i in range(1, n + 1):
        base = random.choice(EQUIPMENT_TYPES)
        name - f"{base} #{i:03d}"

        # Extra safety in case a generated name somehow collides.
        while name in used_names:
            name = f"{base} #{i:03d}-{random.randint(1, 9)}"
            used_names.add(name)

            install = fake.date_time_between(start_date = "-8y", end_date = "-1y")

            records.append({
                "Equipment_ID": i,
                "Name": name,
                "Type": base,
                "Manufacturer:": random.choice(MANUFACTURERS),
                "Model_Number": f"MDL-{rand_num_gen.integers(1000, 9999)}",
                "Serial_Nummber": f"SN-{fake.bothify('??####??').upper()}",
                "Location": random.choice([
                    "Paint Shop",
                    "Body Shop",
                    "Assembly Line A",
                    "Assembly Line B",
                    "Stamping Hall",
                    "Quality Control",
                    "Logistics Bay",
                    "Maintenance Depot",
                    ]),
                "Install_Date": install.strftime("%Y-%m-%d"),
                "Status": random.choices(
                    ["Active", "Active", "Active", "Under Maintenance", "Decommissioned"],
                    weights = [0.70, 0.10, 0.05, 0.12, 0.03],
                    )[0],
                "BlobUrl": None,
                })
    return pd.DataFrame(records)

# ==============================================================
# 3. Work Orders
# ==============================================================

def _random_dt_between(start: datetime, end: datetime) -> datetime:
    """
    Return a random datetime between two datetime bounds.

    Reason for helper:
        - Keeps datetime generation logic in one place.
        - Lets both work orders and sensor events reuse the same random time logic.
    """
    delta = (end - start).total_seconds()
    return start + timedelta(seconds = rand_num_gen.integers(0, int(delta)))

def generate_work_orders(n:int, equipment_ids: list, user_ids: dict) -> pd.DataFrame:
    """
    Creates synthetic work orders for the Work_Orders table.

    Parameters:
        - n: total number of work orders to generate.
        - equipment_ids: list of valid Equipment_ID values.
        - user_ids: dictionary with:
                - 'all': all valid User_ID values
                - 'technician': only technician User_ID values

    Important modeling choice:
        - Created_At timestamps are generated first, then sorted in ascending order (This guarantees the CSV is chronological, which is critical for later time-based train/test splits in predictive maintenance workflows).

    Logical (Business) Assumptions:
        - Every work order belongs to one piece of equipment.
        - Reported_By can be any user.
        - Assigned_To should generally be a technician.
        - About 15% remain open/in progress to reflect unresolved maintenance.
        - Completed work orders receive a Repair_Duration_Hrs and Completed_At.
        """

    created_times = sorted([_random_dt_between(WO_START, WO_END) for _ in range(n)])

    records = []

    for i, created in enumerate(created_times, start=1):
        # Exponential distributions are useful for repair durations because many repairs are short, while a smaller number are much longer.

        repair_hrs = max(0.5, round(rand_num_gen.exponential(scale=4.0), 2))

        # Roughly 85% completed, while the rest are either open or in progress.
        is_closed = random.random() > 0.15

        completed = ((created + timedelta(hours = repair_hrs)).strftime("%Y-%m-%d %H:%M:%S") if is_closed else None)

        records.append({
            "WO_ID": i,
            "Equipment_ID": random.choice(equipment_ids),
            "Reported_By": random.choice(user_ids["all"]),
            "Assigned_To": random.choice(user_ids["technician"]),
            "Failure_Type": random.choice(FAILURE_TYPES),
            "Priority": random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0],
            "Status": "Completed" if is_closed else random.choice(["Open", "In Progress"]),
            "Description": fake.sentence(nb_words=12),
            "Repair_Duration_Hrs": repair_hrs if is_closed else None,
            "Created_At": created.strftime("%Y-%m-%d %H:%M:%S"),
            "Completed_At": completed,
        })

    return pd.DataFrame(records)


# ==============================================================
# 4. Parts Usage
# ==============================================================

def generate_parts_usage(work_order_ids: list, n_target: int = 3000) -> pd.DataFrame:
    """
    Create synthetic parts usage rows for the Parts_Usage table.

    Design notes:
    - Parts are linked only to completed work orders in main().
    - Multiple parts can point to the same work order, which is realistic.
    - Total_Cost is precomputed for convenience in dashboards and analytics.

    Parameters:
        work_order_ids: list of eligible WO_ID values.
        n_target: approximate number of parts rows to create.
    """
    # random.choices samples with replacement, which is what we want here:
    # many different parts rows may belong to the same work order.
    wo_sample = random.choices(work_order_ids, k=n_target)

    records = []

    for pid, wo_id in enumerate(wo_sample, start=1):
        unit_cost = round(random.uniform(12.0, 850.0), 2)
        qty = rand_num_gen.integers(1, 6)

        records.append({
            "Part_ID": pid,
            "WO_ID": wo_id,
            "Part_Name": random.choice(PART_NAMES),
            "Part_Number": f"PN-{fake.bothify('####-???').upper()}",
            "Quantity_Used": int(qty),
            "Unit_Cost": unit_cost,
            "Total_Cost": round(unit_cost * qty, 2),
            "Recorded_At": fake.date_time_between(
                start_date=WO_START,
                end_date=WO_END,
            ).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return pd.DataFrame(records)


# ==============================================================
# 5. Sensor Events
# ==============================================================

def generate_sensor_events(equipment_ids: list, n: int = 12000) -> pd.DataFrame:
    """
    Create synthetic sensor telemetry for the Sensor_Events table.

    Output columns mirror the metrics you referenced for later ML work:
        - Temperature_C
        - Vibration_Hz
        - Torque_Nm
        - Rotational_RPM
        - Tool_Wear_Min

    Modeling notes:
    - Most readings are generated from normal operating ranges.
    - Roughly 5% are marked as anomaly spikes to simulate unusual machine states.
    - Timestamps are sorted so sensor data is time-aware and useful for rolling
      features like 7-day averages and max values.
    - Source is set to 'batch_seed' for now; Phase 3 can emit similar rows from
      Event Hubs with a different source label.
    """

    event_times = sorted([
        _random_dt_between(WO_START, WO_END) for _ in range(n)
    ])

    # Randomly assign each telemetry record to a valid equipment asset.
    equipment_arr = rand_num_gen.choice(equipment_ids, size=n)

    # About 5% of events are anomalies.
    is_anomaly = rand_num_gen.random(n) < 0.05

    records = {
        "Event_ID": list(range(1, n + 1)),
        "Equipment_ID": equipment_arr.tolist(),
        "Timestamp": [t.strftime("%Y-%m-%d %H:%M:%S") for t in event_times],

        # Temperature is usually moderate, but anomaly rows jump much higher.
        "Temperature_C": np.where(
            is_anomaly,
            rand_num_gen.uniform(90, 130, n),
            rand_num_gen.normal(loc=65, scale=8, size=n).clip(30, 89),
        ).round(2).tolist(),

        # Vibration is a common predictive maintenance signal.
        # Normal values stay lower; anomaly rows spike upward.
        "Vibration_Hz": np.where(
            is_anomaly,
            rand_num_gen.uniform(60, 120, n),
            rand_num_gen.normal(loc=25, scale=5, size=n).clip(5, 59),
        ).round(2).tolist(),

        # Torque and RPM stay within reasonable operational ranges.
        "Torque_Nm": rand_num_gen.normal(loc=200, scale=30, size=n).clip(80, 400).round(2).tolist(),
        "Rotational_RPM": rand_num_gen.normal(loc=1500, scale=200, size=n).clip(500, 3000).round(1).tolist(),

        # Tool wear is simulated as elapsed usage minutes for simplicity.
        "Tool_Wear_Min": rand_num_gen.integers(0, 480, size=n).tolist(),

        # Helpful extra field for testing anomaly logic before real streaming.
        "Is_Anomaly": is_anomaly.astype(int).tolist(),

        # Lets you distinguish seeded batch data from future live event data.
        "Source": ["batch_seed"] * n,
    }

    return pd.DataFrame(records)


# ==============================================================
# 6. Query Logs
# ==============================================================

def generate_query_logs(user_ids_all: list, n: int = 500) -> pd.DataFrame:
    """
    Create lightweight audit/query log records for the Query_Logs table.

    Why include this table now:
    - Lets you populate admin screens or analytics around user behavior.
    - Gives the schema complete seed coverage instead of leaving one OLTP table empty.
    - Supports future monitoring/reporting use cases.
    """

    records = []

    for lid in range(1, n + 1):
        exec_ms = int(rand_num_gen.integers(20, 2500))

        records.append({
            "Log_ID": lid,
            "User_ID": random.choice(user_ids_all),
            "Action": random.choice(QUERY_ACTIONS),
            "Query_Text": fake.sentence(nb_words=8),
            "Execution_Ms": exec_ms,
            "Success": 1 if exec_ms < 2000 else 0,
            "Logged_At": fake.date_time_between(
                start_date=WO_START,
                end_date=WO_END,
            ).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return pd.DataFrame(records)


# ==============================================================
# Main Entry Point
# ==============================================================

def main():
    """
    Orchestrate generation of all CSVs in the correct order.

    Order matters because:
    - Users must exist before work orders can reference them.
    - Equipment must exist before work orders and sensor events can reference it.
    - Work orders must exist before parts usage can reference WO_ID values.
    """

    print("FactoryMind — Seed Data Generator v1.0")
    print(f"Output directory: {EXPORTS_DIR}\n")

    # -------------------------------------------------------------------------
    # 1) Users
    # -------------------------------------------------------------------------
    print("Generating users.csv ...")
    users = generate_users(N_USERS)
    users.to_csv(os.path.join(EXPORTS_DIR, "users.csv"), index=False)
    print(f"  {len(users)} rows")

    # Keep these lists in memory so downstream tables can reference valid users.
    all_user_ids = users["User_ID"].tolist()
    tech_user_ids = users[users["Role"] == "Technician"]["User_ID"].tolist()

    # Safety fallback: if the random sample somehow yields zero technicians,
    # allow any user to be assigned so the script never crashes.
    if not tech_user_ids:
        tech_user_ids = all_user_ids

    # -------------------------------------------------------------------------
    # 2) Equipment
    # -------------------------------------------------------------------------
    print("Generating equipment.csv ...")
    equipment = generate_equipment(N_EQUIPMENT)
    equipment.to_csv(os.path.join(EXPORTS_DIR, "equipment.csv"), index=False)
    print(f"  {len(equipment)} rows")

    # Save valid Equipment_ID values for FK-style references in later tables.
    equip_ids = equipment["Equipment_ID"].tolist()

    # -------------------------------------------------------------------------
    # 3) Work Orders
    # -------------------------------------------------------------------------
    print(f"Generating work_orders.csv ({TOTAL_WO} rows) ...")
    work_orders = generate_work_orders(
        TOTAL_WO,
        equipment_ids=equip_ids,
        user_ids={"all": all_user_ids, "technician": tech_user_ids},
    )
    work_orders.to_csv(os.path.join(EXPORTS_DIR, "work_orders.csv"), index=False)

    # Chronological 80/20 split boundary for later ML use.
    train_cutoff = int(len(work_orders) * 0.80)
    print(
        f"  {len(work_orders)} rows  |  "
        f"train split: rows 1–{train_cutoff}  |  "
        f"test split: rows {train_cutoff + 1}–{len(work_orders)}"
    )

    # -------------------------------------------------------------------------
    # 4) Parts Usage
    # -------------------------------------------------------------------------
    print("Generating parts_usage.csv ...")

    # Only completed work orders should consume parts in a simple seed model.
    closed_wo_ids = work_orders[work_orders["Status"] == "Completed"]["WO_ID"].tolist()
    parts = generate_parts_usage(closed_wo_ids, n_target=3000)
    parts.to_csv(os.path.join(EXPORTS_DIR, "parts_usage.csv"), index=False)
    print(f"  {len(parts)} rows")

    # -------------------------------------------------------------------------
    # 5) Sensor Events
    # -------------------------------------------------------------------------
    print("Generating sensor_events.csv (12,000 rows) ...")
    sensors = generate_sensor_events(equip_ids, n=12000)
    sensors.to_csv(os.path.join(EXPORTS_DIR, "sensor_events.csv"), index=False)

    anomaly_count = sensors["Is_Anomaly"].sum()
    print(
        f"  {len(sensors)} rows  |  "
        f"{anomaly_count} anomaly events ({anomaly_count / len(sensors) * 100:.1f}%)"
    )

    # -------------------------------------------------------------------------
    # 6) Query Logs
    # -------------------------------------------------------------------------
    print("Generating query_logs.csv ...")
    logs = generate_query_logs(all_user_ids, n=500)
    logs.to_csv(os.path.join(EXPORTS_DIR, "query_logs.csv"), index=False)
    print(f"  {len(logs)} rows")

    # -------------------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------------------
    total_rows = sum([
        len(users),
        len(equipment),
        len(work_orders),
        len(parts),
        len(sensors),
        len(logs),
    ])

    print(f"\n All CSVs written to {EXPORTS_DIR}")
    print(f"   Total rows generated: {total_rows:,}")
    print("\nNext step: run  python data/seed_database.py")


# Standard Python entry point guard.
# This allows the file to be executed directly as a script.
if __name__ == "__main__":
    main()