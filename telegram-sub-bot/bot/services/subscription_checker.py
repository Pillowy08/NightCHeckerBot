from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import User, Subscription, Event


async def check_subscriptions(
    bot: Bot,
    session_maker: async_sessionmaker[AsyncSession],
    admin_ids: list[int],
):

    async with session_maker() as session:
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
                member = await bot.get_chat_member(
                    chat_id=sub.channel,
                    user_id=user.telegram_id,
                )
                if member.status in ("left", "kicked"):
                    sub.is_active = False

                    event = Event(
                        user_id=user.telegram_id,
                        event_type="unsubscribe",
                        description=f"Unsubscribed from {sub.channel}",
                    )
                    session.add(event)

                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"You have been unsubscribed from {sub.channel}. "
                        "Please re-subscribe to keep access.",
                    )

                    for admin_id in admin_ids:
                        try:
                            await bot.send_message(
                                chat_id=admin_id,
                                text=f"User {user.telegram_id} (@{user.username or 'N/A'}) "
                                f"unsubscribed from {sub.channel}.",
                            )
                        except Exception:
                            pass
            except Exception:
                pass

        await session.commit()
