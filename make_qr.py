"""Har bir bot uchun QR kod rasmini yasaydi: python make_qr.py"""
from __future__ import annotations

import asyncio

import qrcode
from aiogram import Bot

import config


async def main() -> None:
    for shop_id, cfg in config.SHOPS.items():
        if not cfg["token"]:
            print(f"Shop {shop_id}: token yo'q, o'tkazib yuborildi.")
            continue
        bot = Bot(token=cfg["token"])
        me = await bot.get_me()
        await bot.session.close()
        url = f"https://t.me/{me.username}"
        file = f"qr_shop{shop_id}.png"
        qrcode.make(url).save(file)
        print(f"Shop {shop_id}: {url} -> {file}")


if __name__ == "__main__":
    asyncio.run(main())
