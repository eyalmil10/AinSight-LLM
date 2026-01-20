import json
import pandas as pd
from tzarfati_func import call_claude_sonnet


# -------- 1. Load CSV --------
df = pd.read_csv("flight.csv")

# -------- 2. Deterministic analysis --------
altitude_min = df["altitude"].min()
altitude_max = df["altitude"].max()
vertical_speed_min = df["vertical_speed"].min()

events = []

# זיהוי ירידה חדה פשוטה
for i in range(1, len(df)):
    if df.loc[i, "vertical_speed"] < -1.5:
        events.append({
            "time": float(df.loc[i, "time"]),
            "type": "rapid_descent",
            "details": "vertical_speed below -1.5 m/s"
        })

# -------- 3. Facts JSON (האמת היחידה) --------
facts = {
    "stats": {
        "altitude_min": float(altitude_min),
        "altitude_max": float(altitude_max),
        "vertical_speed_min": float(vertical_speed_min)
    },
    "events_detected": events,
    "domain_context": "Drone flight test"
}

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
- Use only the provided facts
- Do not invent data
- Output valid JSON only

Facts:
{json.dumps(facts, indent=2)}
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
