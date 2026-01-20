# rule_core.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union


Operator = Literal["lt", "lte", "gt", "gte", "eq", "between"]
Severity = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ValidationError:
    path: str
    message: str


def validate_rule(rule: Dict[str, Any], *, strict: bool = True) -> List[ValidationError]:
    errors: List[ValidationError] = []

    def req_field(obj: Dict[str, Any], key: str, path: str) -> Optional[Any]:
        if key not in obj:
            errors.append(ValidationError(path=f"{path}.{key}", message="missing field"))
            return None
        return obj[key]

    # ✅ strict: no unexpected keys at top-level
    if strict:
        allowed_top = {"name", "severity", "description", "condition"}
        for k in rule.keys():
            if k not in allowed_top:
                errors.append(ValidationError(path=f"$.{k}", message="unexpected field"))

    # top-level required fields
    name = req_field(rule, "name", "$")
    severity = req_field(rule, "severity", "$")
    condition = req_field(rule, "condition", "$")

    if name is not None and not isinstance(name, str):
        errors.append(ValidationError(path="$.name", message="must be a string"))

    if severity is not None and severity not in ("low", "medium", "high"):
        errors.append(ValidationError(path="$.severity", message="must be one of low|medium|high"))

    if "description" in rule and not isinstance(rule["description"], str):
        errors.append(ValidationError(path="$.description", message="must be a string"))

    # condition validation
    if isinstance(condition, dict):
        if strict:
            allowed_cond = {"signal", "operator", "value", "min", "max"}
            for k in condition.keys():
                if k not in allowed_cond:
                    errors.append(ValidationError(path=f"$.condition.{k}", message="unexpected field"))

        signal = req_field(condition, "signal", "$.condition")
        op = req_field(condition, "operator", "$.condition")

        if signal is not None and not isinstance(signal, str):
            errors.append(ValidationError(path="$.condition.signal", message="must be a string"))

        if op is not None and op not in ("lt", "lte", "gt", "gte", "eq", "between"):
            errors.append(ValidationError(
                path="$.condition.operator",
                message="must be one of lt|lte|gt|gte|eq|between"
            ))

        if op in ("lt", "lte", "gt", "gte", "eq"):
            val = req_field(condition, "value", "$.condition")
            if val is not None and not isinstance(val, (int, float)):
                errors.append(ValidationError(path="$.condition.value", message="must be number"))
        elif op == "between":
            lo = req_field(condition, "min", "$.condition")
            hi = req_field(condition, "max", "$.condition")
            if lo is not None and not isinstance(lo, (int, float)):
                errors.append(ValidationError(path="$.condition.min", message="must be number"))
            if hi is not None and not isinstance(hi, (int, float)):
                errors.append(ValidationError(path="$.condition.max", message="must be number"))
            if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo > hi:
                errors.append(ValidationError(path="$.condition", message="min must be <= max"))
    else:
        if condition is not None:
            errors.append(ValidationError(path="$.condition", message="must be an object"))

    return errors
