import json
from datetime import datetime, timezone
from sqlalchemy import select, func

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from bot.db.database import get_session_maker
from bot.db.models import User, PromoCode, Subscription, Event
from bot.services.promo_service import create_promo_code
from bot.utils.helpers import parse_channel_input
from bot.utils.keyboards import admin_panel_keyboard, main_menu_keyboard

admin_router = Router()


@admin_router.message(F.text == "⚙️ Админ панель")
async def cmd_admin_panel(message: Message):
    await message.answer(
        "⚙️ <b>Панель администратора</b>\n\n"
        "Выбери действие:",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard(),
    )


@admin_router.message(Command("add_code"))
async def cmd_add_code(message: Message):
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer(
            "❌ <b>Использование:</b>\n"
            "<code>/add_code КОД TTL КАНАЛЫ</code>\n\n"
            "Пример: <code>/add_code PROMO7 7d https://t.me/channel1,https://t.me/channel2</code>\n"
            "Можно также @username\n"
            "TTL: <code>30m</code> (мин), <code>24h</code> (ч), <code>7d</code> (д), <code>2w</code> (нед)",
            parse_mode="HTML",
        )
        return

    _, code, ttl, channels_str = parts
    channels = [ch.strip() for ch in channels_str.split(",") if ch.strip()]

    if not channels:
        await message.answer("❌ Укажи хотя бы один канал.")
        return

    maker = get_session_maker()
    async with maker() as session:
        try:
            promo = await create_promo_code(session, code, ttl, channels)
            raw = json.loads(promo.channels)
            display_list = ", ".join(ch.get("display", ch) for ch in raw)
            await message.answer(
                f"✅ Код <code>{promo.code}</code> создан!\n"
                f"Истекает: {promo.expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"Каналы: {display_list}",
                parse_mode="HTML",
            )
        except ValueError as e:
            await message.answer(f"❌ {e}")


@admin_router.message(Command("codes"))
async def cmd_codes(message: Message):
    maker = get_session_maker()
    async with maker() as session:
        result = await session.execute(
            select(PromoCode).order_by(PromoCode.created_at.desc())
        )
        codes = result.scalars().all()

        if not codes:
            await message.answer("📄 Нет созданных промокодов.")
            return

        lines = ["📄 <b>Промокоды:</b>"]
        for c in codes:
            status = "✅" if c.is_active else "❌"
            expires = c.expires_at.strftime("%Y-%m-%d %H:%M")
            max_u = c.max_uses if c.max_uses else "∞"
            uses = f"{c.used_count}/{max_u}"
            raw = json.loads(c.channels)
            chs = ", ".join(ch.get("display", ch) for ch in raw)
            lines.append(
                f"{status} <code>{c.code}</code> | до {expires} | {uses}\n"
                f"       каналы: {chs}"
            )

        await message.answer("\n".join(lines), parse_mode="HTML")


@admin_router.message(Command("revoke_code"))
async def cmd_revoke_code(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ <b>Использование:</b> /revoke_code <код>", parse_mode="HTML")
        return

    code = parts[1].strip().upper()

    maker = get_session_maker()
    async with maker() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.code == code)
        )
        promo = result.scalar_one_or_none()

        if promo is None:
            await message.answer(f"❌ Код <code>{code}</code> не найден.", parse_mode="HTML")
            return

        promo.is_active = False

        sub_result = await session.execute(
            select(Subscription).where(
                Subscription.promo_code_id == promo.id,
                Subscription.is_active == True,
            )
        )
        for sub in sub_result.scalars().all():
            sub.is_active = False

        session.add(
            Event(
                event_type="code_revoked",
                description=f"Code {code} revoked by admin",
            )
        )
        await session.commit()

    await message.answer(
        f"✅ Код <code>{code}</code> отозван. Все связанные подписки деактивированы.",
        parse_mode="HTML",
    )


@admin_router.message(Command("add_channel"))
async def cmd_add_channel(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "❌ <b>Использование:</b> /add_channel <код> <канал>\n"
            "Пример: /add_channel PROMO7 https://t.me/newchannel",
            parse_mode="HTML",
        )
        return

    _, code, channel = parts
    code = code.strip().upper()
    channel = channel.strip()

    maker = get_session_maker()
    async with maker() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.code == code)
        )
        promo = result.scalar_one_or_none()

        if promo is None:
            await message.answer(f"❌ Код <code>{code}</code> не найден.", parse_mode="HTML")
            return

        channels = json.loads(promo.channels)
        display, check = parse_channel_input(channel)
        existing_displays = [ch.get("display", ch) for ch in channels]
        if display in existing_displays:
            await message.answer(
                f"⚠️ Канал {display} уже есть в коде <code>{code}</code>.",
                parse_mode="HTML",
            )
            return

        channels.append({"display": display, "check": check})
        promo.channels = json.dumps(channels)
        await session.commit()

    await message.answer(
        f"✅ Канал {display} добавлен к коду <code>{code}</code>.",
        parse_mode="HTML",
    )


@admin_router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    maker = get_session_maker()
    async with maker() as session:
        total_users = (
            await session.execute(select(func.count(User.id)))
        ).scalar()

        active_subs_count = (
            await session.execute(
                select(func.count(Subscription.id)).where(Subscription.is_active == True)
            )
        ).scalar()

        active_codes = (
            await session.execute(
                select(func.count(PromoCode.id)).where(PromoCode.is_active == True)
            )
        ).scalar()

        total_codes = (
            await session.execute(select(func.count(PromoCode.id)))
        ).scalar()

        unsub_events = (
            await session.execute(
                select(func.count(Event.id)).where(Event.event_type == "unsubscribe")
            )
        ).scalar()

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        activations_today = (
            await session.execute(
                select(func.count(Event.id)).where(
                    Event.event_type == "code_activated",
                    func.date(Event.created_at) == today,
                )
            )
        ).scalar()

    await message.answer(
        f"📊 <b>Статистика:</b>\n"
        f"👥 Пользователей: {total_users}\n"
        f"✅ Активных подписок: {active_subs_count}\n"
        f"🔑 Активных кодов: {active_codes}/{total_codes}\n"
        f"❌ Отписок: {unsub_events}\n"
        f"📈 Активаций сегодня: {activations_today}",
        parse_mode="HTML",
    )


@admin_router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ <b>Использование:</b> /broadcast <сообщение>",
            parse_mode="HTML",
        )
        return

    broadcast_text = parts[1]

    maker = get_session_maker()
    async with maker() as session:
        result = await session.execute(select(User.telegram_id))
        user_ids = [row[0] for row in result.all()]

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=broadcast_text)
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📢 Рассылка завершена.\nДоставлено: {sent}\nНе доставлено: {failed}"
    )


@admin_router.callback_query(F.data.startswith("admin:"))
async def cq_admin_panel(callback: CallbackQuery):
    action = callback.data.split(":", 1)[1]

    if action == "back":
        await callback.message.delete()
        await callback.message.answer(
            "👋 Возвращаюсь в главное меню.",
            reply_markup=main_menu_keyboard(is_admin=True),
        )
        await callback.answer()
        return

    if action == "add_code":
        await callback.message.answer(
            "➕ <b>Создание промокода</b>\n\n"
            "Отправь команду:\n"
            "<code>/add_code КОД TTL КАНАЛЫ</code>\n\n"
            "Пример: <code>/add_code PROMO7 7d https://t.me/channel1,https://t.me/channel2</code>\n"
            "Можно также @username\n"
            "TTL: <code>30m</code> (мин), <code>24h</code> (ч), <code>7d</code> (д), <code>2w</code> (нед)",
            parse_mode="HTML",
        )
    elif action == "codes":
        await cmd_codes(callback.message)
    elif action == "revoke_code":
        await callback.message.answer(
            "❌ <b>Отзыв кода</b>\n\n"
            "Отправь команду:\n<code>/revoke_code КОД</code>",
            parse_mode="HTML",
        )
    elif action == "add_channel":
        await callback.message.answer(
            "➕ <b>Добавление канала к коду</b>\n\n"
            "Отправь команду:\n<code>/add_channel КОД КАНАЛ</code>\n\n"
            "Пример: <code>/add_channel PROMO7 https://t.me/newchannel</code>",
            parse_mode="HTML",
        )
    elif action == "stats":
        await cmd_admin_stats(callback.message)
    elif action == "broadcast":
        await callback.message.answer(
            "📢 <b>Рассылка</b>\n\n"
            "Отправь команду:\n<code>/broadcast ТЕКСТ_СООБЩЕНИЯ</code>",
            parse_mode="HTML",
        )

    await callback.answer()
