from turtle import pd
import pandas as pnd

def detect_events(df, rules):
    events = []

    def _emit(i, name, severity, desc):
        events.append(
            {
                "time": float(df.loc[i, "time"]),
                "event": name,
                "severity": severity,
                "details": desc,
            }
        )

    def _eval_condition_dict(cond: dict, val):
        op = cond.get("operator")
        if op == "between":
            mn = cond.get("min")
            mx = cond.get("max")
            if mn is None or mx is None:
                return False
            return mn <= val <= mx

        target = cond.get("value")
        if target is None:
            return False

        if op == "lt":
            return val < target
        if op == "lte":
            return val <= target
        if op == "gt":
            return val > target
        if op == "gte":
            return val >= target
        if op == "eq":
            return val == target

        return False

    for rule in rules:
        name = rule.get("name")
        severity = rule.get("severity")
        desc = rule.get("description")

        # New format: condition is a dict with signal/operator/... inside it
        cond = rule.get("condition")
        if isinstance(cond, dict):
            signal = cond.get("signal")
            if not signal:
                continue

            # POC: dict-based conditions are single-sample evaluators
            for i in range(len(df)):
                val = df.loc[i, signal]
                if _eval_condition_dict(cond, val):
                    _emit(i, name, severity, desc)
            continue

        # Legacy format: top-level signal and callable condition
        signal = rule.get("signal")
        condition_callable = rule.get("condition")

        if not signal or not callable(condition_callable):
            continue

        if "window" in rule:
            w = rule["window"]
            for i in range(w, len(df)):
                window_vals = df[signal].iloc[i - w : i].values
                if condition_callable(window_vals):
                    _emit(i, name, severity, desc)

        elif getattr(condition_callable, "__code__", None) is not None and condition_callable.__code__.co_argcount == 2:
            for i in range(1, len(df)):
                curr = df.loc[i, signal]
                prev = df.loc[i - 1, signal]
                if condition_callable(curr, prev):
                    _emit(i, name, severity, desc)

        else:
            for i in range(len(df)):
                val = df.loc[i, signal]
                if condition_callable(val):
                    _emit(i, name, severity, desc)

    return events


def main():
    # -------- 1. Load CSV --------
    df = pnd.read_csv("flight.csv")
    rule = {'name': 'rapid_descent', 'severity': 'medium', 'description': 'vertical_speed lt -1.5', 'condition': {'signal': 'vertical_speed', 'operator': 'lt', 'value': -1.5}}
    events = detect_events(df, [rule])
    print (events)

#main()