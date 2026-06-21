from __future__ import annotations

import re

NOQA_PATTERN = re.compile(r"#\s*noqa(?::\s*(?P<codes>[A-Z0-9,\s]+))?", re.IGNORECASE)


def is_noqa_suppressed(lines: list[str], line_number: int, code: str) -> bool:
    if line_number < 1 or line_number > len(lines):
        return False

    line = lines[line_number - 1]
    match = NOQA_PATTERN.search(line)
    if match is None:
        return False

    codes = match.group("codes")
    if codes is None:
        return True

    selectors = [part.strip().upper() for part in codes.split(",") if part.strip()]
    return any(code.startswith(selector) for selector in selectors)
