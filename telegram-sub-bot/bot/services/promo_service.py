import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User, PromoCode, Subscription, Event


def parse_ttl(ttl: str) -> timedelta:
    unit = ttl[-1]
    value = int(ttl[:-1])
    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    else:
        raise ValueError(f"Unknown TTL unit: {unit}")


async def create_promo_code(
    session: AsyncSession,
    code: str,
    ttl: str,
    channels: list[str],
    max_uses: int | None = None,
) -> PromoCode:
    expires_at = datetime.now(timezone.utc) + parse_ttl(ttl)
    promo = PromoCode(
        code=code.upper(),
        expires_at=expires_at,
        channels=json.dumps(channels),
        max_uses=max_uses,
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def activate_code(
    session: AsyncSession,
    telegram_id: int,
    code: str,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> tuple[bool, str]:
    result = await session.execute(
        select(PromoCode).where(PromoCode.code == code.upper())
    )
    promo = result.scalar_one_or_none()

    if promo is None:
        return False, "Code not found."

    if not promo.is_active:
        return False, "This code is no longer active."

    if promo.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return False, "This code has expired."

    if promo.max_uses is not None and promo.used_count >= promo.max_uses:
        return False, "This code has reached its usage limit."

    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        session.add(user)
        await session.flush()
    else:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name

    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.promo_code_id == promo.id,
            Subscription.is_active == True,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return False, "You already have this code activated."

    channels = json.loads(promo.channels)
    for channel in channels:
        sub = Subscription(
            user_id=user.id,
            promo_code_id=promo.id,
            channel=channel.strip(),
        )
        session.add(sub)

    promo.used_count += 1

    event = Event(
        user_id=telegram_id,
        event_type="code_activated",
        description=f"Activated code {code.upper()}, channels: {', '.join(channels)}",
    )
    session.add(event)

    await session.commit()
    return True, f"Code activated! You are now subscribed to:\n" + "\n".join(f"• {ch}" for ch in channels)


async def get_user_subscriptions(session: AsyncSession, telegram_id: int) -> list[dict]:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return []

    result = await session.execute(
        select(Subscription, PromoCode)
        .join(PromoCode, Subscription.promo_code_id == PromoCode.id)
        .where(Subscription.user_id == user.id)
    )
    subs = []
    for sub, promo in result.all():
        subs.append({
            "channel": sub.channel,
            "is_active": sub.is_active,
            "code": promo.code,
            "created_at": sub.created_at,
        })
    return subs


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user
