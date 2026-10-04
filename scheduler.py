"""Avtomatik jarayonlar: to'lov muddati, eslatmalar, baho so'rovi, qaytarish xabari, ertalabki ro'yxat."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import ctx
import db
import i18n
import keyboards as kb
import services
from handlers.common import lang_of, safe_send
from i18n import esc, fmt_min, tr

log = logging.getLogger(__name__)


async def tick() -> None:
    """Har daqiqada ishlaydi."""
    for job in (_expire_unpaid, _send_reminders, _send_review_requests):
        try:
            await job()
        except Exception:  # noqa: BLE001
            log.exception("Scheduler xatosi (%s)", job.__name__)


async def _expire_unpaid() -> None:
    for b in await db.expired_pending(services.now_str()):
        await db.update_booking(b["id"], status="expired", deposit_status="cancelled")
        await services.release_slot(b)
        bot = ctx.bots.get(b["shop_id"])
        if bot:
            lang = await lang_of(b["shop_id"], b["client_id"])
            await safe_send(bot, b["client_id"],
                            tr(lang, "expired_msg", card=i18n.booking_card(b, lang)))


async def _send_reminders() -> None:
    now = services.now_local()
    today = services.today_str()
    rows = await db.confirmed_between(today, services.date_plus(today, 2))
    for b in rows:
        bot = ctx.bots.get(b["shop_id"])
        if not bot or b["client_id"] <= 0:
            continue
        start = services.booking_start_dt(b)
        left_min = (start - now).total_seconds() / 60
        created = datetime.strptime(b["created_at"], services.FMT).replace(tzinfo=config.TZ)
        lead_min = (start - created).total_seconds() / 60
        lang = await lang_of(b["shop_id"], b["client_id"])

        if not b["rem_day_sent"] and 120 < left_min <= 24 * 60 and lead_min > 24 * 60:
            await db.update_booking(b["id"], rem_day_sent=1)
            await safe_send(bot, b["client_id"],
                            tr(lang, "rem_day", card=i18n.booking_card(b, lang)),
                            reply_markup=kb.reminder_kb(lang, b["id"]))
        elif not b["rem_hour_sent"] and 0 < left_min <= 120 and lead_min > 120:
            await db.update_booking(b["id"], rem_hour_sent=1)
            await safe_send(bot, b["client_id"],
                            tr(lang, "rem_hour", card=i18n.booking_card(b, lang)),
                            reply_markup=kb.reminder_kb(lang, b["id"]))


async def _send_review_requests() -> None:
    cutoff = (services.now_local() - timedelta(minutes=config.REVIEW_DELAY_MIN)).strftime(services.FMT)
    for b in await db.review_requests_due(cutoff):
        await db.update_booking(b["id"], review_asked=1)
        bot = ctx.bots.get(b["shop_id"])
        if not bot:
            continue
        lang = await lang_of(b["shop_id"], b["client_id"])
        await safe_send(bot, b["client_id"], tr(lang, "rate_ask", barber=esc(b["staff_name"]),
                                                service=esc(b["service_name"])),
                        reply_markup=kb.rating_kb(b["id"]))


async def winback() -> None:
    """Har kuni 11:00: 3 hafta kelmagan mijozlarga qaytarish xabari (bir tashrif uchun bir marta)."""
    today = services.today_str()
    newest = services.date_plus(today, -config.WINBACK_DAYS)
    oldest = services.date_plus(today, -120)
    for shop_id, bot in ctx.bots.items():
        shop = await db.get_shop(shop_id)
        for c in await db.winback_candidates(shop_id, newest, oldest):
            if await services.client_future_bookings(shop_id, c["tg_id"]):
                await db.mark_winback(shop_id, c["tg_id"], c["last_date"])
                continue
            lang = c["lang"] or "uz"
            sent = await safe_send(bot, c["tg_id"],
                                   tr(lang, "winback", name=esc(c["name"] or ""), shop=esc(shop["name"]),
                                      days=config.WINBACK_DAYS),
                                   reply_markup=kb.winback_kb(lang))
            await db.mark_winback(shop_id, c["tg_id"], c["last_date"])
            if sent is None:
                log.info("Qaytarish xabari yetmadi: %s", c["tg_id"])


async def morning_digest() -> None:
    """Har kuni 08:30 da ustalarga va egalarga bugungi ro'yxat."""
    today = services.today_str()
    for shop_id, bot in ctx.bots.items():
        items = await db.bookings_for_day(shop_id, today)
        items = [b for b in items if b["status"] in ("confirmed", "pending_payment")]
        if not items:
            continue
        by_staff: dict[int, list] = {}
        for b in items:
            by_staff.setdefault(b["staff_id"], []).append(b)
        for staff_id, lst in by_staff.items():
            staff = await db.get_staff(staff_id)
            if staff and staff["tg_id"]:
                lang = await lang_of(shop_id, staff["tg_id"])
                text = tr(lang, "digest_barber", n=len(lst)) + "\n" + "\n".join(
                    f"• {fmt_min(b['start_min'])} {esc(b['client_name'] or '—')} — {esc(b['service_name'])}"
                    for b in lst)
                await safe_send(bot, staff["tg_id"], text)
        for o in await db.list_staff(shop_id, role="owner"):
            if o["tg_id"]:
                lang = await lang_of(shop_id, o["tg_id"])
                text = tr(lang, "digest_owner", n=len(items)) + "\n" + "\n".join(
                    f"• {fmt_min(b['start_min'])} {esc(b['staff_name'])}: {esc(b['client_name'] or '—')}"
                    for b in items)
                await safe_send(bot, o["tg_id"], text)


async def cleanup() -> None:
    await db.purge_waitlist(services.today_str())


def build_scheduler() -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone=config.TZ)
    sched.add_job(tick, "interval", minutes=1, id="tick", max_instances=1, coalesce=True)
    sched.add_job(morning_digest, "cron", hour=8, minute=30, id="morning", max_instances=1)
    sched.add_job(winback, "cron", hour=11, minute=0, id="winback", max_instances=1)
    sched.add_job(cleanup, "cron", hour=3, minute=0, id="cleanup", max_instances=1)
    return sched
