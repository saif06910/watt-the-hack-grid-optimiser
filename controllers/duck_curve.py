"""
Duck Curve — Level 1

Three days on the grid. Solar floods midday, demand spikes at dusk.
No forecast available — decisions based on current telemetry only.

Run:
    python controllers/duck_curve.py
"""

def controller(state):
    demand = float(state["demand"])
    solar  = float(state["solar"])
    soc    = float(state["soc"])
    price  = float(state.get("price", 0.0))

    BATTERY_MWH   = 100.0
    INVERTER_MW   = 50.0
    CHARGE_EFF    = 0.95
    DISCHARGE_EFF = 0.95
    STEP_HOURS    = 0.25
    IMPORT_CAP    = 120.0
    EXPORT_CAP    = 50.0
    PEAK_TARGET   = 100.0

    surplus = solar - demand
    flow    = 0.0

    if (surplus > 0.0 or price <= 0.0) and soc < 1.0:
        headroom = (1.0 - soc) * BATTERY_MWH / CHARGE_EFF / STEP_HOURS
        desired  = max(surplus, INVERTER_MW if price <= 0.0 else 0.0)
        flow     = -min(INVERTER_MW, desired, headroom)

    elif soc > 0.0:
        net        = demand - solar
        shave      = max(0.0, net - PEAK_TARGET)
        available  = soc * BATTERY_MWH * DISCHARGE_EFF / STEP_HOURS

        if price >= 470.0:
            requested = net
        elif price >= 425.0 or shave > 0.0:
            requested = max(shave, net - 86.0)
        else:
            requested = 0.0

        flow = min(INVERTER_MW, requested, available)

    net       = demand - solar - flow
    emergency = min(50.0, max(0.0, net - IMPORT_CAP))
    net      -= emergency
    curtail   = max(0.0, -net - EXPORT_CAP)

    return {
        "battery_flow_mw":     flow,
        "emergency_generator": emergency,
        "curtail_solar":       curtail,
    }


if __name__ == "__main__":
    from watt_the_hack.playtest import run_playtest
    result = run_playtest(__file__, "duck_curve", plots=True, open_report=True)
    print(f"\nTotal cost: ${result['metrics']['final_score']:,.2f}")
    for k, v in sorted(result["breakdown"].items(), key=lambda x: -abs(x[1])):
        if abs(v) > 1e-6 and k != "total":
            print(f"  {k:30s}  ${v:>12,.2f}")