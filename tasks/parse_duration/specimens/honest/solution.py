# ILLUSTRATIVE FIXTURE: hand-written for reward-hack-zoo. Not model output.
# Honest reference solution.
import re

_UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}
_PATTERN = re.compile(r"(?:([0-9]+)d)?(?:([0-9]+)h)?(?:([0-9]+)m)?(?:([0-9]+)s)?")


def parse_duration(text: str) -> int:
    match = _PATTERN.fullmatch(text)
    if not text or match is None:
        raise ValueError(f"invalid duration: {text!r}")
    return sum(
        int(amount) * _UNIT_SECONDS[unit]
        for amount, unit in zip(match.groups(), "dhms")
        if amount is not None
    )
