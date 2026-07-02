from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from bot.db.database import async_session_maker
from bot.services.promo_service import activate_code, get_user_subscriptions, get_or_create_user

user_router = Router()


@user_router.message(Command("start"))
async def cmd_start(message: Message):
    async with async_session_maker() as session:
        await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    await message.answer(
        "Welcome to the Subscription Bot!\n\n"
        "This bot manages access to Telegram channels via promo codes.\n\n"
        "Commands:\n"
        "/code <code> - Activate a promo code\n"
        "/status - Check your subscription status\n"
        "/my_channels - List your channels\n"
        "/commands - List all commands\n"
        "/help - Show this message"
    )


@user_router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Subscription Bot - Help\n\n"
        "Use /code <promo_code> to activate a promo code.\n"
        "Use /status to check your current subscription status.\n"
        "Use /my_channels to see which channels you have access to.\n\n"
        "If you unsubscribe from a channel, you will be notified and "
        "your access will be revoked."
    )


@user_router.message(Command("commands"))
async def cmd_commands(message: Message):
    text = (
        "User commands:\n"
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/commands - List all commands\n"
        "/code <code> - Activate a promo code\n"
        "/status - Check subscription status\n"
        "/my_channels - List your channels\n\n"
        "Admin commands:\n"
        "/add_code <code> <ttl> <channels> - Create a promo code\n"
        "/codes - List all promo codes\n"
        "/revoke_code <code> - Deactivate a code\n"
        "/add_channel <code> <channel> - Add channel to code\n"
        "/admin_stats - View statistics\n"
        "/broadcast <message> - Send to all users"
    )
    await message.answer(text)


@user_router.message(Command("status"))
async def cmd_status(message: Message):
    async with async_session_maker() as session:
        subs = await get_user_subscriptions(session, message.from_user.id)
    if not subs:
        await message.answer("You have no active subscriptions. Use /code to activate a promo code.")
        return

    lines = ["Your subscriptions:"]
    for s in subs:
        status_icon = "✅" if s["is_active"] else "❌"
        lines.append(f"{status_icon} {s['channel']} (code: {s['code']})")
    await message.answer("\n".join(lines))


@user_router.message(Command("my_channels"))
async def cmd_my_channels(message: Message):
    async with async_session_maker() as session:
        subs = await get_user_subscriptions(session, message.from_user.id)
    active = [s for s in subs if s["is_active"]]

    if not active:
        await message.answer("You are not subscribed to any channels.")
        return

    lines = ["Channels you have access to:"]
    for s in active:
        lines.append(f"• {s['channel']}")
    await message.answer("\n".join(lines))


@user_router.message(Command("code"))
async def cmd_code(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /code <promo_code>")
        return

    code = args[1].strip()
    session = async_session_maker()
    async with session:
        success, msg = await activate_code(
            session,
            message.from_user.id,
            code,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    await message.answer(msg)
