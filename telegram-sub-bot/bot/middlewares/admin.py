from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class AdminMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: list[int]):
        self.admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            if event.from_user.id not in self.admin_ids:
                await event.answer("Access denied. You are not an admin.")
                return
        return await handler(event, data)
