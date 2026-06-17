"""Shared test fixtures for C2AI data-agents tests."""

import sqlite3
import sys
from pathlib import Path

import pytest


SCHEMA = """
CREATE TABLE buildings (
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

CREATE TABLE results (
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
"""

SEED_BUILDINGS = [
    (1, "NC", "NC, Wake County", "1990s", "1980-99", "Single-Family Detached",
     "1500-1999", "2", "3", "3", "Electricity", "Electricity",
     "Electricity ASHP", "Yes", "South-Central", "80-100%",
     "Wood Stud, R-11", "R-30"),
    (2, "NC", "NC, Mecklenburg County", "2000s", "2000-09", "Single-Family Detached",
     "2000-2499", "2", "4", "4", "Natural Gas", "Natural Gas",
     "Natural Gas Fuel Furnace", "Yes", "South-Central", "100-120%",
     "Wood Stud, R-13", "R-38"),
    (3, "NC", "NC, Durham County", "1970s", "1960-79", "Mobile Home",
     "750-999", "1", "2", "2", "Propane", "Propane",
     "Propane Fuel Furnace", "Yes", "North-Central", "30-60%",
     "Wood Stud, Uninsulated", None),
    (4, "NC", "NC, Guilford County", "1960s", "1960-79", "Single-Family Attached",
     "1000-1499", "1", "2", "1", "Fuel Oil", "Fuel Oil",
     "Fuel Oil Fuel Boiler", "No", "North-Central", "0-30%",
     "Wood Stud, R-7", "R-19"),
    (5, "NC", "NC, Forsyth County", "2010s", "2010-19", "Single-Family Detached",
     "2500-2999", "2", "4", "5", "Electricity", "Electricity",
     "Electricity ASHP", "Yes", "South-Central", "120-150%",
     "Wood Stud, R-13", "R-38"),
]

SEED_RESULTS = [
    (1, 85.2, 85.2, 85.2, 0.0, 0.0, 0.0, 22.1, 18.5, 12.3, 0.0, 0.0, 0.0, 8.4, 3.2, 2.8),
    (2, 112.5, 112.5, 42.3, 70.2, 0.0, 0.0, 5.1, 20.2, 3.8, 52.4, 14.1, 0.0, 9.1, 3.7, 3.1),
    (3, 95.8, 95.8, 35.6, 0.0, 60.2, 0.0, 3.2, 12.1, 2.4, 0.0, 0.0, 48.5, 6.2, 2.1, 1.9),
    (4, 78.3, 78.3, 28.4, 0.0, 0.0, 49.9, 2.5, 8.9, 1.8, 0.0, 0.0, 0.0, 5.8, 1.8, 1.5),
    (5, 68.9, 68.9, 68.9, 0.0, 0.0, 0.0, 15.4, 22.8, 10.1, 0.0, 0.0, 0.0, 10.2, 4.1, 3.5),
]


@pytest.fixture
def test_db(tmp_path):
    """Create an in-memory SQLite database with known test data."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    conn.executemany(
        "INSERT INTO buildings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        SEED_BUILDINGS,
    )
    conn.executemany(
        "INSERT INTO results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        SEED_RESULTS,
    )
    conn.commit()
    conn.close()
    return db_path
