from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database import get_my_responses, get_user
from validators import ERR_NO_PROFILE

router = Router()

STATUS_LABELS = {
    "pending": "⏳ На рассмотрении",
    "accepted": "✅ Принято (мэтч)",
    "rejected": "❌ Отклонено",
}

MENU_BUTTONS = [
    "🔍 Ищу команду",
    "📢 Ищу человека в проект",
    "👤 Мой профиль",
    "🔴 Редактировать профиль",
    "📁 Мои отклики",
]

# Поля, без которых анкета считается незаполненной
REQUIRED_PROFILE_FIELDS = (
    "full_name",
    "university",
    "role",
    "stack",
    "format",
    "socials",
    "phone",
)


def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Ищу команду")],
            [KeyboardButton(text="📢 Ищу человека в проект")],
            [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="🔴 Редактировать профиль")],
            [KeyboardButton(text="📁 Мои отклики")],
        ],
        resize_keyboard=True,
    )


def fill_profile_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Заполнить анкету", callback_data="profile:start")]
        ]
    )


def profile_is_complete(user) -> bool:
    if not user:
        return False
    for field in REQUIRED_PROFILE_FIELDS:
        try:
            value = user[field]
        except (KeyError, IndexError):
            return False
        if not value or not str(value).strip():
            return False
    return True


async def ensure_profile(message: Message, user_id: int | None = None) -> bool:
    """Проверяет, заполнена ли анкета. Если нет — пишет подсказку и возвращает False.

    При вызове из callback передавай user_id=callback.from_user.id:
    у callback.message.from_user стоит сам бот.
    """
    user = await get_user(user_id if user_id is not None else message.from_user.id)
    if profile_is_complete(user):
        return True
    await message.answer(ERR_NO_PROFILE, reply_markup=fill_profile_kb())
    return False


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я помогу тебе найти команду для проекта или собрать участников в свой проект.\n\n"
        "Чтобы начать, укажи свою основную роль и заполни краткую анкету: /profile",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Сейчас нечего прерывать 🙂", reply_markup=main_menu_kb())
        return
    await state.clear()
    await message.answer("Ок, прервал. Ты в главном меню 👇", reply_markup=main_menu_kb())


@router.message(~StateFilter(None), F.text.in_(MENU_BUTTONS))
async def menu_button_during_form(message: Message, state: FSMContext):
    """Пользователь нажал кнопку меню, не завершив анкету/создание проекта."""
    await state.clear()
    await message.answer(
        "Текущий шаг прерван. Нажми нужную кнопку меню ещё раз 👇",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/profile — создать или отредактировать анкету\n"
        "/bookmarks — посмотреть закладки\n"
        "/reviews — посмотреть отзывы о себе\n"
        "/pause — скрыть свою анкету\n"
        "/resume — снова показывать анкету\n"
        "/cancel — прервать текущий шаг и вернуться в меню\n"
    )


@router.message(F.text == "📁 Мои отклики")
async def my_responses(message: Message):
    responses = await get_my_responses(message.from_user.id)
    if not responses:
        await message.answer("У тебя пока нет откликов. Загляни в «🔍 Ищу команду»!")
        return

    lines = []
    for r in responses:
        status = STATUS_LABELS.get(r["status"], r["status"])
        lines.append(f"• {r['project_title']} — {status}")

    await message.answer("📁 Твои отклики:\n\n" + "\n".join(lines))
