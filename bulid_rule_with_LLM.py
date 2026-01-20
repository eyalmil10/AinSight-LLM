from rule_core import validate_rule

""" rule = {
    "name": "rapid_descent",
    "signal": "vertical_speed",  # <-- בכוונה שגוי: צריך להיות בתוך condition
    "severity": "high",
    "description": "Vertical speed below -1.5 m/s",
    "condition": {"signal": "vertical_speed", "operator": "lt", "value": -1.5},
}

print ("Validating rule:")
errs = validate_rule(rule)
for e in errs:
    print(e.path, "->", e.message) """

from rule_builder import *

""" rule = make_rule(
    name="rapid_descent",
    signal="vertical_speed",
    operator="lt",
    value=-1.5,
    severity="high",
    description="Vertical speed below -1.5 m/s",
) """

dict = {'name': 'rapid_descent', 'severity': 'medium', 'description': 'vertical_speed lt -1.5', 'condition': {'signal': 'vertical_speed', 'operator': 'lt', 'value': -1.5}}
rule = make_rule_from_dict(dict)

print(rule)

