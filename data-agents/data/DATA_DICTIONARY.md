# ResStock Data Dictionary

## Dataset

14,217 residential buildings in North Carolina (baseline, no upgrades applied). Sampled from NREL's ResStock model using the NC poster project configuration. Stock was filtered for single-family and small multifamily (2-4 units), AMI below 150%, and occupied units.

All energy values are **annual totals in MBtu** (million British thermal units). A value of 0.0 means the building does not use that fuel for that end use — it is a real measurement, not missing data. Do not exclude zeros.

## Tables

Two tables joined on `building_id`:
- `buildings` — one row per building, 18 characteristic columns (all TEXT except building_id INTEGER)
- `results` — one row per building, 15 energy metric columns (all REAL, all MBtu annual)

## Energy metrics (results table)

### Totals
- `energy_use_total` — Total site energy consumption across all fuels and end uses (MBtu). This is the single summary number for a building's energy footprint.
- `energy_use_net` — Net site energy (total minus any on-site generation like PV). Equal to energy_use_total for buildings without solar.

### Fuel totals
- `fuel_electricity_total` — Total electricity consumption across all end uses (MBtu). Includes heating, cooling, hot water, lighting, appliances, fans/pumps.
- `fuel_natural_gas_total` — Total natural gas consumption (MBtu). Zero for all-electric homes.
- `fuel_propane_total` — Total propane consumption (MBtu). Zero for homes not using propane.
- `fuel_fuel_oil_total` — Total fuel oil consumption (MBtu). Zero for homes not using fuel oil.

Relationship: `energy_use_total` approximately equals the sum of all `fuel_*_total` columns (small rounding differences possible).

### End uses by fuel
- `end_use_electricity_heating` — Electricity used for space heating (MBtu). Includes heat pumps, electric furnaces, baseboard heaters.
- `end_use_electricity_cooling` — Electricity used for space cooling (MBtu). Zero for homes without AC.
- `end_use_electricity_hot_water` — Electricity used for water heating (MBtu). Zero for homes with gas/propane water heaters.
- `end_use_natural_gas_heating` — Natural gas used for space heating (MBtu). Zero for electric-heated homes.
- `end_use_natural_gas_hot_water` — Natural gas used for water heating (MBtu). Zero for homes with electric water heaters.
- `end_use_propane_hot_water` — Propane used for water heating (MBtu). Most homes show zero.
- `end_use_electricity_lighting` — Electricity used for interior lighting (MBtu).
- `end_use_electricity_cooling_fans` — Electricity used by cooling system fans and pumps (MBtu). Separate from compressor energy in end_use_electricity_cooling.
- `end_use_electricity_heating_fans` — Electricity used by heating system fans and pumps (MBtu). Relevant for forced-air systems.

## Building characteristics (buildings table)

### Geography
- `state` — Always "NC" in this dataset.
- `county` — Format: "NC, Wake County". 100 NC counties represented.
- `climate_zone` — EnergyStar Climate Zone 2023. Two values: "North-Central" or "South-Central". NC is split roughly 50/50.

### Building form
- `building_type` — ACS building type: Single-Family Detached, Single-Family Attached, Mobile Home, Multi-Family with 2-4 Units.
- `floor_area` — Conditioned floor area bin (e.g. "1000-1499", "1500-1999").
- `stories` — Number of stories (e.g. "1", "2", "3+").
- `bedrooms` — Number of bedrooms (e.g. "2", "3", "4").
- `occupants` — Number of occupants (e.g. "1", "3", "5").

### Age
- `vintage` — Construction decade: "<1950", "1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s".
- `vintage_acs` — ACS vintage grouping: "1940-59", "1960-79", "1980-99", "2000-09", "2010-19", "<1940".

### HVAC systems
- `heating_fuel` — Primary heating fuel: Electricity, Natural Gas, Propane, Fuel Oil, None. This is the single most important stratification dimension for energy economics — gas-heated vs electric-heated homes have fundamentally different energy profiles.
- `water_heater_fuel` — Water heater fuel: Electricity, Natural Gas, Propane, Fuel Oil.
- `hvac_type` — Heating system type and fuel combined (e.g. "Electricity ASHP", "Natural Gas Fuel Furnace", "Electricity Electric Furnace"). 15 unique values.
- `hvac_has_ducts` — Whether the HVAC system uses ductwork: "Yes" or "No". Ducted systems have duct losses; ductless (mini-splits, baseboard) do not.

### Envelope
- `insulation_wall` — Wall insulation level (e.g. "Wood Stud, R-11", "Wood Stud, Uninsulated"). 15 unique values.
- `insulation_ceiling` — Ceiling/attic insulation level (e.g. "R-30", "R-38"). NULL for buildings without applicable ceiling insulation (flat roof, cathedral ceiling). 44% of buildings have NULL.

### Income
- `area_median_income` — Household income as percentage of area median: "0-30%", "30-60%", "60-80%", "80-100%", "100-120%", "120-150%". Key equity dimension — energy burden and upgrade economics vary substantially across income levels.

## Query tools

Six tools are available for querying this data:

1. **describe_metric** — Distribution statistics (count, mean, std, min, p25, median, p75, max) for one metric, optionally filtered by building characteristics.
2. **metric_by_group** — A metric aggregated (count, mean, median) by one or more building characteristics.
3. **distribution** — Raw per-building values for a metric, optionally grouped by a characteristic. Use for boxplots, violins, histograms.
4. **compare_metrics** — Multiple metrics side by side for the same buildings, optionally grouped.
5. **building_stock_summary** — Value counts and percentages for a building characteristic.
6. **list_available_data** — Lists all available metric and characteristic column names.

## Key analytical notes

- **Stratify by heating_fuel first.** Gas-heated homes and electric-heated homes have completely different energy profiles. Reporting averages across both is misleading.
- **Climate zone matters.** NC has two zones (North-Central and South-Central) with different heating/cooling balances.
- **Zeros are real.** A building with `fuel_natural_gas_total = 0.0` is an all-electric home, not a data gap.
- **This is baseline only.** No upgrades have been applied. To compare upgrade scenarios, additional results tables would be needed.
- **All units are MBtu (annual).** To convert: 1 MBtu = 293.07 kWh (electricity), 10 therms (natural gas), ~7.15 gallons propane, ~7.19 gallons fuel oil.
