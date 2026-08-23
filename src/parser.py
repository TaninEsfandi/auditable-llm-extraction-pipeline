"""Structured-output parsing and normalization.

Turns free-text LLM completions into a flat dictionary of labeled fields and
numbered confidence-check answers, tolerating the formatting variance
different model providers introduce (markdown bold/headers, inline vs.
next-line answers, etc.).
"""

from __future__ import annotations

import re

# Default field labels the extraction prompt asks the model to produce.
# Override with a custom list when parsing a different schema.
DEFAULT_FIELDS = [
    "Subject",
    "Context",
    "Situation",
    "Root Cause",
    "Outcome",
    "Recommended Action",
]

# Number of numbered confidence-check questions the prompt asks for.
DEFAULT_NUM_CHECKS = 3


def normalize_text(text: str) -> str:
    """Strip common markdown formatting that some providers wrap responses in."""
    text = re.sub(r"\*\*", "", text)  # bold markers
    text = re.sub(r"\*([^*\n]+)\*", r"\1", text)  # single-asterisk emphasis
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)  # markdown headers
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)  # horizontal rules
    text = re.sub(r"\n{3,}", "\n\n", text)  # collapse extra blank lines
    return text


def extract_field(label: str, text: str) -> str:
    """Extract a labeled field's value, supporting two common layouts:

    A: "Label: value" (value may span multiple lines until the next label)
    B: "Label" on its own line, with the value on the following line(s)
    """
    pattern = rf"^{re.escape(label)}:\s*(.+?)(?=\n[A-Za-z][^\n]*:|$)"
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if match:
        value = " ".join(match.group(1).split())
        if value:
            return value

    header = re.escape(label)
    pattern2 = rf"^{header}\s*\n+(.+?)(?=\n[A-Z][^\n]{{2,}}\n|\n[A-Z][^\n]{{2,}}:|\Z)"
    match2 = re.search(pattern2, text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if match2:
        value = " ".join(match2.group(1).split())
        if value:
            return value

    return "Unknown"


def extract_numbered_answer(number: int, text: str, total: int = DEFAULT_NUM_CHECKS) -> str:
    """Extract the answer to a numbered question (e.g. "1. Question? Yes"),
    tolerating the question and its answer being on the same or separate lines.
    """
    if number < total:
        pattern = rf"^\s*{number}\.\s+(.+?)(?=\n\s*{number + 1}\.\s|\Z)"
    else:
        pattern = rf"^\s*{number}\.\s+(.+?)(?=\Z)"

    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if match:
        result = " ".join(match.group(1).split())
        if result and not result.endswith("?"):
            return result
        if result.endswith("?"):
            # The captured text was only the question; look for the answer
            # on the following line(s).
            q_pattern = rf"^\s*{number}\.\s+.+?\?\s*\n+(.+?)(?=\n\s*{number + 1}\.\s|\Z)"
            q_match = re.search(q_pattern, text, re.MULTILINE | re.DOTALL)
            if q_match:
                return f"{result} {' '.join(q_match.group(1).split())}"
            return result

    fallback = re.search(rf"^\s*{number}\.\s+(.+)", text, re.MULTILINE)
    return fallback.group(1).strip() if fallback else "Unknown"


def parse_output(
    text: str,
    fields: list[str] = DEFAULT_FIELDS,
    num_checks: int = DEFAULT_NUM_CHECKS,
) -> dict[str, str]:
    """Parse a raw model completion into a flat dict of field values plus
    numbered confidence-check answers.
    """
    clean = normalize_text(text)

    parsed = {_field_key(label): extract_field(label, clean) for label in fields}
    for i in range(1, num_checks + 1):
        parsed[f"check_{i}"] = extract_numbered_answer(i, clean, total=num_checks)

    return parsed


def _field_key(label: str) -> str:
    return label.strip().lower().replace(" ", "_")
