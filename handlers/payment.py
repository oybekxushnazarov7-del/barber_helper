from __future__ import annotations

import json
import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

import config
import db
import i18n
import keyboards as kb
import receipt_ai
import services
from handlers.common import StaffFilter, can_manage, lang_of, safe_send
from i18n import esc, money, tr

router = Router()
log = logging.getLogger(__name__)


def _info_lines(info: dict | None, lang: str) -> str:
    if not info:
        return ""
    parts = []
    if info.get("amount") is not None:
        parts.append(tr(lang, "rc_amount", v=money(info["amount"], lang)))
    if info.get("datetime"):
        parts.append(tr(lang, "rc_time", v=esc(str(info["datetime"]))))
    if info.get("recipient_last4"):
        parts.append(tr(lang, "rc_card", v=esc(info["recipient_last4"])))
    if info.get("transaction_id"):
        parts.append(tr(lang, "rc_tx", v=esc(info["transaction_id"])))
    return "\n".join(parts)


async def _copy_to_staff(message: Message, b: dict, caption_fn, markup_fn) -> int:
    """Chek xabarini ega va ustaga (har biriga o'z tilida sarlavha bilan) nusxalaydi."""
    sent = 0
    for tg_id in await db.notify_ids(b["shop_id"], b["staff_id"]):
        lang = await lang_of(b["shop_id"], tg_id)
        try:
            await message.bot.copy_message(tg_id, message.chat.id, message.message_id,
                                           caption=caption_fn(lang), reply_markup=markup_fn(lang))
            sent += 1
        except Exception as e:  # noqa: BLE001
            log.warning("Chek nusxasi yuborilmadi (%s): %s", tg_id, e)
    return sent


async def _mark_used(b: dict) -> None:
    if b.get("receipt_uid"):
        await db.mark_receipt_used(f"uid:{b['receipt_uid']}", b["id"])
    try:
        info = json.loads(b["receipt_info"]) if b.get("receipt_info") else None
    except ValueError:
        info = None
    if info and info.get("transaction_id"):
        await db.mark_receipt_used(f"tx:{b['shop_id']}:{info['transaction_id']}", b["id"])


async def _to_manual(message: Message, b: dict, info: dict | None, note_key: str | None, lang: str) -> None:
    await db.update_booking(b["id"], deposit_status="receipt_sent")
    b = await db.get_booking(b["id"])

    def caption(lg: str) -> str:
        text = tr(lg, "rc_caption_title") + "\n\n" + i18n.admin_booking(b, lg) + \
            "\n" + tr(lg, "rc_deposit", v=money(b["deposit_amount"], lg))
        extra = _info_lines(info, lg)
        if extra:
            text += "\n\n" + tr(lg, "rc_ai_read") + "\n" + extra
        if note_key:
            text += "\n⚠️ " + tr(lg, note_key)
        return text + "\n\n" + tr(lg, "rc_check_prompt")

    sent = await _copy_to_staff(message, b, caption, lambda lg: kb.pay_confirm_kb(lg, b["id"]))
    await message.answer(tr(lang, "rc_received" if sent else "rc_not_delivered"))


async def _auto_accept(message: Message, b: dict, info: dict, lang: str) -> None:
    await db.update_booking(b["id"], status="confirmed", deposit_status="paid", pay_deadline=None)
    b = await db.get_booking(b["id"])
    await _mark_used(b)
    await message.answer(tr(lang, "booking_confirmed", card=i18n.booking_card(b, lang)))

    def caption(lg: str) -> str:
        return (tr(lg, "rc_auto_title") + "\n\n" + i18n.admin_booking(b, lg) + "\n\n" +
                _info_lines(info, lg) + "\n\n" + tr(lg, "rc_auto_hint"))

    await _copy_to_staff(message, b, caption, lambda lg: kb.pay_revoke_kb(lg, b["id"]))


# ---------------------------------------------------------------- mijoz chek yuboradi
@router.message(F.photo | F.document)
async def got_receipt(message: Message, shop_id: int, lang: str):
    b = await db.pending_receipt_booking(shop_id, message.from_user.id)
    if not b:
        waiting = await db.receipt_sent_booking(shop_id, message.from_user.id)
        await message.answer(tr(lang, "rc_under_review" if waiting else "rc_none_pending"))
        return
    if message.photo:
        file_id, uid, mime = message.photo[-1].file_id, message.photo[-1].file_unique_id, "image/jpeg"
    else:
        doc = message.document
        file_id, uid, mime = doc.file_id, doc.file_unique_id, (doc.mime_type or "")
    is_image = mime.startswith("image/")

    if await db.receipt_key_used(f"uid:{uid}"):
        await message.answer(tr(lang, "rc_duplicate"))
        return
    await db.update_booking(b["id"], receipt_file_id=file_id, receipt_uid=uid)
    b = await db.get_booking(b["id"])
    shop = await db.get_shop(shop_id)

    if not (receipt_ai.enabled() and is_image and b["receipt_attempts"] < config.AI_MAX_ATTEMPTS):
        await _to_manual(message, b, None, None, lang)
        return

    await message.answer(tr(lang, "rc_checking"))
    info = None
    try:
        buf = await message.bot.download(file_id)
        info = await receipt_ai.analyze(buf.getvalue(), mime)
    except Exception as e:  # noqa: BLE001
        log.warning("Chekni yuklab/tahlil qilib bo'lmadi: %s", e)
    created = datetime.strptime(b["created_at"], services.FMT).replace(tzinfo=config.TZ)
    verdict, reason = receipt_ai.decide(info, expected=b["deposit_amount"], shop_card=shop["card_number"],
                                        created_at=created, now=services.now_local())
    if info and info.get("transaction_id") and await db.receipt_key_used(f"tx:{shop_id}:{info['transaction_id']}"):
        verdict, reason = "reject", "ai_duplicate"
    await db.update_booking(b["id"], receipt_info=json.dumps(info) if info else None)
    b = await db.get_booking(b["id"])

    if verdict == "accept":
        await _auto_accept(message, b, info, lang)
    elif verdict == "reject":
        attempts = b["receipt_attempts"] + 1
        await db.update_booking(b["id"], receipt_attempts=attempts)
        if attempts >= config.AI_MAX_ATTEMPTS:
            await message.answer(tr(lang, "rc_rejected_final", reason=tr(lang, reason)))
            await _to_manual(message, await db.get_booking(b["id"]), info, reason, lang)
        else:
            await message.answer(tr(lang, "rc_rejected", reason=tr(lang, reason),
                                    left=config.AI_MAX_ATTEMPTS - attempts))
    else:
        await _to_manual(message, b, info, reason, lang)


async def _edit_staff_message(cb: CallbackQuery, text: str) -> None:
    try:
        if cb.message.caption is not None or cb.message.photo or cb.message.document:
            await cb.message.edit_caption(caption=text, reply_markup=None)
        else:
            await cb.message.edit_text(text, reply_markup=None)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- usta/ega tasdiqlaydi
@router.callback_query(F.data.startswith("pay_ok:"), StaffFilter())
async def pay_ok(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if not b or b["shop_id"] != shop_id or not can_manage(staff_rows, b):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    if b["status"] != "pending_payment" or b["deposit_status"] != "receipt_sent":
        await cb.answer(tr(lang, "already_handled"), show_alert=True)
        await _edit_staff_message(cb, tr(lang, "already_handled"))
        return
    await db.update_booking(b["id"], status="confirmed", deposit_status="paid", pay_deadline=None)
    b = await db.get_booking(b["id"])
    await _mark_used(b)
    await cb.answer(tr(lang, "confirmed_toast"))
    await _edit_staff_message(cb, tr(lang, "rc_confirmed_title") + "\n\n" + i18n.admin_booking(b, lang))
    clang = await lang_of(shop_id, b["client_id"])
    await safe_send(cb.bot, b["client_id"], tr(clang, "booking_confirmed", card=i18n.booking_card(b, clang)))


@router.callback_query(F.data.startswith("pay_no:"), StaffFilter())
async def pay_no(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if not b or b["shop_id"] != shop_id or not can_manage(staff_rows, b):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    if b["status"] != "pending_payment" or b["deposit_status"] != "receipt_sent":
        await cb.answer(tr(lang, "already_handled"), show_alert=True)
        await _edit_staff_message(cb, tr(lang, "already_handled"))
        return
    await db.update_booking(b["id"], status="cancelled_by_barber", deposit_status="rejected")
    await services.release_slot(b)
    await cb.answer(tr(lang, "rejected_toast"))
    await _edit_staff_message(cb, tr(lang, "rc_rejected_title") + "\n\n" +
                              i18n.admin_booking({**b, "status": "cancelled_by_barber"}, lang))
    clang = await lang_of(shop_id, b["client_id"])
    await safe_send(cb.bot, b["client_id"], tr(clang, "rc_staff_rejected"))


@router.callback_query(F.data.startswith("pay_revoke:"), StaffFilter())
async def pay_revoke(cb: CallbackQuery, shop_id: int, staff_rows: list, lang: str):
    """Avtomatik tasdiqlangan chekni 'noto'g'ri' deb bekor qilish."""
    b = await db.get_booking(int(cb.data.split(":")[1]))
    if not b or b["shop_id"] != shop_id or not can_manage(staff_rows, b):
        await cb.answer(tr(lang, "no_access"), show_alert=True)
        return
    if b["status"] != "confirmed" or b["deposit_status"] != "paid":
        await cb.answer(tr(lang, "already_handled"), show_alert=True)
        await _edit_staff_message(cb, tr(lang, "already_handled"))
        return
    await db.update_booking(b["id"], status="cancelled_by_barber", deposit_status="rejected")
    await services.release_slot(b)
    await cb.answer(tr(lang, "rejected_toast"))
    await _edit_staff_message(cb, tr(lang, "rc_revoked_title") + "\n\n" +
                              i18n.admin_booking({**b, "status": "cancelled_by_barber"}, lang))
    clang = await lang_of(shop_id, b["client_id"])
    await safe_send(cb.bot, b["client_id"], tr(clang, "rc_staff_rejected"))
