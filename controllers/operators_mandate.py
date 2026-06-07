"""
The Operator's Mandate — Level 4

Directives arrive as prose over 3 days. Some are real grid mandates
from AEMO or SES. Some are phishing. The controller parses each alert
via GPT-4o-mini, filters out spam, and adjusts its SOC reserve floor
based on legitimate instructions.

OPENAI_API_KEY is auto-injected on the eval pod.
For local testing: set OPENAI_API_KEY in your shell environment.

Run:
    python controllers/operators_mandate.py
"""

import json
from openai import OpenAI


SYSTEM_PROMPT = """You are an Australian grid control-room assistant.
Analyse ONE operator alert. Reply ONLY with valid JSON:
{
  "is_real": true | false,
  "reserve_soc": <float 0.0-1.0 or null>,
  "is_safety": true | false,
  "summary": "<10-word description>"
}
Real directives come from AEMO, SES, network operators, or grid control.
Spam/phishing: vendor newsletters, marketing, fake alerts with links or credential requests.
Reserve parsing: "one fifth" = 0.20, "raise by 20 pp" = add 0.20, "40% reserve" = 0.40.
SES safety directives override AEMO economic ones."""


class Strategy:
    def __init__(self):
        try:
            self.client = OpenAI()
            self.llm_ok = True
        except Exception:
            self.client = None
            self.llm_ok = False

        self.reserve_soc = 0.0
        self.is_safety   = False

    def _parse_alert(self, alert):
        if not self.llm_ok:
            return
        text = f"TITLE: {alert.get('title', '')}\nBODY: {alert.get('description', '')}"
        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": text},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=120,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            if data.get("is_real"):
                floor = data.get("reserve_soc")
                if isinstance(floor, (int, float)):
                    if data.get("is_safety") or not self.is_safety:
                        self.reserve_soc = float(floor)
                        self.is_safety   = bool(data.get("is_safety", False))
        except Exception:
            pass

    def plan(self, state):
        for alert in state.get("alerts", []):
            self._parse_alert(alert)
        return {}

    def replan(self, state, alerts):
        for alert in alerts:
            self._parse_alert(alert)
        return {}

    def step(self, state):
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

        floor   = self.reserve_soc
        surplus = solar - demand
        flow    = 0.0

        if (surplus > 0.0 or price <= 0.0) and soc < 1.0:
            headroom = (1.0 - soc) * BATTERY_MWH / CHARGE_EFF / STEP_HOURS
            desired  = max(surplus, INVERTER_MW if price <= 0.0 else 0.0)
            flow     = -min(INVERTER_MW, desired, headroom)

        elif soc < floor:
            headroom = (floor - soc) * BATTERY_MWH / CHARGE_EFF / STEP_HOURS
            flow     = -min(INVERTER_MW, headroom)

        elif soc > floor:
            net       = demand - solar
            shave     = max(0.0, net - PEAK_TARGET)
            available = (soc - floor) * BATTERY_MWH * DISCHARGE_EFF / STEP_HOURS

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
            "curtail_solar":       curtail,
            "emergency_generator": emergency,
            "fcas_reserve_mw":     0.0,
        }


if __name__ == "__main__":
    from watt_the_hack.playtest import run_playtest
    result = run_playtest(__file__, "agentic_demo", plots=True, open_report=True)
    print(f"\nTotal cost: ${result['metrics']['final_score']:,.2f}")
    for k, v in sorted(result["breakdown"].items(), key=lambda x: -abs(x[1])):
        if abs(v) > 1e-6 and k != "total":
            print(f"  {k:30s}  ${v:>12,.2f}")