"""Task 4: AI reply. Never raises: on any failure it returns the fallback reply."""
import json
import logging
import os
import re

import requests

from prompts import FALLBACK_REPLY, SYSTEM_PROMPT

log = logging.getLogger("stara.ai")


def generate_reply(message):
    """Return {"text": reply, "source": "mock" | "gemini" | "fallback"}."""
    provider = os.getenv("AI_PROVIDER", "mock").lower()
    try:
        if provider == "mock":
            return {"text": mock_reply(message), "source": "mock"}
        if provider == "gemini":
            text = limit_sentences(call_gemini(message))
            if not text:
                raise ValueError("empty AI reply")
            return {"text": text, "source": "gemini"}
        raise ValueError(f"unknown AI_PROVIDER: {provider}")
    except Exception as exc:  # timeout, bad key, rate limit, bad JSON ...
        log.warning("AI failed (%s: %s); using fallback", type(exc).__name__, exc)
        return {"text": FALLBACK_REPLY, "source": "fallback"}



def call_gemini(message):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        headers={"x-goog-api-key": key},
        json={
            "model": model,
            "system_instruction": SYSTEM_PROMPT,
            "input": message,
            "generation_config": {
                "thinking_level": "low"
            }
    },
        timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "20")),
    )
    if not resp.ok:
        raise RuntimeError(
            f"Gemini API HTTP {resp.status_code}: {resp.text[:1500]}"
    )


    data = resp.json()

    for step in data.get("steps", []):
        if step.get("type") == "model_output":
            for item in step.get("content", []):
                if item.get("type") == "text":
                    text = item.get("text", "").strip()
                    if text:
                        return text

    raise ValueError(
        f"No text output returned. Response keys: {list(data.keys())}"
    )



def limit_sentences(text, max_sentences=3):
    """Enforce 'max 3 sentences' in code, since the model may ignore the prompt."""
    return " ".join(re.split(r"(?<=[.!?])\s+", text.strip())[:max_sentences]).strip()


def mock_reply(message):
    """Fake AI for when there is no API key: canned Indonesian reply, max 3 sentences."""
    text = message.lower()
    if any(w in text for w in ("harga", "biaya", "tarif", "paket")):
        return ("Terima kasih sudah menghubungi STARA. "
                "Tim kami akan segera mengirimkan rincian harga dan paket layanan kepada Anda.")
    if any(w in text for w in ("halo", "hai", "selamat")):
        return "Halo, selamat datang di STARA. Ada yang bisa kami bantu hari ini?"
    return "Terima kasih atas pesan Anda. Tim STARA akan segera menghubungi Anda."
