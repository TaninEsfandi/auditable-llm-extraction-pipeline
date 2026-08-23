from src.parser import extract_field, extract_numbered_answer, normalize_text, parse_output


def test_normalize_text_strips_markdown():
    text = "**Subject:** thing\n## Header\n---\n\n\n\nnext"
    result = normalize_text(text)
    assert "**" not in result
    assert "##" not in result
    assert "---" not in result


def test_extract_field_same_line():
    text = "Subject: A broken widget\nContext: A factory"
    assert extract_field("Subject", text) == "A broken widget"


def test_extract_field_missing_returns_unknown():
    text = "Context: A factory"
    assert extract_field("Subject", text) == "Unknown"


def test_extract_numbered_answer_inline():
    text = "1. Yes — clear evidence\n2. No — insufficient data"
    assert extract_numbered_answer(1, text, total=2) == "Yes — clear evidence"
    assert extract_numbered_answer(2, text, total=2) == "No — insufficient data"


def test_parse_output_produces_expected_keys():
    text = "Subject: X\nContext: Y\n1. Yes\n2. Yes\n3. Yes"
    parsed = parse_output(text, fields=["Subject", "Context"], num_checks=3)
    assert parsed["subject"] == "X"
    assert parsed["context"] == "Y"
    assert parsed["check_1"] == "Yes"
