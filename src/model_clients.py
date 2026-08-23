"""Provider-agnostic model configuration and client helpers.

Supports OpenAI, Anthropic, and any local OpenAI-compatible server (e.g.
LM Studio, Ollama's OpenAI endpoint). API keys are always read from
environment variables — never hard-coded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelConfig:
    """Configuration for a single model/provider combination."""

    model_id: str
    provider: str  # "openai" | "anthropic"
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0
    max_tokens: int = 1024
    timeout: int = 90
    supports_system_role: bool = True
    label: str = field(default="")

    def __post_init__(self) -> None:
        if not self.label:
            self.label = self.model_id


# Built-in presets. Add new entries here, or construct a ModelConfig directly
# for a one-off model.
MODEL_PRESETS: dict[str, ModelConfig] = {
    "openai": ModelConfig(
        model_id="gpt-4o-mini",
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=1000,
    ),
    "anthropic": ModelConfig(
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=2048,
    ),
    "local": ModelConfig(
        model_id=os.getenv("LOCAL_MODEL_ID", "local-model"),
        provider="openai",
        api_key="not-needed",
        base_url=os.getenv("LOCAL_MODEL_BASE_URL", "http://127.0.0.1:1234/v1"),
        max_tokens=1000,
    ),
}


def get_model_config(name: str) -> ModelConfig:
    """Look up a preset model configuration by short name."""
    if name not in MODEL_PRESETS:
        raise ValueError(f"Unknown model preset '{name}'. Options: {list(MODEL_PRESETS)}")
    return MODEL_PRESETS[name]


def create_client(config: ModelConfig) -> Any:
    """Instantiate the appropriate SDK client for a given model configuration."""
    if config.provider == "anthropic":
        from anthropic import Anthropic

        return Anthropic(api_key=config.api_key)

    from openai import OpenAI

    if config.base_url:
        return OpenAI(base_url=config.base_url, api_key=config.api_key)
    return OpenAI(api_key=config.api_key)


def call_model(client: Any, config: ModelConfig, system_prompt: str, user_message: str) -> str:
    """Send a single system/user message pair to the model and return the text response."""
    if config.provider == "anthropic":
        response = client.messages.create(
            model=config.model_id,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    if config.supports_system_role:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
    else:
        messages = [{"role": "user", "content": system_prompt + "\n\n" + user_message}]

    response = client.chat.completions.create(
        model=config.model_id,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        timeout=config.timeout,
        messages=messages,
    )
    return response.choices[0].message.content
