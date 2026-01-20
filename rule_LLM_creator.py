from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

from rule_builder import make_rule
from extract_CSV_columns import *

try:
    # Optional: enable LLM-based parsing
    from tzarfati_func import call_claude_sonnet  # type: ignore
except Exception:  # pragma: no cover
    call_claude_sonnet = None  # type: ignore

Operator = Literal["lt", "lte", "gt", "gte", "eq", "between"]
Severity = Literal["low", "medium", "high"]


# -------------------------
# 1-2) Draft state
# -------------------------


@dataclass
class DraftState:
    draft: Dict[str, Any] = field(default_factory=dict)
    missing_slots: List[str] = field(default_factory=list)
    last_question: Optional[str] = None
    done: bool = False
    awaiting_run_confirmation: bool = False
    run_confirmed: Optional[bool] = None


# -------------------------
# 3-4) Missing slots detector (small & deterministic)
# -------------------------


_SLOT_ORDER: Tuple[str, ...] = (
    "name",
    "signal",
    "operator",
    "value_or_range",
    "severity",
    "description",
)


def detect_missing_slots(draft: Dict[str, Any]) -> List[str]:
    missing: List[str] = []

    if not draft.get("name"):
        missing.append("name")

    cond = draft.get("condition")
    if not isinstance(cond, dict):
        missing.extend(["signal", "operator"])  # condition absent -> both missing
        return missing

    if not cond.get("signal"):
        missing.append("signal")

    op = cond.get("operator")
    if not op:
        missing.append("operator")
        return missing

    if op == "between":
        if cond.get("min") is None:
            missing.append("min")
        if cond.get("max") is None:
            missing.append("max")
    else:
        if cond.get("value") is None:
            missing.append("value")

    # severity/description are optional in POC (defaults will be applied)
    return missing


# -------------------------
# 5) One-question-at-a-time policy
# -------------------------


def next_question(missing_slots: List[str], *, suggested_signals: Optional[List[str]] = None) -> Tuple[str, str]:
    """Return (slot_key_to_fill, question_text)."""
    suggested_signals = suggested_signals or []

    if "signal" in missing_slots:
        if suggested_signals:
            opts = ", ".join(suggested_signals[:5])
            return "signal", f"Which signal should we monitor? (e.g., {opts})"
        return "signal", "Which signal should we monitor?"

    if "operator" in missing_slots:
        return "operator", "What is the condition? less than / greater than / between?"

    if "value" in missing_slots:
        return "value", "What is the numeric threshold? (e.g., -1.5)"

    if "min" in missing_slots or "max" in missing_slots:
        return "minmax", "Provide minimum and maximum (e.g., 10 to 20)"

    if "name" in missing_slots:
        return "name", "What should we call this rule? (short name in English, e.g., rapid_descent)"

    # Fallback
    return "name", "What should we call this rule?"


# -------------------------
# 6) Parsing user input (POC deterministic + optional LLM)
# -------------------------


_OP_HE_MAP = {
    "below": "lt",
    "under": "lt",
    "less": "lt",
    "less than": "lt",
    "above": "gt",
    "over": "gt",
    "greater": "gt",
    "greater than": "gt",
    "between": "between",
    "in range": "between",
    "range": "between",
}


def _parse_number(text: str) -> Optional[float]:
    """Extract first float from text. Handles comma decimals and unicode minus."""
    import re

    t = text.replace("−", "-").replace(",", ".")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", t)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _parse_minmax(text: str) -> Tuple[Optional[float], Optional[float]]:
    import re

    t = text.replace("−", "-").replace(",", ".")
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", t)
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    if len(nums) == 1:
        return float(nums[0]), None
    return None, None


def parse_user_answer(
    slot: str,
    user_text: str,
    *,
    available_signals: Optional[List[str]] = None,
    use_llm: bool = False,
) -> Dict[str, Any]:
    """Parse user answer into dict patch to apply onto draft."""
    available_signals = available_signals or []

    # Optional LLM: keep minimal responsibility (only slot-filling)
    if use_llm and call_claude_sonnet is not None:
        prompt = f"""
You are a slot-filling parser.
Return JSON ONLY.

Slot to fill: {slot}
Allowed operators: lt,lte,gt,gte,eq,between
Available signals: {available_signals}

User text: {user_text}

Output schema:
{{
  "signal": "string?",
  "operator": "lt|lte|gt|gte|eq|between?",
  "value": "number?",
  "min": "number?",
  "max": "number?",
  "name": "string?"
}}
Rules:
- Only include fields you are confident about.
- Numbers must be numbers (not strings).
""".strip()

        raw = call_claude_sonnet(prompt)
        try:
            import json

            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        # fall back to deterministic parsing

    patch: Dict[str, Any] = {}
    text = user_text.strip()

    if slot == "name":
        patch["name"] = text.replace(" ", "_")
        return patch

    if slot == "signal":
        # If user typed an exact signal, take it. Otherwise, try fuzzy contains.
        if text in available_signals:
            patch["signal"] = text
            return patch
        for s in available_signals:
            if s.lower() in text.lower():
                patch["signal"] = s
                return patch
        patch["signal"] = text
        return patch

    if slot == "operator":
        for k, op in _OP_HE_MAP.items():
            if k in text:
                patch["operator"] = op
                return patch
        # accept raw operator tokens
        if text in {"lt", "lte", "gt", "gte", "eq", "between"}:
            patch["operator"] = text
        return patch

    if slot == "value":
        n = _parse_number(text)
        if n is not None:
            patch["value"] = n
        return patch

    if slot == "minmax":
        mn, mx = _parse_minmax(text)
        if mn is not None:
            patch["min"] = mn
        if mx is not None:
            patch["max"] = mx
        return patch

    return patch


# -------------------------
# 7) Apply patch to draft
# -------------------------


def apply_patch(draft: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    new = dict(draft)
    cond = dict(new.get("condition") or {})

    for k, v in patch.items():
        if k in {"signal", "operator", "value", "min", "max"}:
            cond[k] = v
        else:
            new[k] = v

    if cond:
        new["condition"] = cond

    return new


# -------------------------
# 8-10) Conversation loop + finalize
# -------------------------


def _summary(state: DraftState) -> str:
    d = state.draft
    cond = d.get("condition") or {}
    parts: List[str] = []

    if cond.get("signal"):
        parts.append(f"Signal: {cond['signal']}")
    if cond.get("operator"):
        parts.append(f"Operator: {cond['operator']}")
    if cond.get("operator") == "between":
        if cond.get("min") is not None or cond.get("max") is not None:
            parts.append(f"Range: {cond.get('min')}..{cond.get('max')}")
    else:
        if cond.get("value") is not None:
            parts.append(f"Threshold: {cond.get('value')}")

    if d.get("name"):
        parts.append(f"Name: {d['name']}")

    return "Got it: " + ("; ".join(parts) if parts else "Not enough details yet.")


def finalize_rule(draft: Dict[str, Any]) -> Dict[str, Any]:
    """Produce the minimal Rule JSON (via make_rule for consistent format)."""
    cond = draft["condition"]
    op = cond["operator"]

    severity: Severity = draft.get("severity") or "medium"  # default

    if op == "between":
        mn = cond.get("min")
        mx = cond.get("max")
        desc = draft.get("description")
        return make_rule(
            name=draft["name"],
            signal=cond["signal"],
            operator="between",
            min_value=mn,
            max_value=mx,
            severity=severity,
            description=desc,
        )

    desc = draft.get("description")
    return make_rule(
        name=draft["name"],
        signal=cond["signal"],
        operator=op,
        value=cond.get("value"),
        severity=severity,
        description=desc,
    )


class RuleCreator:
    """Iterative rule builder: one question at a time, no JSON exposed to user."""

    def __init__(
        self,
        *,
        available_signals: Optional[List[str]] = None,
        use_llm: bool = False,
    ) -> None:
        self.available_signals = available_signals or []
        self.use_llm = use_llm
        self.state = DraftState(draft={})
        self.last_user_text: Optional[str] = None
        self.final_rule: Optional[Dict[str, Any]] = None
        self._refresh()

    def _refresh(self) -> None:
        self.state.missing_slots = detect_missing_slots(self.state.draft)
        self.state.done = len(self.state.missing_slots) == 0

    def get_rule(self) -> Dict[str, Any]:
        if not self.state.done:
            raise RuntimeError("Rule is not complete yet")
        return finalize_rule(self.state.draft)

    @staticmethod
    def _parse_yes_no(text: str) -> Optional[bool]:
        t = text.strip().lower()
        if t in {"y", "yes", "yeah", "yep", "ok", "okay", "sure"}:
            return True
        if t in {"n", "no", "nope", "nah"}:
            return False
        return None

    def start(self) -> str:
        self._refresh()
        slot, q = next_question(self.state.missing_slots, suggested_signals=self.available_signals)
        self.state.last_question = slot
        return q

    def handle(self, user_text: str):
        self.last_user_text = user_text

        # If we're done and asked the user whether to run on data, treat this as a terminal choice.
        if self.state.awaiting_run_confirmation:
            yn = self._parse_yes_no(user_text)
            if yn is None:
                return "Please answer 'yes' or 'no'. Run it on the data?"
            self.state.run_confirmed = yn
            self.state.awaiting_run_confirmation = False
            return {
                "user_text": user_text,
                "rule": self.final_rule or self.get_rule(),
                "run_on_data": yn,
                "message": "OK. Starting run on the data..." if yn else "OK. Not running on the data.",
            }

        # Apply user input to the slot we asked for
        slot = self.state.last_question or ""
        patch = parse_user_answer(
            slot,
            user_text,
            available_signals=self.available_signals,
            use_llm=self.use_llm,
        )
        self.state.draft = apply_patch(self.state.draft, patch)
        self._refresh()

        if self.state.done:
            rule = finalize_rule(self.state.draft)
            self.final_rule = rule
            cond = rule["condition"]
            if cond["operator"] == "between":
                when = f"{cond['signal']} between {cond.get('min')} and {cond.get('max')}"
            else:
                op_map = {"lt": "<", "lte": "<=", "gt": ">", "gte": ">=", "eq": "=="}
                when = f"{cond['signal']} {op_map.get(cond['operator'], cond['operator'])} {cond.get('value')}"

            self.state.awaiting_run_confirmation = True
            return (
                f"Created rule '{rule['name']}'.\n"
                f"Description: {rule['description']}\n"
                f"Triggers when: {when}\n"
                f"Severity: {rule['severity']}\n"
                "Run it on the data? (yes/no)"
            )

        # Ask next question
        summary = _summary(self.state)
        slot2, q2 = next_question(self.state.missing_slots, suggested_signals=self.available_signals)
        self.state.last_question = slot2
        return f"{summary}\nI still need one more thing: {q2}"


def run_cli_demo() -> None:
    """Small interactive demo in the terminal."""
    signals = extract_csv_columns("NavGpsMetry.csv")
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
            print(out["rule"])
            break
        print(out)

def main() -> None:
    run_cli_demo()

#main()