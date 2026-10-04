from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import config
import db
import i18n
import keyboards as kb
import receipt_ai
import services
from handlers.common import notify_staff, send_or_edit
from i18n import esc, fmt_date, fmt_min, money, tr, variants
from states import Book, Review

router = Router()


async def _menu(shop_id: int, user_id: int, lang: str):
    return kb.main_menu(lang, bool(await db.staff_by_tg(shop_id, user_id)))


# ------------------------------------------------------------------ /start, til, /id
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, shop_id: int, lang: str):
    await state.clear()
    user = message.from_user
    await db.upsert_client(shop_id, user.id, user.full_name)

    args = command.args or ""
    if args.startswith("join_"):
        code = args[5:]
        staff = await db.staff_by_invite(shop_id, code)
        if staff and staff["tg_id"] in (None, user.id):
            await message.answer(
                tr(lang, "join_ask", name=esc(staff["name"])),
                reply_markup=kb.ikb([[(tr(lang, "btn_join_yes"), f"join_yes:{code}"),
                                      (tr(lang, "btn_join_no"), "join_no")]]))
            return
        await message.answer(tr(lang, "join_bad"))

    if await db.get_lang(shop_id, user.id) is None:
        await message.answer(tr("uz", "choose_lang") + "\n" + tr("ru", "choose_lang"), reply_markup=kb.lang_kb())
        return
    shop = await db.get_shop(shop_id)
    await message.answer(tr(lang, "welcome", shop=esc(shop["name"])), reply_markup=await _menu(shop_id, user.id, lang))


@router.callback_query(F.data.startswith("join_yes:"))
async def join_yes(cb: CallbackQuery, shop_id: int, lang: str):
    user = cb.from_user
    staff = await db.staff_by_invite(shop_id, cb.data.split(":", 1)[1])
    if not staff or staff["tg_id"] not in (None, user.id):
        await cb.answer(tr(lang, "join_bad"), show_alert=True)
        return
    await db.link_staff(staff["id"], user.id)
    await cb.answer()
    await send_or_edit(cb, tr(lang, "joined", name=esc(staff["name"])))
    await cb.bot.send_message(user.id, tr(lang, "menu_hint"), reply_markup=await _menu(shop_id, user.id, lang))
    if await db.get_lang(shop_id, user.id) is None:
        await cb.bot.send_message(user.id, tr("uz", "choose_lang") + "\n" + tr("ru", "choose_lang"),
                                  reply_markup=kb.lang_kb())


@router.callback_query(F.data == "join_no")
async def join_no(cb: CallbackQuery, lang: str):
    await cb.answer()
    await send_or_edit(cb, tr(lang, "join_no"))


@router.message(F.text.in_(variants("btn_lang")))
async def lang_button(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(tr("uz", "choose_lang") + "\n" + tr("ru", "choose_lang"), reply_markup=kb.lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def pick_lang(cb: CallbackQuery, shop_id: int):
    new = cb.data.split(":")[1]
    if new not in ("uz", "ru"):
        await cb.answer()
        return
    await db.upsert_client(shop_id, cb.from_user.id, cb.from_user.full_name)
    await db.set_lang(shop_id, cb.from_user.id, new)
    shop = await db.get_shop(shop_id)
    await cb.answer()
    await send_or_edit(cb, tr(new, "lang_saved"))
    await cb.bot.send_message(cb.from_user.id, tr(new, "welcome", shop=esc(shop["name"])),
                              reply_markup=await _menu(shop_id, cb.from_user.id, new))


@router.message(Command("id"))
async def cmd_id(message: Message, lang: str):
    await message.answer(tr(lang, "your_id", id=message.from_user.id))


# ------------------------------------------------------------------ narxlar, manzil, sodiqlik
@router.message(F.text.in_(variants("btn_prices")))
async def prices(message: Message, state: FSMContext, shop_id: int, lang: str):
    await state.clear()
    items = await db.list_services(shop_id)
    barbers = await db.list_staff(shop_id, role="barber")
    lines = [tr(lang, "prices_title")]
    for s in items:
        lines.append(f"• {esc(s['name'])} — {money(s['price'], lang)} ({s['duration_min']} {tr(lang, 'min')})")
    lines.append("\n" + tr(lang, "prices_barbers", names=", ".join(esc(b["name"]) for b in barbers)))
    lines.append(tr(lang, "prices_loyalty", n=config.LOYALTY_EVERY - 1, pct=config.LOYALTY_DISCOUNT))
    await message.answer("\n".join(lines))


@router.message(F.text.in_(variants("btn_address")))
async def address(message: Message, state: FSMContext, shop_id: int, lang: str):
    await state.clear()
    shop = await db.get_shop(shop_id)
    text = tr(lang, "address_card", name=esc(shop["name"]), address=esc(shop["address"] or "—"),
              phone=esc(shop["phone"] or "—"))
    if shop.get("lat") is not None and shop.get("lon") is not None:
        try:
            await message.bot.send_venue(message.chat.id, shop["lat"], shop["lon"], title=shop["name"],
                                         address=shop["address"] or "—")
        except Exception:  # noqa: BLE001
            await message.bot.send_location(message.chat.id, shop["lat"], shop["lon"])
        await message.answer(text, reply_markup=kb.maps_kb(lang, shop["lat"], shop["lon"]))
    else:
        await message.answer(text)


@router.message(F.text.in_(variants("btn_loyalty")))
async def loyalty(message: Message, state: FSMContext, shop_id: int, lang: str):
    await state.clear()
    st = await services.loyalty_state(shop_id, message.from_user.id)
    dots = " ".join("●" if i < st["cycle"] else "○" for i in range(config.LOYALTY_EVERY - 1)) + " 🎁"
    if st["discount_next"]:
        text = tr(lang, "loy_ready", dots=dots, pct=config.LOYALTY_DISCOUNT, visits=st["visits"])
    else:
        text = tr(lang, "loy_progress", dots=dots, left=config.LOYALTY_EVERY - 1 - st["cycle"],
                  pct=config.LOYALTY_DISCOUNT, visits=st["visits"])
    await message.answer(text)


# ------------------------------------------------------------------ yozilish oqimi
async def begin_booking(event, state: FSMContext, shop_id: int, user_id: int, lang: str):
    await state.clear()
    client = await db.get_client(shop_id, user_id)
    if client and client["blocked"]:
        await send_or_edit(event, tr(lang, "blocked_msg"))
        return
    active = await services.client_future_bookings(shop_id, user_id)
    if len(active) >= config.MAX_ACTIVE_BOOKINGS:
        await send_or_edit(event, tr(lang, "too_many", n=len(active)))
        return
    barbers = await db.list_staff(shop_id, role="barber")
    if not barbers:
        await send_or_edit(event, tr(lang, "no_barbers"))
        return
    await state.update_data(shop_id=shop_id, multi=len(barbers) > 1)
    if len(barbers) == 1:
        await state.update_data(staff_id=barbers[0]["id"])
        await show_services(event, state, shop_id, lang)
        return
    rows = kb.grid([(f"✂️ {b['name']}", f"bk_barber:{b['id']}") for b in barbers], 2)
    rows.append([(tr(lang, "btn_cancel"), "bk_cancel")])
    await send_or_edit(event, tr(lang, "pick_barber"), kb.ikb(rows))
    await state.set_state(Book.barber)


@router.message(F.text.in_(variants("btn_book")))
async def book_button(message: Message, state: FSMContext, shop_id: int, lang: str):
    await begin_booking(message, state, shop_id, message.from_user.id, lang)


@router.callback_query(F.data == "wb_book")
async def winback_book(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    await cb.answer()
    await begin_booking(cb.message, state, shop_id, cb.from_user.id, lang)


async def show_services(event, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    items = await db.list_services(shop_id)
    rows = [[(f"{s['name']} · {money(s['price'], lang)}", f"bk_service:{s['id']}")] for s in items]
    nav = []
    if data.get("multi"):
        nav.append((tr(lang, "btn_back"), "bk_back:barber"))
    nav.append((tr(lang, "btn_cancel"), "bk_cancel"))
    rows.append(nav)
    await send_or_edit(event, tr(lang, "pick_service"), kb.ikb(rows))
    await state.set_state(Book.service)


async def show_dates(event, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    svc = await db.get_service(data["service_id"])
    shop = await db.get_shop(shop_id)
    status = await services.date_status(data["staff_id"], svc["duration_min"], shop["slot_step"])
    back = [(tr(lang, "btn_back"), "bk_back:service"), (tr(lang, "btn_cancel"), "bk_cancel")]
    if not status:
        await send_or_edit(event, tr(lang, "no_dates"), kb.ikb([back]))
        return
    items = [((fmt_date(d, lang) if free else f"🔴 {fmt_date(d, lang)}"), f"bk_date:{d}") for d, free in status]
    rows = kb.grid(items, 3)
    rows.append(back)
    await send_or_edit(event, tr(lang, "pick_date"), kb.ikb(rows))
    await state.set_state(Book.date)


def _waitlist_kb(lang: str):
    return kb.ikb([[(tr(lang, "btn_waitlist"), "wl_add")],
                   [(tr(lang, "btn_back"), "bk_back:date"), (tr(lang, "btn_cancel"), "bk_cancel")]])


async def show_times(event, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    svc = await db.get_service(data["service_id"])
    shop = await db.get_shop(shop_id)
    slots = await services.free_slots(data["staff_id"], data["date"], svc["duration_min"], shop["slot_step"])
    if not slots:
        await send_or_edit(event, tr(lang, "date_full", date=fmt_date(data["date"], lang)), _waitlist_kb(lang))
        return
    rows = kb.grid([(fmt_min(m), f"bk_time:{m}") for m in slots], 4)
    rows.append([(tr(lang, "btn_back"), "bk_back:date"), (tr(lang, "btn_cancel"), "bk_cancel")])
    await send_or_edit(event, tr(lang, "pick_time", date=fmt_date(data["date"], lang)), kb.ikb(rows))
    await state.set_state(Book.time)


@router.callback_query(F.data.startswith("bk_barber:"))
async def pick_barber(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    staff = await db.get_staff(int(cb.data.split(":")[1]))
    if not staff or staff["shop_id"] != shop_id or staff["role"] != "barber" or not staff["active"]:
        await cb.answer(tr(lang, "barber_not_found"), show_alert=True)
        return
    await state.update_data(shop_id=shop_id, multi=True, staff_id=staff["id"])
    await cb.answer()
    await show_services(cb, state, shop_id, lang)


@router.callback_query(F.data.startswith("bk_back:"))
async def go_back(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    await cb.answer()
    to = cb.data.split(":")[1]
    data = await state.get_data()
    if to == "barber":
        await begin_booking(cb, state, shop_id, cb.from_user.id, lang)
    elif to == "service" and "staff_id" in data:
        await show_services(cb, state, shop_id, lang)
    elif to == "date" and "service_id" in data:
        await show_dates(cb, state, shop_id, lang)
    else:
        await send_or_edit(cb, tr(lang, "session_lost"))


@router.callback_query(F.data.startswith("bk_service:"))
async def pick_service(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    svc = await db.get_service(int(cb.data.split(":")[1]))
    if "staff_id" not in data or not svc or svc["shop_id"] != shop_id:
        await cb.answer(tr(lang, "session_lost"), show_alert=True)
        return
    await state.update_data(service_id=svc["id"])
    await cb.answer()
    await show_dates(cb, state, shop_id, lang)


@router.callback_query(F.data.startswith("bk_date:"))
async def pick_date(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if "service_id" not in data:
        await cb.answer(tr(lang, "session_lost"), show_alert=True)
        return
    await state.update_data(date=cb.data.split(":", 1)[1])
    await cb.answer()
    await show_times(cb, state, shop_id, lang)


@router.callback_query(F.data.startswith("bk_time:"))
async def pick_time(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if "date" not in data:
        await cb.answer(tr(lang, "session_lost"), show_alert=True)
        return
    start = int(cb.data.split(":")[1])
    svc = await db.get_service(data["service_id"])
    shop = await db.get_shop(shop_id)
    if start not in await services.free_slots(data["staff_id"], data["date"], svc["duration_min"], shop["slot_step"]):
        await cb.answer(tr(lang, "slot_taken"), show_alert=True)
        await show_times(cb, state, shop_id, lang)
        return
    await state.update_data(start_min=start)
    await cb.answer()
    client = await db.get_client(shop_id, cb.from_user.id)
    if client and client["phone"]:
        await show_summary(cb, state, shop_id, cb.from_user.id, lang)
    else:
        await state.set_state(Book.phone)
        await cb.bot.send_message(cb.from_user.id, tr(lang, "ask_phone"), reply_markup=kb.phone_kb(lang))


async def _link_virtual(shop_id: int, real_id: int, phone: str) -> None:
    """Usta oldin qo'lda kiritgan shu raqamli mijoz bilan tarixni (sodiqlik, kredit) birlashtiradi."""
    virtual = await db.find_client_by_phone(shop_id, phone, virtual_only=True)
    if virtual and virtual["tg_id"] != real_id:
        await db.merge_client(shop_id, virtual["tg_id"], real_id)


@router.message(Book.phone, F.contact)
async def got_phone(message: Message, state: FSMContext, shop_id: int, lang: str):
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer(tr(lang, "phone_wrong"))
        return
    phone = services.norm_phone(contact.phone_number)
    await db.set_phone(shop_id, message.from_user.id, phone)
    await _link_virtual(shop_id, message.from_user.id, phone)
    await message.answer(tr(lang, "phone_ok"), reply_markup=await _menu(shop_id, message.from_user.id, lang))
    await show_summary(message, state, shop_id, message.from_user.id, lang)


@router.message(Book.phone)
async def phone_other(message: Message, lang: str):
    await message.answer(tr(lang, "phone_other"), reply_markup=kb.phone_kb(lang))


async def show_summary(event, state: FSMContext, shop_id: int, user_id: int, lang: str):
    data = await state.get_data()
    svc = await db.get_service(data["service_id"])
    staff = await db.get_staff(data["staff_id"])
    shop = await db.get_shop(shop_id)
    client = await db.get_client(shop_id, user_id)
    pct = await services.discount_for(shop_id, user_id)
    price = services.apply_discount(svc["price"], pct)
    lines = [tr(lang, "summary_title"),
             tr(lang, "line_barber", v=esc(staff["name"])),
             tr(lang, "line_service", v=esc(svc["name"])),
             f"📅 {fmt_date(data['date'], lang)} · {fmt_min(data['start_min'])}"]
    if pct:
        lines.append(tr(lang, "line_price_disc", old=money(svc["price"], lang), new=money(price, lang), pct=pct))
    else:
        lines.append(tr(lang, "line_price", v=money(price, lang)))
    lines += ["", tr(lang, "rules", dep=money(shop["deposit_amount"], lang), h=shop["free_cancel_hours"])]
    credit = client["deposit_credit"] if client else 0
    if shop["deposit_amount"] > 0 and credit >= shop["deposit_amount"]:
        lines.append("\n" + tr(lang, "credit_note", v=money(credit, lang)))
    await state.set_state(Book.confirm)
    await send_or_edit(event, "\n".join(lines), kb.confirm_booking_kb(lang))


@router.callback_query(F.data == "bk_cancel")
async def book_cancel(cb: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await cb.answer()
    await send_or_edit(cb, tr(lang, "book_cancelled"))


@router.callback_query(F.data == "bk_confirm")
async def book_confirm(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if "start_min" not in data:
        await cb.answer(tr(lang, "session_lost"), show_alert=True)
        return
    await cb.answer()
    shop = await db.get_shop(shop_id)
    svc = await db.get_service(data["service_id"])
    booking_id = await services.create_booking(
        shop, cb.from_user.id, data["staff_id"], svc, data["date"], data["start_min"])
    if booking_id is None:
        await send_or_edit(cb, tr(lang, "slot_taken_full"))
        await show_times(cb, state, shop_id, lang)
        return
    await state.clear()
    b = await db.get_booking(booking_id)
    if b["status"] == "pending_payment":
        text = i18n.booking_card(b, lang) + "\n\n" + tr(lang, "pay_instruction", card=esc(shop["card_number"]),
                                                       sum=money(shop["deposit_amount"], lang),
                                                       m=config.PAY_TIMEOUT_MIN)
        if receipt_ai.enabled():
            text += "\n" + tr(lang, "pay_auto")
        await send_or_edit(cb, text)
    else:
        await send_or_edit(cb, tr(lang, "booking_confirmed", card=i18n.booking_card(b, lang)))
        await notify_staff(cb.bot, shop_id, b["staff_id"],
                           lambda lg: tr(lg, "staff_new_booking_credit") + "\n\n" + i18n.admin_booking(b, lg))
    await cb.bot.send_message(cb.from_user.id, tr(lang, "menu_hint"),
                              reply_markup=await _menu(shop_id, cb.from_user.id, lang))


# ------------------------------------------------------------------ kutish ro'yxati
@router.callback_query(F.data == "wl_add")
async def wl_add(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    if not all(k in data for k in ("staff_id", "service_id", "date")):
        await cb.answer(tr(lang, "session_lost"), show_alert=True)
        return
    staff = await db.get_staff(data["staff_id"])
    await db.add_waitlist(shop_id, cb.from_user.id, data["staff_id"], data["service_id"], data["date"],
                          services.now_str())
    await state.clear()
    await cb.answer()
    await send_or_edit(cb, tr(lang, "wl_added", date=fmt_date(data["date"], lang), staff=esc(staff["name"])))


@router.callback_query(F.data.startswith("wl_book:"))
async def wl_book(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    e = await db.get_waitlist(int(cb.data.split(":")[1]))
    if not e or e["client_id"] != cb.from_user.id or e["shop_id"] != shop_id:
        await cb.answer(tr(lang, "wl_gone"), show_alert=True)
        return
    await state.clear()
    await state.update_data(shop_id=shop_id, multi=False, staff_id=e["staff_id"], service_id=e["service_id"],
                            date=e["date"])
    await cb.answer()
    await show_times(cb, state, shop_id, lang)


@router.callback_query(F.data.startswith("wl_del:"))
async def wl_del(cb: CallbackQuery, shop_id: int, lang: str):
    e = await db.get_waitlist(int(cb.data.split(":")[1]))
    if e and e["client_id"] == cb.from_user.id and e["shop_id"] == shop_id:
        await db.delete_waitlist(e["id"])
    await cb.answer()
    await send_or_edit(cb, tr(lang, "wl_removed"))


# ------------------------------------------------------------------ mening navbatlarim
@router.message(F.text.in_(variants("btn_my")))
async def my_bookings(message: Message, state: FSMContext, shop_id: int, lang: str):
    await state.clear()
    items = await services.client_future_bookings(shop_id, message.from_user.id)
    waits = await db.client_waitlist(shop_id, message.from_user.id, services.today_str())
    if not items and not waits:
        await message.answer(tr(lang, "my_none"))
        return
    for b in items:
        await message.answer(
            i18n.booking_card(b, lang) + f"\n{i18n.status_label(lang, b['status'])}",
            reply_markup=kb.ikb([[(tr(lang, "btn_cancel_booking"), f"my_cancel:{b['id']}")]]))
    for w in waits:
        await message.answer(
            tr(lang, "wl_item", staff=esc(w["staff_name"]), date=fmt_date(w["date"], lang),
               service=esc(w["service_name"])),
            reply_markup=kb.ikb([[(tr(lang, "btn_wl_remove"), f"wl_del:{w['id']}")]]))


@router.callback_query(F.data.startswith("my_cancel:"))
async def my_cancel(cb: CallbackQuery, shop_id: int, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if not b or b["client_id"] != cb.from_user.id or b["shop_id"] != shop_id or b["status"] not in db.ACTIVE:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    shop = await db.get_shop(shop_id)
    note = ""
    if b["deposit_status"] == "paid" and b["deposit_amount"] > 0:
        if services.hours_left(b) >= shop["free_cancel_hours"]:
            note = "\n\n" + tr(lang, "cancel_note_credit")
        else:
            note = "\n\n" + tr(lang, "cancel_note_lost", h=shop["free_cancel_hours"])
    await cb.answer()
    await send_or_edit(
        cb, i18n.booking_card(b, lang) + "\n\n" + tr(lang, "cancel_ask") + note,
        kb.ikb([[(tr(lang, "btn_yes_cancel"), f"my_cancel_yes:{b['id']}"), (tr(lang, "btn_no"), "my_cancel_no")]]))


@router.callback_query(F.data == "my_cancel_no")
async def my_cancel_no(cb: CallbackQuery, lang: str):
    await cb.answer()
    await send_or_edit(cb, tr(lang, "cancel_kept"))


@router.callback_query(F.data.startswith("my_cancel_yes:"))
async def my_cancel_yes(cb: CallbackQuery, shop_id: int, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if not b or b["client_id"] != cb.from_user.id or b["status"] not in db.ACTIVE:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    outcome = await services.cancel_booking(b, "client")
    await cb.answer()
    text = tr(lang, "cancelled_ok")
    if outcome == "credited":
        text += "\n" + tr(lang, "cancel_credited")
    elif outcome == "forfeited":
        text += "\n" + tr(lang, "cancel_forfeited")
    await send_or_edit(cb, text)
    await notify_staff(cb.bot, shop_id, b["staff_id"],
                       lambda lg: tr(lg, "staff_client_cancelled") + "\n\n" + i18n.admin_booking(
                           {**b, "status": "cancelled_by_client"}, lg))


# ------------------------------------------------------------------ eslatma va ko'chirish javoblari
@router.callback_query(F.data.startswith("rem_ok:"))
async def rem_ok(cb: CallbackQuery, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if b and b["client_id"] == cb.from_user.id and b["status"] == "confirmed":
        await db.update_booking(b["id"], client_confirmed=1)
    await cb.answer(tr(lang, "thanks_short"))
    await send_or_edit(cb, tr(lang, "come_confirmed"))


@router.callback_query(F.data.startswith("mv_ok:"))
async def mv_ok(cb: CallbackQuery, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if b and b["client_id"] == cb.from_user.id and b["status"] == "confirmed":
        await db.update_booking(b["id"], client_confirmed=1)
    await cb.answer(tr(lang, "thanks_short"))
    await send_or_edit(cb, tr(lang, "mv_confirmed"))


@router.callback_query(F.data.startswith("mv_cancel:"))
async def mv_cancel(cb: CallbackQuery, shop_id: int, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if not b or b["client_id"] != cb.from_user.id or b["status"] not in db.ACTIVE:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    await services.cancel_booking(b, "barber")  # usta sababli o'zgargan, depozit kreditga o'tadi
    await cb.answer()
    await send_or_edit(cb, tr(lang, "mv_cancelled"))
    await notify_staff(cb.bot, shop_id, b["staff_id"],
                       lambda lg: tr(lg, "staff_moved_cancelled") + "\n\n" + i18n.admin_booking(
                           {**b, "status": "cancelled_by_client"}, lg))


@router.callback_query(F.data.startswith("mv_other:"))
async def mv_other(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if not b or b["client_id"] != cb.from_user.id or b["status"] not in db.ACTIVE:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    await services.cancel_booking(b, "barber")  # depozit kreditga o'tadi va yangi navbatda ishlatiladi
    await cb.answer()
    await send_or_edit(cb, tr(lang, "mv_other_info"))
    await begin_booking(cb.message, state, shop_id, cb.from_user.id, lang)


# ------------------------------------------------------------------ baho va sharh
async def _notify_low_rating(bot, shop_id: int, booking_id: int) -> None:
    """Past baho (3 va undan past) bo'lsa, egaga darhol xabar."""
    b = await db.get_booking(booking_id)
    rv = await db.get_review(booking_id)
    if not b or not rv or rv["rating"] > 3:
        return
    comment = rv.get("comment") or ""
    await notify_staff(
        bot, shop_id, None,
        lambda lg: tr(lg, "staff_low_rating", stars="⭐" * rv["rating"], barber=esc(b["staff_name"]),
                      client=esc(b["client_name"] or "—"), phone=esc(b["client_phone"] or "—"),
                      date=fmt_date(b["date"], lg), comment=esc(comment) if comment else "—"))


@router.callback_query(F.data.startswith("rv:"))
async def rate(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    try:
        _, bid, rating = cb.data.split(":")
        bid, rating = int(bid), int(rating)
    except ValueError:
        await cb.answer()
        return
    b = await db.get_booking(bid)
    if not b or b["client_id"] != cb.from_user.id or b["shop_id"] != shop_id or not 1 <= rating <= 5:
        await cb.answer(tr(lang, "booking_gone"), show_alert=True)
        return
    if await db.get_review(bid):
        await cb.answer(tr(lang, "already_rated"), show_alert=True)
        return
    await db.add_review(bid, shop_id, b["staff_id"], b["client_id"], rating, services.now_str())
    await state.set_state(Review.comment)
    await state.update_data(review_booking=bid)
    await cb.answer()
    await send_or_edit(cb, tr(lang, "rate_comment_ask", stars="⭐" * rating),
                       kb.ikb([[(tr(lang, "btn_skip"), f"rv_skip:{bid}")]]))


@router.callback_query(F.data.startswith("rv_skip:"))
async def rate_skip(cb: CallbackQuery, state: FSMContext, shop_id: int, lang: str):
    await state.clear()
    await cb.answer()
    await send_or_edit(cb, tr(lang, "rate_thanks"))
    bid = int(cb.data.split(":")[1])
    b = await db.get_booking(bid)
    if b and b["client_id"] == cb.from_user.id:
        await _notify_low_rating(cb.bot, shop_id, bid)


@router.message(Review.comment, F.text)
async def rate_comment(message: Message, state: FSMContext, shop_id: int, lang: str):
    data = await state.get_data()
    bid = data.get("review_booking")
    await state.clear()
    if not bid:
        return
    await db.set_review_comment(bid, message.text.strip()[:500])
    await message.answer(tr(lang, "rate_thanks"))
    await _notify_low_rating(message.bot, shop_id, bid)
