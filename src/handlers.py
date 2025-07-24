from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Location, Contact
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
import re

from .db import db
from .keyboard import *
from .config import ADMIN_IDS, VACANCIES_PER_PAGE, PROMOTION_PRICES

router = Router()


# STATES
class VacancyForm(StatesGroup):
    title = State()
    description = State()
    salary = State()
    work_schedule = State()
    experience = State()
    address = State()
    location = State()
    phone = State()
    contact_name = State()


class SearchFilters(StatesGroup):
    location = State()
    salary_from = State()
    radius = State()


class SubscriptionForm(StatesGroup):
    location = State()
    radius = State()
    salary_from = State()


# HELPER FUNCTIONS
def format_vacancy_text(vacancy: dict) -> str:
    """Vakansiya matnini formatlash"""
    text = f"<b>{vacancy['title']}</b>\n\n"
    text += f"📝 <b>Tavsif:</b>\n{vacancy['description']}\n\n"

    if vacancy.get('salary_from') or vacancy.get('salary_to'):
        if vacancy.get('salary_from') and vacancy.get('salary_to'):
            text += f"💰 <b>Maosh:</b> {vacancy['salary_from']:,} - {vacancy['salary_to']:,} so'm\n"
        elif vacancy.get('salary_from'):
            text += f"💰 <b>Maosh:</b> {vacancy['salary_from']:,} so'm dan\n"
        else:
            text += f"💰 <b>Maosh:</b> {vacancy['salary_to']:,} so'm gacha\n"

    if vacancy.get('work_schedule'):
        text += f"📅 <b>Ish jadvali:</b> {vacancy['work_schedule']}\n"

    if vacancy.get('experience_required'):
        text += f"🎯 <b>Tajriba:</b> {vacancy['experience_required']}\n"

    text += f"📍 <b>Manzil:</b> {vacancy['address']}\n"
    text += f"👤 <b>Ish beruvchi:</b> {vacancy.get('employer_name', 'Noma\'lum')}\n"

    if vacancy.get('contact_name'):
        text += f"📞 <b>Bog'lanish:</b> {vacancy['contact_name']}\n"

    if vacancy.get('distance'):
        text += f"📏 <b>Masofa:</b> {vacancy['distance']:.1f} km\n"

    return text


def format_salary(salary_str: str) -> int:
    """Maosh stringini raqamga aylantirish"""
    if not salary_str:
        return 0

    # Raqamlarni ajratib olish
    numbers = re.findall(r'\d+', salary_str.replace(' ', '').replace(',', ''))
    if numbers:
        return int(''.join(numbers))
    return 0


# ASOSIY HANDLERLAR

@router.message(Command("start"))
async def start_handler(message: Message):
    """Bot boshlash"""
    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    welcome_text = (
        f"Assalomu alaykum, {message.from_user.first_name}! 👋\n\n"
        "🎯 <b>Работа рядом</b> botiga xush kelibsiz!\n\n"
        "Bu bot orqali siz:\n"
        "🔍 O'z lokatsiyangizga yaqin ishlarni topa olasiz\n"
        "📝 Vakansiya e'lon qila olasiz\n"
        "🔔 Yangi ishlar haqida xabardor bo'lib turasiz\n\n"
        "Boshlash uchun quyidagi tugmalardan birini tanlang:"
    )

    await message.answer(welcome_text, reply_markup=main_menu_keyboard())


@router.message(F.text == "🔍 Ish izlash")
async def search_jobs(message: Message, state: FSMContext):
    """Ish izlash boshlash"""
    user = await db.get_or_create_user(message.from_user.id)

    if user.get('latitude') and user.get('longitude'):
        # Foydalanuvchi lokatsiyasi mavjud
        await show_nearby_vacancies(message, user['latitude'], user['longitude'])
    else:
        # Lokatsiya so'rash
        await message.answer(
            "Sizga yaqin ishlarni topish uchun lokatsiyangizni yuboring:",
            reply_markup=request_location_keyboard()
        )
        await state.set_state(SearchFilters.location)


@router.message(SearchFilters.location, F.location)
async def handle_search_location(message: Message, state: FSMContext):
    """Qidiruv uchun lokatsiyani olish"""
    location = message.location
    await db.update_user_location(
        message.from_user.id,
        location.latitude,
        location.longitude
    )

    await show_nearby_vacancies(message, location.latitude, location.longitude)
    await state.clear()


@router.message(F.text == "🏙️ Shahar tanlash")
async def choose_city(message: Message):
    """Shahar tanlash"""
    await message.answer(
        "Qaysi shaharda ish izlayapsiz?",
        reply_markup=cities_keyboard()
    )


@router.callback_query(F.data.startswith("city:"))
async def handle_city_selection(callback: CallbackQuery, state: FSMContext):
    """Shahar tanlash"""
    _, city_name, lat, lon = callback.data.split(":")
    latitude, longitude = float(lat), float(lon)

    await db.update_user_location(
        callback.from_user.id,
        latitude,
        longitude,
        city_name
    )

    await callback.message.edit_text(f"Tanlangan shahar: {city_name}")
    await show_nearby_vacancies(callback.message, latitude, longitude)
    await state.clear()


async def show_nearby_vacancies(message: Message, latitude: float, longitude: float,
                                page: int = 0, salary_from: int = None):
    """Yaqin vakansiyalarni ko'rsatish"""
    offset = page * VACANCIES_PER_PAGE
    vacancies = await db.get_nearby_vacancies(
        latitude, longitude,
        radius_km=50,
        salary_from=salary_from,
        offset=offset,
        limit=VACANCIES_PER_PAGE
    )

    if not vacancies:
        await message.answer(
            "❌ Sizga yaqin hech qanday vakansiya topilmadi.\n\n"
            "Qidiruv radiusini kengaytiring yoki boshqa shaharni tanlang.",
            reply_markup=main_menu_keyboard()
        )
        return

    total_vacancies = len(vacancies) + offset
    total_pages = (total_vacancies + VACANCIES_PER_PAGE - 1) // VACANCIES_PER_PAGE

    text = f"🔍 <b>Sizga yaqin vakansiyalar</b>\n"
    text += f"📍 Topildi: {len(vacancies)} ta\n"
    text += f"📄 Sahifa: {page + 1}/{total_pages}\n\n"

    try:
        await message.edit_text(
            text,
            reply_markup=vacancies_list_keyboard(vacancies, page, total_pages)
        )
    except TelegramBadRequest:
        await message.answer(
            text,
            reply_markup=vacancies_list_keyboard(vacancies, page, total_pages)
        )


@router.callback_query(F.data.startswith("view_vacancy:"))
async def view_vacancy(callback: CallbackQuery):
    """Vakansiyani ko'rish"""
    vacancy_id = int(callback.data.split(":")[1])
    vacancy = await db.get_vacancy(vacancy_id)

    if not vacancy:
        await callback.answer("❌ Vakansiya topilmadi")
        return

    text = format_vacancy_text(vacancy)

    await callback.message.edit_text(
        text,
        reply_markup=vacancy_actions_keyboard(vacancy_id, vacancy.get('phone'))
    )


@router.callback_query(F.data.startswith("contact_employer:"))
async def contact_employer(callback: CallbackQuery):
    """Ish beruvchi bilan bog'lanish"""
    vacancy_id = int(callback.data.split(":")[1])
    vacancy = await db.get_vacancy(vacancy_id)

    if not vacancy:
        await callback.answer("❌ Vakansiya topilmadi")
        return

    contact_text = (
        f"📞 <b>Bog'lanish ma'lumotlari:</b>\n\n"
        f"📱 Telefon: {vacancy['phone']}\n"
    )

    if vacancy.get('contact_name'):
        contact_text += f"👤 Ism: {vacancy['contact_name']}\n"

    contact_text += (
        f"\n💡 <b>Maslahat:</b> Qo'ng'iroq qilishda "
        f"'{vacancy['title']}' vakansiyasi haqida "
        f"ekanligingizni aytishni unutmang!"
    )

    await callback.message.edit_text(
        contact_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="◀️ Orqaga",
                callback_data=f"view_vacancy:{vacancy_id}"
            )
        ]])
    )


# VAKANSIYA JOYLASH

@router.message(F.text == "📝 Vakansiya joylashtirish")
async def post_vacancy_start(message: Message, state: FSMContext):
    """Vakansiya joylashtirish boshlash"""
    user = await db.get_or_create_user(message.from_user.id)

    if not user.get('phone'):
        await message.answer(
            "Vakansiya joylashtirish uchun telefon raqamingizni ulashing:",
            reply_markup=request_phone_keyboard()
        )
        return

    await db.set_user_as_employer(message.from_user.id)

    await message.answer(
        "📝 <b>Yangi vakansiya yaratish</b>\n\n"
        "Vakansiya sarlavhasini kiriting:",
        reply_markup=vacancy_form_keyboard()
    )
    await state.set_state(VacancyForm.title)


@router.message(VacancyForm.title, F.content_type == "contact")
async def handle_phone_for_vacancy(message: Message, state: FSMContext):
    """Telefon raqamini olish"""
    phone = message.contact.phone_number
    await db.update_user_phone(message.from_user.id, phone)
    await db.set_user_as_employer(message.from_user.id)

    await message.answer(
        "✅ Telefon raqam saqlandi!\n\n"
        "📝 <b>Yangi vakansiya yaratish</b>\n\n"
        "Vakansiya sarlavhasini kiriting:",
        reply_markup=vacancy_form_keyboard()
    )
    await state.set_state(VacancyForm.title)


@router.message(VacancyForm.title, F.text)
async def vacancy_title(message: Message, state: FSMContext):
    """Vakansiya sarlavhasi"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Vakansiya yaratish bekor qilindi", reply_markup=main_menu_keyboard())
        return

    await state.update_data(title=message.text)
    await message.answer(
        "📝 Vakansiya tavsifini kiriting (ish haqida batafsil ma'lumot):"
    )
    await state.set_state(VacancyForm.description)


@router.message(VacancyForm.description, F.text)
async def vacancy_description(message: Message, state: FSMContext):
    """Vakansiya tavsifi"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Vakansiya yaratish bekor qilindi", reply_markup=main_menu_keyboard())
        return

    await state.update_data(description=message.text)
    await message.answer(
        "💰 Maoshni kiriting (masalan: 3000000 yoki 2000000-4000000):\n"
        "Agar maosh kelishiladi bo'lsa, 'kelishiladi' deb yozing:"
    )
    await state.set_state(VacancyForm.salary)


@router.message(VacancyForm.salary, F.text)
async def vacancy_salary(message: Message, state: FSMContext):
    """Vakansiya maoshi"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Vakansiya yaratish bekor qilindi", reply_markup=main_menu_keyboard())
        return

    salary_text = message.text.lower()
    salary_from = salary_to = None

    if 'kelishiladi' not in salary_text:
        if '-' in salary_text:
            # Oraliq maosh
            parts = salary_text.split('-')
            if len(parts) == 2:
                salary_from = format_salary(parts[0])
                salary_to = format_salary(parts[1])
        else:
            # Bitta raqam
            salary_from = format_salary(salary_text)

    await state.update_data(salary_from=salary_from, salary_to=salary_to)
    await message.answer(
        "📅 Ish jadvalini tanlang:",
        reply_markup=work_schedule_keyboard()
    )


@router.callback_query(F.data.startswith("schedule:"), VacancyForm.salary)
async def vacancy_schedule(callback: CallbackQuery, state: FSMContext):
    """Ish jadvali"""
    schedule = callback.data.split(":")[1]
    schedule_names = {
        'toliq_kun': 'To\'liq kun',
        'qisman_kun': 'Qisman kun',
        'smenali': 'Smenali ish',
        'masofaviy': 'Masofaviy ish'
    }

    await state.update_data(work_schedule=schedule_names.get(schedule, schedule))
    await callback.message.edit_text(
        "🎯 Tajriba talabini kiriting (masalan: 'Tajriba talab etilmaydi', '1-3 yil tajriba'):"
    )
    await state.set_state(VacancyForm.experience)


@router.message(VacancyForm.experience, F.text)
async def vacancy_experience(message: Message, state: FSMContext):
    """Tajriba talabi"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Vakansiya yaratish bekor qilindi", reply_markup=main_menu_keyboard())
        return

    await state.update_data(experience_required=message.text)
    await message.answer(
        "📍 Ish joyining manzilini kiriting:"
    )
    await state.set_state(VacancyForm.address)


@router.message(VacancyForm.address, F.text)
async def vacancy_address(message: Message, state: FSMContext):
    """Ish joyi manzili"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Vakansiya yaratish bekor qilindi", reply_markup=main_menu_keyboard())
        return

    await state.update_data(address=message.text)
    await message.answer(
        "📍 Ish joyining lokatsiyasini yuboring:",
        reply_markup=request_location_keyboard()
    )
    await state.set_state(VacancyForm.location)


@router.message(VacancyForm.location, F.location)
async def vacancy_location(message: Message, state: FSMContext):
    """Ish joyi lokatsiyasi"""
    location = message.location
    await state.update_data(latitude=location.latitude, longitude=location.longitude)

    await message.answer(
        "👤 Bog'lanish uchun ism-familiyangizni kiriting:",
        reply_markup=vacancy_form_keyboard()
    )
    await state.set_state(VacancyForm.contact_name)


@router.message(VacancyForm.contact_name, F.text)
async def vacancy_contact_name(message: Message, state: FSMContext):
    """Bog'lanish ismi"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Vakansiya yaratish bekor qilindi", reply_markup=main_menu_keyboard())
        return

    data = await state.get_data()
    user = await db.get_or_create_user(message.from_user.id)

    # Vakansiyani yaratish
    vacancy_id = await db.create_vacancy(
        employer_id=user['id'],
        title=data['title'],
        description=data['description'],
        salary_from=data.get('salary_from'),
        salary_to=data.get('salary_to'),
        work_schedule=data.get('work_schedule'),
        experience_required=data.get('experience_required'),
        address=data['address'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        phone=user['phone'],
        contact_name=message.text
    )

    await state.clear()

    await message.answer(
        "✅ <b>Vakansiya muvaffaqiyatli yaratildi!</b>\n\n"
        "📋 Vakansiyangiz moderatsiyadan o'tgach faollashadi.\n"
        "⏱️ Bu odatda 2-24 soat vaqt oladi.\n\n"
        "🎯 Vakansiyangizni ko'proq odamlar ko'rishi uchun "
        "reklama xizmatlaridan foydalanishingiz mumkin.",
        reply_markup=promotion_keyboard(vacancy_id)
    )


# ADMIN HANDLERLAR

@router.message(F.text == "🔍 Yangi vakansiyalar")
async def admin_pending_vacancies(message: Message):
    """Kutilayotgan vakansiyalar (faqat adminlar uchun)"""
    if message.from_user.id not in ADMIN_IDS:
        return

    vacancies = await db.get_pending_vacancies()

    if not vacancies:
        await message.answer("✅ Barcha vakansiyalar ko'rib chiqilgan")
        return

    text = f"📋 <b>Moderatsiyani kutayotgan vakansiyalar: {len(vacancies)} ta</b>\n\n"

    for i, vacancy in enumerate(vacancies[:5], 1):
        text += f"{i}. <b>{vacancy['title']}</b>\n"
        text += f"👤 {vacancy['employer_name']}\n"
        text += f"📍 {vacancy['address'][:50]}...\n\n"

    await message.answer(text)

    # Birinchi vakansiyani ko'rsatish
    if vacancies:
        vacancy = vacancies[0]
        vacancy_text = format_vacancy_text(vacancy)
        await message.answer(
            f"<b>Moderatsiya:</b>\n\n{vacancy_text}",
            reply_markup=admin_vacancy_actions(vacancy['id'])
        )


@router.callback_query(F.data.startswith("admin_approve:"))
async def admin_approve_vacancy(callback: CallbackQuery):
    """Vakansiyani tasdiqlash"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q")
        return

    vacancy_id = int(callback.data.split(":")[1])
    await db.approve_vacancy(vacancy_id)

    # Obunachilarga xabar yuborish
    subscribers = await db.get_subscribers_for_vacancy(vacancy_id)
    vacancy = await db.get_vacancy(vacancy_id)

    for subscriber in subscribers:
        try:
            await callback.bot.send_message(
                subscriber['telegram_id'],
                f"🔔 <b>Yangi vakansiya!</b>\n\n"
                f"📝 {vacancy['title']}\n"
                f"📍 {vacancy['address']}\n"
                f"💰 {vacancy.get('salary_from', 'N/A')} so'm\n\n"
                f"Ko'rish uchun: /start",
                parse_mode="HTML"
            )
        except:
            pass

    await callback.message.edit_text(
        f"✅ Vakansiya tasdiqlandi!\n"
        f"📢 {len(subscribers)} ta obunachiga xabar yuborildi."
    )


@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject_vacancy(callback: CallbackQuery):
    """Vakansiyani rad etish"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q")
        return

    vacancy_id = int(callback.data.split(":")[1])
    await db.reject_vacancy(vacancy_id)

    await callback.message.edit_text("❌ Vakansiya rad etildi")


@router.message(F.text == "📊 Statistika")
async def show_statistics(message: Message):
    """Statistikani ko'rsatish"""
    if message.from_user.id not in ADMIN_IDS:
        return

    stats = await db.get_statistics()

    text = (
        "📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
        f"💼 Ish beruvchilar: {stats['total_employers']}\n"
        f"📋 Jami vakansiyalar: {stats['total_vacancies']}\n"
        f"✅ Faol vakansiyalar: {stats['active_vacancies']}\n"
        f"⏳ Kutilayotgan: {stats['pending_vacancies']}\n"
    )

    await message.answer(text)


# ORQAGA QAYTISH HANDERLARI

@router.message(F.text == "◀️ Orqaga")
@router.message(F.text == "◀️ Asosiy menyu")
async def back_to_main(message: Message, state: FSMContext):
    """Asosiy menyuga qaytish"""
    await state.clear()
    await message.answer(
        "🏠 Asosiy menyu",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery, state: FSMContext):
    """Asosiy menyuga qaytish (callback)"""
    await state.clear()
    await callback.message.edit_text("🏠 Asosiy menyu")
    await callback.message.answer("Tanlang:", reply_markup=main_menu_keyboard())