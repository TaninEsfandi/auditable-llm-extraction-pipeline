"""Validation checks for parsed extraction records.

These are generic, reusable quality checks — missing fields, hedging
language, duplicate/overlapping fields, and self-validation bias in
numbered confidence checks — that surface issues for human review rather
than silently accepting model output.
"""

from __future__ import annotations

import re

DEFAULT_FORBIDDEN_TERMS = ["potential", "possible", "could", "may", "risk"]


def check_missing_fields(parsed: dict[str, str], required: list[str]) -> list[str]:
    """Flag any required field that is missing or still holds a placeholder value."""
    issues = []
    for key in required:
        value = parsed.get(key, "")
        if not value or value.strip().lower() == "unknown":
            issues.append(f"MISSING FIELD: {key}")
    return issues


def check_forbidden_language(
    field_name: str, value: str, forbidden_terms: list[str] = DEFAULT_FORBIDDEN_TERMS
) -> list[str]:
    """Flag hedging/uncertain language in a field that should state a fact."""
    value_lower = value.lower()
    hits = [term for term in forbidden_terms if re.search(rf"\b{term}\b", value_lower)]
    return [f"FORBIDDEN LANGUAGE in {field_name}: {hits}"] if hits else []


def check_field_overlap(
    field_a_name: str, field_a: str, field_b_name: str, field_b: str, overlap_threshold: float = 0.85
) -> list[str]:
    """Flag when two fields are effectively duplicates: exact match, one
    contained in the other, or high word overlap. Useful for catching a
    model collapsing two distinct concepts (e.g. cause and outcome) into
    one restated value.
    """
    a = (field_a or "").strip().lower()
    b = (field_b or "").strip().lower()
    if not a or not b:
        return []

    if a == b:
        return [f"DUPLICATE FIELDS: {field_a_name} == {field_b_name} (exact match)"]

    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    if len(shorter) > 50 and shorter in longer:
        return [f"DUPLICATE FIELDS: {field_a_name}/{field_b_name} (containment)"]

    a_words, b_words = set(a.split()), set(b.split())
    if len(a_words) > 5 and len(b_words) > 5:
        overlap = len(a_words & b_words) / min(len(a_words), len(b_words))
        if overlap > overlap_threshold:
            return [f"DUPLICATE FIELDS: {field_a_name}/{field_b_name} ({overlap:.0%} word overlap)"]

    return []


def check_self_validation_bias(parsed: dict[str, str], check_keys: list[str]) -> list[str]:
    """Flag when every numbered confidence check answers affirmatively —
    a common sign of the model rubber-stamping its own output.
    """
    answers = [parsed.get(key, "").lower() for key in check_keys]
    if answers and all("yes" in a for a in answers):
        return ["ALL CONFIDENCE CHECKS ARE YES — review for self-validation bias"]
    return []


def check_inferred_label_position(field_name: str, value: str) -> list[str]:
    """Flag when an '(inferred)' qualifier appears at the start instead of
    the end of a field, which usually indicates a formatting mistake.
    """
    if value.lower().startswith("(inferred)"):
        return [f"INFERRED LABEL at wrong position in {field_name} (must be at end)"]
    return []


def validate_record(
    parsed: dict[str, str],
    required_fields: list[str] | None = None,
    forbidden_terms: list[str] = DEFAULT_FORBIDDEN_TERMS,
    overlap_pairs: list[tuple[str, str]] | None = None,
    check_keys: list[str] | None = None,
) -> list[str]:
    """Run the standard set of validation checks against a parsed record
    and return a flat list of human-readable issues.
    """
    issues: list[str] = []

    if required_fields:
        issues += check_missing_fields(parsed, required_fields)

    for field_name, value in parsed.items():
        if field_name.startswith("check_"):
            continue
        issues += check_forbidden_language(field_name, value, forbidden_terms)
        issues += check_inferred_label_position(field_name, value)

    for field_a, field_b in overlap_pairs or []:
        issues += check_field_overlap(field_a, parsed.get(field_a, ""), field_b, parsed.get(field_b, ""))

    if check_keys:
        issues += check_self_validation_bias(parsed, check_keys)

    return issues
