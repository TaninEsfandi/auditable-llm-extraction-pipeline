import json
import os

from src.ingestion import extract_metadata, load_records


def test_load_records_from_list(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps([{"id": "1"}, {"id": "2"}]))
    records = load_records(str(path))
    assert len(records) == 2


def test_load_records_from_results_wrapper(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps({"results": [{"id": "1"}]}))
    records = load_records(str(path))
    assert records == [{"id": "1"}]


def test_extract_metadata_flat_record():
    doc = {"date_received": "20260115", "date_of_event": "20260110", "report_date": "20260116"}
    meta = extract_metadata(doc)
    assert meta["year"] == "2026"


def test_extract_metadata_results_wrapper():
    doc = {"results": [{"date_received": "20250501"}]}
    meta = extract_metadata(doc)
    assert meta["year"] == "2025"
