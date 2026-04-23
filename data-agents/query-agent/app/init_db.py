"""
Database initialization script.

If a pre-built .sqlite file exists at SQLITE_DB_PATH, do nothing.
Otherwise, generate realistic sample data for demo/testing purposes.
If CSV files exist in /data/csv/, import them into SQLite.
"""

import csv
import math
import os
import random
import sqlite3

DB_PATH = os.getenv("SQLITE_DB_PATH", "/data/residential_energy.db")
CSV_DIR = os.getenv("CSV_DIR", "/data/csv")

SCHEMA = """
CREATE TABLE IF NOT EXISTS upgrade (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER NOT NULL,
    energy_consumption REAL,
    fuel TEXT NOT NULL,
    use TEXT NOT NULL,
    time TEXT NOT NULL,
    baseline REAL,
    delta REAL,
    characteristics TEXT,
    vintage TEXT,
    occupants INTEGER,
    county TEXT,
    state TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_upgrade_building ON upgrade(building_id);
CREATE INDEX IF NOT EXISTS idx_upgrade_state ON upgrade(state);
CREATE INDEX IF NOT EXISTS idx_upgrade_fuel ON upgrade(fuel);
CREATE INDEX IF NOT EXISTS idx_upgrade_use ON upgrade(use);
CREATE INDEX IF NOT EXISTS idx_upgrade_time ON upgrade(time);
"""

STATES = {
    "TX": ["Harris", "Dallas", "Travis", "Bexar", "Tarrant"],
    "NC": ["Wake", "Mecklenburg", "Guilford", "Durham", "Forsyth"],
    "CA": ["Los Angeles", "San Diego", "Orange", "Santa Clara", "Alameda"],
    "FL": ["Miami-Dade", "Broward", "Palm Beach", "Hillsborough", "Orange"],
    "NY": ["New York", "Kings", "Queens", "Erie", "Suffolk"],
    "GA": ["Fulton", "Gwinnett", "Cobb", "DeKalb", "Chatham"],
    "VA": ["Fairfax", "Prince William", "Loudoun", "Virginia Beach", "Chesterfield"],
    "PA": ["Philadelphia", "Allegheny", "Montgomery", "Bucks", "Delaware"],
    "IL": ["Cook", "DuPage", "Lake", "Will", "Kane"],
    "OH": ["Cuyahoga", "Franklin", "Hamilton", "Summit", "Montgomery"],
}

FUELS = ["electricity", "natural_gas", "propane", "fuel_oil"]
END_USES = ["heating", "cooling", "hot_water", "lighting", "appliances", "cooking"]
VINTAGES = ["<1950", "1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s"]
CHARACTERISTICS = [
    "single-family_detached",
    "single-family_attached",
    "mobile_home",
    "multi-family_2-4",
    "multi-family_5+",
]
UPGRADE_SCENARIOS = [
    "heat_pump_hvac",
    "heat_pump_water_heater",
    "solar_water_heating",
    "envelope_upgrade",
    "full_electrification",
    "efficient_lighting",
    "heat_pump_dryer",
    "induction_cooking",
]

MONTHS = [f"2024-{m:02d}" for m in range(1, 13)]

# Rough baseline energy by end use (kWh-equivalent per month)
BASELINE_BY_USE = {
    "heating":    {"electricity": 400, "natural_gas": 600, "propane": 550, "fuel_oil": 580},
    "cooling":    {"electricity": 350, "natural_gas": 0,   "propane": 0,   "fuel_oil": 0},
    "hot_water":  {"electricity": 150, "natural_gas": 200, "propane": 180, "fuel_oil": 190},
    "lighting":   {"electricity": 80,  "natural_gas": 0,   "propane": 0,   "fuel_oil": 0},
    "appliances": {"electricity": 200, "natural_gas": 30,  "propane": 0,   "fuel_oil": 0},
    "cooking":    {"electricity": 50,  "natural_gas": 40,  "propane": 35,  "fuel_oil": 0},
}

DELTA_BY_UPGRADE = {
    "heat_pump_hvac":           {"heating": -0.45, "cooling": -0.30},
    "heat_pump_water_heater":   {"hot_water": -0.50},
    "solar_water_heating":      {"hot_water": -0.60},
    "envelope_upgrade":         {"heating": -0.25, "cooling": -0.20},
    "full_electrification":     {"heating": -0.40, "cooling": -0.25, "hot_water": -0.45, "cooking": -0.30},
    "efficient_lighting":       {"lighting": -0.55},
    "heat_pump_dryer":          {"appliances": -0.20},
    "induction_cooking":        {"cooking": -0.35},
}


def _seasonal_factor(month_idx, state):
    """Seasonal multiplier: heating peaks in winter, cooling in summer."""
    hot_states = {"TX", "FL", "GA", "CA"}
    if state in hot_states:
        return 1.0 + 0.5 * math.sin(math.pi * month_idx / 11)
    return 1.0 + 0.4 * math.cos(math.pi * month_idx / 11)


def generate_sample_data(conn):
    """Generate realistic sample residential energy data in the upgrade table."""
    random.seed(42)
    cur = conn.cursor()

    building_id = 0
    buildings_per_state = 50
    rows_inserted = 0

    for state, counties in STATES.items():
        for _ in range(buildings_per_state):
            building_id += 1
            county = random.choice(counties)
            vintage = random.choice(VINTAGES)
            chars = random.choices(CHARACTERISTICS, weights=[40, 15, 10, 20, 15])[0]
            occupants = random.randint(1, 6)
            primary_fuel = random.choices(FUELS, weights=[30, 50, 10, 10])[0]

            for use in END_USES:
                fuel_for_use = primary_fuel
                if use in ("cooling", "lighting", "appliances"):
                    fuel_for_use = "electricity"
                if use == "cooking":
                    fuel_for_use = random.choices(["electricity", "natural_gas"], weights=[40, 60])[0]

                base_val = BASELINE_BY_USE[use].get(fuel_for_use, 0)
                if base_val == 0 and fuel_for_use != "electricity":
                    fuel_for_use = "electricity"
                    base_val = BASELINE_BY_USE[use].get("electricity", 50)

                base_val *= (0.7 + random.random() * 0.6)  # building variation
                base_val *= (0.8 + occupants * 0.07)        # occupant scaling

                for month_idx, time_val in enumerate(MONTHS):
                    sf = _seasonal_factor(month_idx, state)
                    if use == "heating":
                        m = 2.0 - sf if state in {"TX", "FL", "GA", "CA"} else sf
                    elif use == "cooling":
                        m = sf if state in {"TX", "FL", "GA", "CA"} else 2.0 - sf
                    else:
                        m = 1.0 + random.gauss(0, 0.05)

                    baseline = max(0, round(base_val * m + random.gauss(0, base_val * 0.05), 2))

                    for upgrade in UPGRADE_SCENARIOS:
                        frac = DELTA_BY_UPGRADE.get(upgrade, {}).get(use, 0.0)
                        if frac == 0.0:
                            continue

                        delta = round(baseline * frac * (0.8 + random.random() * 0.4), 2)
                        ec = round(baseline + delta, 2)

                        cur.execute(
                            "INSERT INTO upgrade "
                            "(building_id, energy_consumption, fuel, use, time, "
                            "baseline, delta, characteristics, vintage, occupants, county, state) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (building_id, ec, fuel_for_use, use, time_val,
                             baseline, delta, chars, vintage, occupants, county, state),
                        )
                        rows_inserted += 1

    conn.commit()
    print(f"Generated {building_id} buildings across {len(STATES)} states")
    print(f"Total upgrade rows: {rows_inserted}")


def import_csvs(conn):
    """Import CSV files from CSV_DIR if they exist."""
    if not os.path.isdir(CSV_DIR):
        return False

    imported = False
    for filename in sorted(os.listdir(CSV_DIR)):
        if not filename.endswith(".csv"):
            continue
        table_name = filename.replace(".csv", "")
        filepath = os.path.join(CSV_DIR, filename)
        print(f"Importing {filepath} into table {table_name}...")

        with open(filepath, "r") as f:
            reader = csv.reader(f)
            headers = next(reader)
            placeholders = ",".join(["?"] * len(headers))
            cols = ",".join(headers)
            batch = []
            for row in reader:
                batch.append(row)
                if len(batch) >= 5000:
                    conn.executemany(
                        f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})", batch
                    )
                    batch = []
            if batch:
                conn.executemany(
                    f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})", batch
                )

        conn.commit()
        imported = True
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        print(f"  Imported {table_name}: {cur.fetchone()[0]} rows")

    return imported


def main():
    db_path = os.getenv("SQLITE_DB_PATH", DB_PATH)
    db_dir = os.path.dirname(db_path) or "."
    os.makedirs(db_dir, exist_ok=True)

    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
        print(f"Database already exists at {db_path}, verifying...")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cur.fetchone()[0]
        conn.close()
        if table_count > 0:
            print(f"  Found {table_count} tables, skipping init.")
            return
        print("  Database is empty, initializing...")

    print(f"Initializing database at {db_path}")
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    if not import_csvs(conn):
        print("No CSV files found, generating sample data...")
        generate_sample_data(conn)

    conn.close()
    print("Database initialization complete.")


if __name__ == "__main__":
    main()
