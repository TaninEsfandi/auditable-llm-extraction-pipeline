"""Structured extraction workflow: turns a source record into a model
completion by building the prompt messages and invoking a model client."""

from __future__ import annotations

import json
from typing import Any

from src.model_clients import ModelConfig, call_model


def build_user_message(record: dict[str, Any]) -> str:
    """Render a source record as the user-turn content sent to the model."""
    return "Extract structured information from this document:\n\n" + json.dumps(record, indent=2)


def extract_record(client: Any, config: ModelConfig, system_prompt: str, record: dict[str, Any]) -> str:
    """Run a single record through the model and return its raw text output."""
    user_message = build_user_message(record)
    return call_model(client, config, system_prompt, user_message)
