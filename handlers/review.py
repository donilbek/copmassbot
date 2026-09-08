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
from database import add_review, get_reviews_for_user

router = Router()

STARS = {n: "⭐" * n for n in range(1, 6)}


def rating_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=STARS[n], callback_data=f"rate:{n}")
                for n in range(1, 6)
            ]
        ]
    )


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
async def save_review(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":", 1)[1])
    data = await state.get_data()

    await add_review(
        reviewer_id=callback.from_user.id,
        target_id=data["target_id"],
        project_id=data["project_id"],
        rating=rating,
    )

    await state.clear()
    await callback.message.edit_text(f"Спасибо за отзыв! Твоя оценка: {STARS[rating]}")
    await callback.answer("Отзыв сохранён 🙌")


@router.message(ReviewForm.choosing_rating)
async def rating_text_instead_of_buttons(message: Message):
    """Пользователь пишет текстом вместо выбора звёзд кнопками."""
    await message.answer(
        "❗️Пожалуйста, выбери оценку от 1 до 5 звёзд с помощью кнопок ниже",
        reply_markup=rating_kb(),
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
        lines.append(f"⭐ Средняя оценка: {avg:.1f} из 5 ({len(ratings)} оценок)\n")
    else:
        lines.append("⭐ Отзывы о тебе:\n")

    for r in reviews:
        author = r["reviewer_name"] or "Аноним"
        if r["rating"]:
            lines.append(f"• {author}: {STARS[r['rating']]}")
        elif r["text"]:
            lines.append(f"• {author}: {r['text']}")

    await message.answer("\n".join(lines))
