from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from states import ProjectForm
from database import create_project, get_user_projects, get_bookmarks
from handlers.profile import ROLES
from handlers.common import ensure_profile
from validators import (
    ERR_PROJECT_TITLE,
    ERR_PROJECT_DESCRIPTION,
    ERR_PROJECT_DESCRIPTION_LONG,
    ERR_PROJECT_ROLES_BUTTONS,
    ERR_MANUAL_FIELD,
    valid_project_title,
    project_description_issue,
    valid_manual_field,
)

router = Router()

ASK_TITLE = "Название проекта:"
ASK_DESCRIPTION = "Краткое описание проекта (1-3 предложения):"
ASK_ROLES = "Кто требуется в проект? Выбери одну или несколько ролей:"
ASK_TOPIC = "Тематика проекта (например: EdTech, AI, Финтех, Геймдев):"
ASK_STAGE = "На какой стадии проект? (например: Идея / Прототип / Готовимся к хакатону):"
ASK_FORMAT = "Формат участия? (например: Пет-проект 5-10 ч/нед / Спринт на выходные):"


def project_entry_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать проект", callback_data="proj:new")],
            [InlineKeyboardButton(text="📋 Мои опубликованные проекты", callback_data="proj:mine")],
        ]
    )


def roles_kb(selected: list[str]):
    buttons = []
    for role in ROLES:
        prefix = "✅ " if role in selected else "🟢"
        buttons.append([InlineKeyboardButton(text=f"{prefix}{role}", callback_data=f"prole:{role}")])
    buttons.append([InlineKeyboardButton(text="Готово, сохранить роли ➡️", callback_data="prole_done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_project_card(project) -> str:
    return (
        f"Название: {project['title']}\n"
        f"Тематика: {project['topic']}\n"
        f"Стадия: {project['stage']}\n"
        f"Формат: {project['format']}\n"
        f"Кого ищут: {project['roles']}\n"
        f"О проекте: {project['description']}"
    )


@router.message(F.text == "📢 Ищу человека в проект")
async def project_menu(message: Message):
    if not await ensure_profile(message):
        return
    projects = await get_user_projects(message.from_user.id)
    if projects:
        text = "Твои проекты уже опубликованы. Можно создать ещё один или посмотреть текущие."
    else:
        text = "У тебя пока нет активных проектов. Создай карточку, чтобы участники могли откликаться."
    await message.answer(text, reply_markup=project_entry_kb())


@router.callback_query(F.data == "proj:new")
async def start_project_creation(callback: CallbackQuery, state: FSMContext):
    if not await ensure_profile(callback.message, callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await state.set_state(ProjectForm.entering_title)
    await callback.message.answer(ASK_TITLE)
    await callback.answer()


@router.message(ProjectForm.entering_title)
async def process_title(message: Message, state: FSMContext):
    if not valid_project_title(message.text):
        await message.answer(ERR_PROJECT_TITLE)
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(ProjectForm.entering_description)
    await message.answer(ASK_DESCRIPTION)


@router.message(ProjectForm.entering_description)
async def process_description(message: Message, state: FSMContext):
    issue = project_description_issue(message.text)
    if issue == "long":
        await message.answer(ERR_PROJECT_DESCRIPTION_LONG)
        return
    if issue:
        await message.answer(ERR_PROJECT_DESCRIPTION)
        return
    await state.update_data(description=message.text.strip(), selected_roles=[])
    await state.set_state(ProjectForm.choosing_roles)
    await message.answer(ASK_ROLES, reply_markup=roles_kb([]))


@router.callback_query(ProjectForm.choosing_roles, F.data.startswith("prole:"))
async def toggle_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":", 1)[1]

    if role == "Другое":
        await state.set_state(ProjectForm.entering_role_custom)
        await callback.message.answer("Напиши нужную роль текстом:")
        await callback.answer()
        return

    data = await state.get_data()
    selected = data.get("selected_roles", [])
    if role in selected:
        selected.remove(role)
    else:
        selected.append(role)
    await state.update_data(selected_roles=selected)

    await callback.message.edit_reply_markup(reply_markup=roles_kb(selected))
    await callback.answer()


@router.message(ProjectForm.choosing_roles)
async def roles_text_instead_of_buttons(message: Message, state: FSMContext):
    """Пользователь пишет роли текстом вместо выбора инлайн-кнопками."""
    data = await state.get_data()
    await message.answer(
        ERR_PROJECT_ROLES_BUTTONS,
        reply_markup=roles_kb(data.get("selected_roles", [])),
    )


@router.message(ProjectForm.entering_role_custom)
async def process_custom_role(message: Message, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_roles", [])

    if not valid_manual_field(message.text):
        await state.set_state(ProjectForm.choosing_roles)
        await message.answer(ERR_PROJECT_ROLES_BUTTONS, reply_markup=roles_kb(selected))
        return

    role = message.text.strip()
    if role not in selected:
        selected.append(role)
    await state.update_data(selected_roles=selected)
    await state.set_state(ProjectForm.choosing_roles)
    await message.answer(
        "Роль добавлена. Можешь выбрать ещё или нажать «Готово, сохранить роли»:",
        reply_markup=roles_kb(selected),
    )


@router.callback_query(ProjectForm.choosing_roles, F.data == "prole_done")
async def finish_roles(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_roles", [])
    if not selected:
        await callback.answer("Выбери хотя бы одну роль", show_alert=True)
        return

    await state.set_state(ProjectForm.entering_topic)
    await callback.message.answer(ASK_TOPIC)
    await callback.answer()


@router.message(ProjectForm.entering_topic)
async def process_topic(message: Message, state: FSMContext):
    if not valid_manual_field(message.text):
        await message.answer(ERR_MANUAL_FIELD)
        return
    await state.update_data(topic=message.text.strip())
    await state.set_state(ProjectForm.entering_stage)
    await message.answer(ASK_STAGE)


@router.message(ProjectForm.entering_stage)
async def process_stage(message: Message, state: FSMContext):
    if not valid_manual_field(message.text):
        await message.answer(ERR_MANUAL_FIELD)
        return
    await state.update_data(stage=message.text.strip())
    await state.set_state(ProjectForm.entering_format)
    await message.answer(ASK_FORMAT)


@router.message(ProjectForm.entering_format)
async def process_format(message: Message, state: FSMContext):
    if not valid_manual_field(message.text):
        await message.answer(ERR_MANUAL_FIELD)
        return

    data = await state.get_data()
    fmt = message.text.strip()

    project_id = await create_project(
        owner_id=message.from_user.id,
        title=data["title"],
        description=data["description"],
        roles=",".join(data["selected_roles"]),
        topic=data["topic"],
        stage=data["stage"],
        fmt=fmt,
    )

    await state.clear()

    from database import get_project
    project = await get_project(project_id)

    await message.answer("Проект опубликован ✅\n\n" + format_project_card(project))


@router.callback_query(F.data == "proj:mine")
async def show_my_projects(callback: CallbackQuery):
    projects = await get_user_projects(callback.from_user.id)
    if not projects:
        await callback.message.answer("Тут пока пусто")
        await callback.answer()
        return

    for project in projects:
        status = "🟢 активен" if project["is_active"] else "🔴 приостановлен"
        await callback.message.answer(format_project_card(project) + f"\nСтатус: {status}")
    await callback.answer()


@router.message(Command("bookmarks"))
async def show_bookmarks(message: Message):
    bookmarks = await get_bookmarks(message.from_user.id)
    if not bookmarks:
        await message.answer("В закладках пока пусто.")
        return

    await message.answer("⭐ Твои закладки:")
    for project in bookmarks:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="🟢Откликнуться",
                    callback_data=f"bresp:{project['project_id']}",
                )
            ]]
        )
        await message.answer(format_project_card(project), reply_markup=kb)
