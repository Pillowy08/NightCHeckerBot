from aiogram import Bot
from sqlalchemy import select

from bot.db.database import get_session_maker
from bot.db.models import User, Subscription, Event


async def check_subscriptions(
    bot: Bot,
    admin_ids: list[int],
):

    maker = get_session_maker()
    async with maker() as session:
        result = await session.execute(
            select(Subscription)
            .where(Subscription.is_active == True)
        )
        subscriptions = result.scalars().all()

        for sub in subscriptions:
            result = await session.execute(
                select(User).where(User.id == sub.user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                continue

            try:
                chat_target = sub.check_id if sub.check_id else sub.channel
                member = await bot.get_chat_member(
                    chat_id=chat_target,
                    user_id=user.telegram_id,
                )
                if member.status in ("left", "kicked"):
                    sub.is_active = False

                    event = Event(
                        user_id=user.telegram_id,
                        event_type="unsubscribe",
                        description=f"Отписка от {sub.channel}",
                    )
                    session.add(event)

                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"❌ Ты отписался от канала {sub.channel}.\n"
                        "Доступ отключён. Подпишись снова, чтобы восстановить доступ.",
                    )

                    for admin_id in admin_ids:
                        try:
                            await bot.send_message(
                                chat_id=admin_id,
                                text=f"⚠️ Пользователь {user.telegram_id} (@{user.username or 'N/A'}) "
                                f"отписался от канала {sub.channel}.",
                            )
                        except Exception:
                            pass
            except Exception:
                pass

        await session.commit()
