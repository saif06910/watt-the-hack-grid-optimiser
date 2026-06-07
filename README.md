# 🔋 Watt The Hack — Australian Energy Grid Optimiser

**City of Melbourne · Watt The Hack 2026 · Advanced Track**

> Physics-aware battery dispatch controllers for 6 simulated Australian distribution grid scenarios.
> Tackles the duck curve, multi-peak demand, AI-driven load spikes, LLM-parsed operator directives,
> and adversarial sensor spoofing — mirroring real challenges faced by Australian network distributors.

---

## Results (Duck Curve — locally verified)

| Controller | Scenario | Cost | Overvoltage | Notes |
|---|---|---|---|---|
| Do nothing | Duck Curve | $1,959,201 | $973,750 | Baseline |
| Rule-based | Duck Curve | $1,895,456 | $973,750 | Price threshold only |
| **level1_duck_curve.py** | Duck Curve | **$858,215** | **$0** | 95.1 / 100 pts |
| **gauntlet.py** | Duck Curve | **$872,532** | **$0** | 83.5 / 100 pts (handles all 6 scenarios) |

---

## What this project is

**Watt The Hack** is a hackathon run by DeepNeuron and the City of Melbourne.
Participants write a Python controller that manages a simulated Australian grid node —
making real-time decisions about battery storage, solar curtailment, and diesel backup
to minimise total energy costs over a 72-hour run.

The challenge directly mirrors what Australian network distributors deal with every day:
integrating large-scale solar while managing export limits, volatile AEMO spot prices,
and unexpected demand events.

---

## How the simulation works

The engine runs in **15-minute steps** (288 steps = 3 days). Every step, your
`controller(state)` function (or `Strategy.step(state)`) receives the current grid
snapshot and must return an action:

```
Every 15 minutes:

  state ──► your controller ──► action ──► engine simulates ──► cost
  (demand,                      (battery,   physics + AEMO
   solar,                        diesel,     market)
   price,                        curtail)
   soc ...)

  score = sum of cost over all 288 steps   (lower wins)
```

**State inputs:**

| Key | Description |
|---|---|
| `demand` | City-wide electricity demand (MW) |
| `solar` | Solar generation this step (MW) |
| `soc` | Battery state of charge (0.0 = empty, 1.0 = full) |
| `price` | AEMO spot market import tariff ($/MWh, range −$50 to $550) |
| `forecast` | Lookahead arrays for demand / solar / price (unlocked in later levels) |
| `alerts` | Operator directives and cyber alerts as prose (agentic levels) |

**Actions returned:**

| Key | Description |
|---|---|
| `battery_flow_mw` | Positive = discharge to grid · Negative = charge from grid |
| `emergency_generator` | MW of diesel backup (expensive — last resort) |
| `curtail_solar` | MW of solar to disconnect (prevents overvoltage if battery full) |
| `fcas_reserve_mw` | MW reserved for frequency control (advanced levels) |

---

## The duck curve problem

On a sunny day in an Australian city, net demand (demand − solar) follows a characteristic
"duck" shape: a belly during the midday solar surplus, and a steep neck as solar drops and
evening demand spikes. This creates two expensive problems:

- **Midday**: solar exceeds demand, surplus floods toward the 50 MW export cap → overvoltage penalty
- **Evening**: solar is gone, demand peaks → expensive grid imports at $400–550/MWh

A do-nothing controller pays **$1,959,201** over 3 days — almost entirely from these two problems.
The Level 1 controller eliminates the overvoltage penalty entirely and cuts total cost to **$858,215**.

---

## Scenarios and controllers

### Level 1 — The Duck Curve  `level1_duck_curve.py`

**Challenge:** 3-day synthetic scenario. Solar surplus at midday, steep evening demand ramp.
No forecast available — react to current telemetry only.

**Approach:**
1. Absorb every MW of solar surplus into the battery before it hits the 50 MW export cap
2. Discharge at two price tiers: ≥$470/MWh (full demand offset) and ≥$425/MWh (selective)
3. Shave demand peaks above 100 MW to avoid monthly demand charges
4. Diesel and curtailment only as last resort

**Key result:** overvoltage penalty drops from $973,750 → $0. Total cost $858,215 (95.1/100 pts).

---

### Level 2 — Frequency Frenzy Melbourne  `level2_frequency_frenzy.py`

**Challenge:** Cold Tuesday in Melbourne. Four demand peaks across the day.
**The most expensive peak is pre-dawn** — heating demand spikes before sunrise, before solar can help.
AEMO data shows the 6 AM heating spike regularly outprices the evening peak.
Controllers that save their battery charge for dusk miss the most valuable window.

**Approach:**
- Use `forecast["price"]` with a 4-hour lookahead window
- Identify when a price spike is approaching (`max_future > price × 2.5`)
- Pre-charge overnight when power is cheap and the pre-dawn spike is 4 hours away
- Deploy battery into the dawn spike, not the dusk ramp

---

### Level 3 — AI Grid Shock  `level3_ai_grid_shock.py`

**Challenge:** OpenAI-scale datacentre load creates volatile demand. GPU clusters saturate and
**demand jumps 60 MW in a single step**. The spot price takes several more steps to catch up.
Controllers that wait for price to confirm the spike have already imported the expensive MW.

**Approach:**
- Maintain an 8-step rolling demand baseline
- Detect sudden demand delta > 30 MW (datacentre saturation event)
- On spike detection: discharge immediately — before price catches up
- Normal price-based dispatch otherwise

---

### Level 4 — The Operator's Mandate  `level4_operators_mandate.py`

**Challenge:** Over 3 days, operator directives arrive as prose in `state["alerts"]`.
Some are real grid mandates (AEMO reserve requirements, SES life-safety directives).
Some are phishing emails and vendor newsletters. The controller must:
- Distinguish real directives from spam (using LLM)
- Parse implicit numerics ("one fifth of capacity" = 0.20, "raise by 20 pp" = +0.20)
- Arbitrate conflicts (SES safety directives override AEMO economic ones)
- Maintain mandated SOC reserve floors while still optimising dispatch

**Approach:**
- `plan()` and `replan()` call GPT-4o-mini to classify each alert and extract reserve targets
- `step()` never calls the LLM — acts only on cached reserve target
- Safety directives (SES) lock in their reserve floors over economic ones
- OPENAI_API_KEY auto-injected by eval cluster; no `.env` needed in submission

---

### Level 5 — Cybersecurity Sandbox  `level5_cybersecurity.py`

**Challenge:** Sensors are under attack. Some readings are real; others are spoofed injections.
The forecast itself may lie during the attack window.

**Detection rules (from scenario spec):**
- Real anomaly → shows up in **both** the meter and the forecast
- Sensor spoof → shows up in the **meter only** (forecast is still clean)
- SOC spoof → reported SOC diverges from dispatch-tracked estimate

**Approach:**
- Cross-corroborate every reading: if meter and forecast disagree by >40 MW (demand) or >30 MW (solar), trust the forecast
- Self-track SOC by integrating every dispatch action (charge efficiency × flow × step duration)
- If self-tracked SOC diverges from reported SOC by >15%, use self-tracked value
- Normal dispatch logic on the trusted (de-spoofed) values

---

### The Gauntlet (3x weight · 1 submission)  `gauntlet.py`

**Challenge:** The Gauntlet runs all scenarios. One submission. 3× the points weight.

**Approach:** combines all five techniques in one `Strategy` class:
- Solar surplus absorption (L1)
- Forecast-based pre-charging for dawn spikes (L2)
- Demand-delta spike detection for datacentre events (L3)
- LLM directive parsing with phishing filter (L4)
- Cross-corroborated sensor trust + self-tracked SOC (L5)

The architecture uses `plan()` / `replan()` for slow LLM calls and `step()` for fast per-tick dispatch — meeting the 14-minute total wall-clock budget.

**Duck Curve result:** $872,532 · 83.5/100 pts · $0 overvoltage

---

## How to run locally

**1. Install**

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install "watt-the-hack[playtest]"
```

**2. Run any controller**

```bash
python level1_duck_curve.py       # best score on L1
python gauntlet.py                # universal controller
```

Each script runs against `duck_curve` (bundled locally), prints a cost breakdown,
and opens an HTML report with per-step charts.

**3. Compare controllers side by side**

```bash
python -m watt_the_hack.playtest level1_duck_curve.py gauntlet.py --scenario duck_curve
```

**4. List available local scenarios**

```bash
python -m watt_the_hack.playtest --list-scenarios
# duck_curve    — The Duck Curve (synthetic)
# agentic_demo  — Agentic Demo (LLM / plan-replan track)
```

> Levels 2–5 and the Gauntlet are scored server-side by the hackathon platform.
> Local runs use `duck_curve` or `agentic_demo` to verify controller logic before submission.

---

## Key concepts

**BESS (Battery Energy Storage System)** — buffers variable solar against stable demand. Charge when surplus / cheap, discharge when scarce / expensive.

**Duck curve** — net demand (demand − solar) across a sunny day looks like a duck: belly = midday solar surplus, neck = steep evening ramp.

**Overvoltage** — when solar export exceeds the 50 MW grid cap, voltage rises beyond safe levels. The penalty models frequency regulation and hardware stress.

**AEMO spot market** — Australian Energy Market Operator sets a spot price every 5 minutes, ranging from −$50/MWh (oversupply) to $550/MWh (scarcity). Optimal dispatch times battery use around these extremes.

**Demand charges** — monthly charge levied on the single peak 15-minute import reading. Keeping imports below 100 MW eliminates or reduces this.

**FCAS (Frequency Control Ancillary Services)** — paid service where battery inverter capacity is reserved to stabilise grid frequency. Unlocked in Level 4 and the Gauntlet.

---

## Project structure

```
watt-the-hack-grid-optimiser/
├── level1_duck_curve.py        # L1: solar surplus + evening peak
├── level2_frequency_frenzy.py  # L2: forecast-aware pre-dawn pre-charging
├── level3_ai_grid_shock.py     # L3: demand-delta spike detection
├── level4_operators_mandate.py # L4: LLM directive parsing + phishing filter
├── level5_cybersecurity.py     # L5: sensor cross-corroboration + self-tracked SOC
├── gauntlet.py                 # Gauntlet: all techniques combined
├── requirements.txt
└── README.md
```

---

## Tech stack

- **Python 3.10+**
- [`watt-the-hack`](https://pypi.org/project/watt-the-hack/) — simulation engine by DeepNeuron / City of Melbourne
- `openai` — GPT-4o-mini for agentic directive parsing (Levels 4 & 5)
- `matplotlib` — per-step visualisation (via engine's playtest extra)

---

## About

Built for **Watt The Hack 2026**, organised by [DeepNeuron](https://deepneuron.org) and the City of Melbourne.
Simulation engine open-sourced at [AaronEliasZachariah/City-of-Melbourne-Watt-the-Hack-Advanced-Track](https://github.com/AaronEliasZachariah/City-of-Melbourne-Watt-the-Hack-Advanced-Track).
