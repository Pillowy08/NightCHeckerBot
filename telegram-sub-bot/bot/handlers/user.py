import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.config import Config
from bot.db.database import get_session_maker
from bot.services.promo_service import activate_code, get_user_subscriptions, get_or_create_user
from bot.utils.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)
user_router = Router()


async def safe_send(message: Message, text: str, **kwargs):
    try:
        await message.answer(text, **kwargs)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")


@user_router.message(Command("start"))
async def cmd_start(message: Message):
    try:
        maker = get_session_maker()
        async with maker() as session:
            await get_or_create_user(
                session,
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name,
            )
        is_admin = message.from_user.id in Config.ADMIN_IDS
        await safe_send(
            message,
            "👋 Добро пожаловать!\n\n"
            "Этот бот управляет доступом к Telegram-каналам через промокоды.\n"
            "Используй кнопки ниже или команды.",
            reply_markup=main_menu_keyboard(is_admin),
        )
    except Exception as e:
        logger.error(f"Error in /start: {e}", exc_info=True)
        await safe_send(message, "❌ Ошибка при запуске. Попробуй ещё раз.")


@user_router.message(Command("help"))
async def cmd_help(message: Message):
    await safe_send(
        message,
        "ℹ️ <b>Как пользоваться ботом</b>\n\n"
        "1. Получи промокод у администратора\n"
        "2. Нажми «🔑 Ввести код» или отправь /code <код>\n"
        "3. После активации ты получишь доступ к каналам\n\n"
        "Бот ежечасно проверяет, не отписался ли ты от каналов.\n"
        "Если отпишешься — доступ будет отключён.",
        parse_mode="HTML",
    )


@user_router.message(Command("commands"))
async def cmd_commands(message: Message):
    await safe_send(
        message,
        "📋 <b>Команды пользователя:</b>\n"
        "/start — запустить бота\n"
        "/help — помощь\n"
        "/commands — список команд\n"
        "/code <код> — активировать промокод\n"
        "/status — статус подписок\n"
        "/my_channels — мои каналы\n\n"
        "<b>Команды администратора:</b>\n"
        "/add_code <код> <ttl> <каналы> — создать код\n"
        "/codes — список кодов\n"
        "/revoke_code <код> — отозвать код\n"
        "/add_channel <код> <канал> — добавить канал\n"
        "/admin_stats — статистика\n"
        "/broadcast <код> <сообщение> — рассылка по коду",
        parse_mode="HTML",
    )


@user_router.message(Command("status"))
async def cmd_status(message: Message):
    try:
        maker = get_session_maker()
        async with maker() as session:
            subs = await get_user_subscriptions(session, message.from_user.id)
        if not subs:
            await safe_send(
                message,
                "❌ У тебя нет активных подписок.\n"
                "Используй /code или нажми «🔑 Ввести код», чтобы активировать промокод.",
            )
            return

        lines = ["📊 <b>Твои подписки:</b>"]
        for s in subs:
            icon = "✅" if s["is_active"] else "❌"
            lines.append(f"{icon} {s['channel']} (код: {s['code']})")
        await safe_send(message, "\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in /status: {e}", exc_info=True)
        await safe_send(message, "❌ Ошибка при получении статуса.")


@user_router.message(Command("my_channels"))
async def cmd_my_channels(message: Message):
    try:
        maker = get_session_maker()
        async with maker() as session:
            subs = await get_user_subscriptions(session, message.from_user.id)
        active = [s for s in subs if s["is_active"]]

        if not active:
            await safe_send(message, "❌ Ты не подписан ни на один канал.")
            return

        lines = ["📋 <b>Твои каналы:</b>"]
        for s in active:
            lines.append(f"• {s['channel']}")
        await safe_send(message, "\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in /my_channels: {e}", exc_info=True)
        await safe_send(message, "❌ Ошибка при получении каналов.")


@user_router.message(Command("code"))
async def cmd_code(message: Message):
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await safe_send(
                message,
                "🔑 <b>Использование:</b> /code <промокод>\n"
                "Пример: /code PROMO2024",
                parse_mode="HTML",
            )
            return

        code = args[1].strip()
        maker = get_session_maker()
        async with maker() as session:
            _, msg = await activate_code(
                session,
                message.from_user.id,
                code,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name,
            )
        await safe_send(message, msg)
    except Exception as e:
        logger.error(f"Error in /code: {e}", exc_info=True)
        await safe_send(message, "❌ Ошибка при активации кода.")


@user_router.message(F.text == "📋 Мои каналы")
async def btn_my_channels(message: Message):
    await cmd_my_channels(message)


@user_router.message(F.text == "✅ Статус")
async def btn_status(message: Message):
    await cmd_status(message)


@user_router.message(F.text == "🔑 Ввести код")
async def btn_enter_code(message: Message):
    await safe_send(
        message,
        "🔑 Отправь промокод командой:\n"
        "<code>/code ТВОЙ_КОД</code>\n\n"
        "Например: <code>/code PROMO2024</code>",
        parse_mode="HTML",
    )


@user_router.message(F.text == "❓ Помощь")
async def btn_help(message: Message):
    await cmd_help(message)


@user_router.message(F.text == "📞 Администрация")
async def btn_admin_contact(message: Message):
    contact = Config.ADMIN_CONTACT
    await safe_send(
        message,
        f"📞 <b>Связь с администрацией</b>\n\n"
        f"По всем вопросам пишите:\n{contact}\n\n"
        f"Если у вас есть промокод — используй /code для активации.\n"
        f"Если возникли проблемы — напишите администратору.",
        parse_mode="HTML",
    )
