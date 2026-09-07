from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from validators import FALLBACK_MESSAGES, get_content_issue


class ContentGuardMiddleware(BaseMiddleware):
    """Отсекает голосовые, стикеры, файлы, контакты и т.п. до всех хендлеров.

    Регистрируется как outer-middleware, поэтому срабатывает раньше фильтров:
    в любом состоянии FSM и в главном меню пользователь получит понятную подсказку,
    а не молчание бота.
    """

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        issue = get_content_issue(event)
        if issue:
            await event.answer(FALLBACK_MESSAGES[issue])
            return None
        return await handler(event, data)
