import json
import re
import time
from dataclasses import dataclass

from anthropic import Anthropic
from pydantic import ValidationError

from app.config import Settings
from app.mock_data import build_mock_artifacts
from app.models import ForgeSession
from app.prompts import PROMPT_VERSION, build_system_prompt, build_user_prompt
from app.schemas import ArtifactSet


@dataclass
class GenerationResult:
    artifacts: ArtifactSet
    provider: str
    model: str
    prompt_version: str
    latency_ms: int


def _extract_json(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("The model response did not contain a JSON object.")
    return cleaned[start : end + 1]


def generate_artifacts(session: ForgeSession, settings: Settings) -> GenerationResult:
    started = time.perf_counter()
    if settings.forge_mock_llm:
        artifacts = build_mock_artifacts(session)
        return GenerationResult(
            artifacts=artifacts,
            provider="mock",
            model="mock-forge-v1",
            prompt_version=PROMPT_VERSION,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required when FORGE_MOCK_LLM=false.")

    client = Anthropic(api_key=settings.anthropic_api_key)
    system_prompt = build_system_prompt(session.domain_pack)
    user_prompt = build_user_prompt(session)

    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=9000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
    try:
        payload = json.loads(_extract_json(text))
        artifacts = ArtifactSet.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, ValueError) as first_error:
        repair_message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=9000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": (
                        "The prior output failed JSON/schema validation. Return a complete corrected "
                        f"JSON object only. Validation error: {first_error}"
                    ),
                },
            ],
        )
        repaired = "".join(
            block.text
            for block in repair_message.content
            if getattr(block, "type", None) == "text"
        )
        payload = json.loads(_extract_json(repaired))
        artifacts = ArtifactSet.model_validate(payload)

    return GenerationResult(
        artifacts=artifacts,
        provider="anthropic",
        model=settings.anthropic_model,
        prompt_version=PROMPT_VERSION,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
