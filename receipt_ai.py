"""To'lov chekini (skrinshotni) avtomatik tahlil qilish: Gemini (bepul kalit) yoki Claude API.

Muhim: bu tahlil 100% kafolat emas (rasmni soxtalashtirish mumkin). Shuning uchun:
- shubhali yoki noaniq holatda chek ustaga/egaga qo'lda tekshirishga yuboriladi;
- bir xil chek ikki marta qabul qilinmaydi;
- ega avtomatik tasdiqlangan chekni istalgan payt "noto'g'ri" deb bekor qila oladi.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime, timedelta

import aiohttp

import config

log = logging.getLogger(__name__)

PROMPT = """You verify payment-transfer screenshots from Uzbek payment apps (Click, Payme, Uzum, Paynet,
Humo, Uzcard, bank apps). The text may be in Uzbek, Russian or English.
Return ONLY one JSON object, no markdown, with exactly these keys:
{"is_receipt": true/false,   // is this a payment/transfer receipt or confirmation screen?
 "status": "success" | "failed" | "pending" | "unknown",  // "success" if it shows a completed successful transfer
 "amount": integer or null,   // transferred amount in UZS (so'm), digits only, e.g. 15000
 "datetime": "YYYY-MM-DD HH:MM" or null,   // payment date and time exactly as shown (24h)
 "recipient_last4": "1234" or null,   // last 4 digits of the RECIPIENT card/account if visible
 "recipient_name": string or null,
 "transaction_id": string or null,
 "looks_edited": true/false,  // true only if there are clear signs of editing/tampering
 "notes": "very short note"}
If something is not visible, use null. Do not guess."""

_gemini_cache: list[str] | None = None


def enabled() -> bool:
    if config.RECEIPT_AI == "gemini":
        return bool(config.GEMINI_API_KEY)
    if config.RECEIPT_AI == "anthropic":
        return bool(config.ANTHROPIC_API_KEY)
    return False


# ---- HTTP (testda almashtiriladi) ----
async def _post_json(url: str, headers: dict, payload: dict, timeout: int = 45) -> dict:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json(content_type=None)
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}: {str(data)[:300]}")
            return data


async def _get_json(url: str, headers: dict, timeout: int = 20) -> dict:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json(content_type=None)
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}: {str(data)[:300]}")
            return data


# ---- yordamchilar ----
def _extract_json(text: str) -> dict | None:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1:
        return None
    try:
        return json.loads(text[a:b + 1])
    except json.JSONDecodeError:
        return None


def _normalize(raw: dict | None) -> dict | None:
    if not isinstance(raw, dict):
        return None
    amount = raw.get("amount")
    if isinstance(amount, str):
        digits = re.sub(r"[^\d]", "", amount.split(".")[0].split(",")[0]) if amount else ""
        amount = int(digits) if digits else None
    elif isinstance(amount, float):
        amount = int(amount)
    elif not isinstance(amount, int):
        amount = None
    l4 = raw.get("recipient_last4")
    l4 = re.sub(r"\D", "", str(l4))[-4:] if l4 else None
    return {
        "is_receipt": bool(raw.get("is_receipt")),
        "status": str(raw.get("status") or "unknown").lower(),
        "amount": amount,
        "datetime": raw.get("datetime"),
        "recipient_last4": l4 or None,
        "recipient_name": raw.get("recipient_name"),
        "transaction_id": str(raw["transaction_id"]).strip() if raw.get("transaction_id") else None,
        "looks_edited": bool(raw.get("looks_edited")),
        "notes": str(raw.get("notes") or "")[:200],
    }


def _model_rank(name: str):
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    version = float(m.group(1)) if m else 0.0
    stable = not any(x in name for x in ("preview", "exp"))
    return (stable, version, "lite" not in name)


async def _gemini_models() -> list[str]:
    global _gemini_cache
    if config.GEMINI_MODEL:
        return [config.GEMINI_MODEL]
    if _gemini_cache is None:
        try:
            data = await _get_json("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                                   {"x-goog-api-key": config.GEMINI_API_KEY})
            names = []
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                low = name.lower()
                if "generateContent" not in m.get("supportedGenerationMethods", []) or "flash" not in low:
                    continue
                if any(x in low for x in ("image", "tts", "audio", "live", "embedding", "robotics",
                                          "computer", "native", "learnlm")):
                    continue
                names.append(name)
            names.sort(key=_model_rank, reverse=True)
            _gemini_cache = names[:3] or ["gemini-2.5-flash"]
        except Exception as e:  # noqa: BLE001
            log.warning("Gemini modellari ro'yxati olinmadi: %s", e)
            _gemini_cache = ["gemini-2.5-flash", "gemini-2.0-flash"]
    return _gemini_cache


async def _analyze_gemini(image: bytes, mime: str) -> dict | None:
    b64 = base64.b64encode(image).decode()
    last_err = None
    for model in await _gemini_models():
        try:
            data = await _post_json(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                {"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"},
                {"contents": [{"parts": [{"text": PROMPT}, {"inline_data": {"mime_type": mime, "data": b64}}]}],
                 "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}})
            parts = data["candidates"][0]["content"]["parts"]
            return _normalize(_extract_json("".join(p.get("text", "") for p in parts)))
        except Exception as e:  # noqa: BLE001
            last_err = e
            if "429" in str(e):
                break
    log.warning("Gemini tahlili amalga oshmadi: %s", last_err)
    return None


async def _analyze_anthropic(image: bytes, mime: str) -> dict | None:
    b64 = base64.b64encode(image).decode()
    try:
        data = await _post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
             "content-type": "application/json"},
            {"model": config.ANTHROPIC_MODEL, "max_tokens": 500,
             "messages": [{"role": "user", "content": [
                 {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                 {"type": "text", "text": PROMPT}]}]})
        text = "".join(c.get("text", "") for c in data.get("content", []) if c.get("type") == "text")
        return _normalize(_extract_json(text))
    except Exception as e:  # noqa: BLE001
        log.warning("Claude tahlili amalga oshmadi: %s", e)
        return None


async def analyze(image: bytes, mime: str = "image/jpeg") -> dict | None:
    if config.RECEIPT_AI == "gemini":
        return await _analyze_gemini(image, mime)
    if config.RECEIPT_AI == "anthropic":
        return await _analyze_anthropic(image, mime)
    return None


# ---- qaror ----
def _parse_dt(s) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(s).strip(), fmt).replace(tzinfo=config.TZ)
        except ValueError:
            continue
    return None


def decide(info: dict | None, *, expected: int, shop_card: str, created_at: datetime,
           now: datetime) -> tuple[str, str]:
    """Natija: (verdict, reason). verdict: accept | reject | review."""
    if info is None:
        return "review", "ai_unavailable"
    if not info["is_receipt"]:
        return "reject", "ai_not_receipt"
    if info["status"] == "failed":
        return "reject", "ai_failed"
    if info["amount"] is None:
        return "review", "ai_no_amount"
    if info["amount"] < expected:
        return "reject", "ai_low_amount"
    if info["looks_edited"]:
        return "review", "ai_edited"
    # Avtomatik tasdiqlash uchun qabul qiluvchi karta oxirgi 4 raqami o'qilib, shop kartasiga mos kelishi shart.
    last4 = re.sub(r"\D", "", shop_card or "")[-4:]
    if not info["recipient_last4"]:
        return "review", "ai_unsure"
    if last4 and info["recipient_last4"] != last4:
        return "reject", "ai_wrong_card"
    dt = _parse_dt(info["datetime"])
    if dt:
        if dt < created_at - timedelta(minutes=10):
            return "reject", "ai_old"
        if dt > now + timedelta(minutes=15):
            return "review", "ai_unsure"
    if info["status"] != "success":
        return "review", "ai_unsure"
    return "accept", "ai_ok"
