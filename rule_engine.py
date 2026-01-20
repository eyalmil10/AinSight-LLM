def detect_events(df, rules):
    events = []

    for rule in rules:
        name = rule["name"]
        signal = rule["signal"]
        severity = rule["severity"]
        desc = rule["description"]

        if "window" in rule:
            w = rule["window"]
            for i in range(w, len(df)):
                window_vals = df[signal].iloc[i-w:i].values
                if rule["condition"](window_vals):
                    events.append({
                        "time": float(df.loc[i, "time"]),
                        "event": name,
                        "severity": severity,
                        "details": desc
                    })

        elif rule["condition"].__code__.co_argcount == 2:
            for i in range(1, len(df)):
                curr = df.loc[i, signal]
                prev = df.loc[i-1, signal]
                if rule["condition"](curr, prev):
                    events.append({
                        "time": float(df.loc[i, "time"]),
                        "event": name,
                        "severity": severity,
                        "details": desc
                    })

        else:
            for i in range(len(df)):
                val = df.loc[i, signal]
                if rule["condition"](val):
                    events.append({
                        "time": float(df.loc[i, "time"]),
                        "event": name,
                        "severity": severity,
                        "details": desc
                    })

    return events
