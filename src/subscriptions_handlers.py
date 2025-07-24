from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Location
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from .db import db
from .keyboard import *

subscription_router = Router()


class SubscriptionForm(StatesGroup):
    location = State()
    radius = State()
    salary_from = State()


@subscription_router.message(F.text == "📍 Mening obunalarim")
async def my_subscriptions(message: Message):
    """Foydalanuvchi obunalarini ko'rsatish"""
    user = await db.get_or_create_user(message.from_user.id)
    subscription = await db.get_user_subscription(user['id'])

    if not subscription:
        await message.answer(
            "🔕 Sizda hali obuna yo'q.\n\n"
            "Obuna orqali yangi vakansiyalar haqida "
            "avtomatik xabar olishingiz mumkin.",
            reply_markup=subscription_keyboard()
        )
    else:
        text = (
            "🔔 <b>Sizning obunangiz</b>\n\n"
            f"📍 Hudud: {subscription.get('location_name', 'Belgilanmagan')}\n"
            f"📏 Radius: {subscription['radius_km']} km\n"
        )

        if subscription.get('salary_from'):
            text += f"💰 Minimal maosh: {subscription['salary_from']:,} so'm\n"

        if subscription.get('keywords'):
            text += f"🔍 Kalit so'zlar: {subscription['keywords']}\n"

        text += f"\n📅 Yaratilgan: {subscription['created_at'].strftime('%d.%m.%Y')}"

        await message.answer(text, reply_markup=subscription_keyboard())


@subscription_router.callback_query(F.data == "create_subscription")
async def create_subscription_start(callback: CallbackQuery, state: FSMContext):
    """Obuna yaratish boshlash"""
    await callback.message.edit_text(
        "🔔 <b>Yangi obuna yaratish</b>\n\n"
        "Qaysi hududda yangi vakansiyalar haqida "
        "xabar olmoqchisiz?\n\n"
        "Lokatsiyangizni yuboring:",
        reply_markup=request_location_keyboard()
    )
    await state.set_state(SubscriptionForm.location)


@subscription_router.message(SubscriptionForm.location, F.location)
async def subscription_location(message: Message, state: FSMContext):
    """Obuna lokatsiyasi"""
    location = message.location
    await state.update_data(
        latitude=location.latitude,
        longitude=location.longitude
    )

    await message.answer(
        "📏 Qancha radiusda qidirilsin?",
        reply_markup=subscription_radius_keyboard()
    )
    await state.set_state(SubscriptionForm.radius)


@subscription_router.callback_query(F.data.startswith("radius:"), SubscriptionForm.radius)
async def subscription_radius(callback: CallbackQuery, state: FSMContext):
    """Obuna radiusi"""
    radius = int(callback.data.split(":")[1])
    await state.update_data(radius_km=radius)

    await callback.message.edit_text(
        "💰 Minimal maosh miqdorini kiriting (so'mda):\n\n"
        "Agar maosh muhim bo'lmasa, 'yo'q' deb yozing:"
    )
    await state.set_state(SubscriptionForm.salary_from)


@subscription_router.message(SubscriptionForm.salary_from, F.text)
async def subscription_salary(message: Message, state: FSMContext):
    """Obuna maoshi"""
    salary_text = message.text.lower().strip()
    salary_from = None

    if salary_text not in ['yo\'q', 'yoq', 'yo\'q', 'kerak emas', 'muhim emas']:
        try:
            salary_from = int(''.join(filter(str.isdigit, salary_text)))
        except ValueError:
            salary_from = None

    data = await state.get_data()
    user = await db.get_or_create_user(message.from_user.id)

    # Obuna yaratish
    await db.create_subscription(
        user_id=user['id'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        radius_km=data['radius_km'],
        salary_from=salary_from
    )

    await state.clear()

    success_text = (
        "✅ <b>Obuna muvaffaqiyatli yaratildi!</b>\n\n"
        f"📏 Radius: {data['radius_km']} km\n"
    )

    if salary_from:
        success_text += f"💰 Minimal maosh: {salary_from:,} so'm\n"

    success_text += (
        "\n🔔 Endi yangi vakansiyalar haqida "
        "avtomatik xabar olasiz!"
    )

    await message.answer(success_text, reply_markup=main_menu_keyboard())


@subscription_router.callback_query(F.data == "edit_subscription")
async def edit_subscription(callback: CallbackQuery, state: FSMContext):
    """Obunani tahrirlash"""
    await callback.message.edit_text(
        "⚙️ Obunani yangilash uchun yangi parametrlarni kiriting.\n\n"
        "Yangi lokatsiyani yuboring:",
        reply_markup=request_location_keyboard()
    )
    await state.set_state(SubscriptionForm.location)


@subscription_router.callback_query(F.data == "delete_subscription")
async def delete_subscription_confirm(callback: CallbackQuery):
    """Obunani o'chirish tasdiqi"""
    await callback.message.edit_text(
        "❓ Obunani o'chirishni xohlaysizmi?\n\n"
        "Bu obunani o'chirgach, yangi vakansiyalar "
        "haqida xabar olmaysiz.",
        reply_markup=confirm_keyboard("delete_subscription", 0)
    )


@subscription_router.callback_query(F.data.startswith("confirm:delete_subscription"))
async def delete_subscription_confirmed(callback: CallbackQuery):
    """Obunani o'chirish tasdiqlandi"""
    user = await db.get_or_create_user(callback.from_user.id)

    # Obunani o'chirish
    async with db.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM subscriptions WHERE user_id = $1",
            user['id']
        )

    await callback.message.edit_text(
        "✅ Obuna muvaffaqiyatli o'chirildi!\n\n"
        "Kerak bo'lsa, yangi obuna yaratishingiz mumkin."
    )


@subscription_router.callback_query(F.data.startswith("cancel:delete_subscription"))
async def cancel_delete_subscription(callback: CallbackQuery):
    """Obunani o'chirishni bekor qilish"""
    await callback.message.edit_text(
        "❌ Obunani o'chirish bekor qilindi.",
        reply_markup=subscription_keyboard()
    )


@subscription_router.callback_query(F.data == "back_to_subscription")
async def back_to_subscription(callback: CallbackQuery, state: FSMContext):
    """Obuna menyusiga qaytish"""
    await state.clear()
    await my_subscriptions(callback.message)