from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from states import ReviewForm
from database import add_review, get_reviews_for_user
from validators import has_repeated_run, letters_count, looks_like_gibberish

router = Router()


def valid_review(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 10 or len(t) > 500:
        return False
    if letters_count(t) < 8:
        return False
    if has_repeated_run(t) or looks_like_gibberish(t):
        return False
    return True


@router.callback_query(F.data.startswith("review:"))
async def start_review(callback: CallbackQuery, state: FSMContext):
    _, project_id, target_id = callback.data.split(":")
    await state.set_state(ReviewForm.entering_text)
    await state.update_data(project_id=int(project_id), target_id=int(target_id))
    await callback.message.answer("Напиши отзыв о партнёре по проекту (пару предложений):")
    await callback.answer()


@router.message(ReviewForm.entering_text)
async def save_review(message: Message, state: FSMContext):
    if not valid_review(message.text):
        await message.answer(
            "❗️Отзыв слишком короткий или непонятный.\n"
            "Напиши пару предложений: как человек работал в команде и что получилось"
        )
        return

    data = await state.get_data()
    await add_review(
        reviewer_id=message.from_user.id,
        target_id=data["target_id"],
        project_id=data["project_id"],
        text=message.text.strip(),
    )
    await state.clear()
    await message.answer("Отзыв сохранён, спасибо! 🙌")


@router.message(Command("reviews"))
async def show_my_reviews(message: Message):
    reviews = await get_reviews_for_user(message.from_user.id)
    if not reviews:
        await message.answer("У тебя пока нет отзывов.")
        return

    lines = ["⭐ Отзывы о тебе:\n"]
    for r in reviews:
        author = r["reviewer_name"] or "Аноним"
        lines.append(f"• {author}: {r['text']}")

    await message.answer("\n".join(lines))
