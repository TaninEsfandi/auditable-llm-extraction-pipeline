"""Main orchestration entry point for the extraction pipeline.

Loads input records, runs each through a chosen model, parses the
completion into structured fields, validates it, and saves results —
resuming automatically if the output file already has partial results.

Usage:
    python -m src.pipeline --input examples/sample_input.json --model openai
    python -m src.pipeline --input examples/sample_input.json --model anthropic --limit 5
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os

from src.extractor import extract_record
from src.ingestion import load_records
from src.model_clients import create_client, get_model_config
from src.parser import DEFAULT_FIELDS, DEFAULT_NUM_CHECKS, parse_output
from src.validator import validate_record

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "configs", "extraction_prompt.txt")


def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_existing_results(output_path: str) -> list[dict]:
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(records: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def save_csv(records: list[dict], path: str) -> None:
    if not records:
        return
    exclude = {"raw_output", "validation_issues"}
    rows = [{k: v for k, v in r.items() if k not in exclude} for r in records]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[-1].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_pipeline(
    input_path: str,
    model_name: str,
    output_dir: str,
    prompt_path: str = DEFAULT_PROMPT_PATH,
    record_id_field: str = "id",
    limit: int | None = None,
) -> list[dict]:
    """Run extraction + parsing + validation over all input records, saving
    incrementally so an interrupted run can resume from where it left off.
    """
    config = get_model_config(model_name)
    client = create_client(config)
    system_prompt = load_prompt(prompt_path)

    records = load_records(input_path)
    if limit:
        records = records[:limit]

    os.makedirs(output_dir, exist_ok=True)
    output_json = os.path.join(output_dir, f"results_{config.label}.json")
    output_csv = os.path.join(output_dir, f"results_{config.label}.csv")
    raw_dir = os.path.join(output_dir, f"raw_outputs_{config.label}")
    os.makedirs(raw_dir, exist_ok=True)

    results = load_existing_results(output_json)
    already_done = {str(r[record_id_field]) for r in results if record_id_field in r}
    if already_done:
        logger.info("Resuming: %d records already processed, skipping.", len(already_done))

    for i, record in enumerate(records, start=1):
        record_id = str(record.get(record_id_field, f"record_{i}"))
        if record_id in already_done:
            continue

        logger.info("[%d/%d] Processing %s", i, len(records), record_id)
        try:
            raw_output = extract_record(client, config, system_prompt, record)
        except Exception as exc:
            logger.error("Extraction failed for %s: %s", record_id, exc)
            continue

        with open(os.path.join(raw_dir, f"{record_id}.txt"), "w", encoding="utf-8") as f:
            f.write(raw_output)

        parsed = parse_output(raw_output, fields=DEFAULT_FIELDS, num_checks=DEFAULT_NUM_CHECKS)
        check_keys = [f"check_{n}" for n in range(1, DEFAULT_NUM_CHECKS + 1)]
        issues = validate_record(parsed, check_keys=check_keys)

        if issues:
            logger.info("  %d issue(s) flagged", len(issues))

        results.append(
            {
                record_id_field: record_id,
                "model_used": config.model_id,
                "raw_output": raw_output,
                "validation_issues": issues,
                **parsed,
            }
        )

        save_json(results, output_json)

    save_csv(results, output_csv)
    logger.info("Done. JSON -> %s | CSV -> %s", output_json, output_csv)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the structured extraction pipeline.")
    parser.add_argument("--input", required=True, help="Path to input JSON records")
    parser.add_argument("--model", default="openai", choices=["openai", "anthropic", "local"])
    parser.add_argument("--output-dir", default="results", help="Directory to write results into")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT_PATH, help="Path to system prompt file")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N records")
    args = parser.parse_args()

    run_pipeline(
        input_path=args.input,
        model_name=args.model,
        output_dir=args.output_dir,
        prompt_path=args.prompt,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
