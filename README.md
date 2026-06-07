# Watt The Hack 2026 — Hackathon

Controllers built for the **Watt The Hack 2026 Hackathon** run by DeepNeuron and the City of Melbourne.

The challenge: manage a simulated Australian electricity grid node over 72 hours. You control a battery, a diesel generator, and solar panels — your job is to charge when power is cheap, discharge when it's expensive, and keep the grid stable. Lower cost wins.

---

## The six scenarios

**Duck Curve** — Solar floods the grid at midday, demand spikes at sunset. No forecast available, react to what you see.

**Frequency Frenzy** — Four demand peaks across a cold Melbourne Tuesday. The most expensive one hits before sunrise, not in the evening.

**AI Grid Shock** — A datacentre load jumps 60 MW in one step. The price signal takes a few steps to catch up, so you need to act before the price confirms it.

**The Operator's Mandate** — Directives arrive as plain text every few hours. Some are real grid instructions, some are phishing emails. Parse them, filter the spam, follow the legitimate ones.

**Cybersecurity Sandbox** — Sensor readings are being spoofed. Cross-check the meter against the forecast before trusting any value.

**The Gauntlet** — All of the above in one controller.

---

## Running it

```bash
pip install -r requirements.txt
python controllers/duck_curve.py
```

Runs a 72-hour simulation, prints costs, and opens a report in your browser.

> `operators_mandate.py` and `gauntlet.py` need `OPENAI_API_KEY` set in your environment.