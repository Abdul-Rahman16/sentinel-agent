from groq import Groq
from google import genai

from core.config import settings
from core.logging import log

_groq_client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None
_gemini_client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None

GROQ_MODEL = "openai/gpt-oss-120b"  # llama-3.3-70b-versatile was deprecated June 2026
GEMINI_MODEL = "gemini-3.6-flash"


def call_llm(prompt: str, system: str = "", max_tokens: int = 1024) -> dict:
    """Tries Groq first (fast, primary). Falls back to Gemini if Groq fails
    or rate-limits. Returns {"text": ..., "tokens_used": ..., "provider": ...}
    — never raises, so a provider outage never crashes the agent loop."""
    if _groq_client:
        try:
            response = _groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            return {
                "text": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "provider": "groq",
            }
        except Exception as e:
            log.warning("groq_call_failed_falling_back_to_gemini", error=str(e))

    if _gemini_client:
        try:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            response = _gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=full_prompt,
            )
            # Gemini doesn't return exact token counts the same way — estimate
            # conservatively from character count as a reasonable approximation.
            estimated_tokens = len(full_prompt + response.text) // 4
            return {
                "text": response.text,
                "tokens_used": estimated_tokens,
                "provider": "gemini",
            }
        except Exception as e:
            log.error("gemini_call_also_failed", error=str(e))

    return {"text": "", "tokens_used": 0, "provider": "none", "error": "All LLM providers failed"}