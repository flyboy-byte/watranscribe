"""Claude summarization — ported from the original claude_integration.py,
unchanged apart from the module name/import path.
"""
import os
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = (
            os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        if not api_key:
            raise ValueError(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY or enable "
                "Replit AI Integrations."
            )
        base_url = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        _client = Anthropic(**kwargs)
    return _client


def has_api_key() -> bool:
    return bool(
        os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
    )


def is_rate_limit_error(exception: BaseException) -> bool:
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and exception.status_code == 429)
    )


def get_condensation_instruction(level: int) -> str:
    instructions = {
        1: "Provide an ultra-brief summary in 1-2 sentences, capturing only the absolute core message.",
        2: "Provide a brief summary in 2-3 sentences, highlighting the main points.",
        3: "Provide a balanced summary that captures key points and important context.",
        4: "Provide a detailed summary covering all important points, supporting details, and context.",
        5: "Provide a comprehensive summary that captures everything: main points, nuances, context, supporting details, and implications.",
    }
    return instructions.get(level, instructions[3])


# Output caps well above what each style needs, so cost/latency scale with the
# requested condensation level instead of a flat 8192-token ceiling.
_MAX_TOKENS_BY_LEVEL = {1: 150, 2: 250, 3: 500, 4: 800, 5: 1200}

# Haiku is far cheaper than Sonnet and is plenty capable for condensing a
# transcript into a summary — reserve Sonnet/Opus for tasks that need deeper
# reasoning.
_MODEL = "claude-haiku-4-5-20251001"


@retry(
    stop=stop_after_attempt(7),
    wait=wait_exponential(multiplier=1, min=2, max=128),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True,
)
def summarize_text(text: str, context: str = "WhatsApp audio message", condensation: int = 3) -> str:
    style_instruction = get_condensation_instruction(condensation)
    message = _get_client().messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS_BY_LEVEL.get(condensation, 500),
        system=f"You are a helpful assistant that summarizes {context}. {style_instruction}",
        messages=[{"role": "user", "content": f"Please summarize the following transcription:\n\n{text}"}],
    )
    return message.content[0].text


@retry(
    stop=stop_after_attempt(7),
    wait=wait_exponential(multiplier=1, min=2, max=128),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True,
)
def summarize_conversation(transcriptions: list[str], condensation: int = 3) -> str:
    combined = "\n\n---\n\n".join([f"Message {i+1}:\n{t}" for i, t in enumerate(transcriptions)])
    style_instruction = get_condensation_instruction(condensation)
    message = _get_client().messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS_BY_LEVEL.get(condensation, 500),
        system=f"You are a helpful assistant that summarizes conversations from WhatsApp audio messages. {style_instruction}",
        messages=[{"role": "user", "content": f"Please summarize this conversation:\n\n{combined}"}],
    )
    return message.content[0].text
