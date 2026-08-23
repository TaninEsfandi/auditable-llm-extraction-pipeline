"""Data ingestion utilities: downloading source archives and loading/summarizing
JSON documents into a normalized record list ready for extraction."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Iterable

import requests
from tqdm import tqdm


def download_files(
    urls: Iterable[str],
    output_dir: str,
    min_valid_size: int = 1000,
    max_retries: int = 3,
    request_timeout: int = 30,
) -> list[str]:
    """Download a list of file URLs to ``output_dir``, skipping already-valid
    files and retrying failed or undersized downloads.

    Returns the list of filenames that failed to download after all retries.
    """
    os.makedirs(output_dir, exist_ok=True)
    failed: list[str] = []

    for index, url in enumerate(tqdm(list(urls)), start=1):
        file_name = f"document_{index:04d}{os.path.splitext(url)[1] or '.bin'}"
        file_path = os.path.join(output_dir, file_name)

        if os.path.exists(file_path):
            if os.path.getsize(file_path) < min_valid_size:
                os.remove(file_path)
            else:
                continue

        success = False
        for attempt in range(max_retries):
            try:
                response = requests.get(url, stream=True, timeout=request_timeout)
                if response.status_code == 200:
                    with open(file_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    success = True
                    break
                time.sleep(1)
            except requests.RequestException:
                time.sleep(2)

        if not success:
            failed.append(file_name)

    return failed


def load_json_documents(folder: str) -> list[dict[str, Any]]:
    """Load every ``.json`` file in ``folder`` and return their parsed contents."""
    documents = []
    for file_name in sorted(f for f in os.listdir(folder) if f.endswith(".json")):
        path = os.path.join(folder, file_name)
        with open(path, "r", encoding="utf-8") as f:
            documents.append(json.load(f))
    return documents


def extract_metadata(
    document: dict[str, Any],
    fields: Iterable[str] = ("date_received", "date_of_event", "report_date"),
) -> dict[str, Any]:
    """Pull a flat metadata record out of a document's first result entry.

    Works with documents shaped as ``{"results": [ {...}, ... ]}`` or a
    flat record dict directly.
    """
    entry = document.get("results", [document])[0] if "results" in document else document
    record = {field: entry.get(field, "") for field in fields}
    if record.get("date_received"):
        record["year"] = record["date_received"][:4]
    return record


def load_records(input_path: str) -> list[dict[str, Any]]:
    """Load a list of records to be processed by the extraction pipeline.

    Accepts either a JSON array of records or a single JSON object with a
    ``results`` key containing the array.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Unrecognized input format in {input_path}")
