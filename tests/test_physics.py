import pytest
from src.physics_engine.loss_calculator import (
    calculate_line_current,
    calculate_cable_loss,
    calculate_transformer_losses,
    calculate_hourly_technical_loss,
    reconcile_energy_balance
)

def test_line_current_calculation():
    """Verify 3-phase line current formula: I = P / (sqrt(3) * V_LL * pf)."""
    # 500 kW at 11 kV, 0.92 pf
    # I = 500 / (1.73205 * 11 * 0.92) = 500 / 17.5283 = ~28.525 A
    current = calculate_line_current(500.0, 11.0, 0.92)
    assert 28.0 < current < 29.0
    # Zero input should return 0.0
    assert calculate_line_current(0.0) == 0.0
    assert calculate_line_current(-10.0) == 0.0

def test_cable_loss_calculation():
    """Verify cable loss: P = 3 * I^2 * R / 1000 kW."""
    current = 28.525
    r = 0.40  # ohms
    # 3 * 28.525^2 * 0.40 / 1000 = 3 * 813.67 * 0.40 / 1000 = 0.9764 kWh
    loss = calculate_cable_loss(current, r, 1.0)
    assert 0.95 < loss < 1.05
    assert calculate_cable_loss(0.0, r) == 0.0

def test_transformer_losses():
    """Verify core is constant and copper scales with apparent power squared."""
    core_kw = 1.5
    copper_rated_kw = 8.0
    rated_s = 1000.0

    # At 50% load
    s_half = 500.0
    core, copper = calculate_transformer_losses(s_half, rated_s, core_kw, copper_rated_kw, 1.0)
    assert core == 1.5
    # Copper should be ~25% of rated (8.0 * 0.25 = 2.0 kW)
    assert abs(copper - 2.0) < 0.05

def test_energy_balance_reconciliation():
    """
    Verify:
    Supplied Energy = Billed Energy + Technical Losses + Unexplained Losses + Residual
    Residual must be <= 0.01 kWh tolerance.
    """
    supplied = 1000.0
    billed = 850.0
    cable = 25.0
    core = 10.0
    copper = 15.0

    result = reconcile_energy_balance(supplied, billed, cable, core, copper)
    assert result.is_reconciled is True
    assert result.total_technical_loss_kwh == 50.0
    assert result.unexplained_loss_kwh == 100.0
    assert result.total_distribution_loss_kwh == 150.0
    assert result.loss_percentage == 15.0
    assert abs(result.reconciliation_residual_kwh) < 0.001

