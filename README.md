# Auditable LLM Extraction Pipeline

A configurable LLM pipeline for structured information extraction,
normalization, validation, and traceability from unstructured documents.

## What it does

Given a set of source documents, the pipeline:

1. **Ingests** raw JSON documents and prepares them for extraction.
2. **Extracts** structured fields from each document using a chosen LLM
   provider (OpenAI, Anthropic, or a local OpenAI-compatible server such as
   LM Studio).
3. **Parses** the model's free-text completion into a flat, structured
   record — tolerating markdown and formatting differences across providers.
4. **Validates** each record against a set of quality checks (missing
   fields, hedging language, duplicate/overlapping fields, self-validation
   bias) and flags issues for human review instead of silently accepting
   model output.
5. **Saves** results incrementally, so a run can resume from where it left
   off after an interruption or a rate-limit error.

Every stage keeps the raw model output alongside the parsed fields, so any
extraction can be traced back to exactly what the model said.

## Why this design

- **Provider-agnostic**: swapping models is a config change, not a
  rewrite — `src/model_clients.py` normalizes OpenAI, Anthropic, and local
  model calls behind one interface.
- **Resilient to messy LLM output**: `src/parser.py` handles the same field
  being formatted inline, on its own line, in bold, or under a header,
  which is the norm across real model responses.
- **Trust but verify**: `src/validator.py` treats the model as a fallible
  extractor, not an oracle — it checks for hedging language, missing
  fields, duplicated content, and answers that all trend suspiciously
  affirmative.
- **Crash-safe**: `src/pipeline.py` checkpoints after every record, so
  large batches can be resumed without reprocessing completed work.

## Project structure

```text
src/
├── ingestion.py       # load/download source documents, extract metadata
├── model_clients.py   # provider configs and API client creation
├── extractor.py        # builds prompts and invokes the model
├── parser.py           # parses raw model output into structured fields
├── validator.py         # quality checks on parsed records
└── pipeline.py          # CLI orchestration: ingest -> extract -> parse -> validate -> save
configs/
└── extraction_prompt.txt  # the system prompt used for extraction
examples/
├── sample_input.json      # synthetic example input records
└── sample_output.json     # synthetic example of parsed/validated output
tests/                     # unit tests for parser, validator, ingestion
```

## Usage

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your API key(s)

python -m src.pipeline --input examples/sample_input.json --model openai
```

Options:

- `--model {openai,anthropic,local}` — which provider/model preset to use
- `--output-dir DIR` — where to write results (default: `results/`)
- `--prompt PATH` — use a custom system prompt
- `--limit N` — only process the first N records (useful for smoke tests)

## Testing

```bash
pytest tests/
```

## Notes

This project was extracted and generalized from a research pipeline
originally built for analyzing FDA medical device adverse event reports.
The extraction schema, prompt, and examples here are simplified and
synthetic — they demonstrate the engineering pattern rather than reproduce
any specific dataset or study results.
