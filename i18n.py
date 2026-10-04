"""Ikki tilli matnlar (O'zbekcha / Русский) va formatlash yordamchilari."""
from __future__ import annotations

from datetime import datetime
from html import escape as _escape


def esc(value) -> str:
    """Telegram HTML uchun faqat < > & ni almashtiradi."""
    return _escape(str(value), quote=False)

WEEKDAYS = {
    "uz": ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"],
    "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
}
WEEKDAYS_FULL = {
    "uz": ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"],
    "ru": ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
}

STATUS = {
    "uz": {
        "pending_payment": "⏳ To'lov kutilmoqda", "confirmed": "✅ Tasdiqlangan", "completed": "✔️ Keldi",
        "no_show": "❌ Kelmadi", "cancelled_by_client": "🚫 Mijoz bekor qildi",
        "cancelled_by_barber": "🚫 Usta bekor qildi", "expired": "⌛ Muddati tugadi",
    },
    "ru": {
        "pending_payment": "⏳ Ожидает оплаты", "confirmed": "✅ Подтверждено", "completed": "✔️ Пришёл",
        "no_show": "❌ Не пришёл", "cancelled_by_client": "🚫 Клиент отменил",
        "cancelled_by_barber": "🚫 Мастер отменил", "expired": "⌛ Время истекло",
    },
}

S: dict[str, dict[str, str]] = {"uz": {}, "ru": {}}


def _add(key: str, uz: str, ru: str) -> None:
    S["uz"][key] = uz
    S["ru"][key] = ru


# ============================== TUGMALAR ==============================
_add("btn_book", "📅 Yozilish", "📅 Записаться")
_add("btn_my", "📋 Yozilishlarim", "📋 Мои записи")
_add("btn_prices", "💈 Narxlar", "💈 Цены")
_add("btn_address", "📍 Manzil", "📍 Адрес")
_add("btn_loyalty", "🎁 Sodiqlik", "🎁 Бонусы")
_add("btn_lang", "🌐 Til / Язык", "🌐 Til / Язык")
_add("btn_admin", "🛠 Admin panel", "🛠 Админ-панель")
_add("btn_today", "📋 Bugun", "📋 Сегодня")
_add("btn_tomorrow", "🗓 Ertaga", "🗓 Завтра")
_add("btn_manual", "➕ Mijoz qo'shish", "➕ Добавить клиента")
_add("btn_block", "⏸ Vaqtni bloklash", "⏸ Заблокировать время")
_add("btn_report", "📊 Hisobot", "📊 Отчёт")
_add("btn_clients", "👥 Mijozlar", "👥 Клиенты")
_add("btn_staff", "✂️ Ustalar", "✂️ Мастера")
_add("btn_broadcast", "📢 Ommaviy xabar", "📢 Рассылка")
_add("btn_settings", "⚙️ Sozlamalar", "⚙️ Настройки")
_add("btn_main", "⬅️ Asosiy menyu", "⬅️ Главное меню")
_add("btn_phone", "📱 Raqamni yuborish", "📱 Отправить номер")
_add("btn_my_location", "📍 Hozirgi joylashuvim", "📍 Моё текущее местоположение")
_add("btn_agree", "✅ Roziman, davom etish", "✅ Согласен, продолжить")
_add("btn_cancel", "❌ Bekor qilish", "❌ Отмена")
_add("btn_back", "⬅️ Orqaga", "⬅️ Назад")
_add("btn_confirm", "✅ Tasdiqlash", "✅ Подтвердить")
_add("btn_pay_ok", "✅ Tasdiqlash", "✅ Подтвердить")
_add("btn_pay_no", "❌ Rad etish", "❌ Отклонить")
_add("btn_revoke", "↩️ Noto'g'ri, bekor qilish", "↩️ Неверно, отменить")
_add("btn_arrived", "✅ Keldi", "✅ Пришёл")
_add("btn_noshow", "❌ Kelmadi", "❌ Не пришёл")
_add("btn_will_come", "✅ Kelaman", "✅ Приду")
_add("btn_will_cancel", "🚫 Bekor qilaman", "🚫 Отменяю")
_add("btn_mv_ok", "✅ Mos keladi", "✅ Подходит")
_add("btn_mv_other", "🔄 Boshqa vaqt tanlash", "🔄 Выбрать другое время")
_add("btn_cancel_booking", "🚫 Navbatni bekor qilish", "🚫 Отменить запись")
_add("btn_yes_cancel", "✅ Ha, bekor qilish", "✅ Да, отменить")
_add("btn_no", "⬅️ Yo'q", "⬅️ Нет")
_add("btn_yes_delete", "✅ Ha, o'chirish", "✅ Да, удалить")
_add("btn_send", "📤 Yuborish", "📤 Отправить")
_add("btn_skip", "⏭ O'tkazib yuborish", "⏭ Пропустить")
_add("btn_staff_add", "➕ Usta qo'shish", "➕ Добавить мастера")
_add("btn_unblock", "🔓 Ochish", "🔓 Разблокировать")
_add("btn_block_client", "🚫 Yopish", "🚫 Заблокировать")
_add("btn_waitlist", "🔔 Bo'shasa xabar bering", "🔔 Сообщить, если освободится")
_add("btn_wl_remove", "❌ Ro'yxatdan olib tashlash", "❌ Убрать из списка")

# ============================== MIJOZ ==============================
_add("choose_lang", "🌐 Tilni tanlang:", "🌐 Выберите язык:")
_add("lang_saved", "✅ Til saqlandi: O'zbekcha", "✅ Язык сохранён: Русский")
_add("welcome",
     "Assalomu alaykum! 👋\n<b>{shop}</b> navbat botiga xush kelibsiz.\n\nPastdagi tugmalar orqali navbat oling.",
     "Здравствуйте! 👋\nДобро пожаловать в бот записи <b>{shop}</b>.\n\nЗаписывайтесь с помощью кнопок ниже.")
_add("menu_hint", "Asosiy menyu 👇", "Главное меню 👇")
_add("your_id", "Sizning Telegram ID: <code>{id}</code>", "Ваш Telegram ID: <code>{id}</code>")
_add("joined",
     "✅ Siz <b>{name}</b> ustasi sifatida bog'landingiz.\nEndi yangi navbatlar haqida shu yerga xabar keladi. "
     "Admin panel: pastdagi 🛠 tugma.",
     "✅ Вы подключены как мастер <b>{name}</b>.\nТеперь сюда будут приходить уведомления о новых записях. "
     "Админ-панель — кнопка 🛠 внизу.")
_add("join_bad", "Bu havola eskirgan yoki allaqachon ishlatilgan.",
     "Эта ссылка устарела или уже использована.")
_add("min", "daq.", "мин.")
_add("prices_title", "💈 <b>Narxlar</b>", "💈 <b>Цены</b>")
_add("prices_barbers", "✂️ <b>Ustalar:</b> {names}", "✂️ <b>Мастера:</b> {names}")
_add("prices_loyalty", "🎁 Har {n} ta tashrifdan keyingi navbat <b>{pct}% arzon</b>!",
     "🎁 После каждых {n} визитов следующая запись <b>со скидкой {pct}%</b>!")
_add("address_card", "📍 <b>{name}</b>\n{address}\n📞 {phone}", "📍 <b>{name}</b>\n{address}\n📞 {phone}")
_add("loy_progress",
     "🎁 <b>Sodiqlik dasturi</b>\n\n{dots}\nTashriflar: <b>{visits}</b>\nYana <b>{left}</b> ta tashrifdan keyin "
     "keyingi navbatingiz <b>{pct}% arzon</b> bo'ladi.",
     "🎁 <b>Программа лояльности</b>\n\n{dots}\nВизитов: <b>{visits}</b>\nЕщё <b>{left}</b> визит(а) — и следующая "
     "запись будет <b>со скидкой {pct}%</b>.")
_add("loy_ready",
     "🎁 <b>Sodiqlik dasturi</b>\n\n{dots}\nTashriflar: <b>{visits}</b>\n🎉 Keyingi navbatingiz <b>{pct}% chegirma</b> "
     "bilan! Navbat olganda avtomatik qo'llanadi.",
     "🎁 <b>Программа лояльности</b>\n\n{dots}\nВизитов: <b>{visits}</b>\n🎉 Ваша следующая запись — "
     "<b>со скидкой {pct}%</b>! Применится автоматически при записи.")
_add("blocked_msg", "Kechirasiz, onlayn yozilish siz uchun yopilgan. Iltimos, usta bilan telefon orqali bog'laning.",
     "К сожалению, онлайн-запись для вас закрыта. Пожалуйста, свяжитесь с мастером по телефону.")
_add("too_many",
     "Sizda allaqachon {n} ta faol navbat bor. Yangisini olish uchun avval birini bekor qiling (📋 Yozilishlarim).",
     "У вас уже {n} активных записи. Чтобы записаться снова, сначала отмените одну (📋 Мои записи).")
_add("no_barbers", "Hozircha ustalar mavjud emas.", "Пока нет доступных мастеров.")
_add("pick_barber", "✂️ Ustani tanlang:", "✂️ Выберите мастера:")
_add("pick_service", "💈 Xizmatni tanlang:", "💈 Выберите услугу:")
_add("no_dates", "😔 Yaqin kunlarda ish kunlari yo'q. Keyinroq urinib ko'ring.",
     "😔 В ближайшие дни нет рабочих дней. Попробуйте позже.")
_add("pick_date", "📅 Kunni tanlang (🔴 — bo'sh vaqt yo'q):", "📅 Выберите день (🔴 — нет свободного времени):")
_add("date_full",
     "🔴 {date} kuni bo'sh vaqt qolmagan.\n\nXohlasangiz, kutish ro'yxatiga yoziling: vaqt bo'shasa, sizga birinchi bo'lib xabar beramiz.",
     "🔴 На {date} свободного времени нет.\n\nМожно встать в список ожидания: если время освободится, мы сообщим вам первым.")
_add("pick_time", "🕒 {date} uchun vaqtni tanlang:", "🕒 Выберите время на {date}:")
_add("slot_taken", "Bu vaqt band bo'ldi, boshqasini tanlang", "Это время уже занято, выберите другое")
_add("slot_taken_full", "😔 Kechirasiz, bu vaqt hozirgina band bo'ldi. Boshqa vaqtni tanlang.",
     "😔 К сожалению, это время только что заняли. Выберите другое.")
_add("session_lost", "Sessiya tugagan. Iltimos, 📅 Yozilish tugmasini qaytadan bosing.",
     "Сессия истекла. Пожалуйста, нажмите 📅 Записаться заново.")
_add("barber_not_found", "Usta topilmadi", "Мастер не найден")
_add("ask_phone", "📱 Bog'lanish uchun telefon raqamingizni yuboring (pastdagi tugmani bosing):",
     "📱 Отправьте свой номер телефона для связи (нажмите кнопку ниже):")
_add("phone_wrong", "Iltimos, faqat o'zingizning raqamingizni yuboring (tugma orqali).",
     "Пожалуйста, отправьте только свой номер (через кнопку).")
_add("phone_ok", "✅ Raqam qabul qilindi.", "✅ Номер принят.")
_add("phone_other", "Iltimos, pastdagi «📱 Raqamni yuborish» tugmasini bosing.",
     "Пожалуйста, нажмите кнопку «📱 Отправить номер» внизу.")
_add("summary_title", "📝 <b>Navbat ma'lumotlari</b>", "📝 <b>Данные записи</b>")
_add("line_barber", "👤 Usta: {v}", "👤 Мастер: {v}")
_add("line_service", "💈 Xizmat: {v}", "💈 Услуга: {v}")
_add("line_price", "💰 Narx: {v}", "💰 Цена: {v}")
_add("line_price_disc", "💰 Narx: <s>{old}</s> → <b>{new}</b> (🎁 sodiqlik −{pct}%)",
     "💰 Цена: <s>{old}</s> → <b>{new}</b> (🎁 лояльность −{pct}%)")
_add("rules",
     "ℹ️ <b>Shartlar</b>\n• Navbat uchun depozit: <b>{dep}</b>. U xizmat narxidan ayriladi.\n"
     "• Kelmasangiz yoki {h} soatdan kam qolganda bekor qilsangiz, depozit qaytarilmaydi.\n"
     "• {h} soatdan oldin bekor qilsangiz yoki usta sababli vaqt o'zgarsa, depozit keyingi navbatingizga hisobga o'tadi.",
     "ℹ️ <b>Условия</b>\n• Депозит за запись: <b>{dep}</b>. Он засчитывается в стоимость услуги.\n"
     "• Если не придёте или отмените менее чем за {h} ч, депозит не возвращается.\n"
     "• Если отмените раньше чем за {h} ч или время изменит мастер, депозит перейдёт на вашу следующую запись.")
_add("credit_note", "🎁 Sizda {v} depozit krediti bor, u avtomatik ishlatiladi.",
     "🎁 У вас есть депозитный кредит {v}, он применится автоматически.")
_add("book_cancelled", "Bekor qilindi. Yangi navbat uchun 📅 Yozilish tugmasini bosing.",
     "Отменено. Для новой записи нажмите 📅 Записаться.")
_add("pay_instruction",
     "💳 Depozitni shu kartaga o'tkazing:\n<code>{card}</code>\nSumma: <b>{sum}</b>\n\n"
     "To'lov chekining <b>rasmini (skrinshotini) shu yerga yuboring</b>. Muddat: {m} daqiqa, aks holda navbat bekor bo'ladi.",
     "💳 Переведите депозит на карту:\n<code>{card}</code>\nСумма: <b>{sum}</b>\n\n"
     "<b>Отправьте сюда фото (скриншот) чека</b>. Срок: {m} мин, иначе запись будет отменена.")
_add("pay_auto", "🤖 Chek avtomatik tekshiriladi, odatda bir necha soniya ichida.",
     "🤖 Чек проверяется автоматически, обычно за несколько секунд.")
_add("booking_confirmed", "✅ <b>Navbatingiz tasdiqlandi!</b>\n\n{card}\n\nKutib qolamiz! 💈",
     "✅ <b>Ваша запись подтверждена!</b>\n\n{card}\n\nЖдём вас! 💈")
_add("staff_new_booking_credit", "🆕 <b>Yangi navbat</b> (depozit kredit hisobidan)",
     "🆕 <b>Новая запись</b> (депозит из кредита)")

# kutish ro'yxati
_add("wl_added", "🔔 Kutish ro'yxatiga yozildingiz: {staff}, {date}.\nVaqt bo'shasa, birinchilardan bo'lib xabar beramiz.",
     "🔔 Вы в списке ожидания: {staff}, {date}.\nЕсли время освободится, мы сообщим одним из первых.")
_add("wl_free", "🔔 <b>{staff}</b> ustada <b>{date}</b> kuni bo'sh vaqt paydo bo'ldi ({service})! Tez yoziling:",
     "🔔 У мастера <b>{staff}</b> на <b>{date}</b> освободилось время ({service})! Записывайтесь скорее:")
_add("wl_pick_time", "📅 Vaqtni tanlash", "📅 Выбрать время")
_add("wl_gone", "Bu so'rov topilmadi yoki eskirgan.", "Этот запрос не найден или устарел.")
_add("wl_removed", "Kutish ro'yxatidan olib tashlandi.", "Удалено из списка ожидания.")
_add("wl_item", "🔔 <b>Kutish ro'yxati</b>\n✂️ {staff}\n📅 {date}\n💈 {service}",
     "🔔 <b>Список ожидания</b>\n✂️ {staff}\n📅 {date}\n💈 {service}")

# mening navbatlarim va bekor qilish
_add("my_none", "Sizda faol navbat yo'q. 📅 Yozilish tugmasi orqali yangi navbat oling.",
     "У вас нет активных записей. Нажмите 📅 Записаться, чтобы создать новую.")
_add("booking_gone", "Bu navbat topilmadi yoki allaqachon bekor qilingan", "Эта запись не найдена или уже отменена")
_add("cancel_note_credit", "Depozitingiz keyingi navbatingizga hisobga o'tadi.",
     "Депозит перейдёт на вашу следующую запись.")
_add("cancel_note_lost", "⚠️ {h} soatdan kam qolgan, depozit qaytarilmaydi.",
     "⚠️ Осталось менее {h} ч, депозит не возвращается.")
_add("cancel_ask", "Navbatni bekor qilasizmi?", "Отменить запись?")
_add("cancel_kept", "Navbat saqlab qolindi ✅", "Запись сохранена ✅")
_add("cancelled_ok", "🚫 Navbat bekor qilindi.", "🚫 Запись отменена.")
_add("cancel_credited", "Depozitingiz keyingi navbatingizga hisobga o'tadi.", "Депозит перейдёт на вашу следующую запись.")
_add("cancel_forfeited", "Depozit qaytarilmaydi.", "Депозит не возвращается.")
_add("staff_client_cancelled", "🚫 <b>Mijoz navbatni bekor qildi</b>", "🚫 <b>Клиент отменил запись</b>")
_add("thanks_short", "Rahmat, kutamiz! 💈", "Спасибо, ждём! 💈")
_add("come_confirmed", "✅ Kelishingiz tasdiqlandi. Kutib qolamiz!", "✅ Ваш визит подтверждён. Ждём вас!")
_add("mv_confirmed", "✅ Yangi vaqt tasdiqlandi. Kutib qolamiz!", "✅ Новое время подтверждено. Ждём вас!")
_add("mv_cancelled", "🚫 Navbat bekor qilindi. Depozitingiz keyingi navbatingizga hisobga o'tadi.",
     "🚫 Запись отменена. Депозит перейдёт на вашу следующую запись.")
_add("staff_moved_cancelled", "🚫 <b>Mijoz ko'chirilgan navbatni bekor qildi</b>",
     "🚫 <b>Клиент отменил перенесённую запись</b>")
_add("mv_other_info", "🔄 Eski navbat bekor qilindi, depozitingiz saqlanadi. Yangi vaqtni tanlang 👇",
     "🔄 Старая запись отменена, ваш депозит сохранён. Выберите новое время 👇")

# baho
_add("rate_ask", "⭐ <b>{barber}</b> ustaga ({service}) xizmat uchun baho bering:",
     "⭐ Оцените работу мастера <b>{barber}</b> ({service}):")
_add("rate_comment_ask", "{stars} Rahmat! Izoh qoldirmoqchimisiz? Yozib yuboring yoki o'tkazib yuboring.",
     "{stars} Спасибо! Хотите оставить отзыв? Напишите или пропустите.")
_add("rate_thanks", "🙏 Fikringiz uchun rahmat!", "🙏 Спасибо за ваш отзыв!")
_add("already_rated", "Siz bu navbatni allaqachon baholagansiz", "Вы уже оценили эту запись")
_add("staff_low_rating",
     "⚠️ <b>Past baho</b> {stars}\n✂️ Usta: {barber}\n👤 {client} · {phone}\n📅 {date}\n💬 {comment}",
     "⚠️ <b>Низкая оценка</b> {stars}\n✂️ Мастер: {barber}\n👤 {client} · {phone}\n📅 {date}\n💬 {comment}")

# avtomatik xabarlar
_add("winback", "Assalomu alaykum, {name}! 👋\n<b>{shop}</b>da {days} kundan beri ko'rishmadik. "
                "Sochingiz o'sib qolgandir 😉 Navbat oling:",
     "Здравствуйте, {name}! 👋\nМы не виделись в <b>{shop}</b> уже {days} дней. "
     "Наверное, пора освежить причёску 😉 Записывайтесь:")
_add("expired_msg", "⌛ To'lov muddati tugadi, navbat bekor qilindi.\n\n{card}\n\nYangi navbat uchun 📅 Yozilish tugmasini bosing.",
     "⌛ Время оплаты истекло, запись отменена.\n\n{card}\n\nДля новой записи нажмите 📅 Записаться.")
_add("rem_day", "⏰ <b>Ertaga navbatingiz bor</b>\n\n{card}\n\nKelasizmi?",
     "⏰ <b>Завтра у вас запись</b>\n\n{card}\n\nПридёте?")
_add("rem_hour", "⏰ <b>Navbatingizga 2 soatdan kam qoldi</b>\n\n{card}",
     "⏰ <b>До вашей записи меньше 2 часов</b>\n\n{card}")
_add("digest_barber", "☀️ <b>Bugun {n} ta navbat</b>", "☀️ <b>Сегодня записей: {n}</b>")
_add("digest_owner", "☀️ <b>Bugun jami {n} ta navbat</b>", "☀️ <b>Сегодня всего записей: {n}</b>")

# ============================== CHEK ==============================
_add("rc_none_pending", "Hozir to'lov kutayotgan navbat yo'q. Navbat olish uchun 📅 Yozilish ni bosing.",
     "Сейчас нет записей, ожидающих оплаты. Нажмите 📅 Записаться.")
_add("rc_duplicate", "⚠️ Bu chek avval ishlatilgan. Iltimos, yangi to'lov chekini yuboring.",
     "⚠️ Этот чек уже был использован. Пожалуйста, отправьте новый чек об оплате.")
_add("rc_under_review", "⏳ Chekingiz ustaga yuborilgan va tekshirilmoqda. Iltimos, kuting.",
     "⏳ Ваш чек передан мастеру и проверяется. Пожалуйста, подождите.")
_add("rc_checking", "🔍 Chek tekshirilmoqda...", "🔍 Проверяю чек...")
_add("rc_rejected", "❌ Chek qabul qilinmadi: {reason}\nTo'g'ri chekni qayta yuboring (urinish qoldi: {left}).",
     "❌ Чек не принят: {reason}\nОтправьте правильный чек ещё раз (осталось попыток: {left}).")
_add("rc_rejected_final", "❌ Chek avtomatik tasdiqlanmadi: {reason}\nUni usta qo'lda tekshiradi, iltimos kuting.",
     "❌ Чек не подтверждён автоматически: {reason}\nМастер проверит его вручную, пожалуйста, подождите.")
_add("rc_received", "✅ Chek qabul qilindi. Usta tasdiqlashi bilan sizga xabar beramiz.",
     "✅ Чек получен. Как только мастер подтвердит, мы сообщим вам.")
_add("rc_not_delivered", "Chek qabul qilindi, lekin ustaga yetkazib bo'lmadi. Iltimos, usta bilan bog'laning.",
     "Чек получен, но передать мастеру не удалось. Пожалуйста, свяжитесь с мастером.")
_add("rc_caption_title", "🧾 <b>Depozit cheki</b>", "🧾 <b>Чек депозита</b>")
_add("rc_deposit", "💳 Depozit: {v}", "💳 Депозит: {v}")
_add("rc_ai_read", "🤖 <b>Chekdan o'qilgan:</b>", "🤖 <b>Считано с чека:</b>")
_add("rc_amount", "• Summa: {v}", "• Сумма: {v}")
_add("rc_time", "• Vaqt: {v}", "• Время: {v}")
_add("rc_card", "• Qabul qiluvchi karta: ...{v}", "• Карта получателя: ...{v}")
_add("rc_tx", "• Tranzaksiya: {v}", "• Транзакция: {v}")
_add("rc_check_prompt", "To'lov tushganini tekshirib, tasdiqlang:", "Проверьте поступление платежа и подтвердите:")
_add("rc_auto_title", "🤖 <b>Chek avtomatik tasdiqlandi</b>", "🤖 <b>Чек подтверждён автоматически</b>")
_add("rc_auto_hint", "Agar chek shubhali bo'lsa, quyidagi tugma bilan bekor qiling.",
     "Если чек кажется подозрительным, отмените кнопкой ниже.")
_add("rc_confirmed_title", "✅ <b>Tasdiqlandi</b>", "✅ <b>Подтверждено</b>")
_add("rc_rejected_title", "❌ <b>Rad etildi</b>", "❌ <b>Отклонено</b>")
_add("rc_revoked_title", "↩️ <b>Chek bekor qilindi</b>", "↩️ <b>Чек аннулирован</b>")
_add("rc_staff_rejected",
     "❌ Chekingiz tasdiqlanmadi, shuning uchun navbat bekor qilindi.\nAgar to'lov qilgan bo'lsangiz, usta bilan bog'laning yoki qaytadan navbat oling.",
     "❌ Ваш чек не подтверждён, поэтому запись отменена.\nЕсли вы оплатили, свяжитесь с мастером или запишитесь заново.")
_add("no_access", "Ruxsat yo'q", "Нет доступа")
_add("already_handled", "Bu navbat allaqachon ko'rib chiqilgan", "Эта запись уже обработана")
_add("confirmed_toast", "Tasdiqlandi ✅", "Подтверждено ✅")
_add("rejected_toast", "Rad etildi", "Отклонено")
# AI rad etish sabablari
_add("ai_not_receipt", "bu to'lov cheki emas", "это не чек об оплате")
_add("ai_failed", "to'lov muvaffaqiyatsiz ko'rinadi", "платёж выглядит неуспешным")
_add("ai_low_amount", "summa depozitdan kam", "сумма меньше депозита")
_add("ai_wrong_card", "to'lov boshqa kartaga qilingan", "платёж отправлен на другую карту")
_add("ai_old", "chek eski (navbat olishdan oldingi)", "чек старый (до создания записи)")
_add("ai_duplicate", "bu tranzaksiya avval ishlatilgan", "эта транзакция уже использовалась")
_add("ai_unavailable", "avtomatik tahlil ishlamadi", "автоматический анализ не сработал")
_add("ai_no_amount", "summani o'qib bo'lmadi", "не удалось прочитать сумму")
_add("ai_edited", "chek tahrirlanganga o'xshaydi", "чек похож на отредактированный")
_add("ai_unsure", "chekni ishonchli tasdiqlab bo'lmadi", "не удалось надёжно подтвердить чек")
_add("ai_ok", "tasdiqlandi", "подтверждено")

# ============================== ADMIN ==============================
_add("admin_title", "🛠 <b>Admin panel</b>", "🛠 <b>Админ-панель</b>")
_add("day_empty", "📭 {date} uchun navbatlar yo'q.", "📭 На {date} записей нет.")
_add("day_header", "📋 <b>{date}</b> — {n} ta navbat", "📋 <b>{date}</b> — записей: {n}")
_add("status_changed", "Bu navbat holati allaqachon o'zgargan", "Статус этой записи уже изменён")
_add("arrived_toast", "✔️ Keldi deb belgilandi", "✔️ Отмечено: пришёл")
_add("noshow_toast", "❌ Kelmadi deb belgilandi", "❌ Отмечено: не пришёл")
_add("ns_count", "⚠️ Mijoz {n} marta kelmagan.", "⚠️ Клиент не приходил {n} раз(а).")
_add("ns_blocked", "Onlayn yozilish yopildi.", "Онлайн-запись закрыта.")
_add("no_linked_barber", "Sizga bog'langan usta yo'q.", "К вам не привязан ни один мастер.")
_add("session_lost_admin", "Sessiya tugagan, qaytadan boshlang", "Сессия истекла, начните заново")
_add("cancelled_plain", "Bekor qilindi.", "Отменено.")
_add("bl_pick_date", "📅 Qaysi kunni bloklaysiz?", "📅 Какой день блокируем?")
_add("bl_pick_barber", "Qaysi usta uchun?", "Для какого мастера?")
_add("bl_not_workday", "{date} — ish kuni emas, bloklash shart emas.", "{date} — выходной, блокировка не нужна.")
_add("bl_whole_day", "🚫 Butun kunni yopish", "🚫 Закрыть весь день")
_add("bl_from", "🕒 {date}: qaysi vaqtdan boshlab band?", "🕒 {date}: с какого времени занято?")
_add("bl_to", "🕒 {start} dan qaysi vaqtgacha band?", "🕒 С {start} до какого времени занято?")
_add("bl_whole", "butun kun", "весь день")
_add("bl_confirm",
     "⏸ <b>Bloklash</b>\n✂️ {barber}\n📅 {date} · {span}\n\nKo'chiriladigan navbatlar: <b>{n}</b> ta. Mijozlarga avtomatik xabar yuboriladi.",
     "⏸ <b>Блокировка</b>\n✂️ {barber}\n📅 {date} · {span}\n\nЗаписей к переносу: <b>{n}</b>. Клиентам будет отправлено уведомление.")
_add("bl_done", "✅ Vaqt bloklandi: {barber}, {date}", "✅ Время заблокировано: {barber}, {date}")
_add("bl_line_cancelled", "• {who}: {old} → bekor qilindi (bo'sh vaqt topilmadi)",
     "• {who}: {old} → отменено (свободное время не найдено)")
_add("bl_none_moved", "Ko'chiriladigan navbat yo'q edi.", "Записей для переноса не было.")
_add("mv_msg_moved",
     "Hurmatli {who}, ustaning ishi chiqib qolgani uchun navbatingiz <b>{old}</b> dan <b>{new}</b> ga ko'chirildi.",
     "Уважаемый(ая) {who}, из-за внезапных дел мастера ваша запись перенесена с <b>{old}</b> на <b>{new}</b>.")
_add("mv_msg_cancelled",
     "Hurmatli {who}, ustaning ishi chiqib qolgani uchun {old} dagi navbatingiz bekor qilindi. "
     "Depozitingiz keyingi navbatingizga hisobga o'tadi. Yangi vaqt: 📅 Yozilish.",
     "Уважаемый(ая) {who}, из-за внезапных дел мастера запись на {old} отменена. "
     "Депозит перейдёт на вашу следующую запись. Новая запись: 📅 Записаться.")

# qo'lda navbat
_add("mn_intro", "📞 <b>Qo'lda navbat qo'shish</b>\nTelefon qilgan mijoz uchun. Depozit so'ralmaydi.",
     "📞 <b>Добавить запись вручную</b>\nДля клиента, позвонившего по телефону. Депозит не требуется.")
_add("date_full_admin", "Bu kunda bo'sh vaqt yo'q.", "В этот день нет свободного времени.")
_add("mn_ask_name", "👤 Mijoz ismini yozing:", "👤 Напишите имя клиента:")
_add("mn_ask_phone", "📱 Mijoz telefon raqamini yozing (masalan, 901234567). Keyin u botdan yozilsa, tarixi birlashadi.",
     "📱 Напишите номер телефона клиента (например, 901234567). Если он потом запишется через бота, история объединится.")
_add("mn_phone_bad", "Raqam noto'g'ri. Masalan: 901234567", "Неверный номер. Например: 901234567")
_add("mn_no_phone", "Raqamsiz qo'shilmoqda...", "Добавляю без номера...")
_add("mn_taken", "😔 Bu vaqt band bo'lib qoldi. Qaytadan urinib ko'ring.", "😔 Это время занято. Попробуйте снова.")
_add("mn_done", "✅ <b>Navbat qo'shildi</b> (telefon orqali)", "✅ <b>Запись добавлена</b> (по телефону)")
_add("mn_discount", "🎁 Sodiqlik: −{pct}% → {price}", "🎁 Лояльность: −{pct}% → {price}")
_add("mn_notify", "📞 <b>Navbat qo'lda qo'shildi</b>", "📞 <b>Запись добавлена вручную</b>")

# hisobot
_add("per_today", "Bugun", "Сегодня")
_add("per_yesterday", "Kecha", "Вчера")
_add("per_7", "7 kun", "7 дней")
_add("per_30", "30 kun", "30 дней")
_add("rp_empty", "📊 {period}: ma'lumot yo'q.", "📊 {period}: данных нет.")
_add("rp_title", "📊 <b>Hisobot — {period}</b>", "📊 <b>Отчёт — {period}</b>")
_add("rp_revenue", "💰 Tushum (taxminiy): <b>{v}</b>", "💰 Выручка (примерно): <b>{v}</b>")
_add("rp_done", "✔️ Xizmat ko'rsatildi: <b>{n}</b> · o'rtacha chek {avg}", "✔️ Обслужено: <b>{n}</b> · средний чек {avg}")
_add("rp_noshow", "❌ Kelmaganlar: <b>{n}</b> ({p}%)", "❌ Не пришли: <b>{n}</b> ({p}%)")
_add("rp_cancelled", "🚫 Bekor qilinganlar: <b>{n}</b>", "🚫 Отменено: <b>{n}</b>")
_add("rp_upcoming", "📅 Kutilayotgan navbatlar: <b>{n}</b>", "📅 Предстоящих записей: <b>{n}</b>")
_add("rp_saved", "🛡 Depozit tufayli saqlab qolingan: <b>{v}</b>", "🛡 Сохранено благодаря депозиту: <b>{v}</b>")
_add("rp_by_barber", "✂️ <b>Ustalar bo'yicha</b>", "✂️ <b>По мастерам</b>")
_add("rp_services", "💈 <b>Mashhur xizmatlar</b>", "💈 <b>Популярные услуги</b>")
_add("rp_clients", "👥 Mijozlar: <b>{total}</b> (yangi {new}, qaytganlar {ret})",
     "👥 Клиентов: <b>{total}</b> (новых {new}, вернувшихся {ret})")
_add("rp_busy", "🔥 Eng band: {day}, {hour} atrofida", "🔥 Самое загруженное: {day}, около {hour}")
_add("rp_rating", "⭐ O'rtacha baho: <b>{avg}</b> {stars} ({n} ta baho)", "⭐ Средняя оценка: <b>{avg}</b> {stars} (оценок: {n})")

# mijozlar
_add("owner_only", "Bu bo'lim faqat ega uchun.", "Этот раздел только для владельца.")
_add("clients_none", "Hali mijozlar yo'q.", "Клиентов пока нет.")
_add("clients_title", "👥 <b>Mijozlar</b> (20 tagacha)", "👥 <b>Клиенты</b> (до 20)")
_add("clients_noshow", "kelmagan", "не пришёл")
_add("client_not_found", "Mijoz topilmadi", "Клиент не найден")
_add("client_blocked", "Yopildi 🚫", "Заблокирован 🚫")
_add("client_unblocked", "Ochildi 🔓", "Разблокирован 🔓")

# sozlamalar
_add("settings_card",
     "⚙️ <b>Sozlamalar — {name}</b>\n\n💳 Depozit: {dep}\n🏦 Karta: <code>{card}</code>\n📍 Manzil: {address}\n"
     "📞 Telefon: {phone}\n⏳ Bepul bekor qilish: {h} soat oldin\n🗺 Lokatsiya: {loc}\n\nNimani o'zgartirasiz?",
     "⚙️ <b>Настройки — {name}</b>\n\n💳 Депозит: {dep}\n🏦 Карта: <code>{card}</code>\n📍 Адрес: {address}\n"
     "📞 Телефон: {phone}\n⏳ Бесплатная отмена: за {h} ч\n🗺 Локация: {loc}\n\nЧто изменить?")
_add("set_loc_yes", "✅ o'rnatilgan", "✅ задана")
_add("set_loc_no", "❌ yo'q", "❌ нет")
_add("set_btn_deposit", "💳 Depozit summasi", "💳 Сумма депозита")
_add("set_btn_card", "🏦 Karta raqami", "🏦 Номер карты")
_add("set_btn_address", "📍 Manzil", "📍 Адрес")
_add("set_btn_phone", "📞 Telefon", "📞 Телефон")
_add("set_btn_cancel_hours", "⏳ Bekor qilish muddati", "⏳ Срок отмены")
_add("set_btn_location", "🗺 Xaritadagi lokatsiya", "🗺 Локация на карте")
_add("set_btn_demo_clear", "🧹 Demo ma'lumotlarni o'chirish", "🧹 Удалить демо-данные")
_add("set_deposit", "Depozit summasi (so'm, faqat raqam)", "Сумма депозита (сум, только цифры)")
_add("set_card", "Karta raqami", "Номер карты")
_add("set_address", "Manzil", "Адрес")
_add("set_phone", "Telefon raqami", "Номер телефона")
_add("set_cancel_hours", "Bepul bekor qilish muddati (soat, faqat raqam)", "Срок бесплатной отмены (часы, только цифры)")
_add("set_ask", "✏️ {what} ni yozib yuboring:", "✏️ Напишите: {what}")
_add("set_digits", "Iltimos, faqat raqam yozing.", "Пожалуйста, пишите только цифры.")
_add("set_saved", "✅ Saqlandi. Yangi qiymat keyingi navbatlardan boshlab amal qiladi.",
     "✅ Сохранено. Новое значение действует для следующих записей.")
_add("set_loc_ask",
     "🗺 Lokatsiyani yuboring: 📎 (skrepka) → «Joylashuv» → xaritadan shopingiz joyini tanlang.\nYoki shopda bo'lsangiz, pastdagi tugmani bosing.",
     "🗺 Отправьте локацию: 📎 (скрепка) → «Геопозиция» → выберите место заведения на карте.\nИли, если вы на месте, нажмите кнопку ниже.")
_add("set_loc_saved", "✅ Lokatsiya saqlandi. Endi mijozlar 📍 Manzil bosganda xaritani ko'radi.",
     "✅ Локация сохранена. Теперь клиенты увидят карту при нажатии 📍 Адрес.")
_add("demo_clear_ask", "🧹 Hamma demo (soxta) navbatlar, baholar va mijozlar o'chiriladi. Haqiqiy ma'lumotlar saqlanadi. Davom etamizmi?",
     "🧹 Будут удалены все демо-записи, оценки и клиенты. Реальные данные сохранятся. Продолжить?")
_add("demo_cleared", "✅ Demo ma'lumotlar o'chirildi.", "✅ Демо-данные удалены.")

# ustalar
_add("staff_title", "✂️ <b>Ustalar</b>\n", "✂️ <b>Мастера</b>\n")
_add("staff_linked", "✅ bog'langan", "✅ подключён")
_add("staff_not_linked", "⏳ havola kutilmoqda", "⏳ ожидает ссылку")
_add("staff_hint", "🔄 — ajratish (yangi havola), 🗑 — o'chirish. Havolani faqat o'sha ustaga shaxsiy yuboring.",
     "🔄 — отвязать (новая ссылка), 🗑 — удалить. Отправляйте ссылку только лично нужному мастеру.")
_add("staff_add_ask", "✏️ Yangi usta ismini yozing:", "✏️ Напишите имя нового мастера:")
_add("staff_name_bad", "Ism 2-30 belgidan iborat bo'lsin.", "Имя должно быть от 2 до 30 символов.")
_add("staff_added", "✅ <b>{name}</b> qo'shildi (Du-Sh, 09:00-21:00, tushlik 13:00-14:00).\nHavola:\n{link}",
     "✅ <b>{name}</b> добавлен (Пн-Сб, 09:00-21:00, обед 13:00-14:00).\nСсылка:\n{link}")
_add("staff_unlinked", "Ajratildi", "Отвязан")
_add("staff_last", "Kamida 1 ta usta qolishi kerak.", "Должен остаться хотя бы 1 мастер.")
_add("staff_del_ask", "🗑 <b>{name}</b> ni o'chirasizmi?\nKeyingi navbatlari: <b>{n}</b> ta. Ular bekor qilinadi, mijozlarga xabar boradi va depozitlari saqlanadi.",
     "🗑 Удалить мастера <b>{name}</b>?\nБудущих записей: <b>{n}</b>. Они будут отменены, клиентам придёт уведомление, депозиты сохранятся.")
_add("staff_removed_client", "Hurmatli mijoz, {barber} ustaning {when} dagi navbati bekor qilindi. Depozitingiz keyingi navbatingizga hisobga o'tadi. Yangi navbat: 📅 Yozilish.",
     "Уважаемый клиент, запись к мастеру {barber} на {when} отменена. Депозит перейдёт на вашу следующую запись. Новая запись: 📅 Записаться.")
_add("staff_deleted", "O'chirildi", "Удалён")

# ommaviy xabar
_add("bc_ask", "📢 Mijozlarga yuboriladigan xabarni yozing (matn yoki rasm + izoh). Faqat siz yuborasiz.",
     "📢 Напишите сообщение для клиентов (текст или фото с подписью). Отправляете только вы.")
_add("bc_nobody", "Hozircha xabar yuboriladigan mijozlar yo'q.", "Пока некому отправлять сообщение.")
_add("bc_confirm", "Xabar <b>{n}</b> ta mijozga yuboriladi. Tasdiqlaysizmi?", "Сообщение получат клиентов: <b>{n}</b>. Подтвердить?")
_add("bc_sending", "📤 Yuborilmoqda ({n} ta)...", "📤 Отправляю ({n})...")
_add("bc_done", "✅ Yuborildi: {ok}\n⚠️ Yetmadi: {fail}", "✅ Отправлено: {ok}\n⚠️ Не доставлено: {fail}")


# --- usta havolasini tasdiqlash va "Men ham ustaman" ---
_add("join_ask", "Siz <b>{name}</b> ustasi sifatida bog'lanmoqchimisiz?",
     "Вы хотите подключиться как мастер <b>{name}</b>?")
_add("btn_join_yes", "✅ Ha, bu menman", "✅ Да, это я")
_add("btn_join_no", "❌ Yo'q", "❌ Нет")
_add("join_no", "Bekor qilindi. Siz usta sifatida bog'lanmadingiz.", "Отменено. Вы не подключены как мастер.")
_add("btn_staff_me", "🙋 Men ham ustaman", "🙋 Я тоже мастер")
_add("staff_me_exists", "Siz allaqachon usta sifatida qo'shilgansiz.", "Вы уже добавлены как мастер.")
_add("staff_me_done", "✅ Siz usta sifatida qo'shildingiz: {name}", "✅ Вы добавлены как мастер: {name}")


# --- xizmatlar va ish vaqti (faqat ega) ---
_add("btn_services", "💈 Xizmatlar", "💈 Услуги")
_add("btn_hours", "🕒 Ish vaqti", "🕒 Рабочее время")
_add("set_btn_name", "🏷 Do'kon nomi", "🏷 Название заведения")
_add("set_name", "Do'kon nomi", "Название заведения")
_add("sv_title", "💈 <b>Xizmatlar</b>\nNarx, nom yoki davomiylikni o'zgartirish uchun xizmatni bosing.",
     "💈 <b>Услуги</b>\nНажмите на услугу, чтобы изменить цену, название или длительность.")
_add("sv_btn_add", "➕ Xizmat qo'shish", "➕ Добавить услугу")
_add("sv_detail", "💈 <b>{name}</b>\n💰 {price}\n⏱ {dur} {unit}\n\nNimani o'zgartirasiz?",
     "💈 <b>{name}</b>\n💰 {price}\n⏱ {dur} {unit}\n\nЧто изменить?")
_add("sv_btn_name", "✏️ Nomi", "✏️ Название")
_add("sv_btn_price", "💰 Narxi", "💰 Цена")
_add("sv_btn_dur", "⏱ Davomiyligi", "⏱ Длительность")
_add("sv_btn_del", "🗑 O'chirish", "🗑 Удалить")
_add("sv_ask_name", "✏️ Xizmat nomini yozing (2-30 belgi):", "✏️ Напишите название услуги (2-30 символов):")
_add("sv_ask_price", "💰 Narxni yozing (so'm, faqat raqam, masalan 60000):", "💰 Напишите цену (сум, только цифры, например 60000):")
_add("sv_pick_dur", "⏱ Davomiylikni tanlang:", "⏱ Выберите длительность:")
_add("sv_name_bad", "Nom 2-30 belgidan iborat bo'lsin.", "Название должно быть от 2 до 30 символов.")
_add("sv_price_bad", "Narx 1 000 dan 10 000 000 gacha, faqat raqam bo'lsin.", "Цена от 1 000 до 10 000 000, только цифры.")
_add("sv_saved", "✅ Saqlandi. Yangi narx faqat yangi navbatlarga amal qiladi.", "✅ Сохранено. Новая цена действует только для новых записей.")
_add("sv_added", "✅ Xizmat qo'shildi: {name}", "✅ Услуга добавлена: {name}")
_add("sv_del_ask", "🗑 <b>{name}</b> o'chirilsinmi?\nEski navbatlar saqlanadi, yangi navbat olinmaydi.",
     "🗑 Удалить <b>{name}</b>?\nСтарые записи сохранятся, новые записи на неё создаваться не будут.")
_add("sv_deleted", "O'chirildi", "Удалено")
_add("sv_last", "Kamida 1 ta xizmat qolishi kerak.", "Должна остаться хотя бы 1 услуга.")
_add("wh_pick_barber", "🕒 Qaysi usta uchun ish vaqti?", "🕒 Для какого мастера рабочее время?")
_add("wh_screen", "🕒 <b>{name}</b> — ish vaqti\n\n{lines}\n\nKunni bosib o'zgartiring (✅ ish kuni, 🔴 dam olish).",
     "🕒 <b>{name}</b> — рабочее время\n\n{lines}\n\nНажмите на день, чтобы изменить (✅ рабочий, 🔴 выходной).")
_add("wh_off", "dam olish", "выходной")
_add("wh_btn_all", "⚡ Hamma ish kuniga bir xil vaqt", "⚡ Одинаковое время для всех рабочих дней")
_add("wh_btn_copy", "👥 Hamma ustalarga nusxalash", "👥 Скопировать всем мастерам")
_add("wh_day_screen", "🕒 <b>{name}</b> · {day}\n{line}", "🕒 <b>{name}</b> · {day}\n{line}")
_add("wh_btn_edit", "✏️ Vaqtni o'zgartirish", "✏️ Изменить время")
_add("wh_btn_off", "🔴 Dam olish kuni qilish", "🔴 Сделать выходным")
_add("wh_pick_start", "🟢 Ish boshlanishi qaysi vaqtda?", "🟢 Во сколько начало работы?")
_add("wh_pick_end", "🔴 Ish tugashi qaysi vaqtda?", "🔴 Во сколько конец работы?")
_add("wh_pick_lunch", "🍽 Tushlik qachon boshlanadi? (yoki tushliksiz)", "🍽 Когда начинается обед? (или без обеда)")
_add("wh_btn_nolunch", "🍽 Tushliksiz", "🍽 Без обеда")
_add("wh_pick_lunch_len", "🍽 Tushlik necha daqiqa?", "🍽 Сколько минут обед?")
_add("wh_saved", "✅ Saqlandi.", "✅ Сохранено.")
_add("wh_off_done", "✅ Dam olish kuni qilindi.", "✅ Сделан выходным.")
_add("wh_copied", "✅ Jadval boshqa ustalarga nusxalandi: {n} ta.", "✅ Расписание скопировано другим мастерам: {n}.")
_add("wh_warn_outside",
     "⚠️ Ish vaqtidan tashqarida qolgan navbatlar: {n} ta (ular o'zgarmagan). Kerak bo'lsa, ⏸ Vaqtni bloklash orqali ko'chiring.",
     "⚠️ Записей вне рабочего времени: {n} (они не изменены). При необходимости перенесите через ⏸ Заблокировать время.")
_add("wh_bad_lunch", "Tushlik vaqti noto'g'ri tanlandi, qaytadan urinib ko'ring.", "Время обеда выбрано неверно, попробуйте снова.")


# ============================== FUNKSIYALAR ==============================
def tr(lang: str | None, key: str, **kw) -> str:
    table = S.get(lang or "uz", S["uz"])
    text = table.get(key) or S["uz"][key]
    return text.format(**kw) if kw else text


def variants(key: str) -> list[str]:
    """Reply-tugma matnining barcha til variantlari (handlerlarda F.text.in_ uchun)."""
    return sorted({S["uz"][key], S["ru"][key]})


def money(n: int, lang: str = "uz") -> str:
    unit = "сум" if lang == "ru" else "so'm"
    return f"{int(n):,}".replace(",", " ") + f" {unit}"


def fmt_min(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def fmt_date(date_str: str, lang: str = "uz") -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{WEEKDAYS[lang if lang in WEEKDAYS else 'uz'][d.weekday()]} {d:%d.%m}"


def status_label(lang: str, status: str) -> str:
    return STATUS.get(lang, STATUS["uz"]).get(status, status)


def booking_card(b: dict, lang: str = "uz") -> str:
    price = tr(lang, "line_price", v=money(b["price"], lang))
    if b.get("discount_percent"):
        price += f" (🎁 −{b['discount_percent']}%)"
    return (
        f"💈 <b>{esc(b['service_name'])}</b>\n"
        f"{tr(lang, 'line_barber', v=esc(b['staff_name']))}\n"
        f"📅 {fmt_date(b['date'], lang)} · {fmt_min(b['start_min'])}\n"
        f"{price}"
    )


def admin_booking(b: dict, lang: str = "uz") -> str:
    phone = esc(b.get("client_phone") or "—")
    name = esc(b.get("client_name") or "—")
    tags = ""
    if b.get("client_confirmed"):
        tags += " ✔️"
    if b.get("source") == "manual":
        tags += " 📞"
    if b.get("discount_percent"):
        tags += f" 🎁−{b['discount_percent']}%"
    return (
        f"🕒 <b>{fmt_min(b['start_min'])}</b> · {esc(b['service_name'])}\n"
        f"👤 {name} · {phone}\n"
        f"✂️ {esc(b['staff_name'])}\n"
        f"{status_label(lang, b['status'])}{tags}"
    )
