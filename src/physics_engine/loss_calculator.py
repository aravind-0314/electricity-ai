"""
Electrical Physics Engine for Electricity Distribution Loss Calculations.

Formulas & Principles:
1. Three-Phase Line Current:
   I = P / (sqrt(3) * V_LL * pf)
   where:
     P = Total 3-phase active power in kW
     V_LL = Line-to-line voltage in kV (e.g. 11.0 kV)
     pf = Power factor (dimensionless, ~0.92)
     I = Line current in Amperes (A)

2. Three-Phase Cable Power Loss (I^2 * R):
   P_cable = 3 * I^2 * R_phase / 1000  (kW)
   Energy Loss (kWh) = P_cable * Delta_t (hours)

3. Transformer Losses:
   P_transformer = P_core + P_copper
   - Core Loss (Iron Loss): Constant no-load excitation loss in kW.
   - Copper Loss (Ohmic Loss): P_copper = P_copper_rated * (S / S_rated)^2
     where S is apparent power (kVA).

4. Energy Balance Reconciliation:
   E_supplied = E_billed + E_technical + E_unexplained + Residual
   where:
     E_technical = E_cable + E_transformer_core + E_transformer_copper
     E_unexplained = max(0.0, E_supplied - E_billed - E_technical)
     Residual = E_supplied - (E_billed + E_technical + E_unexplained)
"""

import math
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class TechnicalLossResult:
    cable_loss_kwh: float
    transformer_core_loss_kwh: float
    transformer_copper_loss_kwh: float
    total_technical_loss_kwh: float
    line_current_amperes: float
    apparent_power_kva: float

@dataclass
class EnergyBalanceResult:
    supplied_energy_kwh: float
    billed_energy_kwh: float
    cable_loss_kwh: float
    transformer_core_loss_kwh: float
    transformer_copper_loss_kwh: float
    total_technical_loss_kwh: float
    unexplained_loss_kwh: float
    total_distribution_loss_kwh: float
    loss_percentage: float
    reconciliation_residual_kwh: float
    is_reconciled: bool

def calculate_line_current(
    active_power_kw: float,
    nominal_voltage_kv: float = 11.0,
    power_factor: float = 0.92
) -> float:
    """
    Calculate 3-phase line current in Amperes.
    I = P / (sqrt(3) * V_LL * pf)
    """
    if active_power_kw <= 0.0 or nominal_voltage_kv <= 0.0 or power_factor <= 0.0:
        return 0.0
    # active_power_kw * 1000 gives Watts; nominal_voltage_kv * 1000 gives Volts
    # I = (P_kW * 1000) / (sqrt(3) * (V_kV * 1000) * pf) = P_kW / (sqrt(3) * V_kV * pf)
    current = active_power_kw / (math.sqrt(3.0) * nominal_voltage_kv * power_factor)
    return max(0.0, float(current))

def calculate_cable_loss(
    line_current_amperes: float,
    resistance_ohm: float,
    duration_hours: float = 1.0
) -> float:
    """
    Calculate 3-phase conductor ohmic loss in kWh.
    P_cable = 3 * I^2 * R / 1000 (in kW)
    Energy (kWh) = P_cable * duration_hours
    """
    if line_current_amperes <= 0.0 or resistance_ohm <= 0.0 or duration_hours <= 0.0:
        return 0.0
    power_loss_kw = (3.0 * (line_current_amperes ** 2) * resistance_ohm) / 1000.0
    energy_loss_kwh = power_loss_kw * duration_hours
    return max(0.0, float(round(energy_loss_kwh, 6)))

def calculate_transformer_losses(
    apparent_power_kva: float,
    rated_capacity_kva: float,
    core_loss_kw: float,
    rated_copper_loss_kw: float,
    duration_hours: float = 1.0
) -> tuple[float, float]:
    """
    Calculate transformer core (iron) and copper (winding) losses in kWh.
    Core loss is constant under energization.
    Copper loss varies with (S / S_rated)^2.
    """
    if duration_hours <= 0.0:
        return 0.0, 0.0
    
    # Core loss (no-load excitation loss)
    core_energy_kwh = max(0.0, core_loss_kw * duration_hours)

    # Copper loss (load dependent)
    if rated_capacity_kva <= 0.0 or apparent_power_kva <= 0.0:
        copper_energy_kwh = 0.0
    else:
        loading_ratio = min(apparent_power_kva / rated_capacity_kva, 1.5)  # Cap at 150% overload
        copper_power_kw = rated_copper_loss_kw * (loading_ratio ** 2)
        copper_energy_kwh = max(0.0, copper_power_kw * duration_hours)

    return float(round(core_energy_kwh, 6)), float(round(copper_energy_kwh, 6))

def calculate_hourly_technical_loss(
    supplied_power_kw: float,
    resistance_ohm: float,
    transformer_rated_kva: float,
    transformer_core_loss_kw: float,
    transformer_rated_copper_kw: float,
    nominal_voltage_kv: float = 11.0,
    power_factor: float = 0.92,
    duration_hours: float = 1.0
) -> TechnicalLossResult:
    """Calculate all technical loss components for an hourly interval."""
    # Current
    current = calculate_line_current(supplied_power_kw, nominal_voltage_kv, power_factor)
    
    # Apparent power S = P / pf
    apparent_power_kva = (supplied_power_kw / power_factor) if power_factor > 0 else supplied_power_kw

    # Cable loss
    cable_loss = calculate_cable_loss(current, resistance_ohm, duration_hours)

    # Transformer losses
    core_loss, copper_loss = calculate_transformer_losses(
        apparent_power_kva=apparent_power_kva,
        rated_capacity_kva=transformer_rated_kva,
        core_loss_kw=transformer_core_loss_kw,
        rated_copper_loss_kw=transformer_rated_copper_kw,
        duration_hours=duration_hours
    )

    total_tech = cable_loss + core_loss + copper_loss

    return TechnicalLossResult(
        cable_loss_kwh=round(cable_loss, 4),
        transformer_core_loss_kwh=round(core_loss, 4),
        transformer_copper_loss_kwh=round(copper_loss, 4),
        total_technical_loss_kwh=round(total_tech, 4),
        line_current_amperes=round(current, 3),
        apparent_power_kva=round(apparent_power_kva, 3)
    )

def reconcile_energy_balance(
    supplied_energy_kwh: float,
    billed_energy_kwh: float,
    cable_loss_kwh: float,
    transformer_core_loss_kwh: float,
    transformer_copper_loss_kwh: float,
    tolerance_kwh: float = 0.01
) -> EnergyBalanceResult:
    """
    Reconciles:
    Supplied Energy = Billed Energy + Technical Losses + Unexplained Losses + Residual
    """
    supplied = max(0.0, float(supplied_energy_kwh))
    billed = max(0.0, float(billed_energy_kwh))
    cable = max(0.0, float(cable_loss_kwh))
    core = max(0.0, float(transformer_core_loss_kwh))
    copper = max(0.0, float(transformer_copper_loss_kwh))
    
    total_tech = cable + core + copper

    # Unexplained loss cannot be negative (if billed + tech > supplied due to edge timing, unexplained is 0)
    raw_unexplained = supplied - (billed + total_tech)
    unexplained = max(0.0, raw_unexplained)

    total_loss = total_tech + unexplained
    
    # Exact residual check: supplied - (billed + tech + unexplained)
    residual = supplied - (billed + total_tech + unexplained)
    is_reconciled = abs(residual) <= tolerance_kwh

    loss_pct = (total_loss / supplied * 100.0) if supplied > 0 else 0.0

    return EnergyBalanceResult(
        supplied_energy_kwh=round(supplied, 3),
        billed_energy_kwh=round(billed, 3),
        cable_loss_kwh=round(cable, 3),
        transformer_core_loss_kwh=round(core, 3),
        transformer_copper_loss_kwh=round(copper, 3),
        total_technical_loss_kwh=round(total_tech, 3),
        unexplained_loss_kwh=round(unexplained, 3),
        total_distribution_loss_kwh=round(total_loss, 3),
        loss_percentage=round(loss_pct, 2),
        reconciliation_residual_kwh=round(residual, 5),
        is_reconciled=is_reconciled
    )

