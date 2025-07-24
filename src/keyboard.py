from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# ASOSIY MENYULAR

def main_menu_keyboard():
    """Asosiy menyu klaviaturasi"""
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="🔍 Ish izlash"))
    kb.add(KeyboardButton(text="📝 Vakansiya joylashtirish"))
    kb.add(KeyboardButton(text="📍 Mening obunalarim"))
    kb.add(KeyboardButton(text="⚙️ Sozlamalar"))
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)


def request_location_keyboard():
    """Lokatsiya so'rash klaviaturasi"""
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True))
    kb.add(KeyboardButton(text="🏙️ Shahar tanlash"))
    kb.add(KeyboardButton(text="◀️ Orqaga"))
    kb.adjust(1, 2)
    return kb.as_markup(resize_keyboard=True)


def back_keyboard():
    """Orqaga qaytish klaviaturasi"""
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="◀️ Orqaga"))
    return kb.as_markup(resize_keyboard=True)


def request_phone_keyboard():
    """Telefon raqami so'rash klaviaturasi"""
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="📱 Telefon raqamini yuborish", request_contact=True))
    kb.add(KeyboardButton(text="◀️ Orqaga"))
    kb.adjust(1, 1)
    return kb.as_markup(resize_keyboard=True)


# INLINE KLAVIATURALAR

def vacancy_actions_keyboard(vacancy_id: int, phone: str = None):
    """Vakansiya uchun amallar klaviaturasi"""
    kb = InlineKeyboardBuilder()

    if phone:
        kb.add(InlineKeyboardButton(
            text="📞 Qo'ng'iroq qilish",
            url=f"tel:{phone}"
        ))

    kb.add(InlineKeyboardButton(
        text="✉️ Xabar yozish",
        callback_data=f"contact_employer:{vacancy_id}"
    ))
    kb.add(InlineKeyboardButton(
        text="❤️ Saqlash",
        callback_data=f"save_vacancy:{vacancy_id}"
    ))
    kb.add(InlineKeyboardButton(
        text="◀️ Orqaga",
        callback_data="back_to_search"
    ))

    kb.adjust(2, 1, 1)
    return kb.as_markup()


def vacancies_list_keyboard(vacancies: list, page: int = 0, total_pages: int = 1):
    """Vakansiyalar ro'yxati klaviaturasi"""
    kb = InlineKeyboardBuilder()

    # Vakansiyalar
    for i, vacancy in enumerate(vacancies):
        kb.add(InlineKeyboardButton(
            text=f"{i + 1}. {vacancy['title'][:30]}...",
            callback_data=f"view_vacancy:{vacancy['id']}"
        ))

    # Sahifalash
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️", callback_data=f"page:{page - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}", callback_data="current_page"
    ))

    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️", callback_data=f"page:{page + 1}"
        ))

    if nav_buttons:
        kb.row(*nav_buttons)

    # Filtrlar va orqaga
    kb.add(InlineKeyboardButton(text="🔧 Filtrlar", callback_data="filters"))
    kb.add(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main"))

    kb.adjust(1, len(nav_buttons), 2)
    return kb.as_markup()


def filters_keyboard():
    """Filtrlar klaviaturasi"""
    kb = InlineKeyboardBuilder()

    kb.add(InlineKeyboardButton(text="💰 Maosh", callback_data="filter_salary"))
    kb.add(InlineKeyboardButton(text="📅 Ish jadvali", callback_data="filter_schedule"))
    kb.add(InlineKeyboardButton(text="🎯 Tajriba", callback_data="filter_experience"))
    kb.add(InlineKeyboardButton(text="📍 Masofani o'zgartirish", callback_data="filter_distance"))

    kb.add(InlineKeyboardButton(text="🗑️ Filtrlarni tozalash", callback_data="clear_filters"))
    kb.add(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_search"))

    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def salary_filter_keyboard():
    """Maosh filtri klaviaturasi"""
    kb = InlineKeyboardBuilder()

    salaries = [
        ("💸 1 mln dan kam", "salary:0:1000000"),
        ("💰 1-3 mln", "salary:1000000:3000000"),
        ("💎 3-5 mln", "salary:3000000:5000000"),
        ("👑 5 mln dan ko'p", "salary:5000000:100000000"),
    ]

    for text, callback in salaries:
        kb.add(InlineKeyboardButton(text=text, callback_data=callback))

    kb.add(InlineKeyboardButton(text="◀️ Orqaga", callback_data="filters"))
    kb.adjust(1)
    return kb.as_markup()


def work_schedule_keyboard():
    """Ish jadvali klaviaturasi"""
    kb = InlineKeyboardBuilder()

    schedules = [
        ("🕘 To'liq kun", "schedule:toliq_kun"),
        ("⏰ Qisman kun", "schedule:qisman_kun"),
        ("🌙 Smenali", "schedule:smenali"),
        ("🏠 Masofaviy", "schedule:masofaviy")
    ]

    for text, callback in schedules:
        kb.add(InlineKeyboardButton(text=text, callback_data=callback))

    kb.add(InlineKeyboardButton(text="◀️ Orqaga", callback_data="filters"))
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def cities_keyboard():
    """Shaharlar klaviaturasi"""
    kb = InlineKeyboardBuilder()

    cities = [
        ("🏙️ Toshkent", "city:tashkent:41.2995:69.2401"),
        ("🌆 Samarqand", "city:samarkand:39.6270:66.9750"),
        ("🏘️ Andijon", "city:andijan:40.7821:72.3442"),
        ("🌁 Namangan", "city:namangan:40.9983:71.6726"),
        ("🏞️ Farg'ona", "city:fergana:40.3842:71.7843"),
        ("🏔️ Buxoro", "city:bukhara:39.7747:64.4286")
    ]

    for text, callback in cities:
        kb.add(InlineKeyboardButton(text=text, callback_data=callback))

    kb.add(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_location"))
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


# ISH BERUVCHI KLAVIATURALARI

def employer_menu_keyboard():
    """Ish beruvchi menyu klaviaturasi"""
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="➕ Yangi vakansiya"))
    kb.add(KeyboardButton(text="📋 Mening vakansiyalarim"))
    kb.add(KeyboardButton(text="📊 Statistika"))
    kb.add(KeyboardButton(text="◀️ Asosiy menyu"))
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)


def vacancy_form_keyboard():
    """Vakansiya shakli klaviaturasi"""
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="❌ Bekor qilish"))
    return kb.as_markup(resize_keyboard=True)


def promotion_keyboard(vacancy_id: int):
    """Reklama klaviaturasi"""
    kb = InlineKeyboardBuilder()

    kb.add(InlineKeyboardButton(
        text="⭐ Yuqoriga chiqarish (10,000 so'm)",
        callback_data=f"promote:top:{vacancy_id}"
    ))
    kb.add(InlineKeyboardButton(
        text="🔥 Tezkor e'lon (15,000 so'm)",
        callback_data=f"promote:urgent:{vacancy_id}"
    ))
    kb.add(InlineKeyboardButton(
        text="✨ Ajratib ko'rsatish (5,000 so'm)",
        callback_data=f"promote:highlight:{vacancy_id}"
    ))
    kb.add(InlineKeyboardButton(
        text="◀️ Orqaga",
        callback_data=f"view_vacancy:{vacancy_id}"
    ))

    kb.adjust(1)
    return kb.as_markup()


# ADMIN KLAVIATURALARI

def admin_menu_keyboard():
    """Admin menyu klaviaturasi"""
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="🔍 Yangi vakansiyalar"))
    kb.add(KeyboardButton(text="📊 Statistika"))
    kb.add(KeyboardButton(text="👥 Foydalanuvchilar"))
    kb.add(KeyboardButton(text="📢 Xabar yuborish"))
    kb.add(KeyboardButton(text="◀️ Asosiy menyu"))
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def admin_vacancy_actions(vacancy_id: int):
    """Admin vakansiya amallari"""
    kb = InlineKeyboardBuilder()

    kb.add(InlineKeyboardButton(
        text="✅ Tasdiqlash",
        callback_data=f"admin_approve:{vacancy_id}"
    ))
    kb.add(InlineKeyboardButton(
        text="❌ Rad etish",
        callback_data=f"admin_reject:{vacancy_id}"
    ))
    kb.add(InlineKeyboardButton(
        text="📋 Batafsil",
        callback_data=f"admin_view:{vacancy_id}"
    ))

    kb.adjust(2, 1)
    return kb.as_markup()


def confirm_keyboard(action: str, item_id: int):
    """Tasdiqlash klaviaturasi"""
    kb = InlineKeyboardBuilder()

    kb.add(InlineKeyboardButton(
        text="✅ Ha",
        callback_data=f"confirm:{action}:{item_id}"
    ))
    kb.add(InlineKeyboardButton(
        text="❌ Yo'q",
        callback_data=f"cancel:{action}:{item_id}"
    ))

    kb.adjust(2)
    return kb.as_markup()


# OBUNA KLAVIATURALARI

def subscription_keyboard():
    """Obuna klaviaturasi"""
    kb = InlineKeyboardBuilder()

    kb.add(InlineKeyboardButton(text="🔔 Obuna bo'lish", callback_data="create_subscription"))
    kb.add(InlineKeyboardButton(text="⚙️ Obunani sozlash", callback_data="edit_subscription"))
    kb.add(InlineKeyboardButton(text="🔕 Obunani o'chirish", callback_data="delete_subscription"))
    kb.add(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main"))

    kb.adjust(1)
    return kb.as_markup()


def subscription_radius_keyboard():
    """Obuna radiusi klaviaturasi"""
    kb = InlineKeyboardBuilder()

    radiuses = [
        ("📍 5 km", "radius:5"),
        ("🌐 10 km", "radius:10"),
        ("🗺️ 25 km", "radius:25"),
        ("🌍 50 km", "radius:50")
    ]

    for text, callback in radiuses:
        kb.add(InlineKeyboardButton(text=text, callback_data=callback))

    kb.add(InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_subscription"))
    kb.adjust(2, 2, 1)
    return kb.as_markup()