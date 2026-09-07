from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from states import ProfileForm
from database import upsert_user, get_user, get_reviews_for_user
from validators import (
    ERR_FULL_NAME,
    ERR_UNIVERSITY,
    ERR_ROLE_BUTTONS,
    ERR_STACK,
    ERR_FORMAT,
    ERR_SOCIALS,
    ERR_PHONE,
    ERR_STATUS_BUTTONS,
    valid_full_name,
    valid_university,
    valid_stack,
    valid_format,
    valid_socials,
    valid_phone,
    valid_manual_field,
)

router = Router()

ROLES = [
    "Тимлид",
    "Бэкендер",
    "Фронтендер",
    "Мобайл-дев",
    "Дизайнер",
    "Тестировщик",
    "Другое",
]

ASK_FULL_NAME = "Как тебя зовут? Укажи Фамилию и Имя:"
ASK_UNIVERSITY = "В каком вузе учишься и на каком курсе? (например: УрФУ, 3 курс)"
ASK_ROLE = "Выбери свою роль:"
ASK_ROLE_CUSTOM = "Напиши свою роль:"
ASK_STACK = "Какой стек/навыки используешь? (например: Python, aiogram, Docker)"
ASK_FORMAT = "В каком формате готов участвовать? (например: Хакатон, Пет-проект, Full-time стартап)"
ASK_STATUS = "Какой у тебя статус поиска?"
ASK_SOCIALS = "Скинь ссылки на свои соц сети (Telegram, VK, GitHub):"
ASK_PHONE = "Укажи номер телефона для связи (например: +7 999 111 22 33):"
ASK_PROJECTS = "Расскажи о своих проектах (или напиши «нет»):"


def role_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🟢{role}", callback_data=f"role:{role}")]
            for role in ROLES
        ]
    )


def status_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢В активном поиске команды", callback_data="status:active")],
            [InlineKeyboardButton(text="🔴Приостановить поиск", callback_data="status:paused")],
        ]
    )


def _field(user, name, default="не указано"):
    try:
        value = user[name]
    except (KeyError, IndexError):
        return default
    return value if value else default


def format_profile_card(user, review_count: int = 0) -> str:
    status_text = "🟢 В активном поиске" if user["is_active"] else "🔴 Приостановлен"
    projects_raw = _field(user, "projects", "")
    projects = projects_raw if projects_raw and projects_raw.lower() != "нет" else "не указано"
    reviews_line = f"{review_count} отзыв(ов) — посмотреть: /reviews" if review_count else "пока нет"
    return (
        "👤 Твоя карточка соискателя:\n"
        f"• ФИО: {_field(user, 'full_name')}\n"
        f"• Вуз: {_field(user, 'university')}\n"
        f"• Роль: {_field(user, 'role')}\n"
        f"• Стек: {_field(user, 'stack')}\n"
        f"• Формат: {_field(user, 'format')}\n"
        f"• Статус: {status_text}\n"
        f"• Мои соц сети: {_field(user, 'socials')}\n"
        f"• Номер телефона: {_field(user, 'phone')}\n"
        f"• Мои проекты: {projects}\n"
        f"• Отзывы: {reviews_line}\n"
        "• Закладки: посмотреть можно командой /bookmarks"
    )


async def build_profile_card(user) -> str:
    reviews = await get_reviews_for_user(user["user_id"])
    return format_profile_card(user, review_count=len(reviews))


async def start_profile_form(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ProfileForm.entering_full_name)
    await message.answer(ASK_FULL_NAME)


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext):
    await start_profile_form(message, state)


@router.message(F.text == "🔴 Редактировать профиль")
async def edit_profile_button(message: Message, state: FSMContext):
    await start_profile_form(message, state)


@router.callback_query(F.data == "profile:start")
async def start_profile_from_button(callback: CallbackQuery, state: FSMContext):
    await start_profile_form(callback.message, state)
    await callback.answer()


@router.message(F.text == "👤 Мой профиль")
async def show_profile_button(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("У тебя ещё нет анкеты. Создай её: /profile")
        return
    await message.answer(await build_profile_card(user))


# ---------------------------------------------------------------------------
# Шаги анкеты
# ---------------------------------------------------------------------------

@router.message(ProfileForm.entering_full_name)
async def process_full_name(message: Message, state: FSMContext):
    if not valid_full_name(message.text):
        await message.answer(ERR_FULL_NAME)
        return
    await state.update_data(full_name=" ".join(message.text.split()))
    await state.set_state(ProfileForm.entering_university)
    await message.answer(ASK_UNIVERSITY)


@router.message(ProfileForm.entering_university)
async def process_university(message: Message, state: FSMContext):
    if not valid_university(message.text):
        await message.answer(ERR_UNIVERSITY)
        return
    await state.update_data(university=message.text.strip())
    await state.set_state(ProfileForm.choosing_role)
    await message.answer(ASK_ROLE, reply_markup=role_kb())


@router.callback_query(ProfileForm.choosing_role, F.data.startswith("role:"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":", 1)[1]
    if role == "Другое":
        await state.set_state(ProfileForm.entering_role_custom)
        await callback.message.answer(ASK_ROLE_CUSTOM)
    else:
        await state.update_data(role=role)
        await state.set_state(ProfileForm.entering_stack)
        await callback.message.answer(ASK_STACK)
    await callback.answer()


@router.message(ProfileForm.choosing_role)
async def role_text_instead_of_button(message: Message):
    """Пользователь написал роль текстом или прислал эмодзи вместо клика по кнопке."""
    await message.answer(ERR_ROLE_BUTTONS, reply_markup=role_kb())


@router.message(ProfileForm.entering_role_custom)
async def process_role_custom(message: Message, state: FSMContext):
    if not valid_manual_field(message.text):
        await message.answer(ERR_ROLE_BUTTONS, reply_markup=role_kb())
        return
    await state.update_data(role=message.text.strip())
    await state.set_state(ProfileForm.entering_stack)
    await message.answer(ASK_STACK)


@router.message(ProfileForm.entering_stack)
async def process_stack(message: Message, state: FSMContext):
    if not valid_stack(message.text):
        await message.answer(ERR_STACK)
        return
    await state.update_data(stack=message.text.strip())
    await state.set_state(ProfileForm.entering_format)
    await message.answer(ASK_FORMAT)


@router.message(ProfileForm.entering_format)
async def process_format(message: Message, state: FSMContext):
    if not valid_format(message.text):
        await message.answer(ERR_FORMAT)
        return
    await state.update_data(format=message.text.strip())
    await state.set_state(ProfileForm.choosing_status)
    await message.answer(ASK_STATUS, reply_markup=status_kb())


@router.callback_query(ProfileForm.choosing_status, F.data.startswith("status:"))
async def process_status(callback: CallbackQuery, state: FSMContext):
    status = callback.data.split(":", 1)[1]
    await state.update_data(is_active=1 if status == "active" else 0)
    await state.set_state(ProfileForm.entering_socials)
    await callback.message.answer(ASK_SOCIALS)
    await callback.answer()


@router.message(ProfileForm.choosing_status)
async def status_text_instead_of_button(message: Message):
    await message.answer(ERR_STATUS_BUTTONS, reply_markup=status_kb())


@router.message(ProfileForm.entering_socials)
async def process_socials(message: Message, state: FSMContext):
    if not valid_socials(message.text):
        await message.answer(ERR_SOCIALS)
        return
    await state.update_data(socials=message.text.strip())
    await state.set_state(ProfileForm.entering_phone)
    await message.answer(ASK_PHONE)


@router.message(ProfileForm.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    if not valid_phone(message.text):
        await message.answer(ERR_PHONE)
        return
    await state.update_data(phone=message.text.strip())
    await state.set_state(ProfileForm.entering_projects)
    await message.answer(ASK_PROJECTS)


@router.message(ProfileForm.entering_projects)
async def process_projects(message: Message, state: FSMContext):
    data = await state.get_data()
    data["projects"] = message.text.strip()

    await upsert_user(
        message.from_user.id,
        message.from_user.username or "",
        full_name=data["full_name"],
        university=data["university"],
        role=data["role"],
        stack=data["stack"],
        format=data["format"],
        is_active=data["is_active"],
        socials=data["socials"],
        phone=data["phone"],
        projects=data["projects"],
    )

    await state.clear()
    user = await get_user(message.from_user.id)
    await message.answer("Анкета сохранена ✅\n\n" + await build_profile_card(user))


@router.message(Command("pause"))
async def cmd_pause(message: Message):
    from database import set_active
    await set_active(message.from_user.id, False)
    await message.answer("Твоя анкета скрыта. Включить обратно: /resume")


@router.message(Command("resume"))
async def cmd_resume(message: Message):
    from database import set_active
    await set_active(message.from_user.id, True)
    await message.answer("Твоя анкета снова видна другим.")
