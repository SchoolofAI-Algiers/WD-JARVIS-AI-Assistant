"""Text-only LLM client with ordered provider fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq
from groq.types.chat import ChatCompletionMessageParam

PRIMARY_MODEL = "gemini-3.8-flash"
FIRST_FALLBACK_MODEL = "gemini-3.5-flash-lite"
SECOND_FALLBACK_MODEL = "openai/gpt-oss-120b"


class LLMError(RuntimeError):
    """Raised when every configured LLM provider fails."""


@dataclass(frozen=True)
class _Provider:
    name: str
    model: str


class LLMClient:
    """Generate text using the configured ordered provider fallbacks."""

    _providers = (
        _Provider("primary", PRIMARY_MODEL),
        _Provider("first-fallback", FIRST_FALLBACK_MODEL),
        _Provider("second-fallback", SECOND_FALLBACK_MODEL),
    )

    def __init__(
        self,
        *,
        gemini_api_key: str | None = None,
        groq_api_key: str | None = None,
        gemini_client: Any | None = None,
        groq_client: Any | None = None,
    ) -> None:
        load_dotenv()
        self._gemini_api_key = (
            gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
        self._groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self._gemini = gemini_client
        self._groq = groq_client

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> str:
        """Return a text response, trying providers in configured order."""
        if not prompt or not prompt.strip():
            raise ValueError("prompt must not be empty")

        errors: list[str] = []

        for provider in self._providers:
            try:
                if self._is_gemini_model(provider.model):
                    response = self._generate_gemini(
                        provider,
                        prompt,
                        system_instruction,
                        temperature,
                        max_output_tokens,
                    )
                else:
                    response = self._generate_groq(
                        provider,
                        prompt,
                        system_instruction,
                        temperature,
                        max_output_tokens,
                    )
                return self._require_text(response, provider.name)
            except Exception as error:
                errors.append(f"{provider.name}: {error}")

        detail = "; ".join(errors)
        raise LLMError(f"all LLM providers failed: {detail}")

    def generate_response(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> str:
        """Compatibility alias for callers that use a response-oriented name."""
        return self.generate(
            prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    def _generate_gemini(
        self,
        provider: _Provider,
        prompt: str,
        system_instruction: str | None,
        temperature: float,
        max_output_tokens: int,
    ) -> Any:
        if self._gemini is None:
            if not self._gemini_api_key:
                raise LLMError("GEMINI_API_KEY or GOOGLE_API_KEY is not set")
            self._gemini = genai.Client(api_key=self._gemini_api_key)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="text/plain",
            system_instruction=system_instruction,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        return self._gemini.models.generate_content(
            model=provider.model,
            contents=prompt,
            config=config,
        )

    def _generate_groq(
        self,
        provider: _Provider,
        prompt: str,
        system_instruction: str | None,
        temperature: float,
        max_output_tokens: int,
    ) -> Any:
        if self._groq is None:
            if not self._groq_api_key:
                raise LLMError("GROQ_API_KEY is not set")
            self._groq = Groq(api_key=self._groq_api_key)

        messages: list[ChatCompletionMessageParam] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        return self._groq.chat.completions.create(
            model=provider.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_output_tokens,
        )

    @staticmethod
    def _is_gemini_model(model: str) -> bool:
        return model.startswith("gemini")

    @staticmethod
    def _require_text(response: Any, provider_name: str) -> str:
        text = getattr(response, "text", None)
        if text is None and getattr(response, "choices", None):
            text = response.choices[0].message.content

        if not isinstance(text, str) or not text.strip():
            raise LLMError(f"{provider_name} returned no text")
        return text.strip()
