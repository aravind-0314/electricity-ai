"""
Synthetic Electricity Data Simulation Engine.

Simulates 500 consumers across 5 feeders and 5 transformers over 30 days (720 hourly intervals).
Produces exactly:
- 5 Feeders
- 5 Transformers
- 500 Consumers
- 360,000 Consumer Hourly Readings
- 3,600 Feeder Hourly Readings
- 150 Daily Feeder Loss Audit Records
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import math
import random
import datetime
from typing import List, Dict, Tuple, Any
import numpy as np

from config import Config
from database.db import get_db, init_db
from src.physics_engine.loss_calculator import (
    calculate_hourly_technical_loss,
    reconcile_energy_balance
)

# Realistic 24-hour baseline load profiles normalized to [0.0, 1.0]
PROFILE_RESIDENTIAL = np.array([
    0.20, 0.18, 0.16, 0.15, 0.18, 0.35,  # 00:00 - 05:00
    0.65, 0.85, 0.80, 0.60, 0.45, 0.40,  # 06:00 - 11:00
    0.42, 0.40, 0.38, 0.42, 0.55, 0.75,  # 12:00 - 17:00
    0.95, 1.00, 0.92, 0.78, 0.50, 0.30   # 18:00 - 23:00 (Evening peak 18-22)
])

PROFILE_COMMERCIAL = np.array([
    0.15, 0.15, 0.15, 0.15, 0.18, 0.25,  # 00:00 - 05:00
    0.40, 0.65, 0.85, 0.95, 1.00, 0.98,  # 06:00 - 11:00 (Business ramp)
    0.95, 0.96, 0.98, 0.95, 0.90, 0.82,  # 12:00 - 17:00 (Active operations)
    0.70, 0.55, 0.40, 0.30, 0.22, 0.18   # 18:00 - 23:00
])

PROFILE_AGRICULTURAL = np.array([
    0.85, 0.95, 1.00, 0.95, 0.85, 0.60,  # 00:00 - 05:00 (Night irrigation)
    0.40, 0.25, 0.15, 0.15, 0.20, 0.30,  # 06:00 - 11:00
    0.35, 0.70, 0.85, 0.80, 0.50, 0.30,  # 12:00 - 17:00 (Afternoon pumping)
    0.20, 0.20, 0.25, 0.35, 0.55, 0.75   # 18:00 - 23:00
])

class DataSimulator:
    def __init__(
        self,
        consumer_count: int = Config.CONSUMER_COUNT,
        feeder_count: int = Config.FEEDER_COUNT,
        simulation_days: int = Config.SIMULATION_DAYS,
        seed: int = Config.RANDOM_SEED
    ):
        self.consumer_count = consumer_count
        self.feeder_count = feeder_count
        self.simulation_days = simulation_days
        self.readings_per_day = Config.READINGS_PER_DAY
        self.total_hours = self.simulation_days * self.readings_per_day  # 720
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        random.seed(seed)

        # Simulation base start date (fixed for reproducible timestamps)
        self.start_date = datetime.datetime(2026, 10, 1, 0, 0, 0)

    def generate_feeders_and_transformers(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Generate 5 feeders and 5 matching distribution transformers."""
        feeders = []
        transformers = []

        substations = ["SS-Central", "SS-North", "SS-South", "SS-East", "SS-West"]
        feeder_lengths = [3.2, 4.5, 2.8, 5.1, 3.8]  # km
        feeder_resistances = [0.38, 0.42, 0.34, 0.48, 0.39]  # ohms per phase

        transformer_capacities = [800.0, 1000.0, 630.0, 1250.0, 800.0]  # kVA
        core_losses = [1.65, 2.10, 1.35, 2.60, 1.70]  # kW
        copper_losses = [7.50, 9.20, 5.80, 11.50, 7.80]  # kW

        for i in range(self.feeder_count):
            fdr_id = f"FDR-{i+1:02d}"
            tx_id = f"TX-{i+1:02d}"

            feeders.append({
                "feeder_id": fdr_id,
                "name": f"Feeder {i+1} ({substations[i]})",
                "substation_name": substations[i],
                "nominal_voltage_kv": Config.NOMINAL_VOLTAGE_KV,
                "conductor_resistance_ohm": feeder_resistances[i],
                "length_km": feeder_lengths[i]
            })

            transformers.append({
                "transformer_id": tx_id,
                "feeder_id": fdr_id,
                "capacity_kva": transformer_capacities[i],
                "core_loss_kw": core_losses[i],
                "rated_copper_loss_kw": copper_losses[i]
            })

        return feeders, transformers

    def generate_consumers(self) -> List[Dict[str, Any]]:
        """
        Generate 500 consumers distributed across 5 feeders.
        Distribution:
        - ~60% Residential (300)
        - ~25% Commercial (125)
        - ~15% Agricultural (75)

        Simulation scenarios:
        - NORMAL: ~410 (82%)
        - PARTIAL_BYPASS: 25 (5%)
        - METER_FLATLINE: 15 (3%)
        - PEAK_BYPASS: 20 (4%)
        - TELEMETRY_DROPOUT: 15 (3%)
        - VACATION: 15 (3%)
        Total = 500
        """
        consumers = []

        # Target scenario counts
        scenarios = (
            ["NORMAL"] * 410 +
            ["PARTIAL_BYPASS"] * 25 +
            ["METER_FLATLINE"] * 15 +
            ["PEAK_BYPASS"] * 20 +
            ["TELEMETRY_DROPOUT"] * 15 +
            ["VACATION"] * 15
        )
        self.rng.shuffle(scenarios)

        # Distribute 500 consumers evenly across 5 feeders (100 each)
        for idx in range(self.consumer_count):
            cons_id = f"CONS-{idx+1:04d}"
            feeder_idx = idx % self.feeder_count
            feeder_id = f"FDR-{feeder_idx+1:02d}"
            transformer_id = f"TX-{feeder_idx+1:02d}"

            # Tariff category distribution: ~60% Res, 25% Comm, 15% Agri
            rand_val = self.rng.rand()
            if rand_val < 0.60:
                tariff = "Residential"
                sanctioned_load = round(float(self.rng.uniform(2.0, 7.0)), 1)
            elif rand_val < 0.85:
                tariff = "Commercial"
                sanctioned_load = round(float(self.rng.uniform(8.0, 25.0)), 1)
            else:
                tariff = "Agricultural"
                sanctioned_load = round(float(self.rng.uniform(5.0, 15.0)), 1)

            meter_id = f"MTR-{100000 + idx + 1}"
            scenario = scenarios[idx]

            consumers.append({
                "consumer_id": cons_id,
                "feeder_id": feeder_id,
                "transformer_id": transformer_id,
                "tariff_category": tariff,
                "sanctioned_load_kw": sanctioned_load,
                "meter_id": meter_id,
                "simulation_scenario": scenario
            })

        return consumers

    def simulate_hourly_readings(
        self,
        consumers: List[Dict[str, Any]],
        feeders: List[Dict[str, Any]],
        transformers: List[Dict[str, Any]]
    ) -> Tuple[List[Tuple], List[Tuple], List[Tuple]]:
        """
        Simulate 30 days * 24 hours of readings.
        Returns:
        - consumer_readings: 360,000 rows
        - feeder_readings: 3,600 rows
        - loss_audit_logs: 150 rows
        """
        feeder_dict = {f["feeder_id"]: f for f in feeders}
        tx_dict = {t["transformer_id"]: t for t in transformers}

        # Consumer lookup by feeder
        consumers_by_feeder: Dict[str, List[Dict[str, Any]]] = {f["feeder_id"]: [] for f in feeders}
        for c in consumers:
            consumers_by_feeder[c["feeder_id"]].append(c)

        consumer_rows = []
        feeder_rows = []
        audit_rows_by_feeder_day: Dict[Tuple[str, int], Dict[str, float]] = {}

        # Precompute consumer base factors for efficiency
        consumer_factors = {}
        for c in consumers:
            consumer_factors[c["consumer_id"]] = {
                "base_scale": c["sanctioned_load_kw"] * 0.35 * float(self.rng.uniform(0.75, 1.25)),
                "noise_level": 0.08 + self.rng.rand() * 0.05
            }

        # Simulation loop: 30 days, 24 hours = 720 intervals
        for day in range(1, self.simulation_days + 1):
            for hour in range(self.readings_per_day):
                interval_hours = (day - 1) * 24 + hour
                dt = self.start_date + datetime.timedelta(hours=interval_hours)
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%Y-%m-%d")

                # Track feeder level sums for this hour
                feeder_actual_sum = {f_id: 0.0 for f_id in consumers_by_feeder}
                feeder_billed_sum = {f_id: 0.0 for f_id in consumers_by_feeder}

                for c in consumers:
                    c_id = c["consumer_id"]
                    f_id = c["feeder_id"]
                    tariff = c["tariff_category"]
                    scenario = c["simulation_scenario"]
                    factors = consumer_factors[c_id]

                    # Baseline consumption calculation
                    if tariff == "Residential":
                        profile_val = PROFILE_RESIDENTIAL[hour]
                    elif tariff == "Commercial":
                        profile_val = PROFILE_COMMERCIAL[hour]
                    else:
                        profile_val = PROFILE_AGRICULTURAL[hour]

                    # Add random noise
                    noise = self.rng.normal(0, factors["noise_level"])
                    consumption_mult = max(0.05, profile_val + noise)
                    actual_kwh = factors["base_scale"] * consumption_mult

                    # Scenario logic
                    billed_kwh = actual_kwh
                    meter_status = "NORMAL"

                    if scenario == "PARTIAL_BYPASS":
                        # Tampering active from day 8 onward
                        if day >= 8:
                            bypass_ratio = float(self.rng.uniform(0.25, 0.40))
                            billed_kwh = actual_kwh * bypass_ratio
                            meter_status = "TAMPER_BYPASS"

                    elif scenario == "METER_FLATLINE":
                        # Meter flatline starting from day 6
                        if day >= 6:
                            billed_kwh = float(self.rng.uniform(0.04, 0.12))
                            meter_status = "FLATLINE"

                    elif scenario == "PEAK_BYPASS":
                        # Evening peak bypass 18:00 - 22:00 from day 5 onward
                        if day >= 5 and (18 <= hour <= 22):
                            bypass_ratio = float(self.rng.uniform(0.20, 0.35))
                            billed_kwh = actual_kwh * bypass_ratio
                            meter_status = "TAMPER_BYPASS"

                    elif scenario == "TELEMETRY_DROPOUT":
                        # Intermittent communication failure (~15% chance)
                        if self.rng.rand() < 0.15:
                            billed_kwh = 0.0
                            meter_status = "DROPOUT"

                    elif scenario == "VACATION":
                        # Occupants away on vacation from day 12 to 22 (NOT theft, accurate meter)
                        if 12 <= day <= 22:
                            actual_kwh = factors["base_scale"] * 0.10  # base standby power only
                            billed_kwh = actual_kwh
                            meter_status = "NORMAL"

                    # Safeguard bounds
                    actual_kwh = max(0.0, round(float(actual_kwh), 4))
                    billed_kwh = max(0.0, round(float(billed_kwh), 4))

                    feeder_actual_sum[f_id] += actual_kwh
                    feeder_billed_sum[f_id] += billed_kwh

                    consumer_rows.append((
                        c_id,
                        timestamp_str,
                        day,
                        hour,
                        actual_kwh,
                        billed_kwh,
                        meter_status
                    ))

                # Now calculate physics and energy balance for each feeder for this hour
                for f_id, f_data in feeder_dict.items():
                    tx_id = f_data["feeder_id"].replace("FDR-", "TX-")
                    t_data = tx_dict[tx_id]

                    actual_load_kw = feeder_actual_sum[f_id]
                    billed_load_kw = feeder_billed_sum[f_id]

                    # Auxiliary background distribution overhead (~1.5% of actual)
                    unmetered_aux_kwh = actual_load_kw * 0.015

                    # Technical loss calculations
                    tech_res = calculate_hourly_technical_loss(
                        supplied_power_kw=actual_load_kw + unmetered_aux_kwh,
                        resistance_ohm=f_data["conductor_resistance_ohm"],
                        transformer_rated_kva=t_data["capacity_kva"],
                        transformer_core_loss_kw=t_data["core_loss_kw"],
                        transformer_rated_copper_kw=t_data["rated_copper_loss_kw"],
                        nominal_voltage_kv=f_data["nominal_voltage_kv"],
                        power_factor=Config.SYSTEM_POWER_FACTOR,
                        duration_hours=1.0
                    )

                    cable_loss = tech_res.cable_loss_kwh
                    core_loss = tech_res.transformer_core_loss_kwh
                    copper_loss = tech_res.transformer_copper_loss_kwh
                    tech_loss = tech_res.total_technical_loss_kwh

                    # Supplied energy at feeder head
                    # Supplied Energy = Actual Customer Usage + Technical Losses + Unmetered Aux
                    supplied_kwh = round(actual_load_kw + tech_loss + unmetered_aux_kwh, 4)
                    total_billed_kwh = round(billed_load_kw, 4)

                    # Reconcile hourly balance
                    balance = reconcile_energy_balance(
                        supplied_energy_kwh=supplied_kwh,
                        billed_energy_kwh=total_billed_kwh,
                        cable_loss_kwh=cable_loss,
                        transformer_core_loss_kwh=core_loss,
                        transformer_copper_loss_kwh=copper_loss
                    )

                    feeder_rows.append((
                        f_id,
                        timestamp_str,
                        day,
                        hour,
                        balance.supplied_energy_kwh,
                        balance.billed_energy_kwh,
                        balance.cable_loss_kwh,
                        balance.transformer_core_loss_kwh,
                        balance.transformer_copper_loss_kwh,
                        balance.total_technical_loss_kwh,
                        balance.unexplained_loss_kwh,
                        balance.loss_percentage
                    ))

                    # Aggregate for daily audit log
                    audit_key = (f_id, day)
                    if audit_key not in audit_rows_by_feeder_day:
                        audit_rows_by_feeder_day[audit_key] = {
                            "date": date_str,
                            "supplied": 0.0,
                            "billed": 0.0,
                            "cable": 0.0,
                            "core": 0.0,
                            "copper": 0.0,
                            "technical": 0.0,
                            "unexplained": 0.0
                        }

                    entry = audit_rows_by_feeder_day[audit_key]
                    entry["supplied"] += balance.supplied_energy_kwh
                    entry["billed"] += balance.billed_energy_kwh
                    entry["cable"] += balance.cable_loss_kwh
                    entry["core"] += balance.transformer_core_loss_kwh
                    entry["copper"] += balance.transformer_copper_loss_kwh
                    entry["technical"] += balance.total_technical_loss_kwh
                    entry["unexplained"] += balance.unexplained_loss_kwh

        # Build 150 daily loss audit log records
        audit_rows = []
        for (f_id, day), vals in audit_rows_by_feeder_day.items():
            sup = vals["supplied"]
            bil = vals["billed"]
            cab = vals["cable"]
            cor = vals["core"]
            cop = vals["copper"]

            rec = reconcile_energy_balance(
                supplied_energy_kwh=sup,
                billed_energy_kwh=bil,
                cable_loss_kwh=cab,
                transformer_core_loss_kwh=cor,
                transformer_copper_loss_kwh=cop
            )

            audit_rows.append((
                vals["date"],
                f_id,
                day,
                rec.supplied_energy_kwh,
                rec.billed_energy_kwh,
                rec.cable_loss_kwh,
                rec.transformer_core_loss_kwh,
                rec.transformer_copper_loss_kwh,
                rec.total_technical_loss_kwh,
                rec.unexplained_loss_kwh,
                rec.total_distribution_loss_kwh,
                rec.loss_percentage,
                rec.reconciliation_residual_kwh
            ))

        return consumer_rows, feeder_rows, audit_rows

def generate_complete_dataset(verbose: bool = True) -> Dict[str, int]:
    """
    Executes full simulation and populates SQLite database.
    Ensures:
    - 5 Feeders
    - 5 Transformers
    - 500 Consumers
    - 360,000 Consumer Readings
    - 3,600 Feeder Readings
    - 150 Loss Audit Logs
    """
    if verbose:
        print("Starting synthetic data simulation for Electricity Theft & Loss Detection...")

    simulator = DataSimulator()
    feeders, transformers = simulator.generate_feeders_and_transformers()
    consumers = simulator.generate_consumers()

    if verbose:
        print(f"Generated metadata: {len(feeders)} feeders, {len(transformers)} transformers, {len(consumers)} consumers.")
        print("Simulating 720 hourly intervals (30 days x 24 hrs)...")

    consumer_readings, feeder_readings, loss_audit_logs = simulator.simulate_hourly_readings(
        consumers, feeders, transformers
    )

    if verbose:
        print(f"Readings generated: {len(consumer_readings)} consumer readings, {len(feeder_readings)} feeder readings, {len(loss_audit_logs)} audit logs.")
        print("Inserting records into SQLite database...")

    # Clear existing simulation data and insert safely
    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("DELETE FROM inspection_records;")
        conn.execute("DELETE FROM theft_predictions;")
        conn.execute("DELETE FROM loss_audit_logs;")
        conn.execute("DELETE FROM feeder_readings;")
        conn.execute("DELETE FROM consumer_readings;")
        conn.execute("DELETE FROM consumers;")
        conn.execute("DELETE FROM transformers;")
        conn.execute("DELETE FROM feeders;")

        # Insert Feeders
        conn.executemany(
            """INSERT INTO feeders (feeder_id, name, substation_name, nominal_voltage_kv, conductor_resistance_ohm, length_km)
               VALUES (:feeder_id, :name, :substation_name, :nominal_voltage_kv, :conductor_resistance_ohm, :length_km)""",
            feeders
        )

        # Insert Transformers
        conn.executemany(
            """INSERT INTO transformers (transformer_id, feeder_id, capacity_kva, core_loss_kw, rated_copper_loss_kw)
               VALUES (:transformer_id, :feeder_id, :capacity_kva, :core_loss_kw, :rated_copper_loss_kw)""",
            transformers
        )

        # Insert Consumers
        conn.executemany(
            """INSERT INTO consumers (consumer_id, feeder_id, transformer_id, tariff_category, sanctioned_load_kw, meter_id, simulation_scenario)
               VALUES (:consumer_id, :feeder_id, :transformer_id, :tariff_category, :sanctioned_load_kw, :meter_id, :simulation_scenario)""",
            consumers
        )

        # Bulk Insert Consumer Readings in chunks of 20,000 for fast I/O
        chunk_size = 20000
        for i in range(0, len(consumer_readings), chunk_size):
            chunk = consumer_readings[i:i + chunk_size]
            conn.executemany(
                """INSERT INTO consumer_readings (consumer_id, timestamp, day_number, hour, actual_consumption_kwh, billed_consumption_kwh, meter_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                chunk
            )

        # Insert Feeder Readings
        conn.executemany(
            """INSERT INTO feeder_readings (feeder_id, timestamp, day_number, hour, supplied_energy_kwh, total_billed_kwh,
                                            cable_loss_kwh, transformer_core_loss_kwh, transformer_copper_loss_kwh,
                                            technical_loss_kwh, unexplained_loss_kwh, loss_percentage)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            feeder_readings
        )

        # Insert Loss Audit Logs
        conn.executemany(
            """INSERT INTO loss_audit_logs (audit_date, feeder_id, day_number, supplied_energy_kwh, billed_energy_kwh,
                                           cable_loss_kwh, transformer_core_loss_kwh, transformer_copper_loss_kwh,
                                           technical_loss_kwh, unexplained_loss_kwh, total_distribution_loss_kwh,
                                           loss_percentage, reconciliation_residual_kwh)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            loss_audit_logs
        )

        # Update system setting
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, description) VALUES ('last_simulation_run', ?, 'Timestamp of last simulation')",
            (now_str,)
        )

        conn.execute("PRAGMA foreign_keys = ON;")

    if verbose:
        print("Database insertion successfully completed.")

    return {
        "feeders": len(feeders),
        "transformers": len(transformers),
        "consumers": len(consumers),
        "consumer_readings": len(consumer_readings),
        "feeder_readings": len(feeder_readings),
        "loss_audit_logs": len(loss_audit_logs)
    }

if __name__ == "__main__":
    init_db()
    generate_complete_dataset()
