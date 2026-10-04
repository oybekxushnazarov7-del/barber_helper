"""Ishga tushgan botlar haqida umumiy ma'lumot (main.py to'ldiradi)."""
from __future__ import annotations

bots: dict = {}        # shop_id -> Bot
bot_shop: dict = {}    # bot_id -> shop_id
usernames: dict = {}   # shop_id -> bot username
