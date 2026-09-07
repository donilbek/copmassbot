from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import add_like, mark_seen, get_user
from handlers.browse import send_next_card

router = Router()


@router.callback_query(F.data.startswith("like:"))
async def process_like(callback: CallbackQuery):
    from_id = callback.from_user.id
    to_id = int(callback.data.split(":")[1])

    await mark_seen(from_id, to_id)
    is_mutual = await add_like(from_id, to_id)

    await callback.answer("Отклик отправлен ✅")

    if is_mutual:
        me = await get_user(from_id)
        other = await get_user(to_id)

        me_username = f"@{me['username']}" if me["username"] else f"id{me['user_id']}"
        other_username = f"@{other['username']}" if other["username"] else f"id{other['user_id']}"

        await callback.bot.send_message(
            from_id,
            f"🎉 Взаимное совпадение! Контакт: {other_username}",
        )
        await callback.bot.send_message(
            to_id,
            f"🎉 Взаимное совпадение! Контакт: {me_username}",
        )
    else:
        # Уведомляем того, кому пришёл отклик, что есть новая карточка на рассмотрение
        try:
            await callback.bot.send_message(
                to_id,
                "У тебя новый отклик на анкету! Посмотри через /browse (раздел откликов можно добавить отдельно).",
            )
        except Exception:
            pass  # пользователь мог заблокировать бота

    await send_next_card(callback, from_id)
