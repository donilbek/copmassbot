from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from states import ReviewForm
from database import add_review, get_reviews_for_user, get_top_tags

router = Router()

STARS = {n: "⭐" * n for n in range(1, 6)}

# Теги-характеристики, как в Яндекс.Такси: набор зависит от того, какую оценку поставили
POSITIVE_TAGS = [
    ("communicative", "🗣 Общительный"),
    ("skilled", "💡 Хорошие знания в стеке"),
    ("responsible", "✅ Ответственный"),
    ("deadlines", "⏰ Соблюдает дедлайны"),
    ("team_player", "🤝 Помогает команде"),
    ("creative", "🎨 Креативный"),
    ("fast_start", "⚡ Быстро включается в задачи"),
    ("clear", "📢 Понятно объясняет"),
]

NEGATIVE_TAGS = [
    ("slow_reply", "🐌 Долго отвечает"),
    ("missed_calls", "📵 Пропускал созвоны"),
    ("weak_skills", "📉 Слабые технические знания"),
    ("missed_deadlines", "⏳ Не соблюдал дедлайны"),
    ("poor_comm", "🙊 Плохая коммуникация"),
    ("passive", "😐 Мало вовлечён в проект"),
]

TAG_LABELS = dict(POSITIVE_TAGS + NEGATIVE_TAGS)


def tags_for_rating(rating: int):
    if rating >= 4:
        return POSITIVE_TAGS
    if rating <= 2:
        return NEGATIVE_TAGS
    return POSITIVE_TAGS + NEGATIVE_TAGS


def rating_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=STARS[n], callback_data=f"rate:{n}")
                for n in range(1, 6)
            ]
        ]
    )


def tags_kb(available_tags, selected: list[str]):
    buttons = []
    for key, label in available_tags:
        prefix = "✅ " if key in selected else ""
        buttons.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"tag:{key}")])
    buttons.append([InlineKeyboardButton(text="Готово ➡️", callback_data="tags_done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("review:"))
async def start_review(callback: CallbackQuery, state: FSMContext):
    _, project_id, target_id = callback.data.split(":")
    await state.set_state(ReviewForm.choosing_rating)
    await state.update_data(project_id=int(project_id), target_id=int(target_id))
    await callback.message.answer(
        "Оцени партнёра по проекту от 1 до 5 звёзд:",
        reply_markup=rating_kb(),
    )
    await callback.answer()


@router.callback_query(ReviewForm.choosing_rating, F.data.startswith("rate:"))
async def rating_chosen(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":", 1)[1])
    await state.update_data(rating=rating, selected_tags=[])
    await state.set_state(ReviewForm.choosing_tags)

    await callback.message.edit_text(f"Твоя оценка: {STARS[rating]}")
    await callback.message.answer(
        "Что можешь отметить дополнительно? Выбери подходящие варианты (можно несколько) "
        "и нажми «Готово»:",
        reply_markup=tags_kb(tags_for_rating(rating), []),
    )
    await callback.answer()


@router.callback_query(ReviewForm.choosing_tags, F.data.startswith("tag:"))
async def toggle_tag(callback: CallbackQuery, state: FSMContext):
    tag = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_tags", [])

    if tag in selected:
        selected.remove(tag)
    else:
        selected.append(tag)
    await state.update_data(selected_tags=selected)

    await callback.message.edit_reply_markup(
        reply_markup=tags_kb(tags_for_rating(data["rating"]), selected)
    )
    await callback.answer()


@router.callback_query(ReviewForm.choosing_tags, F.data == "tags_done")
async def finish_review(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    rating = data["rating"]
    tags = data.get("selected_tags", [])

    await add_review(
        reviewer_id=callback.from_user.id,
        target_id=data["target_id"],
        project_id=data["project_id"],
        rating=rating,
        tags=tags,
    )

    await state.clear()

    tags_line = ("\n" + ", ".join(TAG_LABELS[t] for t in tags)) if tags else ""
    await callback.message.edit_text(f"Спасибо за отзыв! {STARS[rating]}{tags_line}")
    await callback.answer("Отзыв сохранён 🙌")


@router.message(ReviewForm.choosing_rating)
async def rating_text_instead_of_buttons(message: Message):
    """Пользователь пишет текстом вместо выбора звёзд кнопками."""
    await message.answer(
        "❗️Пожалуйста, выбери оценку от 1 до 5 звёзд с помощью кнопок ниже",
        reply_markup=rating_kb(),
    )


@router.message(ReviewForm.choosing_tags)
async def tags_text_instead_of_buttons(message: Message, state: FSMContext):
    """Пользователь пишет текстом вместо выбора тегов кнопками."""
    data = await state.get_data()
    await message.answer(
        "❗️Пожалуйста, выбери варианты кнопками ниже и нажми «Готово»",
        reply_markup=tags_kb(tags_for_rating(data["rating"]), data.get("selected_tags", [])),
    )


@router.message(Command("reviews"))
async def show_my_reviews(message: Message):
    reviews = await get_reviews_for_user(message.from_user.id)
    if not reviews:
        await message.answer("У тебя пока нет отзывов.")
        return

    ratings = [r["rating"] for r in reviews if r["rating"]]
    lines = []
    if ratings:
        avg = sum(ratings) / len(ratings)
        lines.append(f"⭐ Средняя оценка: {avg:.1f} из 5 ({len(ratings)} оценок)")
    else:
        lines.append("⭐ Отзывы о тебе:")

    top_tags = await get_top_tags(message.from_user.id)
    if top_tags:
        tags_summary = ", ".join(f"{TAG_LABELS.get(tag, tag)} ×{count}" for tag, count in top_tags)
        lines.append(f"Часто отмечают: {tags_summary}")

    lines.append("")

    for r in reviews:
        author = r["reviewer_name"] or "Аноним"
        parts = []
        if r["rating"]:
            parts.append(STARS[r["rating"]])
        if r["tags"]:
            parts.append(", ".join(TAG_LABELS.get(t, t) for t in r["tags"].split(",") if t))
        if not parts and r["text"]:
            parts.append(r["text"])
        if parts:
            lines.append(f"• {author}: {' — '.join(parts)}")

    await message.answer("\n".join(lines))
