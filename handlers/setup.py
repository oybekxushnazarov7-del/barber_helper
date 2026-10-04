"""Do'kon sozlamalari: xizmatlar (nom, narx, davomiylik) va ustalar ish vaqti. Faqat egalar uchun."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
import keyboards as kb
import services
from handlers.common import StaffFilter, is_owner, send_or_edit
from i18n import WEEKDAYS, esc, fmt_min, money, tr, variants
from states import Hours, Svc

router = Router()
router.message.filter(StaffFilter())
router.callback_query.filter(StaffFilter())

DURATIONS = [30, 60, 90, 120]
STEP = 30


async def _deny(cb: CallbackQuery, staff_rows: list, lang: str) -> bool:
    if is_owner(staff_rows):
        return False
    await cb.answer(tr(lang, "owner_only"), show_alert=True)
    return True


# ====================================================================== XIZMATLAR
async def _services_screen(event, shop_id: int, lang: str) -> None:
    items = await db.list_services(shop_id)
    lines = [tr(lang, "sv_title"), ""]
    rows = []
    for s in items:
        lines.append(f"• {esc(s['name'])} — {money(s['price'], lang)} · {s['duration_min']} {tr(lang, 'min')}")
        rows.append([(f"✏️ {s['name']}", f"sv:{s['id']}")])
    rows.append([(tr(lang, "sv_btn_add"), "sv_add")])
    await send_or_edit(event, "\n".join(lines), kb.ikb(rows))


async def _service_detail(event, service_id: int, lang: str) -> None:
    s = await db.get_service(service_id)
    text = tr(lang, "sv_detail", name=esc(s["name"]), price=money(s["price"], lang), dur=s["duration_min"],
              unit=tr(lang, "min"))
    rows = [[(tr(lang, "sv_btn_name"), f"sv_ed:{s['id']}:name"), (tr(lang, "sv_btn_price"), f"sv_ed:{s['id']}:price")],
            [(tr(lang, "sv_btn_dur"), f"sv_ed:{s['id']}:dur")],
            [(tr(lang, "sv_btn_del"), f"sv_del:{s['id']}")],
            [(tr(lang, "btn_back"), "sv_back")]]
    await send_or_edit(event, text, kb.ikb(rows))


async def _own_service(service_id: int, shop_id: int):
    s = await db.get_service(service_id)
    return s if s and s["shop_id"] == shop_id and s["active"] else None


def _parse_price(raw: str) -> int | None:
    digits = raw.replace(" ", "").replace(",", "")
    if not digits.isdigit():
        return None
    value = int(digits)
    return value if 1000 <= value <= 10_000_000 else None


def _dur_kb(lang: str, prefix: str):
    rows = kb.grid([(f"{m} {tr(lang, 'min')}", f"{prefix}:{m}") for m in DURATIONS], 4)
    rows.append([(tr(lang, "btn_cancel"), "sv_back")])
    return kb.ikb(rows)


@router.message(F.text.in_(variants("btn_services")))
async def services_menu(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    if not is_owner(staff_rows):
        await message.answer(tr(lang, "owner_only"))
        return
    await _services_screen(message, shop_id, lang)


@router.callback_query(F.data == "sv_back")
async def sv_back(cb: CallbackQuery, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    await state.clear()
    await cb.answer()
    await _services_screen(cb, shop_id, lang)


@router.callback_query(F.data.regexp(r"^sv:\d+$"))
async def sv_open(cb: CallbackQuery, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    s = await _own_service(int(cb.data.split(":")[1]), shop_id)
    if not s:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    await state.clear()
    await cb.answer()
    await _service_detail(cb, s["id"], lang)


@router.callback_query(F.data.startswith("sv_ed:"))
async def sv_edit(cb: CallbackQuery, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    _, sid, field = cb.data.split(":")
    s = await _own_service(int(sid), shop_id)
    if not s:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    await cb.answer()
    if field == "dur":
        await send_or_edit(cb, tr(lang, "sv_pick_dur"), _dur_kb(lang, f"sv_dur:{s['id']}"))
        return
    await state.set_state(Svc.edit_name if field == "name" else Svc.edit_price)
    await state.update_data(service_id=s["id"])
    await cb.bot.send_message(cb.from_user.id, tr(lang, "sv_ask_name" if field == "name" else "sv_ask_price"))


@router.callback_query(F.data.startswith("sv_dur:"))
async def sv_set_duration(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    _, sid, minutes = cb.data.split(":")
    s = await _own_service(int(sid), shop_id)
    if not s or int(minutes) not in DURATIONS:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    await db.update_service(s["id"], duration_min=int(minutes))
    await cb.answer(tr(lang, "sv_saved"), show_alert=True)
    await _service_detail(cb, s["id"], lang)


@router.message(Svc.edit_name, F.text)
async def sv_edit_name(message: Message, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    name = message.text.strip()
    if not 2 <= len(name) <= 30:
        await message.answer(tr(lang, "sv_name_bad"))
        return
    s = await _own_service(data.get("service_id", 0), shop_id)
    await state.clear()
    if not s:
        return
    await db.update_service(s["id"], name=name)
    await message.answer(tr(lang, "sv_saved"))
    await _service_detail(message, s["id"], lang)


@router.message(Svc.edit_price, F.text)
async def sv_edit_price(message: Message, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    price = _parse_price(message.text)
    if price is None:
        await message.answer(tr(lang, "sv_price_bad"))
        return
    s = await _own_service(data.get("service_id", 0), shop_id)
    await state.clear()
    if not s:
        return
    await db.update_service(s["id"], price=price)
    await message.answer(tr(lang, "sv_saved"))
    await _service_detail(message, s["id"], lang)


# ---- yangi xizmat
@router.callback_query(F.data == "sv_add")
async def sv_add(cb: CallbackQuery, state: FSMContext, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    await state.set_state(Svc.add_name)
    await cb.answer()
    await cb.bot.send_message(cb.from_user.id, tr(lang, "sv_ask_name"))


@router.message(Svc.add_name, F.text)
async def sv_add_name(message: Message, state: FSMContext, lang: str):
    name = message.text.strip()
    if not 2 <= len(name) <= 30:
        await message.answer(tr(lang, "sv_name_bad"))
        return
    await state.update_data(new_name=name)
    await state.set_state(Svc.add_price)
    await message.answer(tr(lang, "sv_ask_price"))


@router.message(Svc.add_price, F.text)
async def sv_add_price(message: Message, state: FSMContext, lang: str):
    price = _parse_price(message.text)
    if price is None:
        await message.answer(tr(lang, "sv_price_bad"))
        return
    await state.update_data(new_price=price)
    await message.answer(tr(lang, "sv_pick_dur"), reply_markup=_dur_kb(lang, "sv_newdur"))


@router.callback_query(F.data.startswith("sv_newdur:"))
async def sv_add_duration(cb: CallbackQuery, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    data = await state.get_data()
    minutes = int(cb.data.split(":")[1])
    if "new_name" not in data or "new_price" not in data or minutes not in DURATIONS:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    await db.insert_service(shop_id, data["new_name"], data["new_price"], minutes)
    await state.clear()
    await cb.answer(tr(lang, "sv_added", name=data["new_name"]), show_alert=True)
    await _services_screen(cb, shop_id, lang)


# ---- o'chirish
@router.callback_query(F.data.startswith("sv_del:"))
async def sv_delete_ask(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    s = await _own_service(int(cb.data.split(":")[1]), shop_id)
    if not s:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    if len(await db.list_services(shop_id)) <= 1:
        await cb.answer(tr(lang, "sv_last"), show_alert=True)
        return
    await cb.answer()
    await send_or_edit(cb, tr(lang, "sv_del_ask", name=esc(s["name"])),
                       kb.ikb([[(tr(lang, "btn_yes_delete"), f"sv_del_yes:{s['id']}"), (tr(lang, "btn_no"), f"sv:{s['id']}")]]))


@router.callback_query(F.data.startswith("sv_del_yes:"))
async def sv_delete(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    s = await _own_service(int(cb.data.split(":")[1]), shop_id)
    if not s:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    if len(await db.list_services(shop_id)) <= 1:
        await cb.answer(tr(lang, "sv_last"), show_alert=True)
        return
    await db.deactivate_service(s["id"])
    await cb.answer(tr(lang, "sv_deleted"))
    await _services_screen(cb, shop_id, lang)


# ====================================================================== ISH VAQTI
def _day_line(lang: str, weekday: int, rows: list[dict]) -> str:
    name = WEEKDAYS.get(lang, WEEKDAYS["uz"])[weekday]
    if not rows:
        return f"{name}: {tr(lang, 'wh_off')}"
    return f"{name}: " + ", ".join(f"{fmt_min(r['start_min'])}–{fmt_min(r['end_min'])}" for r in rows)


async def _by_day(staff_id: int) -> dict[int, list[dict]]:
    by: dict[int, list[dict]] = {wd: [] for wd in range(7)}
    for r in await db.get_week_hours(staff_id):
        by[r["weekday"]].append(r)
    return by


async def _own_barber(staff_id: int, shop_id: int):
    s = await db.get_staff(staff_id)
    return s if s and s["shop_id"] == shop_id and s["role"] == "barber" and s["active"] else None


async def _week_screen(event, staff: dict, lang: str, note: str = "") -> None:
    by = await _by_day(staff["id"])
    wd_names = WEEKDAYS.get(lang, WEEKDAYS["uz"])
    lines = "\n".join(_day_line(lang, wd, by[wd]) for wd in range(7))
    text = tr(lang, "wh_screen", name=esc(staff["name"]), lines=lines)
    if note:
        text = note + "\n\n" + text
    items = [(("✅ " if by[wd] else "🔴 ") + wd_names[wd], f"wh_day:{staff['id']}:{wd}") for wd in range(7)]
    rows = kb.grid(items, 4)
    rows.append([(tr(lang, "wh_btn_all"), f"wh_edit:{staff['id']}:7")])
    rows.append([(tr(lang, "wh_btn_copy"), f"wh_copy:{staff['id']}")])
    await send_or_edit(event, text, kb.ikb(rows))


@router.message(F.text.in_(variants("btn_hours")))
async def hours_menu(message: Message, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    await state.clear()
    if not is_owner(staff_rows):
        await message.answer(tr(lang, "owner_only"))
        return
    barbers = await db.list_staff(shop_id, role="barber")
    if not barbers:
        await message.answer(tr(lang, "no_barbers"))
        return
    if len(barbers) == 1:
        await _week_screen(message, barbers[0], lang)
        return
    rows = kb.grid([(f"✂️ {b['name']}", f"wh_barber:{b['id']}") for b in barbers], 2)
    await message.answer(tr(lang, "wh_pick_barber"), reply_markup=kb.ikb(rows))


@router.callback_query(F.data.startswith("wh_barber:"))
async def wh_barber(cb: CallbackQuery, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    staff = await _own_barber(int(cb.data.split(":")[1]), shop_id)
    if not staff:
        await cb.answer(tr(lang, "barber_not_found"), show_alert=True)
        return
    await state.clear()
    await cb.answer()
    await _week_screen(cb, staff, lang)


@router.callback_query(F.data.startswith("wh_day:"))
async def wh_day(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    _, sid, wd = cb.data.split(":")
    staff = await _own_barber(int(sid), shop_id)
    if not staff:
        await cb.answer(tr(lang, "barber_not_found"), show_alert=True)
        return
    wd = int(wd)
    by = await _by_day(staff["id"])
    text = tr(lang, "wh_day_screen", name=esc(staff["name"]), day=WEEKDAYS.get(lang, WEEKDAYS["uz"])[wd],
              line=_day_line(lang, wd, by[wd]))
    rows = [[(tr(lang, "wh_btn_edit"), f"wh_edit:{staff['id']}:{wd}")]]
    if by[wd]:
        rows.append([(tr(lang, "wh_btn_off"), f"wh_off:{staff['id']}:{wd}")])
    rows.append([(tr(lang, "btn_back"), f"wh_barber:{staff['id']}")])
    await cb.answer()
    await send_or_edit(cb, text, kb.ikb(rows))


@router.callback_query(F.data.startswith("wh_off:"))
async def wh_off(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    _, sid, wd = cb.data.split(":")
    staff = await _own_barber(int(sid), shop_id)
    if not staff or not 0 <= int(wd) <= 6:
        await cb.answer(tr(lang, "barber_not_found"), show_alert=True)
        return
    await db.set_day_hours(staff["id"], int(wd), [])
    note = tr(lang, "wh_off_done")
    outside = await services.outside_hours(staff["id"], [int(wd)])
    if outside:
        note += "\n" + tr(lang, "wh_warn_outside", n=outside)
    await cb.answer()
    await _week_screen(cb, staff, lang, note)


# ---- vaqtni o'zgartirish: boshlanish -> tugash -> tushlik -> tushlik davomiyligi
@router.callback_query(F.data.startswith("wh_edit:"))
async def wh_edit(cb: CallbackQuery, state: FSMContext, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    _, sid, wd = cb.data.split(":")
    staff = await _own_barber(int(sid), shop_id)
    if not staff or not 0 <= int(wd) <= 7:
        await cb.answer(tr(lang, "barber_not_found"), show_alert=True)
        return
    await state.clear()
    await state.update_data(staff_id=staff["id"], wd=int(wd))
    await state.set_state(Hours.start)
    items = [(fmt_min(m), f"wh_s:{m}") for m in range(5 * 60, 15 * 60 + 1, STEP)]
    rows = kb.grid(items, 4)
    rows.append([(tr(lang, "btn_cancel"), f"wh_barber:{staff['id']}")])
    await cb.answer()
    await send_or_edit(cb, tr(lang, "wh_pick_start"), kb.ikb(rows))


@router.callback_query(F.data.startswith("wh_s:"))
async def wh_start(cb: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    if "staff_id" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    ws = int(cb.data.split(":")[1])
    await state.update_data(ws=ws)
    await state.set_state(Hours.end)
    items = [(fmt_min(m), f"wh_e:{m}") for m in range(ws + 60, 24 * 60 + 1, STEP)]
    rows = kb.grid(items, 4)
    rows.append([(tr(lang, "btn_cancel"), f"wh_barber:{data['staff_id']}")])
    await cb.answer()
    await send_or_edit(cb, tr(lang, "wh_pick_end"), kb.ikb(rows))


@router.callback_query(F.data.startswith("wh_e:"))
async def wh_end(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if "ws" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    ws, we = data["ws"], int(cb.data.split(":")[1])
    await state.update_data(we=we)
    options = list(range(ws + STEP, we - 2 * STEP + 1, STEP))  # tushlikdan oldin va keyin kamida 30 daqiqa ish
    preferred = [m for m in options if 10 * 60 <= m <= 17 * 60]
    options = preferred or options
    await cb.answer()
    if not options:
        await _save_hours(cb, state, shop_id, lang, [(ws, we)])
        return
    items = [(fmt_min(m), f"wh_l:{m}") for m in options]
    rows = kb.grid(items, 4)
    rows.insert(0, [(tr(lang, "wh_btn_nolunch"), "wh_l:0")])
    rows.append([(tr(lang, "btn_cancel"), f"wh_barber:{data['staff_id']}")])
    await state.set_state(Hours.lunch)
    await send_or_edit(cb, tr(lang, "wh_pick_lunch"), kb.ikb(rows))


@router.callback_query(F.data.startswith("wh_l:"))
async def wh_lunch(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if "we" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    ls = int(cb.data.split(":")[1])
    await cb.answer()
    if ls == 0:
        await _save_hours(cb, state, shop_id, lang, [(data["ws"], data["we"])])
        return
    await state.update_data(ls=ls)
    lens = [m for m in (30, 60, 90) if ls + m <= data["we"] - STEP]
    if not lens:
        await cb.bot.send_message(cb.from_user.id, tr(lang, "wh_bad_lunch"))
        return
    rows = kb.grid([(f"{m} {tr(lang, 'min')}", f"wh_ld:{m}") for m in lens], 3)
    rows.append([(tr(lang, "btn_cancel"), f"wh_barber:{data['staff_id']}")])
    await state.set_state(Hours.lunch_len)
    await send_or_edit(cb, tr(lang, "wh_pick_lunch_len"), kb.ikb(rows))


@router.callback_query(F.data.startswith("wh_ld:"))
async def wh_lunch_len(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if "ls" not in data:
        await cb.answer(tr(lang, "session_lost_admin"), show_alert=True)
        return
    ls, length = data["ls"], int(cb.data.split(":")[1])
    if ls + length > data["we"] - STEP:
        await cb.answer(tr(lang, "wh_bad_lunch"), show_alert=True)
        return
    await cb.answer()
    await _save_hours(cb, state, shop_id, lang, [(data["ws"], ls), (ls + length, data["we"])])


async def _save_hours(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str,
                      intervals: list[tuple[int, int]]) -> None:
    data = await state.get_data()
    staff = await _own_barber(data.get("staff_id", 0), shop_id)
    await state.clear()
    if not staff:
        return
    if data["wd"] == 7:  # hamma ish kunlariga (hozir ish kuni bo'lganlar; bo'lmasa Du-Sh)
        by = await _by_day(staff["id"])
        days = [wd for wd in range(7) if by[wd]] or list(range(6))
    else:
        days = [data["wd"]]
    for wd in days:
        await db.set_day_hours(staff["id"], wd, intervals)
    note = tr(lang, "wh_saved")
    outside = await services.outside_hours(staff["id"], days)
    if outside:
        note += "\n" + tr(lang, "wh_warn_outside", n=outside)
    await _week_screen(cb, staff, lang, note)


@router.callback_query(F.data.startswith("wh_copy:"))
async def wh_copy(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    if await _deny(cb, staff_rows, lang):
        return
    staff = await _own_barber(int(cb.data.split(":")[1]), shop_id)
    if not staff:
        await cb.answer(tr(lang, "barber_not_found"), show_alert=True)
        return
    others = [b for b in await db.list_staff(shop_id, role="barber") if b["id"] != staff["id"]]
    for b in others:
        await db.copy_week_hours(staff["id"], b["id"])
    await cb.answer()
    await _week_screen(cb, staff, lang, tr(lang, "wh_copied", n=len(others)))
