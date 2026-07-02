import json
from datetime import datetime, timezone
from sqlalchemy import select, func

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command

from bot.db.database import async_session_maker
from bot.db.models import User, PromoCode, Subscription, Event
from bot.services.promo_service import create_promo_code

admin_router = Router()


@admin_router.message(Command("add_code"))
async def cmd_add_code(message: Message):
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer(
            "Usage: /add_code <code> <ttl> <channels>\n"
            "Example: /add_code PROMO2024 7d @channel1,@channel2\n"
            "TTL: m (minutes), h (hours), d (days), w (weeks)"
        )
        return

    _, code, ttl, channels_str = parts
    channels = [ch.strip() for ch in channels_str.split(",") if ch.strip()]

    if not channels:
        await message.answer("At least one channel is required.")
        return

    async with async_session_maker() as session:
        try:
            promo = await create_promo_code(session, code, ttl, channels)
            await message.answer(
                f"Code `{promo.code}` created!\n"
                f"Expires: {promo.expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"Channels: {', '.join(channels)}",
                parse_mode="Markdown",
            )
        except ValueError as e:
            await message.answer(str(e))


@admin_router.message(Command("codes"))
async def cmd_codes(message: Message):
    async with async_session_maker() as session:
        result = await session.execute(
            select(PromoCode).order_by(PromoCode.created_at.desc())
        )
        codes = result.scalars().all()

        if not codes:
            await message.answer("No promo codes found.")
            return

        lines = ["Promo codes:"]
        for c in codes:
            status = "✅" if c.is_active else "❌"
            expires = c.expires_at.strftime("%Y-%m-%d %H:%M")
            max_u = c.max_uses if c.max_uses else "∞"
            uses = f"{c.used_count}/{max_u}"
            chs = ", ".join(json.loads(c.channels))
            lines.append(
                f"{status} `{c.code}` | expires: {expires} | uses: {uses}\n"
                f"       channels: {chs}"
            )

        await message.answer("\n".join(lines), parse_mode="Markdown")


@admin_router.message(Command("revoke_code"))
async def cmd_revoke_code(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /revoke_code <code>")
        return

    code = parts[1].strip().upper()

    async with async_session_maker() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.code == code)
        )
        promo = result.scalar_one_or_none()

        if promo is None:
            await message.answer(f"Code `{code}` not found.", parse_mode="Markdown")
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

    await message.answer(f"Code `{code}` revoked and all related subscriptions deactivated.", parse_mode="Markdown")


@admin_router.message(Command("add_channel"))
async def cmd_add_channel(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /add_channel <code> <channel>")
        return

    _, code, channel = parts
    code = code.strip().upper()
    channel = channel.strip()

    async with async_session_maker() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.code == code)
        )
        promo = result.scalar_one_or_none()

        if promo is None:
            await message.answer(f"Code `{code}` not found.", parse_mode="Markdown")
            return

        channels = json.loads(promo.channels)
        if channel in channels:
            await message.answer(f"Channel {channel} already exists in code `{code}`.", parse_mode="Markdown")
            return

        channels.append(channel)
        promo.channels = json.dumps(channels)
        await session.commit()

    await message.answer(f"Channel {channel} added to code `{code}`.", parse_mode="Markdown")


@admin_router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    async with async_session_maker() as session:
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
        f"Statistics:\n"
        f"Users: {total_users}\n"
        f"Active subscriptions: {active_subs_count}\n"
        f"Active codes: {active_codes}/{total_codes}\n"
        f"Unsubscribes: {unsub_events}\n"
        f"Activations today: {activations_today}"
    )


@admin_router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /broadcast <message>")
        return

    broadcast_text = parts[1]

    async with async_session_maker() as session:
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

    await message.answer(f"Broadcast sent.\nDelivered: {sent}\nFailed: {failed}")
