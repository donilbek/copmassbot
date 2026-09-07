from aiogram import Router
from aiogram.types import Message

from handlers.common import main_menu_kb
from validators import ERR_FREE_TEXT_MENU

router = Router()


@router.message()
async def unhandled_message(message: Message):
    """Любой текст в главном меню, который бот не понял."""
    await message.answer(ERR_FREE_TEXT_MENU, reply_markup=main_menu_kb())
