"""Barcha o'zbekcha matnlar va formatlash funksiyalari."""
from __future__ import annotations

from datetime import datetime
from html import escape as esc

# ---- Tugma matnlari ----
BTN_BOOK = "📅 Yozilish"
BTN_MY = "📋 Yozilishlarim"
BTN_PRICES = "💈 Narxlar"
BTN_ADDRESS = "📍 Manzil"
BTN_ADMIN = "🛠 Admin panel"
BTN_TODAY = "📋 Bugun"
BTN_TOMORROW = "🗓 Ertaga"
BTN_BLOCK = "⏸ Vaqtni bloklash"
BTN_CLIENTS = "👥 Mijozlar"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_INVITE = "➕ Barber bog'lash"
BTN_MAIN = "⬅️ Asosiy menyu"
BTN_PHONE = "📱 Raqamni yuborish"

WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]

STATUS = {
    "pending_payment": "⏳ To'lov kutilmoqda",
    "confirmed": "✅ Tasdiqlangan",
    "completed": "✔️ Keldi",
    "no_show": "❌ Kelmadi",
    "cancelled_by_client": "🚫 Mijoz bekor qildi",
    "cancelled_by_barber": "🚫 Usta bekor qildi",
    "expired": "⌛ Muddati tugadi",
}


# ---- Formatlash ----
def money(n: int) -> str:
    return f"{int(n):,}".replace(",", " ") + " so'm"


def fmt_min(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def fmt_date(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{WEEKDAYS[d.weekday()]} {d:%d.%m}"


def booking_card(b: dict) -> str:
    return (
        f"💈 <b>{esc(b['service_name'])}</b>\n"
        f"👤 Usta: {esc(b['staff_name'])}\n"
        f"📅 {fmt_date(b['date'])} · {fmt_min(b['start_min'])}\n"
        f"💰 {money(b['price'])}"
    )


def admin_booking(b: dict) -> str:
    phone = esc(b.get("client_phone") or "—")
    name = esc(b.get("client_name") or "Mijoz")
    mark = " ✔️ keladi" if b.get("client_confirmed") else ""
    return (
        f"🕒 <b>{fmt_min(b['start_min'])}</b> · {esc(b['service_name'])}\n"
        f"👤 {name} · {phone}\n"
        f"✂️ Usta: {esc(b['staff_name'])}\n"
        f"{STATUS.get(b['status'], b['status'])}{mark}"
    )


# ---- Mijoz matnlari ----
def welcome(shop: dict) -> str:
    return (
        f"Assalomu alaykum! 👋\n<b>{esc(shop['name'])}</b> navbat botiga xush kelibsiz.\n\n"
        f"Pastdagi tugmalar orqali navbat oling."
    )


def rules(shop: dict) -> str:
    return (
        f"ℹ️ <b>Shartlar</b>\n"
        f"• Navbat uchun depozit: <b>{money(shop['deposit_amount'])}</b>. U xizmat narxidan ayriladi.\n"
        f"• Kelmasangiz yoki {shop['free_cancel_hours']} soatdan kam qolganda bekor qilsangiz, depozit qaytarilmaydi.\n"
        f"• {shop['free_cancel_hours']} soatdan oldin bekor qilsangiz yoki usta sababli vaqt o'zgarsa, "
        f"depozit keyingi navbatingizga hisobga o'tadi."
    )


def summary(b_data: dict, shop: dict, credit: int) -> str:
    lines = [
        "📝 <b>Navbat ma'lumotlari</b>",
        f"👤 Usta: {esc(b_data['staff_name'])}",
        f"💈 Xizmat: {esc(b_data['service_name'])}",
        f"📅 {fmt_date(b_data['date'])} · {fmt_min(b_data['start_min'])}",
        f"💰 Narx: {money(b_data['price'])}",
        "",
        rules(shop),
    ]
    if shop["deposit_amount"] > 0 and credit >= shop["deposit_amount"]:
        lines.append(f"\n🎁 Sizda {money(credit)} depozit krediti bor, u avtomatik ishlatiladi.")
    return "\n".join(lines)


def pay_instruction(shop: dict, minutes: int) -> str:
    return (
        f"💳 Depozitni shu kartaga o'tkazing:\n<code>{esc(shop['card_number'])}</code>\n"
        f"Summa: <b>{money(shop['deposit_amount'])}</b>\n\n"
        f"To'lov chekining <b>rasmini shu yerga yuboring</b>. Muddat: {minutes} daqiqa, "
        f"aks holda navbat bekor bo'ladi."
    )


def booking_confirmed(b: dict) -> str:
    return "✅ <b>Navbatingiz tasdiqlandi!</b>\n\n" + booking_card(b) + "\n\nKutib qolamiz! 💈"
