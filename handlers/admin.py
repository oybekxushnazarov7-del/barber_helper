from __future__ import annotations

import asyncio
import secrets

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

import config
import ctx
import db
import i18n
import keyboards as kb
import report
import seed
import services
from handlers.common import (StaffFilter, can_manage, is_owner, lang_of, my_barber_ids, notify_staff,
                             safe_send, send_or_edit)
from i18n import esc, fmt_date, fmt_min, money, tr, variants
from states import Block, Broadcast, Manual, Settings, StaffAdd

router = Router()
router.message.filter(StaffFilter())
router.callback_query.filter(StaffFilter())

EDITABLE = {
    "name": ("set_name", False),
    "deposit_amount": ("set_deposit", True),
    "card_number": ("set_card", False),
    "address": ("set_address", False),
    "phone": ("set_phone", False),
    "free_cancel_hours": ("set_cancel_hours", True),
}


async def _barber_choices(shop_id: int, staff_rows: list) -> list[dict]:
    if is_owner(staff_rows):
        return await db.list_staff(shop_id, role="barber")
    ids = my_barber_ids(staff_rows)
    return [r for r in staff_rows if r["id"] in ids]


# ------------------------------------------------------------------ menyu
@router.message(F.text.in_(variants("btn_admin")))
async def admin_panel(message: Message, state: FSMContext, staff_rows: list, lang: str):
    await state.clear()
    await message.answer(tr(lang, "admin_title"), reply_markup=kb.admin_menu(lang, is_owner(staff_rows)))


@router.message(F.text.in_(variants("btn_main")))
async def back_main(message: Message, state: FSMContext, lang: str):
    await state.clear()
    await message.answer(tr(lang, "menu_hint"), reply_markup=kb.main_menu(lang, True))


# ------------------------------------------------------------------ bugun / ertaga
async def day_view(message: Message, shop_id: int, staff_rows: list, offset: int, lang: str):
    date_str = services.date_plus(services.today_str(), offset)
    ids = None if is_owner(staff_rows) else my_barber_ids(staff_rows)
    items = await db.bookings_for_day(shop_id, date_str, ids)
    if not items:
        await message.answer(tr(lang, "day_empty", date=fmt_date(date_str, lang)))
        return
    await message.answer(tr(lang, "day_header", date=fmt_date(date_str, lang), n=len(items)))
    for b in items:
        markup = kb.attendance_kb(lang, b["id"]) if b["status"] == "confirmed" else None
        await message.answer(i18n.admin_booking(b, lang), reply_markup=markup)


@router.message(F.text.in_(variants("btn_today")))
async def today(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    await day_view(message, shop_id, staff_rows, 0, lang)


@router.message(F.text.in_(variants("btn_tomorrow")))
async def tomorrow(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    await day_view(message, shop_id, staff_rows, 1, lang)


# ------------------------------------------------------------------ keldi / kelmadi
@router.callback_query(F.data.startswith("arr:"))
async def arrived(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if not b or b["shop_id"] != shop_id or not can_manage(staff_rows, b):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    if b["status"] != "confirmed":
        await cb.answer(tr(lang, "status_changed"), show_alert=True)
        return
    await services.mark_arrived(b)
    await cb.answer(tr(lang, "arrived_toast"))
    await send_or_edit(cb, i18n.admin_booking({**b, "status": "completed"}, lang))


@router.callback_query(F.data.startswith("noshow:"))
async def no_show(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if not b or b["shop_id"] != shop_id or not can_manage(staff_rows, b):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    if b["status"] != "confirmed":
        await cb.answer(tr(lang, "status_changed"), show_alert=True)
        return
    count = await services.mark_no_show(b)
    await cb.answer(tr(lang, "noshow_toast"))
    extra = "\n" + tr(lang, "ns_count", n=count) if count else ""
    if count >= config.NO_SHOW_LIMIT:
        extra += " " + tr(lang, "ns_blocked")
    await send_or_edit(cb, i18n.admin_booking({**b, "status": "no_show"}, lang) + extra)


# ------------------------------------------------------------------ vaqtni bloklash
async def _show_block_dates(event, state: FSMContext, lang: str):
    today_s = services.today_str()
    dates = [services.date_plus(today_s, i) for i in range(config.BOOK_DAYS)]
    rows = kb.grid([(fmt_date(d, lang), f"bl_date:{d}") for d in dates], 3)
    rows.append([(tr(lang, "btn_cancel"), "bl_no")])
    await state.set_state(Block.date)
    await send_or_edit(event, tr(lang, "bl_pick_date"), kb.ikb(rows))


@router.message(F.text.in_(variants("btn_block")))
async def block_start(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    barbers = await _barber_choices(shop_id, staff_rows)
    if not barbers:
        await message.answer(tr(lang, "no_linked_barber"))
        return
    if len(barbers) == 1:
        await state.update_data(staff_id=barbers[0]["id"])
        await _show_block_dates(message, state, lang)
        return
    rows = kb.grid([(f"✂️ {b['name']}", f"bl_barber:{b['id']}") for b in barbers], 2)
    rows.append([(tr(lang, "btn_cancel"), "bl_no")])
    await state.set_state(Block.barber)
    await message.answer(tr(lang, "bl_pick_barber"), reply_markup=kb.ikb(rows))


@router.callback_query(F.data.startswith("bl_barber:"))
async def block_barber(cb: CallbackQuery, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    staff = await db.get_staff(int(cb.data.split(":")[1]))
    allowed = {b["id"] for b in await _barber_choices(shop_id, staff_rows)}
    if not staff or staff["id"] not in allowed:
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    await state.update_data(staff_id=staff["id"])
    await cb.answer()
    await _show_block_dates(cb, state, lang)


@router.callback_query(F.data.startswith("bl_date:"))
async def block_date(cb: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    if "staff_id" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    date_str = cb.data.split(":", 1)[1]
    hours = await db.get_work_hours(data["staff_id"], services.parse_date(date_str).weekday())
    await cb.answer()
    if not hours:
        await send_or_edit(cb, tr(lang, "bl_not_workday", date=fmt_date(date_str, lang)))
        await state.clear()
        return
    await state.update_data(date=date_str, day_start=hours[0]["start_min"], day_end=hours[-1]["end_min"])
    items = [(fmt_min(m), f"bl_from:{m}") for m in range(hours[0]["start_min"], hours[-1]["end_min"], config.SLOT_STEP)]
    rows = kb.grid(items, 4)
    rows.insert(0, [(tr(lang, "bl_whole_day"), "bl_day")])
    rows.append([(tr(lang, "btn_cancel"), "bl_no")])
    await state.set_state(Block.start)
    await send_or_edit(cb, tr(lang, "bl_from", date=fmt_date(date_str, lang)), kb.ikb(rows))


@router.callback_query(F.data.startswith("bl_from:"))
async def block_from(cb: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    if "date" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    start = int(cb.data.split(":")[1])
    await state.update_data(b_start=start)
    items = [(fmt_min(m), f"bl_to:{m}") for m in range(start + config.SLOT_STEP, data["day_end"] + 1, config.SLOT_STEP)]
    rows = kb.grid(items, 4)
    rows.append([(tr(lang, "btn_cancel"), "bl_no")])
    await state.set_state(Block.end)
    await cb.answer()
    await send_or_edit(cb, tr(lang, "bl_to", start=fmt_min(start)), kb.ikb(rows))


async def _block_confirm_screen(cb: CallbackQuery, state: FSMContext, s: int, e: int, lang: str):
    data = await state.get_data()
    staff = await db.get_staff(data["staff_id"])
    n = len(await services.affected_bookings(data["staff_id"], data["date"], s, e))
    span = tr(lang, "bl_whole") if (s, e) == (0, 1440) else f"{fmt_min(s)}–{fmt_min(e)}"
    await state.update_data(b_start=s, b_end=e)
    await state.set_state(Block.confirm)
    await send_or_edit(
        cb, tr(lang, "bl_confirm", barber=esc(staff["name"]), date=fmt_date(data["date"], lang), span=span, n=n),
        kb.ikb([[(tr(lang, "btn_confirm"), "bl_yes")], [(tr(lang, "btn_cancel"), "bl_no")]]))


@router.callback_query(F.data == "bl_day")
async def block_whole_day(cb: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    if "date" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    await cb.answer()
    await _block_confirm_screen(cb, state, 0, 1440, lang)


@router.callback_query(F.data.startswith("bl_to:"))
async def block_to(cb: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    if "b_start" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    await cb.answer()
    await _block_confirm_screen(cb, state, data["b_start"], int(cb.data.split(":")[1]), lang)


@router.callback_query(F.data == "bl_no")
async def block_cancel(cb: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await cb.answer()
    await send_or_edit(cb, tr(lang, "cancelled_plain"))


@router.callback_query(F.data == "bl_yes")
async def block_yes(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if "b_end" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    await cb.answer()
    await state.clear()
    shop = await db.get_shop(shop_id)
    staff = await db.get_staff(data["staff_id"])
    moves = await services.block_and_move(data["staff_id"], data["date"], data["b_start"], data["b_end"],
                                          shop["slot_step"])
    for m in moves:
        b = m["booking"]
        clang = await lang_of(shop_id, b["client_id"])
        who = esc(b.get("client_name") or "—")
        old = f"{fmt_date(m['old_date'], clang)} {fmt_min(m['old_start'])}"
        if m["cancelled"]:
            await safe_send(cb.bot, b["client_id"], tr(clang, "mv_msg_cancelled", who=who, old=old))
        else:
            new = f"{fmt_date(m['new_date'], clang)} {fmt_min(m['new_start'])}"
            await safe_send(cb.bot, b["client_id"], tr(clang, "mv_msg_moved", who=who, old=old, new=new),
                            reply_markup=kb.moved_kb(clang, b["id"]))

    def summary(lg: str) -> str:
        lines = [tr(lg, "bl_done", barber=esc(staff["name"]), date=fmt_date(data["date"], lg))]
        for m in moves:
            b = m["booking"]
            who = esc(b.get("client_name") or "—")
            old = f"{fmt_date(m['old_date'], lg)} {fmt_min(m['old_start'])}"
            if m["cancelled"]:
                lines.append(tr(lg, "bl_line_cancelled", who=who, old=old))
            else:
                lines.append(f"• {who}: {old} → {fmt_date(m['new_date'], lg)} {fmt_min(m['new_start'])}")
        if not moves:
            lines.append(tr(lg, "bl_none_moved"))
        return "\n".join(lines)

    await send_or_edit(cb, summary(lang))
    await notify_staff(cb.bot, shop_id, data["staff_id"], summary, exclude=cb.from_user.id)


# ------------------------------------------------------------------ qo'lda navbat qo'shish (telefon qilgan mijoz)
async def _manual_services(event, state: FSMContext, shop_id: int, lang: str):
    items = await db.list_services(shop_id)
    rows = [[(f"{s['name']} · {money(s['price'], lang)}", f"mn_service:{s['id']}")] for s in items]
    rows.append([(tr(lang, "btn_cancel"), "mn_cancel")])
    await state.set_state(Manual.service)
    await send_or_edit(event, tr(lang, "pick_service"), kb.ikb(rows))


@router.message(F.text.in_(variants("btn_manual")))
async def manual_start(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    barbers = await _barber_choices(shop_id, staff_rows)
    if not barbers:
        await message.answer(tr(lang, "no_linked_barber"))
        return
    await state.update_data(shop_id=shop_id)
    if len(barbers) == 1:
        await state.update_data(staff_id=barbers[0]["id"])
        await message.answer(tr(lang, "mn_intro"))
        await _manual_services(message, state, shop_id, lang)
        return
    rows = kb.grid([(f"✂️ {b['name']}", f"mn_barber:{b['id']}") for b in barbers], 2)
    rows.append([(tr(lang, "btn_cancel"), "mn_cancel")])
    await state.set_state(Manual.barber)
    await message.answer(tr(lang, "mn_intro") + "\n\n" + tr(lang, "bl_pick_barber"), reply_markup=kb.ikb(rows))


@router.callback_query(F.data == "mn_cancel")
async def manual_cancel(cb: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await cb.answer()
    await send_or_edit(cb, tr(lang, "cancelled_plain"))


@router.callback_query(F.data.startswith("mn_barber:"))
async def manual_barber(cb: CallbackQuery, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    staff = await db.get_staff(int(cb.data.split(":")[1]))
    allowed = {b["id"] for b in await _barber_choices(shop_id, staff_rows)}
    if not staff or staff["id"] not in allowed:
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    await state.update_data(staff_id=staff["id"])
    await cb.answer()
    await _manual_services(cb, state, shop_id, lang)


@router.callback_query(F.data.startswith("mn_service:"))
async def manual_service(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    svc = await db.get_service(int(cb.data.split(":")[1]))
    if "staff_id" not in data or not svc or svc["shop_id"] != shop_id:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    shop = await db.get_shop(shop_id)
    dates = await services.available_dates(data["staff_id"], svc["duration_min"], shop["slot_step"], lead=0)
    await state.update_data(service_id=svc["id"])
    await cb.answer()
    if not dates:
        await send_or_edit(cb, tr(lang, "no_dates"))
        await state.clear()
        return
    rows = kb.grid([(fmt_date(d, lang), f"mn_date:{d}") for d in dates], 3)
    rows.append([(tr(lang, "btn_cancel"), "mn_cancel")])
    await state.set_state(Manual.date)
    await send_or_edit(cb, tr(lang, "pick_date"), kb.ikb(rows))


@router.callback_query(F.data.startswith("mn_date:"))
async def manual_date(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if "service_id" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    date_str = cb.data.split(":", 1)[1]
    svc = await db.get_service(data["service_id"])
    shop = await db.get_shop(shop_id)
    slots = await services.free_slots(data["staff_id"], date_str, svc["duration_min"], shop["slot_step"], lead=0)
    await state.update_data(date=date_str)
    await cb.answer()
    if not slots:
        await send_or_edit(cb, tr(lang, "date_full_admin"))
        return
    rows = kb.grid([(fmt_min(m), f"mn_time:{m}") for m in slots], 4)
    rows.append([(tr(lang, "btn_cancel"), "mn_cancel")])
    await state.set_state(Manual.time)
    await send_or_edit(cb, tr(lang, "pick_time", date=fmt_date(date_str, lang)), kb.ikb(rows))


@router.callback_query(F.data.startswith("mn_time:"))
async def manual_time(cb: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    if "date" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    await state.update_data(start_min=int(cb.data.split(":")[1]))
    await state.set_state(Manual.name)
    await cb.answer()
    await send_or_edit(cb, tr(lang, "mn_ask_name"))


@router.message(Manual.name, F.text)
async def manual_name(message: Message, state: FSMContext, lang: str):
    name = message.text.strip()[:40]
    if len(name) < 2:
        await message.answer(tr(lang, "mn_ask_name"))
        return
    await state.update_data(client_name=name)
    await state.set_state(Manual.phone)
    await message.answer(tr(lang, "mn_ask_phone"), reply_markup=kb.ikb([[(tr(lang, "btn_skip"), "mn_skip")]]))


async def _manual_create(bot, chat_id: int, actor_id: int, state: FSMContext, shop_id: int, lang: str,
                         phone: str | None) -> None:
    data = await state.get_data()
    await state.clear()
    shop = await db.get_shop(shop_id)
    svc = await db.get_service(data["service_id"])
    name = data["client_name"]
    client_id = None
    if phone:
        existing = await db.find_client_by_phone(shop_id, phone)
        if existing:
            client_id = existing["tg_id"]
    if client_id is None:
        client_id = await db.new_virtual_client_id()
        await db.insert_client_full(shop_id, client_id, name, phone)
    booking_id = await services.create_booking(shop, client_id, data["staff_id"], svc, data["date"],
                                               data["start_min"], manual=True)
    if booking_id is None:
        await safe_send(bot, chat_id, tr(lang, "mn_taken"))
        return
    b = await db.get_booking(booking_id)
    text = tr(lang, "mn_done") + "\n\n" + i18n.admin_booking(b, lang)
    if b["discount_percent"]:
        text += "\n" + tr(lang, "mn_discount", pct=b["discount_percent"], price=money(b["price"], lang))
    await safe_send(bot, chat_id, text)
    await notify_staff(bot, shop_id, b["staff_id"],
                       lambda lg: tr(lg, "mn_notify") + "\n\n" + i18n.admin_booking(b, lg), exclude=actor_id)


@router.message(Manual.phone, F.text)
async def manual_phone(message: Message, state: FSMContext, shop_id: int, lang: str):
    phone = services.norm_phone(message.text)
    if len(phone.replace("+", "")) < 9:
        await message.answer(tr(lang, "mn_phone_bad"))
        return
    await _manual_create(message.bot, message.chat.id, message.from_user.id, state, shop_id, lang, phone)


@router.callback_query(F.data == "mn_skip")
async def manual_skip(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if "client_name" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    await cb.answer()
    await send_or_edit(cb, tr(lang, "mn_no_phone"))
    await _manual_create(cb.bot, cb.from_user.id, cb.from_user.id, state, shop_id, lang, None)


# ------------------------------------------------------------------ hisobot
def _period(key: str) -> tuple[str, str, str]:
    today_s = services.today_str()
    if key == "today":
        return today_s, today_s, "per_today"
    if key == "yesterday":
        y = services.date_plus(today_s, -1)
        return y, y, "per_yesterday"
    if key == "30":
        return services.date_plus(today_s, -29), today_s, "per_30"
    return services.date_plus(today_s, -6), today_s, "per_7"


async def _send_report(event, shop_id: int, staff_rows: list, key: str, lang: str):
    d_from, d_to, label_key = _period(key)
    ids = None if is_owner(staff_rows) else my_barber_ids(staff_rows)
    text = await report.build_report(shop_id, d_from, d_to, ids, lang, tr(lang, label_key))
    rows = [[(tr(lang, "per_today"), "rp:today"), (tr(lang, "per_yesterday"), "rp:yesterday")],
            [(tr(lang, "per_7"), "rp:7"), (tr(lang, "per_30"), "rp:30")]]
    await send_or_edit(event, text, kb.ikb(rows))


@router.message(F.text.in_(variants("btn_report")))
async def report_button(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    await _send_report(message, shop_id, staff_rows, "7", lang)


@router.callback_query(F.data.startswith("rp:"))
async def report_period(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    await cb.answer()
    await _send_report(cb, shop_id, staff_rows, cb.data.split(":")[1], lang)


# ------------------------------------------------------------------ mijozlar
@router.message(F.text.in_(variants("btn_clients")))
async def clients_list(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    if not is_owner(staff_rows):
        await message.answer(tr(lang, "owner_only"))
        return
    rows = await db.list_clients(shop_id, 20)
    if not rows:
        await message.answer(tr(lang, "clients_none"))
        return
    lines = [tr(lang, "clients_title")]
    buttons = []
    for c in rows:
        flag = " 🚫" if c["blocked"] else ""
        lines.append(f"• {esc(c['name'] or '—')} · {esc(c['phone'] or '—')} · {tr(lang, 'clients_noshow')}: {c['no_show_count']}{flag}")
        if c["blocked"] or c["no_show_count"] > 0:
            label = tr(lang, "btn_unblock") if c["blocked"] else tr(lang, "btn_block_client")
            buttons.append([(f"{label}: {c['name'] or c['tg_id']}", f"cl_toggle:{c['tg_id']}")])
    await message.answer("\n".join(lines), reply_markup=kb.ikb(buttons) if buttons else None)


@router.callback_query(F.data.startswith("cl_toggle:"))
async def client_toggle(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    if not is_owner(staff_rows):
        await cb.answer(tr(lang, "owner_only"), show_alert=True)
        return
    tg_id = int(cb.data.split(":")[1])
    c = await db.get_client(shop_id, tg_id)
    if not c:
        await cb.answer(tr(lang, "client_not_found"), show_alert=True)
        return
    await db.set_client_blocked(shop_id, tg_id, not c["blocked"])
    await cb.answer(tr(lang, "client_blocked") if not c["blocked"] else tr(lang, "client_unblocked"), show_alert=True)


# ------------------------------------------------------------------ sozlamalar
@router.message(F.text.in_(variants("btn_settings")))
async def settings(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    if not is_owner(staff_rows):
        await message.answer(tr(lang, "owner_only"))
        return
    s = await db.get_shop(shop_id)
    loc = tr(lang, "set_loc_yes") if s.get("lat") is not None else tr(lang, "set_loc_no")
    text = tr(lang, "settings_card", name=esc(s["name"]), dep=money(s["deposit_amount"], lang),
              card=esc(s["card_number"]), address=esc(s["address"]), phone=esc(s["phone"]),
              h=s["free_cancel_hours"], loc=loc)
    rows = [
        [(tr(lang, "set_btn_name"), "set:name")],
        [(tr(lang, "set_btn_deposit"), "set:deposit_amount")],
        [(tr(lang, "set_btn_card"), "set:card_number")],
        [(tr(lang, "set_btn_address"), "set:address"), (tr(lang, "set_btn_phone"), "set:phone")],
        [(tr(lang, "set_btn_cancel_hours"), "set:free_cancel_hours")],
        [(tr(lang, "set_btn_location"), "set_loc")],
    ]
    if await db.count_demo(shop_id):
        rows.append([(tr(lang, "set_btn_demo_clear"), "demo_clear")])
    await message.answer(text, reply_markup=kb.ikb(rows))


@router.callback_query(F.data.startswith("set:"))
async def set_field(cb: CallbackQuery, state: FSMContext, staff_rows: list, lang: str):
    field = cb.data.split(":")[1]
    if field not in EDITABLE or not is_owner(staff_rows):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    await state.set_state(Settings.value)
    await state.update_data(field=field)
    await cb.answer()
    await cb.bot.send_message(cb.from_user.id, tr(lang, "set_ask", what=tr(lang, EDITABLE[field][0])))


@router.message(Settings.value, F.text)
async def set_value(message: Message, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    field = data.get("field")
    if field not in EDITABLE:
        await state.clear()
        return
    raw = message.text.strip()
    value: int | str = raw
    if EDITABLE[field][1]:
        digits = raw.replace(" ", "")
        if not digits.isdigit():
            await message.answer(tr(lang, "set_digits"))
            return
        value = int(digits)
    await db.update_shop(shop_id, **{field: value})
    await state.clear()
    await message.answer(tr(lang, "set_saved"))


@router.callback_query(F.data == "set_loc")
async def set_location_ask(cb: CallbackQuery, state: FSMContext, staff_rows: list, lang: str):
    if not is_owner(staff_rows):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    await state.set_state(Settings.location)
    await cb.answer()
    await cb.bot.send_message(cb.from_user.id, tr(lang, "set_loc_ask"), reply_markup=kb.location_kb(lang))


@router.message(Settings.location, F.location)
async def set_location(message: Message, state: FSMContext, shop_id: int, lang: str):
    await db.update_shop(shop_id, lat=message.location.latitude, lon=message.location.longitude)
    await state.clear()
    await message.answer(tr(lang, "set_loc_saved"), reply_markup=kb.admin_menu(lang, True))


@router.callback_query(F.data == "demo_clear")
async def demo_clear_ask(cb: CallbackQuery, staff_rows: list, lang: str):
    if not is_owner(staff_rows):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    await cb.answer()
    await send_or_edit(cb, tr(lang, "demo_clear_ask"),
                       kb.ikb([[(tr(lang, "btn_yes_delete"), "demo_clear_yes"), (tr(lang, "btn_no"), "bl_no")]]))


@router.callback_query(F.data == "demo_clear_yes")
async def demo_clear_yes(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    if not is_owner(staff_rows):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    await db.clear_demo(shop_id)
    await cb.answer()
    await send_or_edit(cb, tr(lang, "demo_cleared"))


# ------------------------------------------------------------------ ustalar (qo'shish / o'chirish / bog'lash)
async def _staff_screen(event, shop_id: int, lang: str):
    username = ctx.usernames.get(shop_id, "")
    barbers = await db.list_staff(shop_id, role="barber")
    lines = [tr(lang, "staff_title")]
    rows = [[(tr(lang, "btn_staff_add"), "st_add")], [(tr(lang, "btn_staff_me"), "st_me")]]
    for b in barbers:
        if b["tg_id"]:
            lines.append(f"✂️ <b>{esc(b['name'])}</b> — {tr(lang, 'staff_linked')}")
            rows.append([(f"🔄 {b['name']}", f"st_unlink:{b['id']}"), (f"🗑 {b['name']}", f"st_del:{b['id']}")])
        else:
            lines.append(f"✂️ <b>{esc(b['name'])}</b> — {tr(lang, 'staff_not_linked')}\n"
                         f"https://t.me/{username}?start=join_{b['invite_code']}")
            rows.append([(f"🗑 {b['name']}", f"st_del:{b['id']}")])
    lines.append("\n" + tr(lang, "staff_hint"))
    text = "\n".join(lines)
    markup = kb.ikb(rows)
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=markup,
                                          link_preview_options=LinkPreviewOptions(is_disabled=True))
            return
        except Exception:  # noqa: BLE001
            await event.bot.send_message(event.from_user.id, text, reply_markup=markup,
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
    else:
        await event.answer(text, reply_markup=markup, link_preview_options=LinkPreviewOptions(is_disabled=True))


@router.message(F.text.in_(variants("btn_staff")))
async def staff_menu(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    if not is_owner(staff_rows):
        await message.answer(tr(lang, "owner_only"))
        return
    await _staff_screen(message, shop_id, lang)


@router.callback_query(F.data == "st_add")
async def staff_add_ask(cb: CallbackQuery, state: FSMContext, staff_rows: list, lang: str):
    if not is_owner(staff_rows):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    await state.set_state(StaffAdd.name)
    await cb.answer()
    await cb.bot.send_message(cb.from_user.id, tr(lang, "staff_add_ask"))


@router.message(StaffAdd.name, F.text)
async def staff_add_name(message: Message, state: FSMContext, shop_id: int, lang: str):
    name = message.text.strip()
    if not 2 <= len(name) <= 30:
        await message.answer(tr(lang, "staff_name_bad"))
        return
    await state.clear()
    staff = await seed.create_barber(shop_id, name)
    username = ctx.usernames.get(shop_id, "")
    await message.answer(tr(lang, "staff_added", name=esc(name),
                            link=f"https://t.me/{username}?start=join_{staff['invite_code']}"),
                         link_preview_options=LinkPreviewOptions(is_disabled=True))
    await _staff_screen(message, shop_id, lang)


@router.callback_query(F.data == "st_me")
async def staff_me(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    """Ega o'zini usta sifatida qo'shadi (havola bosish shart emas)."""
    if not is_owner(staff_rows):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    if my_barber_ids(staff_rows):
        await cb.answer(tr(lang, "staff_me_exists"), show_alert=True)
        return
    name = (cb.from_user.first_name or "Ega").strip()[:30]
    staff = await seed.create_barber(shop_id, name)
    await db.link_staff(staff["id"], cb.from_user.id)
    await cb.answer(tr(lang, "staff_me_done", name=name), show_alert=True)
    await _staff_screen(cb, shop_id, lang)


@router.callback_query(F.data.startswith("st_unlink:"))
async def staff_unlink(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    staff = await db.get_staff(int(cb.data.split(":")[1]))
    if not is_owner(staff_rows) or not staff or staff["shop_id"] != shop_id:
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    await db.unlink_staff(staff["id"], secrets.token_hex(4))
    await cb.answer(tr(lang, "staff_unlinked"))
    await _staff_screen(cb, shop_id, lang)


@router.callback_query(F.data.startswith("st_del:"))
async def staff_del_ask(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    staff = await db.get_staff(int(cb.data.split(":")[1]))
    if not is_owner(staff_rows) or not staff or staff["shop_id"] != shop_id:
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    if len(await db.list_staff(shop_id, role="barber")) <= 1:
        await cb.answer(tr(lang, "staff_last"), show_alert=True)
        return
    n = len(await db.future_bookings_of_staff(staff["id"], services.today_str()))
    await cb.answer()
    await send_or_edit(cb, tr(lang, "staff_del_ask", name=esc(staff["name"]), n=n),
                       kb.ikb([[(tr(lang, "btn_yes_delete"), f"st_del_yes:{staff['id']}"), (tr(lang, "btn_no"), "st_back")]]))


@router.callback_query(F.data == "st_back")
async def staff_back(cb: CallbackQuery, shop_id: int, lang: str):
    await cb.answer()
    await _staff_screen(cb, shop_id, lang)


@router.callback_query(F.data.startswith("st_del_yes:"))
async def staff_del_yes(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    staff = await db.get_staff(int(cb.data.split(":")[1]))
    if not is_owner(staff_rows) or not staff or staff["shop_id"] != shop_id:
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    if len(await db.list_staff(shop_id, role="barber")) <= 1:
        await cb.answer(tr(lang, "staff_last"), show_alert=True)
        return
    for b in await db.future_bookings_of_staff(staff["id"], services.today_str()):
        await services.cancel_booking(b, "barber")
        clang = await lang_of(shop_id, b["client_id"])
        await safe_send(cb.bot, b["client_id"],
                        tr(clang, "staff_removed_client", barber=esc(staff["name"]),
                           when=f"{fmt_date(b['date'], clang)} {fmt_min(b['start_min'])}"))
    await db.deactivate_staff(staff["id"])
    await cb.answer(tr(lang, "staff_deleted"))
    await _staff_screen(cb, shop_id, lang)


# ------------------------------------------------------------------ ommaviy xabar (faqat ega)
@router.message(F.text.in_(variants("btn_broadcast")))
async def broadcast_start(message: Message, state: FSMContext, staff_rows: list, lang: str):
    await state.clear()
    if not is_owner(staff_rows):
        await message.answer(tr(lang, "owner_only"))
        return
    await state.set_state(Broadcast.content)
    await message.answer(tr(lang, "bc_ask"))


@router.message(Broadcast.content)
async def broadcast_content(message: Message, state: FSMContext, shop_id: int, lang: str):
    targets = await db.broadcast_targets(shop_id)
    if not targets:
        await state.clear()
        await message.answer(tr(lang, "bc_nobody"))
        return
    await state.update_data(bc_chat=message.chat.id, bc_msg=message.message_id)
    await state.set_state(Broadcast.confirm)
    await message.answer(tr(lang, "bc_confirm", n=len(targets)),
                         reply_markup=kb.ikb([[(tr(lang, "btn_send"), "bc_yes"), (tr(lang, "btn_cancel"), "bc_no")]]))


@router.callback_query(F.data == "bc_no")
async def broadcast_no(cb: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await cb.answer()
    await send_or_edit(cb, tr(lang, "cancelled_plain"))


@router.callback_query(F.data == "bc_yes")
async def broadcast_yes(cb: CallbackQuery, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    data = await state.get_data()
    if not is_owner(staff_rows) or "bc_msg" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    await state.clear()
    await cb.answer()
    targets = await db.broadcast_targets(shop_id)
    await send_or_edit(cb, tr(lang, "bc_sending", n=len(targets)))
    ok = fail = 0
    for tg_id in targets:
        for attempt in range(2):
            try:
                await cb.bot.copy_message(tg_id, data["bc_chat"], data["bc_msg"])
                ok += 1
                break
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except TelegramForbiddenError:
                fail += 1
                break
            except Exception:  # noqa: BLE001
                fail += 1
                break
        else:
            fail += 1
        await asyncio.sleep(0.06)
    await cb.bot.send_message(cb.from_user.id, tr(lang, "bc_done", ok=ok, fail=fail))
