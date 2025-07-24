from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from db import db
from keyboard import *
from config import PROMOTION_PRICES

employer_router = Router()


@employer_router.message(F.text == "📋 Mening vakansiyalarim")
async def my_vacancies(message: Message):
    """Ish beruvchi vakansiyalarini ko'rsatish"""
    user = await db.get_or_create_user(message.from_user.id)

    async with db.pool.acquire() as conn:
        vacancies = await conn.fetch(
            """SELECT * FROM vacancies 
               WHERE employer_id = $1 
               ORDER BY created_at DESC""",
            user['id']
        )

    if not vacancies:
        await message.answer(
            "📋 Sizda hali vakansiyalar yo'q.\n\n"
            "Yangi vakansiya yaratish uchun "
            "'➕ Yangi vakansiya' tugmasini bosing.",
            reply_markup=employer_menu_keyboard()
        )
        return

    text = f"📋 <b>Sizning vakansiyalaringiz ({len(vacancies)} ta)</b>\n\n"

    for i, vacancy in enumerate(vacancies[:10], 1):
        status = "✅" if vacancy['is_approved'] else "⏳"
        if not vacancy['is_active']:
            status = "❌"

        text += f"{status} <b>{vacancy['title']}</b>\n"
        text += f"📅 {vacancy['created_at'].strftime('%d.%m.%Y')}\n"

        if vacancy['is_promoted']:
            text += f"⭐ Reklama: {vacancy['promotion_type']}\n"

        text += "\n"

    text += (
        "📊 Holat belgilari:\n"
        "✅ - Tasdiqlangan\n"
        "⏳ - Moderatsiyada\n"
        "❌ - Faol emas"
    )

    await message.answer(text, reply_markup=employer_menu_keyboard())


@employer_router.callback_query(F.data.startswith("promote:"))
async def promote_vacancy(callback: CallbackQuery):
    """Vakansiyani reklama qilish"""
    _, promotion_type, vacancy_id = callback.data.split(":")
    vacancy_id = int(vacancy_id)

    price = PROMOTION_PRICES.get(promotion_type, 0)

    promotion_names = {
        'top': 'Yuqoriga chiqarish',
        'urgent': 'Tezkor e\'lon',
        'highlight': 'Ajratib ko\'rsatish'
    }

    promotion_descriptions = {
        'top': 'Vakansiyangiz qidiruv natijalarida birinchi o\'rinlarda ko\'rsatiladi',
        'urgent': 'Vakansiyangiz "TEZKOR" belgisi bilan ajralib turadi',
        'highlight': 'Vakansiyangiz rangli fon bilan ajratib ko\'rsatiladi'
    }

    text = (
        f"⭐ <b>{promotion_names[promotion_type]}</b>\n\n"
        f"📝 {promotion_descriptions[promotion_type]}\n\n"
        f"💰 Narx: {price:,} so'm\n"
        f"⏰ Muddat: 7 kun\n\n"
        f"❓ To'lovni amalga oshirasizmi?"
    )

    await callback.message.edit_text(
        text,
        reply_markup=confirm_keyboard(f"payment:{promotion_type}", vacancy_id)
    )


@employer_router.callback_query(F.data.startswith("confirm:payment:"))
async def confirm_payment(callback: CallbackQuery):
    """To'lovni tasdiqlash"""
    parts = callback.data.split(":")
    promotion_type = parts[2]
    vacancy_id = int(parts[3])

    # Haqiqiy to'lov tizimi integratsiyasi bu yerda bo'lishi kerak
    # Hozircha reklama avtomatik faollashtiriladi

    await db.promote_vacancy(vacancy_id, promotion_type, 7)

    # To'lov yozuvini yaratish
    user = await db.get_or_create_user(callback.from_user.id)
    price = PROMOTION_PRICES.get(promotion_type, 0)

    async with db.pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO payments 
               (user_id, vacancy_id, amount, service_type, status)
               VALUES ($1, $2, $3, $4, 'completed')""",
            user['id'], vacancy_id, price, promotion_type
        )

    await callback.message.edit_text(
        "✅ <b>To'lov muvaffaqiyatli amalga oshirildi!</b>\n\n"
        "⭐ Vakansiyangiz endi reklama orqali "
        "ko'proq odamlarga ko'rsatiladi.\n\n"
        "📊 Natijalarni kuzatib borishingiz mumkin."
    )


@employer_router.callback_query(F.data.startswith("cancel:payment:"))
async def cancel_payment(callback: CallbackQuery):
    """To'lovni bekor qilish"""
    vacancy_id = int(callback.data.split(":")[-1])

    await callback.message.edit_text(
        "❌ To'lov bekor qilindi.",
        reply_markup=promotion_keyboard(vacancy_id)
    )


@employer_router.message(F.text == "📊 Statistika")
async def employer_statistics(message: Message):
    """Ish beruvchi statistikasi"""
    user = await db.get_or_create_user(message.from_user.id)

    async with db.pool.acquire() as conn:
        # Vakansiyalar statistikasi
        total_vacancies = await conn.fetchval(
            "SELECT COUNT(*) FROM vacancies WHERE employer_id = $1",
            user['id']
        )

        active_vacancies = await conn.fetchval(
            """SELECT COUNT(*) FROM vacancies 
               WHERE employer_id = $1 AND is_active = TRUE AND is_approved = TRUE""",
            user['id']
        )

        pending_vacancies = await conn.fetchval(
            """SELECT COUNT(*) FROM vacancies 
               WHERE employer_id = $1 AND is_approved = FALSE""",
            user['id']
        )

        promoted_vacancies = await conn.fetchval(
            """SELECT COUNT(*) FROM vacancies 
               WHERE employer_id = $1 AND is_promoted = TRUE""",
            user['id']
        )

        # To'lovlar statistikasi
        total_spent = await conn.fetchval(
            """SELECT COALESCE(SUM(amount), 0) FROM payments 
               WHERE user_id = $1 AND status = 'completed'""",
            user['id']
        ) or 0

    text = (
        "📊 <b>Sizning statistikangiz</b>\n\n"
        f"📋 Jami vakansiyalar: {total_vacancies}\n"
        f"✅ Faol vakansiyalar: {active_vacancies}\n"
        f"⏳ Moderatsiyada: {pending_vacancies}\n"
        f"⭐ Reklama qilingan: {promoted_vacancies}\n\n"
        f"💰 Jami sarflangan: {total_spent:,} so'm\n"
    )

    await message.answer(text, reply_markup=employer_menu_keyboard())


@employer_router.callback_query(F.data.startswith("edit_vacancy:"))
async def edit_vacancy_menu(callback: CallbackQuery):
    """Vakansiyani tahrirlash menyu"""
    vacancy_id = int(callback.data.split(":")[1])

    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="📝 Tavsifni o'zgartirish", callback_data=f"edit_desc:{vacancy_id}"))
    kb.add(InlineKeyboardButton(text="💰 Maoshni o'zgartirish", callback_data=f"edit_salary:{vacancy_id}"))
    kb.add(InlineKeyboardButton(text="📞 Telefoni o'zgartirish", callback_data=f"edit_phone:{vacancy_id}"))
    kb.add(InlineKeyboardButton(text="❌ Vakansiyani o'chirish", callback_data=f"delete_vacancy:{vacancy_id}"))
    kb.add(InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"view_vacancy:{vacancy_id}"))
    kb.adjust(1)

    await callback.message.edit_text(
        "⚙️ <b>Vakansiyani tahrirlash</b>\n\n"
        "Qaysi ma'lumotni o'zgartirmoqchisiz?",
        reply_markup=kb.as_markup()
    )


@employer_router.callback_query(F.data.startswith("delete_vacancy:"))
async def delete_vacancy_confirm(callback: CallbackQuery):
    """Vakansiyani o'chirish tasdiqi"""
    vacancy_id = int(callback.data.split(":")[1])

    await callback.message.edit_text(
        "❓ <b>Vakansiyani o'chirishni tasdiqlaysizmi?</b>\n\n"
        "⚠️ Bu amalni qaytarib bo'lmaydi!",
        reply_markup=confirm_keyboard("delete_vacancy", vacancy_id)
    )


@employer_router.callback_query(F.data.startswith("confirm:delete_vacancy:"))
async def delete_vacancy_confirmed(callback: CallbackQuery):
    """Vakansiyani o'chirish tasdiqlandi"""
    vacancy_id = int(callback.data.split(":")[-1])

    async with db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE vacancies SET is_active = FALSE WHERE id = $1",
            vacancy_id
        )

    await callback.message.edit_text(
        "✅ Vakansiya muvaffaqiyatli o'chirildi!"
    )


@employer_router.callback_query(F.data.startswith("cancel:delete_vacancy:"))
async def cancel_delete_vacancy(callback: CallbackQuery):
    """Vakansiyani o'chirishni bekor qilish"""
    vacancy_id = int(callback.data.split(":")[-1])

    await edit_vacancy_menu(callback)