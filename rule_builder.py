# rule_builder.py
from __future__ import annotations
from typing import Any, Dict, Literal, Optional

Operator = Literal["lt", "lte", "gt", "gte", "eq", "between"]
Severity = Literal["low", "medium", "high"]

def make_rule(
    name: str,
    signal: str,
    operator: Operator,
    severity: Severity = "medium",
    *,
    value: Optional[float] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    POC builder: returns a rule dict that is JSON-serializable.
    No validations (MSS assumption).
    """
    cond: Dict[str, Any] = {"signal": signal, "operator": operator}

    if operator == "between":
        cond["min"] = min_value
        cond["max"] = max_value
        if description is None:
            description = f"{signal} between {min_value} and {max_value}"
    else:
        cond["value"] = value
        if description is None:
            description = f"{signal} {operator} {value}"

    return {
        "name": name,
        "severity": severity,
        "description": description,
        "condition": cond,
    }

def make_rule_from_dict(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Create a normalized rule from the fixed dict format.

    Expected input shape:
    {
      "name": str,
      "severity": "low"|"medium"|"high" (optional),
      "description": str (optional),
      "condition": {"signal": str, "operator": str, "value"?: number, "min"?: number, "max"?: number}
    }

    This helper keeps the existing make_rule(...) as the single formatting source.
    """
    if not isinstance(rule, dict):
        raise TypeError("rule must be a dict")

    cond = rule.get("condition")
    if not isinstance(cond, dict):
        raise ValueError("rule['condition'] must be a dict")

    name = rule.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("rule['name'] must be a non-empty string")

    signal = cond.get("signal")
    if not isinstance(signal, str) or not signal:
        raise ValueError("rule['condition']['signal'] must be a non-empty string")

    operator = cond.get("operator")
    if operator not in {"lt", "lte", "gt", "gte", "eq", "between"}:
        raise ValueError("rule['condition']['operator'] must be one of: lt,lte,gt,gte,eq,between")

    sev = rule.get("severity", "medium")
    if sev not in {"low", "medium", "high"}:
        raise ValueError("rule['severity'] must be one of: low,medium,high")

    desc = rule.get("description")

    if operator == "between":
        return make_rule(
            name=name,
            signal=signal,
            operator="between",
            severity=sev,
            min_value=cond.get("min"),
            max_value=cond.get("max"),
            description=desc,
        )

    return make_rule(
        name=name,
        signal=signal,
        operator=operator,  # type: ignore[arg-type]
        severity=sev,
        value=cond.get("value"),
        description=desc,
    )
