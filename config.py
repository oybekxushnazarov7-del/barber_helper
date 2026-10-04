from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip() or default)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).strip() or default)
    except ValueError:
        return default


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tashkent"))
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "barber.db"))

OWNER_ID = _int("OWNER_ID", 0)
CARD_NUMBER = os.getenv("CARD_NUMBER", "8600 0000 0000 0000").strip()
DEPOSIT_AMOUNT = _int("DEPOSIT_AMOUNT", 15000)
DEMO_DATA = _flag("DEMO_DATA", "1")

# shop_id -> sozlamalar. Token bo'sh bo'lsa, o'sha shop boti ishga tushmaydi.
SHOPS = {
    1: {"name": os.getenv("SHOP1_NAME", "Barber Shop 1"), "token": os.getenv("SHOP1_TOKEN", "").strip(),
        "lat": _float("SHOP1_LAT", 41.311081), "lon": _float("SHOP1_LON", 69.240562),
        "owner_id": _int("SHOP1_OWNER_ID", 0)},
    2: {"name": os.getenv("SHOP2_NAME", "Barber Shop 2"), "token": os.getenv("SHOP2_TOKEN", "").strip(),
        "lat": _float("SHOP2_LAT", 41.326000), "lon": _float("SHOP2_LON", 69.228000),
        "owner_id": _int("SHOP2_OWNER_ID", 0)},
}


def owner_ids(shop_id: int) -> set[int]:
    """Shopning egalari: shopga xos SHOPn_OWNER_ID + umumiy OWNER_ID (bo'sh bo'lsa hisobga olinmaydi)."""
    return {i for i in (SHOPS[shop_id]["owner_id"], OWNER_ID) if i}

# Umumiy qoidalar
SLOT_STEP = 30             # daqiqa
MIN_LEAD_MIN = 30          # hozirdan kamida shuncha daqiqa keyingi vaqtga yozilish mumkin
PAY_TIMEOUT_MIN = 30       # chek yuborish muddati
FREE_CANCEL_HOURS = 24     # shu soatdan oldin bekor qilinsa depozit kreditga o'tadi
BOOK_DAYS = 7              # nechta kun oldinga yozilish mumkin
MAX_ACTIVE_BOOKINGS = 2    # bir mijozning bir vaqtdagi faol bronlari
NO_SHOW_LIMIT = 3          # shuncha marta kelmasa, bron yopiladi

# Sodiqlik: har 3 ta tashrifdan keyin 4-si chegirma bilan
LOYALTY_EVERY = 4
LOYALTY_DISCOUNT = 20      # foiz
WINBACK_DAYS = 21          # shuncha kun kelmasa, qaytarish xabari
REVIEW_DELAY_MIN = 20      # xizmatdan keyin baho so'rash kechikishi

# Chekni avtomatik tekshirish
RECEIPT_AI = os.getenv("RECEIPT_AI", "off").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001").strip()
AI_MAX_ATTEMPTS = 3        # shuncha marta rad etilgach, chek qo'lda tekshiruvga o'tadi
