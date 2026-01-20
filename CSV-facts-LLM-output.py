import json
import pandas as pd
from tzarfati_func import call_claude_sonnet
from rule_engine import detect_events

# Prefer explicit imports rather than star-imports
from extract_CSV_columns import extract_csv_columns, build_facts_from_csv_and_events


# -------- 1. Load CSV --------
# df = pd.read_csv("flight.csv")
df = pd.read_csv("NavGpsMetry.csv")

# -------- 2. Deterministic analysis --------
""" altitude_min = df["altitude"].min()
altitude_max = df["altitude"].max()
vertical_speed_min = df["vertical_speed"].min() """

events = []

signals = extract_csv_columns("NavGpsMetry.csv")
#signals = extract_csv_columns("flight.csv")
print(signals)
rc = RuleCreator(available_signals=signals, use_llm=True)

print("RuleCreator (type 'exit' to stop)")
print(rc.start())

while True:
    user = input("> ").strip()
    if user.lower() in {"exit", "quit"}:
        break
    out = rc.handle(user)
    if isinstance(out, dict):
        print(out.get("message", ""))
        print("Final rule:")
        print("rule:", out["rule"])
        rule = out["rule"]
        break
    print(out)

rule = {'name': 'rapid_descent', 'severity': 'medium', 'description': 'vertical_speed lt -1.5', 'condition': {'signal': 'vertical_speed', 'operator': 'lt', 'value': -1.5}}

# זיהוי כללי של אירוע
events = detect_events(df, [rule])

# -------- 3. Facts JSON (האמת היחידה) --------
""" facts = {
    "stats": {
        "altitude_min": float(altitude_min),
        "altitude_max": float(altitude_max),
        "vertical_speed_min": float(vertical_speed_min)
    },
    "events_detected": events,
    "domain_context": "Drone flight test"
} """

# ✅ build_facts_from_csv_and_events expects a CSV path, not the signals list
# facts = build_facts_from_csv_and_events("flight.csv", events, domain_context="Drone flight test")

# print("Facts:", facts)
# -------- 4. Schema --------
schema = {
    "run_summary": {
        "one_liner": "string",
        "overall_status": "normal | warning | failed"
    },
    "key_events": [
        {
            "time": "number",
            "event": "string",
            "severity": "low | medium | high",
            "explanation": "string"
        }
    ],
    "possible_causes": [
        {
            "cause": "string",
            "confidence": "low | medium | high"
        }
    ],
    "recommended_checks": ["string"]
}

# -------- 5. Prompt --------
prompt = f"""
You are an analysis assistant.

Produce a JSON that strictly follows this schema:
{json.dumps(schema, indent=2)}

Rules:
- Use only the provided events
- Do not invent data
- Output valid JSON only

Events:
{json.dumps(events, indent=2)}
"""

# -------- 6. LLM Call --------
# response = client.chat.completions.create(
    # model="gpt-4o-mini",
    # messages=[{"role": "user", "content": prompt}],
    # temperature=0
# )

response = call_claude_sonnet( prompt )

# -------- 7. Result --------
result = response
print(result)

# אופציונלי: ולידציה
#json.loads(result)
