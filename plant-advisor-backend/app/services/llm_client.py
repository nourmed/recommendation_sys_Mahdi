"""
llm_client.py
Centralized LLM client.

Flow:
  1. GPT-4o               (PRIMARY)    — high quality, reliable, streaming
  2. Groq Llama 3.3 70B   (FALLBACK 1) — fast, free fallback
  3. [Gemma 4 via Gradio — DISABLED, kept in comments]
"""

import os
import time
import json
import requests
import logging
from typing import Optional, Generator

logger = logging.getLogger("plant_advisor.llm_client")


def _safe_print(message: str):
    """Print helper with fallback."""
    try:
        print(message)
    except Exception:
        pass


# ── Config ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "***REMOVED***"
)
GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    "***REMOVED***"
)

GPT_MODEL  = "gpt-4o"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Startup diagnostic ────────────────────────────────────────────────────────
print(f"[llm_client] PRIMARY=GPT-4o  FALLBACK=Groq({GROQ_MODEL})")


# ═════════════════════════════════════════════════════════════════════════════
#  PRIMARY — GPT-4o
# ═════════════════════════════════════════════════════════════════════════════

def call_gpt(prompt: str,
             system_message: str = "You are an expert botanist and plant advisor.",
             temperature: float = 0.7,
             max_tokens: int = 5000) -> Optional[str]:
    """
    Call GPT-4o (non-streaming, PRIMARY).
    Returns the response text or None on failure.
    """
    try:
        _safe_print("🤖 Calling GPT-4o (primary)...")
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user",   "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        result = response.choices[0].message.content
        if result:
            _safe_print("✅ GPT-4o responded successfully")
            return result.strip()
        _safe_print("❌ GPT-4o returned empty response")
        return None
    except Exception as e:
        _safe_print(f"❌ GPT-4o error: {e}")
        return None


def call_gpt_streaming(prompt: str,
                       system_message: str = "You are an expert botanist and plant advisor.",
                       temperature: float = 0.7,
                       max_tokens: int = 5000) -> Generator[str, None, None]:
    """
    Call GPT-4o with streaming (PRIMARY).
    Yields text chunks as they arrive.
    """
    try:
        _safe_print("🤖 Calling GPT-4o streaming (primary)...")
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user",   "content": prompt}
            ],
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens
        )
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        _safe_print(f"❌ GPT-4o streaming error: {e}")
        yield f"\n\n❌ GPT-4o Error: {e}"


# ═════════════════════════════════════════════════════════════════════════════
#  FALLBACK — Groq  (Llama 3.3 70B)
# ═════════════════════════════════════════════════════════════════════════════

def call_groq(prompt: str,
              system_message: str = "You are an expert botanist and plant advisor.",
              temperature: float = 0.7,
              max_tokens: int = 4000) -> Optional[str]:
    """
    Call Groq Llama-3.3-70B (non-streaming, FALLBACK).
    Returns the response text or None on failure.
    """
    try:
        _safe_print("🔄 Falling back to Groq Llama-3.3-70B...")
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user",   "content": prompt}
            ],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            stream=False
        )
        result = completion.choices[0].message.content
        if result:
            _safe_print("✅ Groq responded successfully")
            return result.strip()
        _safe_print("❌ Groq returned empty response")
        return None
    except Exception as e:
        _safe_print(f"❌ Groq fallback error: {e}")
        return None


def call_groq_streaming(prompt: str,
                        system_message: str = "You are an expert botanist and plant advisor.",
                        temperature: float = 0.7,
                        max_tokens: int = 5000) -> Generator[str, None, None]:
    """
    Call Groq Llama-3.3-70B with streaming (FALLBACK).
    Yields text chunks as they arrive.
    """
    try:
        _safe_print("🔄 Falling back to Groq streaming...")
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user",   "content": prompt}
            ],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            stream=True
        )
        for chunk in completion:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        _safe_print(f"❌ Groq streaming error: {e}")
        yield f"\n\n❌ Groq Error: {e}"


# ═════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR
# ═════════════════════════════════════════════════════════════════════════════

def call_llm(prompt: str, system_message: str = "",
             temperature: float = 0.7, max_tokens: int = 5000) -> Optional[str]:
    """
    Main LLM orchestrator (non-streaming):
      1. GPT-4o              (PRIMARY)
      2. Groq Llama 3.3 70B  (FALLBACK)
    """
    sys_msg = system_message or "You are an expert botanist and plant advisor."

    # Step 1: GPT-4o (PRIMARY)
    result = call_gpt(prompt, sys_msg, temperature, max_tokens)
    if result:
        return result

    # Step 2: Groq (FALLBACK)
    _safe_print("⚠️ GPT-4o failed — switching to Groq Llama-3.3-70B fallback...")
    return call_groq(prompt, sys_msg, temperature, max_tokens)


def call_llm_streaming(prompt: str,
                       system_message: str = "You are an expert botanist and plant advisor.",
                       temperature: float = 0.7, max_tokens: int = 5000):
    """
    Main LLM orchestrator (streaming):
      1. GPT-4o streaming    (PRIMARY)
      2. Groq streaming      (FALLBACK)

    Returns a dict:
      - 'source': 'gpt', or 'groq'
      - 'text':   the full response text (for non-generator sources)
      - 'stream': generator yielding text chunks (or None)
    """
    
    # Step 1: Try GPT-4o streaming
    def _gpt_stream_with_fallback():
        """Try GPT streaming; if it fails/is empty fall through to Groq."""
        collected = []
        gpt_ok = False
        try:
            for chunk in call_gpt_streaming(prompt, system_message, temperature, max_tokens):
                if chunk and not chunk.startswith("\n\n❌"):
                    collected.append(chunk)
                    yield chunk
                    gpt_ok = True
        except Exception:
            pass

        if not gpt_ok or not collected:
            # Step 2: Groq streaming (FALLBACK)
            _safe_print("⚠️ GPT-4o streaming failed — switching to Groq (fallback)...")
            for chunk in call_groq_streaming(prompt, system_message, temperature, max_tokens):
                yield chunk

    return {
        "source": "gpt",
        "text": None,
        "stream": _gpt_stream_with_fallback()
    }


# ═════════════════════════════════════════════════════════════════════════════
#  DISABLED — Gemma 4 via Gradio (kept for reference)
# ═════════════════════════════════════════════════════════════════════════════
#
# GEMMA_GRADIO_URL = os.getenv("GEMMA_GRADIO_URL", "https://caf6ac0dd8f093e4ba.gradio.live")
# GEMMA_GRADIO_FN      = "chat"
# GEMMA_MAX_RETRIES    = 3
# GEMMA_SUBMIT_TIMEOUT = 30
# GEMMA_SSE_TIMEOUT    = 300
# GEMMA_MAX_PROMPT_CHARS = 12_000
#
# def _extract_gemma_text(result) -> str:
#     if isinstance(result, str): return result
#     if isinstance(result, dict): return result.get("text") or result.get("content") or str(result)
#     if isinstance(result, list) and result: return str(result[0])
#     return str(result)
#
# def call_gemma(prompt: str, system_message: str = "", max_retries: int = GEMMA_MAX_RETRIES,
#                submit_timeout: int = GEMMA_SUBMIT_TIMEOUT, sse_timeout: int = GEMMA_SSE_TIMEOUT) -> Optional[str]:
#     combined = f"{system_message}\n\n{prompt}" if system_message else prompt
#     if len(combined) > GEMMA_MAX_PROMPT_CHARS:
#         combined = combined[:GEMMA_MAX_PROMPT_CHARS]
#
#     for attempt in range(1, max_retries + 1):
#         try:
#             from gradio_client import Client
#             client = Client(GEMMA_GRADIO_URL, verbose=False)
#             result = client.predict(message=combined, api_name=f"/{GEMMA_GRADIO_FN}")
#             text = _extract_gemma_text(result)
#             if len(text.strip()) > 10: return text.strip()
#         except Exception: pass
#         if attempt < max_retries: time.sleep(2)
#     return None
#
# def call_gemma_streaming(prompt: str, system_message: str = "", max_retries: int = GEMMA_MAX_RETRIES,
#                          submit_timeout: int = GEMMA_SUBMIT_TIMEOUT, sse_timeout: int = GEMMA_SSE_TIMEOUT) -> Generator[str, None, None]:
#     combined = f"{system_message}\n\n{prompt}" if system_message else prompt
#     if len(combined) > GEMMA_MAX_PROMPT_CHARS:
#         combined = combined[:GEMMA_MAX_PROMPT_CHARS]
#
#     try:
#         from gradio_client import Client
#         client = Client(GEMMA_GRADIO_URL, verbose=False)
#         result = client.predict(message=combined, api_name=f"/{GEMMA_GRADIO_FN}")
#         text = _extract_gemma_text(result)
#         chunk_size = 60
#         for i in range(0, len(text), chunk_size): yield text[i:i + chunk_size]
#            
#         for auto_continue in range(1, 7):
#             lower_text = text.lower()
#             if "cost & token estimation" in lower_text or "estimated cost" in lower_text or "timeline verification" in lower_text and len(text) > 2000:
#                 break
#                
#             next_result = client.predict(
#                 message="Continue exactly from where you left off. Do not repeat anything. Do not add any conversational filler or introductory text. Just print the direct continuation of the report.", 
#                 api_name=f"/{GEMMA_GRADIO_FN}"
#             )
#             text = _extract_gemma_text(next_result)
#             if not text or len(text.strip()) < 10: break
#             for i in range(0, len(text), chunk_size): yield text[i:i + chunk_size]
#     except Exception as e:
#         yield f"\n\n❌ Gemma Error: {e}"
