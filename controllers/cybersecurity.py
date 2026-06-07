"""
Cybersecurity Sandbox — Level 5

Sensors are under attack. Some readings are spoofed injections.
A real anomaly appears in both the meter and the forecast.
A spoof only shows up in the meter — the forecast stays clean.
SOC can also be spoofed, so we track it ourselves from dispatch history.

Run:
    python controllers/cybersecurity.py
"""


class Strategy:
    def __init__(self):
        self.own_soc   = 0.5
        self.prev_flow = 0.0

    def _update_soc(self):
        BATTERY_MWH = 100.0
        STEP        = 0.25
        if self.prev_flow < 0:
            self.own_soc = min(1.0, self.own_soc + abs(self.prev_flow) * 0.95 * STEP / BATTERY_MWH)
        else:
            self.own_soc = max(0.0, self.own_soc - self.prev_flow / 0.95 * STEP / BATTERY_MWH)

    def _trust(self, meter, forecast_val, threshold):
        if forecast_val is None:
            return meter
        return forecast_val if abs(meter - forecast_val) > threshold else meter

    def step(self, state):
        self._update_soc()

        forecast = state.get("forecast", {})
        f_demand = (forecast.get("demand", [None]) or [None])[0]
        f_solar  = (forecast.get("solar",  [None]) or [None])[0]

        demand = self._trust(float(state["demand"]), f_demand, threshold=40.0)
        solar  = self._trust(float(state["solar"]),  f_solar,  threshold=30.0)
        price  = float(state.get("price", 0.0))
        soc    = self.own_soc if abs(self.own_soc - float(state["soc"])) > 0.15 else float(state["soc"])

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
            net       = demand - solar
            shave     = max(0.0, net - PEAK_TARGET)
            available = soc * BATTERY_MWH * DISCHARGE_EFF / STEP_HOURS

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

        self.prev_flow = flow
        return {
            "battery_flow_mw":     flow,
            "curtail_solar":       curtail,
            "emergency_generator": emergency,
            "fcas_reserve_mw":     0.0,
        }


if __name__ == "__main__":
    from watt_the_hack.playtest import run_playtest
    result = run_playtest(__file__, "duck_curve", plots=True, open_report=True)
    print(f"\nTotal cost: ${result['metrics']['final_score']:,.2f}")
    for k, v in sorted(result["breakdown"].items(), key=lambda x: -abs(x[1])):
        if abs(v) > 1e-6 and k != "total":
            print(f"  {k:30s}  ${v:>12,.2f}")