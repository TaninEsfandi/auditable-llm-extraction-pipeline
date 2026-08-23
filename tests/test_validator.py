from src.validator import (
    check_field_overlap,
    check_forbidden_language,
    check_inferred_label_position,
    check_missing_fields,
    check_self_validation_bias,
    validate_record,
)


def test_check_missing_fields():
    parsed = {"subject": "Unknown", "context": "A factory"}
    issues = check_missing_fields(parsed, ["subject", "context"])
    assert len(issues) == 1
    assert "subject" in issues[0]


def test_check_forbidden_language():
    issues = check_forbidden_language("outcome", "This could be a risk")
    assert issues
    assert "outcome" in issues[0]


def test_check_field_overlap_exact_match():
    issues = check_field_overlap("situation", "the pump failed", "outcome", "the pump failed")
    assert issues


def test_check_inferred_label_position():
    issues = check_inferred_label_position("root_cause", "(inferred) unclear cause")
    assert issues


def test_check_self_validation_bias():
    parsed = {"check_1": "Yes", "check_2": "Yes", "check_3": "Yes"}
    issues = check_self_validation_bias(parsed, ["check_1", "check_2", "check_3"])
    assert issues


def test_validate_record_clean():
    parsed = {
        "subject": "A sensor",
        "outcome": "It failed",
        "check_1": "Yes",
        "check_2": "No",
    }
    issues = validate_record(parsed, required_fields=["subject"], check_keys=["check_1", "check_2"])
    assert issues == []
