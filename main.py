from __future__ import annotations

import asyncio
import logging
import threading
from flask import Flask

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import config
import ctx
import db
import receipt_ai
import seed
import seed_demo
from handlers import admin, client, payment, setup
from scheduler import build_scheduler

# --- RENDER KEEPALIVE FLASK SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot tirik!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
# -------------------------------------

log = logging.getLogger("main")


class ShopMiddleware(BaseMiddleware):
    """Qaysi bot (shop) ga xabar kelganini aniqlaydi va foydalanuvchi tilini beradi."""

    async def __call__(self, handler, event, data):
        bot = data.get("bot")
        shop_id = ctx.bot_shop.get(bot.id) if bot else None
        if shop_id is None:
            return None
        data["shop_id"] = shop_id
        user = data.get("event_from_user")
        data["lang"] = (await db.get_lang(shop_id, user.id) if user else None) or "uz"
        return await handler(event, data)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    await db.init_db()
    if await seed.seed_if_empty():
        log.info("Boshlang'ich ma'lumotlar kiritildi (2 shop, 6 usta).")
        if config.DEMO_DATA and await seed_demo.generate():
            log.info("Demo (soxta) tarixiy ma'lumotlar qo'shildi. Ularni bot ichidan o'chirsa bo'ladi.")

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(ShopMiddleware())
    dp.include_router(admin.router)
    dp.include_router(setup.router)
    dp.include_router(payment.router)
    dp.include_router(client.router)

    bots: list[Bot] = []
    for shop_id, cfg in config.SHOPS.items():
        if not cfg["token"]:
            log.warning("Shop %s uchun token yo'q (.env), bu bot ishga tushmaydi.", shop_id)
            continue
        bot = Bot(token=cfg["token"], default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            me = await bot.get_me()
        except Exception as e:  # noqa: BLE001
            log.error("Shop %s: token noto'g'ri yoki internet yo'q (%s). .env ni tekshiring.", shop_id, e)
            await bot.session.close()
            continue
        ctx.bots[shop_id] = bot
        ctx.bot_shop[bot.id] = shop_id
        ctx.usernames[shop_id] = me.username
        await db.sync_owners(shop_id, config.owner_ids(shop_id))
        if not config.owner_ids(shop_id):
            log.warning("Shop %s uchun ega yo'q: .env ga SHOP%s_OWNER_ID yozing (botga /id yozsangiz ID chiqadi).",
                        shop_id, shop_id)
        await bot.set_my_commands([BotCommand(command="start", description="Boshlash / Начать"),
                                   BotCommand(command="id", description="Telegram ID")])
        await bot.delete_webhook(drop_pending_updates=True)
        bots.append(bot)
        log.info("Shop %s boti ishga tushdi: @%s", shop_id, me.username)

    if not bots:
        log.error("Hech qanday bot tokeni topilmadi. .env faylga SHOP1_TOKEN yozing.")
        return
    if config.RECEIPT_AI != "off":
        if receipt_ai.enabled():
            log.info("Chekni avtomatik tekshirish yoqilgan: %s", config.RECEIPT_AI)
        else:
            log.warning("RECEIPT_AI=%s, lekin API kalit yo'q: cheklar qo'lda tekshiriladi.", config.RECEIPT_AI)

    sched = build_scheduler()
    sched.start()
    try:
        await dp.start_polling(*bots)
    finally:
        sched.shutdown(wait=False)
        for b in bots:
            await b.session.close()
        await db.close_db()


if __name__ == "__main__":
    try:
        keep_alive()  # Web-serverni orqa fonda yoqish
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("To'xtatildi.")