"""
Load real ResStock data into SQLite.

Reads buildstock.csv (building characteristics) and results_up00.parquet
(baseline annual energy metrics) and writes two normalized tables:
  - buildings: 18 curated characteristic columns
  - results: 15 curated energy metric columns (all MBtu, annual)
"""

import os
import sqlite3
import logging

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("load-resstock")

DB_PATH = os.getenv("SQLITE_DB_PATH", "/data/residential_energy.db")
BUILDSTOCK_PATH = os.getenv("BUILDSTOCK_CSV_PATH", "/data/source/buildstock.csv")
RESULTS_PATH = os.getenv("RESULTS_PARQUET_PATH", "/data/source/results_up00.parquet")

BUILDING_COLUMN_MAP = {
    "Building": "building_id",
    "State": "state",
    "County": "county",
    "Vintage": "vintage",
    "Vintage ACS": "vintage_acs",
    "Geometry Building Type ACS": "building_type",
    "Geometry Floor Area": "floor_area",
    "Geometry Stories": "stories",
    "Bedrooms": "bedrooms",
    "Occupants": "occupants",
    "Heating Fuel": "heating_fuel",
    "Water Heater Fuel": "water_heater_fuel",
    "HVAC Heating Type And Fuel": "hvac_type",
    "HVAC Has Ducts": "hvac_has_ducts",
    "Energystar Climate Zone 2023": "climate_zone",
    "Area Median Income": "area_median_income",
    "Insulation Wall": "insulation_wall",
    "Insulation Ceiling": "insulation_ceiling",
}

METRIC_COLUMN_MAP = {
    "building_id": "building_id",
    "report_simulation_output.energy_use_total_m_btu": "energy_use_total",
    "report_simulation_output.energy_use_net_m_btu": "energy_use_net",
    "report_simulation_output.fuel_use_electricity_total_m_btu": "fuel_electricity_total",
    "report_simulation_output.fuel_use_natural_gas_total_m_btu": "fuel_natural_gas_total",
    "report_simulation_output.fuel_use_propane_total_m_btu": "fuel_propane_total",
    "report_simulation_output.fuel_use_fuel_oil_total_m_btu": "fuel_fuel_oil_total",
    "report_simulation_output.end_use_electricity_heating_m_btu": "end_use_electricity_heating",
    "report_simulation_output.end_use_electricity_cooling_m_btu": "end_use_electricity_cooling",
    "report_simulation_output.end_use_electricity_hot_water_m_btu": "end_use_electricity_hot_water",
    "report_simulation_output.end_use_natural_gas_heating_m_btu": "end_use_natural_gas_heating",
    "report_simulation_output.end_use_natural_gas_hot_water_m_btu": "end_use_natural_gas_hot_water",
    "report_simulation_output.end_use_propane_hot_water_m_btu": "end_use_propane_hot_water",
    "report_simulation_output.end_use_electricity_lighting_interior_m_btu": "end_use_electricity_lighting",
    "report_simulation_output.end_use_electricity_cooling_fans_pumps_m_btu": "end_use_electricity_cooling_fans",
    "report_simulation_output.end_use_electricity_heating_fans_pumps_m_btu": "end_use_electricity_heating_fans",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS buildings (
    building_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,
    county TEXT,
    vintage TEXT,
    vintage_acs TEXT,
    building_type TEXT,
    floor_area TEXT,
    stories TEXT,
    bedrooms TEXT,
    occupants TEXT,
    heating_fuel TEXT,
    water_heater_fuel TEXT,
    hvac_type TEXT,
    hvac_has_ducts TEXT,
    climate_zone TEXT,
    area_median_income TEXT,
    insulation_wall TEXT,
    insulation_ceiling TEXT
);

CREATE TABLE IF NOT EXISTS results (
    building_id INTEGER PRIMARY KEY REFERENCES buildings(building_id),
    energy_use_total REAL,
    energy_use_net REAL,
    fuel_electricity_total REAL,
    fuel_natural_gas_total REAL,
    fuel_propane_total REAL,
    fuel_fuel_oil_total REAL,
    end_use_electricity_heating REAL,
    end_use_electricity_cooling REAL,
    end_use_electricity_hot_water REAL,
    end_use_natural_gas_heating REAL,
    end_use_natural_gas_hot_water REAL,
    end_use_propane_hot_water REAL,
    end_use_electricity_lighting REAL,
    end_use_electricity_cooling_fans REAL,
    end_use_electricity_heating_fans REAL
);

CREATE INDEX IF NOT EXISTS idx_buildings_state ON buildings(state);
CREATE INDEX IF NOT EXISTS idx_buildings_county ON buildings(county);
CREATE INDEX IF NOT EXISTS idx_buildings_heating_fuel ON buildings(heating_fuel);
CREATE INDEX IF NOT EXISTS idx_buildings_climate_zone ON buildings(climate_zone);
CREATE INDEX IF NOT EXISTS idx_buildings_ami ON buildings(area_median_income);
"""


def main():
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        conn = sqlite3.connect(DB_PATH)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        if "buildings" in tables and "results" in tables:
            b_count = conn.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
            r_count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
            conn.close()
            if b_count > 14000 and r_count > 14000:
                logger.info(
                    "Database exists with %d buildings, %d results. Skipping.",
                    b_count, r_count,
                )
                return
        conn.close()

    logger.info("Loading ResStock data into %s", DB_PATH)

    logger.info("Reading buildstock from %s", BUILDSTOCK_PATH)
    bs = pd.read_csv(BUILDSTOCK_PATH)
    bs = bs[list(BUILDING_COLUMN_MAP.keys())].rename(columns=BUILDING_COLUMN_MAP)
    bs["building_id"] = pd.to_numeric(bs["building_id"], errors="coerce").astype("Int64")
    logger.info("  %d buildings loaded", len(bs))

    logger.info("Reading results from %s", RESULTS_PATH)
    results = pd.read_parquet(RESULTS_PATH, columns=list(METRIC_COLUMN_MAP.keys()))
    results = results.rename(columns=METRIC_COLUMN_MAP)
    pre_count = len(results)
    results = results.dropna(subset=["energy_use_total"])
    if len(results) < pre_count:
        logger.info("  Dropped %d rows with NULL energy_use_total (failed simulations)",
                     pre_count - len(results))
    logger.info("  %d results loaded", len(results))

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    bs.to_sql("buildings", conn, if_exists="replace", index=False)
    logger.info("  Written %d rows to buildings table", len(bs))

    results.to_sql("results", conn, if_exists="replace", index=False)
    logger.info("  Written %d rows to results table", len(results))

    conn.executescript(SCHEMA)
    conn.close()

    logger.info("Done. Database at %s", DB_PATH)


if __name__ == "__main__":
    main()
