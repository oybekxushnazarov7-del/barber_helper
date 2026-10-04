"""Asosiy biznes mantiq: bo'sh vaqt, bron, bekor qilish, bloklash, sodiqlik, kutish ro'yxati."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import config
import ctx
import db
import i18n
import keyboards as kb

log = logging.getLogger(__name__)
FMT = "%Y-%m-%d %H:%M:%S"


# ---------- vaqt yordamchilari ----------
def now_local() -> datetime:
    return datetime.now(config.TZ)


def now_str() -> str:
    return now_local().strftime(FMT)


def today_str() -> str:
    return now_local().strftime("%Y-%m-%d")


def parse_date(s: str):
    return datetime.strptime(s, "%Y-%m-%d").date()


def date_plus(date_str: str, days: int) -> str:
    return (parse_date(date_str) + timedelta(days=days)).strftime("%Y-%m-%d")


def booking_start_dt(b: dict) -> datetime:
    d = parse_date(b["date"])
    return datetime(d.year, d.month, d.day, tzinfo=config.TZ) + timedelta(minutes=b["start_min"])


def hours_left(b: dict) -> float:
    return (booking_start_dt(b) - now_local()).total_seconds() / 3600


def norm_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:
        return "+998" + digits
    if len(digits) >= 9:
        return "+" + digits
    return digits


# ---------- bo'sh vaqtlar ----------
async def free_slots(staff_id: int, date_str: str, duration: int, step: int = 30,
                     exclude_id: int | None = None, lead: int | None = None) -> list[int]:
    today = today_str()
    if date_str < today:
        return []
    d = parse_date(date_str)
    hours = await db.get_work_hours(staff_id, d.weekday())
    if not hours:
        return []
    busy = [(x["start_min"], x["start_min"] + x["duration_min"])
            for x in await db.active_bookings(staff_id, date_str) if x["id"] != exclude_id]
    busy += [(x["start_min"], x["end_min"]) for x in await db.get_blocks(staff_id, date_str)]
    min_start = -1
    if date_str == today:
        now = now_local()
        min_start = now.hour * 60 + now.minute + (config.MIN_LEAD_MIN if lead is None else lead)
    result = set()
    for h in hours:
        t = h["start_min"]
        while t + duration <= h["end_min"]:
            if t >= min_start and not any(t < e and s < t + duration for s, e in busy):
                result.add(t)
            t += step
    return sorted(result)


async def date_status(staff_id: int, duration: int, step: int = 30,
                      lead: int | None = None) -> list[tuple[str, bool]]:
    """Keyingi kunlar: [(sana, bo'sh vaqt bormi)] — ish kuni bo'lmagan kunlar kiritilmaydi."""
    out = []
    today = today_str()
    for i in range(config.BOOK_DAYS):
        ds = date_plus(today, i)
        if not await db.get_work_hours(staff_id, parse_date(ds).weekday()):
            continue
        out.append((ds, bool(await free_slots(staff_id, ds, duration, step, lead=lead))))
    return out


async def available_dates(staff_id: int, duration: int, step: int = 30, lead: int | None = None) -> list[str]:
    return [d for d, free in await date_status(staff_id, duration, step, lead) if free]


async def outside_hours(staff_id: int, weekdays) -> int:
    """Kelgusi navbatlardan nechtasi (berilgan hafta kunlarida) ish vaqtidan tashqarida qolgan."""
    count = 0
    for b in await db.future_bookings_of_staff(staff_id, today_str()):
        wd = parse_date(b["date"]).weekday()
        if wd not in weekdays:
            continue
        hours = await db.get_work_hours(staff_id, wd)
        if not any(h["start_min"] <= b["start_min"] and b["start_min"] + b["duration_min"] <= h["end_min"]
                   for h in hours):
            count += 1
    return count


# ---------- sodiqlik ----------
async def loyalty_state(shop_id: int, client_id: int) -> dict:
    visits = await db.count_completed(shop_id, client_id)
    cycle = visits % config.LOYALTY_EVERY
    return {"visits": visits, "cycle": cycle, "discount_next": cycle == config.LOYALTY_EVERY - 1}


async def discount_for(shop_id: int, client_id: int) -> int:
    st = await loyalty_state(shop_id, client_id)
    if not st["discount_next"]:
        return 0
    if await db.has_active_discounted(shop_id, client_id):
        return 0
    return config.LOYALTY_DISCOUNT


def apply_discount(price: int, pct: int) -> int:
    return int(round(price * (100 - pct) / 100, -2)) if pct else price


# ---------- bron yaratish ----------
async def create_booking(shop: dict, client_id: int, staff_id: int, service: dict, date_str: str,
                         start_min: int, manual: bool = False) -> int | None:
    """Vaqt hali bo'sh bo'lsa bron yaratadi, bo'lmasa None qaytaradi."""
    async with db.lock:
        slots = await free_slots(staff_id, date_str, service["duration_min"], shop["slot_step"],
                                 lead=0 if manual else None)
        if start_min not in slots:
            return None
        pct = await discount_for(shop["id"], client_id)
        price = apply_discount(service["price"], pct)
        now = now_local()
        deadline = None
        use_credit = False
        deposit = 0 if manual else shop["deposit_amount"]
        client = await db.get_client(shop["id"], client_id)
        credit = client["deposit_credit"] if client else 0
        if deposit <= 0:
            status, dstat = "confirmed", "none"
        elif credit >= deposit:
            status, dstat, use_credit = "confirmed", "paid", True
        else:
            status, dstat = "pending_payment", "pending"
            deadline = (now + timedelta(minutes=config.PAY_TIMEOUT_MIN)).strftime(FMT)
        booking_id = await db.insert_booking(
            shop_id=shop["id"], client_id=client_id, staff_id=staff_id, service_id=service["id"],
            date=date_str, start_min=start_min, duration_min=service["duration_min"],
            price=price, status=status, deposit_amount=deposit, deposit_status=dstat,
            created_at=now.strftime(FMT), pay_deadline=deadline, discount_percent=pct,
            source="manual" if manual else "bot",
        )
        if use_credit:
            await db.add_credit(shop["id"], client_id, -deposit)
        await db.delete_waitlist_for(client_id, staff_id, date_str)
        return booking_id


async def client_future_bookings(shop_id: int, tg_id: int) -> list[dict]:
    now = now_local()
    rows = await db.client_active_bookings(shop_id, tg_id, today_str())
    return [b for b in rows if booking_start_dt(b) > now]


# ---------- bekor qilish ----------
async def cancel_booking(b: dict, by: str) -> str:
    """by='client' yoki 'barber'. Natija: 'credited' | 'forfeited' | 'check' | 'none'."""
    if b["status"] not in db.ACTIVE:
        return "none"
    dep, ds = b["deposit_amount"], b["deposit_status"]
    outcome = "none"
    new_ds = "cancelled"
    if by == "client":
        status = "cancelled_by_client"
        shop = await db.get_shop(b["shop_id"])
        if ds == "paid" and dep > 0:
            if hours_left(b) >= shop["free_cancel_hours"]:
                await db.add_credit(b["shop_id"], b["client_id"], dep)
                new_ds, outcome = "credited", "credited"
            else:
                new_ds, outcome = "forfeited", "forfeited"
        elif ds == "receipt_sent":
            outcome = "check"
    else:
        status = "cancelled_by_barber"
        if ds == "paid" and dep > 0:
            await db.add_credit(b["shop_id"], b["client_id"], dep)
            new_ds, outcome = "credited", "credited"
    await db.update_booking(b["id"], status=status, deposit_status=new_ds)
    await db.unmark_receipts(b["id"])
    await notify_waitlist(b["shop_id"], b["staff_id"], b["date"])
    return outcome


async def release_slot(b: dict) -> None:
    """Boshqa yo'l bilan (muddat tugashi, chek rad etilishi) bo'shagan vaqt haqida kutayotganlarga xabar."""
    await db.unmark_receipts(b["id"])
    await notify_waitlist(b["shop_id"], b["staff_id"], b["date"])


async def mark_arrived(b: dict) -> None:
    ds = "applied" if b["deposit_status"] == "paid" else b["deposit_status"]
    await db.update_booking(b["id"], status="completed", deposit_status=ds, completed_at=now_str())


async def mark_no_show(b: dict) -> int:
    ds = "forfeited" if b["deposit_status"] == "paid" else b["deposit_status"]
    await db.update_booking(b["id"], status="no_show", deposit_status=ds)
    count = await db.inc_no_show(b["shop_id"], b["client_id"])
    if count >= config.NO_SHOW_LIMIT:
        await db.set_client_blocked(b["shop_id"], b["client_id"], True)
    return count


# ---------- bloklash va ko'chirish ----------
async def find_next_slot(staff_id: int, date_str: str, min_start: int, duration: int,
                         step: int, exclude_id: int | None = None):
    """min_start dan keyingi eng yaqin bo'sh vaqt (bugun yoki keyingi kunlarda)."""
    for offset in range(0, 15):
        ds = date_plus(date_str, offset)
        slots = await free_slots(staff_id, ds, duration, step, exclude_id)
        if offset == 0:
            slots = [t for t in slots if t >= min_start]
        if slots:
            return ds, min(slots)
    return None


async def affected_bookings(staff_id: int, date_str: str, s: int, e: int) -> list[dict]:
    rows = await db.active_bookings(staff_id, date_str)
    return [b for b in rows if b["start_min"] < e and s < b["start_min"] + b["duration_min"]]


async def block_and_move(staff_id: int, date_str: str, s: int, e: int, step: int = 30) -> list[dict]:
    """Vaqtni bloklaydi, to'qnashgan bronlarni eng yaqin bo'sh vaqtga ko'chiradi."""
    async with db.lock:
        affected = sorted(await affected_bookings(staff_id, date_str, s, e), key=lambda x: x["start_min"])
        await db.add_block(staff_id, date_str, s, e)
        results = []
        for raw in affected:
            b = await db.get_booking(raw["id"])
            found = await find_next_slot(staff_id, date_str, e, b["duration_min"], step, exclude_id=b["id"])
            item = {"booking": b, "old_date": b["date"], "old_start": b["start_min"],
                    "new_date": None, "new_start": None, "cancelled": False}
            if found:
                nd, ns = found
                await db.update_booking(b["id"], date=nd, start_min=ns, rem_day_sent=0, rem_hour_sent=0,
                                        client_confirmed=0)
                item["new_date"], item["new_start"] = nd, ns
            else:
                await cancel_booking(b, "barber")
                item["cancelled"] = True
            results.append(item)
        return results


# ---------- kutish ro'yxati ----------
async def notify_waitlist(shop_id: int, staff_id: int, date_str: str) -> None:
    """Shu usta/kunda bo'sh vaqt paydo bo'lgan bo'lsa, kutayotganlarga (FIFO, 3 tagacha) xabar beradi."""
    bot = ctx.bots.get(shop_id)
    if bot is None:
        return
    try:
        entries = await db.waitlist_for(staff_id, date_str)
        if not entries:
            return
        shop = await db.get_shop(shop_id)
        now = now_local()
        sent = 0
        for e in entries:
            if sent >= 3:
                break
            if e["notified_at"]:
                last = datetime.strptime(e["notified_at"], FMT).replace(tzinfo=config.TZ)
                if (now - last).total_seconds() < 3600:
                    continue
            if e["client_id"] <= 0:
                continue
            if not await free_slots(staff_id, date_str, e["duration_min"], shop["slot_step"]):
                continue
            lang = await db.get_lang(shop_id, e["client_id"]) or "uz"
            text = i18n.tr(lang, "wl_free", staff=i18n.esc(e["staff_name"]), date=i18n.fmt_date(date_str, lang),
                           service=i18n.esc(e["service_name"]))
            try:
                await bot.send_message(e["client_id"], text,
                                       reply_markup=kb.ikb([[(i18n.tr(lang, "wl_pick_time"), f"wl_book:{e['id']}")]]))
                await db.mark_waitlist_notified(e["id"], now_str())
                sent += 1
            except Exception as ex:  # noqa: BLE001
                log.warning("Kutish ro'yxati xabari yuborilmadi: %s", ex)
    except Exception:  # noqa: BLE001
        log.exception("notify_waitlist xatosi")
