from __future__ import annotations

from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                           ReplyKeyboardMarkup)

from i18n import tr


def ikb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    """rows = [[(matn, callback_data), ...], ...]"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=a, callback_data=b) for a, b in row] for row in rows]
    )


def grid(items: list[tuple[str, str]], per_row: int) -> list[list[tuple[str, str]]]:
    return [items[i:i + per_row] for i in range(0, len(items), per_row)]


def _reply(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x) for x in row] for row in rows], resize_keyboard=True
    )


def main_menu(lang: str, is_staff: bool) -> ReplyKeyboardMarkup:
    rows = [[tr(lang, "btn_book"), tr(lang, "btn_my")],
            [tr(lang, "btn_prices"), tr(lang, "btn_address")],
            [tr(lang, "btn_loyalty"), tr(lang, "btn_lang")]]
    if is_staff:
        rows.append([tr(lang, "btn_admin")])
    return _reply(rows)


def admin_menu(lang: str, is_owner: bool) -> ReplyKeyboardMarkup:
    if is_owner:
        rows = [[tr(lang, "btn_today"), tr(lang, "btn_tomorrow")],
                [tr(lang, "btn_manual"), tr(lang, "btn_block")],
                [tr(lang, "btn_report"), tr(lang, "btn_clients")],
                [tr(lang, "btn_services"), tr(lang, "btn_hours")],
                [tr(lang, "btn_staff"), tr(lang, "btn_broadcast")],
                [tr(lang, "btn_settings")]]
    else:
        rows = [[tr(lang, "btn_today"), tr(lang, "btn_tomorrow")],
                [tr(lang, "btn_manual"), tr(lang, "btn_block")],
                [tr(lang, "btn_report")]]
    rows.append([tr(lang, "btn_main")])
    return _reply(rows)


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=tr(lang, "btn_phone"), request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def location_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=tr(lang, "btn_my_location"), request_location=True)],
                  [KeyboardButton(text=tr(lang, "btn_main"))]],
        resize_keyboard=True,
    )


def lang_kb() -> InlineKeyboardMarkup:
    return ikb([[("🇺🇿 O'zbekcha", "lang:uz"), ("🇷🇺 Русский", "lang:ru")]])


def maps_kb(lang: str, lat: float, lon: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗺 Google Maps", url=f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"),
        InlineKeyboardButton(text="🗺 Yandex", url=f"https://yandex.com/maps/?pt={lon},{lat}&z=17&l=map"),
    ]])


def confirm_booking_kb(lang: str) -> InlineKeyboardMarkup:
    return ikb([[(tr(lang, "btn_agree"), "bk_confirm")], [(tr(lang, "btn_cancel"), "bk_cancel")]])


def pay_confirm_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    return ikb([[(tr(lang, "btn_pay_ok"), f"pay_ok:{booking_id}"), (tr(lang, "btn_pay_no"), f"pay_no:{booking_id}")]])


def pay_revoke_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    return ikb([[(tr(lang, "btn_revoke"), f"pay_revoke:{booking_id}")]])


def attendance_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    return ikb([[(tr(lang, "btn_arrived"), f"arr:{booking_id}"), (tr(lang, "btn_noshow"), f"noshow:{booking_id}")]])


def reminder_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    return ikb([[(tr(lang, "btn_will_come"), f"rem_ok:{booking_id}"), (tr(lang, "btn_will_cancel"), f"my_cancel:{booking_id}")]])


def moved_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    return ikb([
        [(tr(lang, "btn_mv_ok"), f"mv_ok:{booking_id}")],
        [(tr(lang, "btn_mv_other"), f"mv_other:{booking_id}")],
        [(tr(lang, "btn_cancel_booking"), f"mv_cancel:{booking_id}")],
    ])


def rating_kb(booking_id: int) -> InlineKeyboardMarkup:
    return ikb([[(f"{'⭐' * n}", f"rv:{booking_id}:{n}") for n in (1, 2, 3)],
                [(f"{'⭐' * n}", f"rv:{booking_id}:{n}") for n in (4, 5)]])


def winback_kb(lang: str) -> InlineKeyboardMarkup:
    return ikb([[(tr(lang, "btn_book"), "wb_book")]])
