from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

import db

log = logging.getLogger(__name__)


class StaffFilter(BaseFilter):
    """Faqat shu shopning ega/ustalariga ruxsat beradi; `staff_rows` ni handlerga uzatadi."""

    async def __call__(self, event: TelegramObject, shop_id: int):
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        rows = await db.staff_by_tg(shop_id, user.id)
        return {"staff_rows": rows} if rows else False


def is_owner(rows: list[dict]) -> bool:
    return any(r["role"] == "owner" for r in rows)


def my_barber_ids(rows: list[dict]) -> list[int]:
    return [r["id"] for r in rows if r["role"] == "barber"]


def can_manage(rows: list[dict], booking: dict) -> bool:
    return is_owner(rows) or booking["staff_id"] in my_barber_ids(rows)


async def lang_of(shop_id: int, tg_id: int) -> str:
    return (await db.get_lang(shop_id, tg_id)) or "uz"


async def send_or_edit(event, text: str, markup=None) -> None:
    """Callback bo'lsa xabarni tahrirlaydi, aks holda yangi xabar yuboradi."""
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=markup)
            return
        except TelegramBadRequest as e:
            if "not modified" in str(e):
                return
        except Exception:  # noqa: BLE001
            pass
        await event.bot.send_message(event.from_user.id, text, reply_markup=markup)
    else:
        await event.answer(text, reply_markup=markup)


async def safe_send(bot: Bot, chat_id: int, text: str, **kw) -> Message | None:
    if chat_id <= 0:  # qo'lda qo'shilgan (virtual) mijozga yuborib bo'lmaydi
        return None
    try:
        return await bot.send_message(chat_id, text, **kw)
    except Exception as e:  # noqa: BLE001
        log.warning("Xabar yuborilmadi (%s): %s", chat_id, e)
        return None


async def notify_staff(bot: Bot, shop_id: int, staff_id: int | None, text_fn, markup_fn=None,
                       exclude: int | None = None) -> None:
    """Ega(lar) va (berilgan) ustaga, har biriga o'z tilida xabar yuboradi.

    text_fn(lang) -> matn, markup_fn(lang) -> tugmalar (ixtiyoriy)."""
    for tg_id in await db.notify_ids(shop_id, staff_id):
        if tg_id == exclude:
            continue
        lang = await lang_of(shop_id, tg_id)
        await safe_send(bot, tg_id, text_fn(lang), reply_markup=markup_fn(lang) if markup_fn else None)
