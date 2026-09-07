import re

# ---------------------------------------------------------------------------
# Тексты ошибок
# ---------------------------------------------------------------------------

FALLBACK_MESSAGES = {
    "voice": "❗️Бот не может распознать аудио. Пожалуйста, напишите текстом или воспользуйтесь кнопками",
    "sticker": "❗️Классный стикер! Но сейчас бот ожидает выбор действия по кнопкам или текстовый ответ на текущий шаг",
    "file": "❗️Отправка файлов пока не поддерживается",
    "contact": "❗️Пожалуйста, напишите номер текстом. Например 📞 +7 999 111 22 33",
    "other": "❗️Пожалуйста, ответь текстом или воспользуйся кнопками",
}

ERR_FULL_NAME = (
    "❗️Укажи корректные Фамилию и Имя.\n"
    "Это нужно, чтобы сокомандники и тимлид знали, как к тебе обращаться"
)
ERR_UNIVERSITY = (
    "❗️Пожалуйста, напиши название вуза и курс понятнее.\n"
    "Тимлиды часто ищут ребят из своего университета"
)
ERR_ROLE_BUTTONS = (
    "❗️Пожалуйста, выбери роль с помощью кнопок ниже.\n"
    "Если твоей роли нет в списке, нажми кнопку «Другое» (напиши свой вариант)"
)
ERR_STACK = (
    "❗️Укажи хотя бы 1-2 ключевые технологии или инструмента.\n"
    "Без этого проект не сможет оценить твой профиль"
)
ERR_FORMAT = (
    "❗️Уточни желаемый формат участия.\n"
    "Напиши, что тебе ближе: хакатоны, долгосрочные проекты или стартапы"
)
ERR_SOCIALS = (
    "❗️Укажи корректный контакт для связи.\n"
    "Сюда тимлид напишет при успешном мэтче"
)
ERR_PHONE = (
    "❗️Пожалуйста, проверь номер телефона.\n"
    "Номер должен содержать код страны и не менее 10 цифр\n"
    "Пример: +7 999 111 22 33"
)
ERR_STATUS_BUTTONS = "❗️Пожалуйста, выбери статус поиска с помощью кнопок ниже"

ERR_PROJECT_TITLE = (
    "❗️Слишком короткое или непонятное название.\n"
    "Напиши, как называется проект (от 3 до 100 символов)"
)
ERR_PROJECT_DESCRIPTION = (
    "❗️Слишком краткое описание. Опиши проект в 1-3 предложениях: "
    "в чём его главная идея и текущая стадия?\n"
    "Так потенциальные сокомандники быстрее заинтересуются"
)
ERR_PROJECT_DESCRIPTION_LONG = (
    "❗️Слишком длинное описание — оно не влезет в карточку проекта.\n"
    "Уложись в 500 символов: главная идея и текущая стадия"
)
ERR_PROJECT_ROLES_BUTTONS = (
    "❗️Пожалуйста, отметьте нужные роли кнопками ниже.\n"
    "Можно выбрать сразу несколько ролей. "
    "После выбора нажмите на кнопку: «Готово, сохранить роли»"
)
ERR_MANUAL_FIELD = (
    "❗️Поле не может быть пустым или состоять только из спецсимволов\n\n"
    "Примеры:\n"
    "Тематика: EdTech, AI, Финтех, Геймдев\n"
    "Стадия: Идея / Прототип / Готовимся к хакатону\n"
    "Формат: Пет-проект (5-10 ч/нед) / Спринт на выходные"
)
ERR_CARD_BUTTONS = "❗️Для управления карточками используй кнопки под проектом:"
ERR_NO_PROFILE = (
    "❗️Анкета соискателя ещё не заполнена!\n"
    "Чтобы откликаться на проекты или набирать участников, необходимо указать "
    "свои данные (роль, стек, вуз и контакты). Это займёт всего минуту"
)
ERR_FREE_TEXT_MENU = (
    "❗️Я пока не умею поддерживать свободный диалог текстом.\n"
    "Чтобы найти команду, проект или изменить свои данные, "
    "воспользуйся кнопками меню ниже:"
)


# ---------------------------------------------------------------------------
# Проверка типа сообщения (не текст → фолбек)
# ---------------------------------------------------------------------------

def get_content_issue(message):
    """Возвращает ключ проблемы (для FALLBACK_MESSAGES) или None, если это обычный текст."""
    if message.voice or message.video_note or message.audio:
        return "voice"
    if message.sticker or message.animation:
        return "sticker"
    if message.photo or message.document or message.video:
        return "file"
    if message.contact:
        return "contact"
    if message.location or message.venue or message.poll or message.dice:
        return "other"
    if not message.text or not message.text.strip():
        return "other"
    return None


# ---------------------------------------------------------------------------
# Вспомогательные эвристики
# ---------------------------------------------------------------------------

_REPEATED_CHAR_RE = re.compile(r"(.)\1{2,}")
_NAME_PART_RE = re.compile(r"^[A-Za-zА-Яа-яЁё]+(?:[-'][A-Za-zА-Яа-яЁё]+)*$")
_VOWELS = set("аеёиоуыэюяaeiouy")

# Типичные «прогоны по клавиатуре»
_KEYBOARD_MASH = (
    "йцукен", "фыва", "ячсми", "ывап", "апрол", "олдж", "ждлор",
    "qwer", "wert", "asdf", "sdfg", "zxcv", "xcvb", "hjkl",
)


def letters_count(text: str) -> int:
    return sum(1 for c in text if c.isalpha())


def has_repeated_run(text: str) -> bool:
    """3 и более одинаковых символа подряд («aaaaaaa», «ыыыы»)."""
    return bool(_REPEATED_CHAR_RE.search(text.lower()))


def looks_like_gibberish(text: str) -> bool:
    """Грубая проверка на бессмыслицу: прогон по клавиатуре или слово без гласных."""
    low = text.lower()
    if any(seq in low for seq in _KEYBOARD_MASH):
        return True
    for token in re.findall(r"[A-Za-zА-Яа-яЁё]+", low):
        if len(token) >= 5 and not (set(token) & _VOWELS):
            return True
    return False


# ---------------------------------------------------------------------------
# Валидаторы анкеты
# ---------------------------------------------------------------------------

def valid_full_name(text: str) -> bool:
    """Минимум два слова, только буквы (дефис/апостроф допустимы), без повторов."""
    t = " ".join((text or "").strip().split())
    parts = t.split(" ")
    if len(parts) < 2:
        return False
    if has_repeated_run(t):
        return False
    for part in parts:
        if len(part) < 2 or not _NAME_PART_RE.match(part):
            return False
    return True


def valid_university(text: str) -> bool:
    t = (text or "").strip()
    if not (3 <= len(t) <= 120):
        return False
    if letters_count(t) < 3:
        return False
    if has_repeated_run(t) or looks_like_gibberish(t):
        return False
    return True


def valid_stack(text: str) -> bool:
    t = (text or "").strip()
    low = t.lower()
    if len(t) < 3 or len(t) > 300:
        return False
    if letters_count(t) < 2:
        return False
    if low in {"да", "нет", "х3", "хз", "не знаю", "любой", "всё", "все", "-", "не важно"}:
        return False
    if has_repeated_run(t) or looks_like_gibberish(t):
        return False
    return True


def valid_format(text: str) -> bool:
    t = (text or "").strip()
    if len(t) > 300:
        return False
    if letters_count(t) < 4:
        return False
    if has_repeated_run(t) or looks_like_gibberish(t):
        return False
    return True


def valid_socials(text: str) -> bool:
    t = (text or "").strip().lower()
    if len(t) < 4:
        return False
    return bool(
        re.search(
            r"(https?://|t\.me/|tg://|@[\w\d_]{3,}|vk\.com|vk\.ru|instagram|linkedin|"
            r"github\.com|behance|telegram|whatsapp|\+?\d[\d\s\-()]{8,})",
            t,
        )
    )


def valid_phone(text: str) -> bool:
    t = (text or "").strip()
    if re.search(r"[A-Za-zА-Яа-яЁё]", t):
        return False
    digits = re.sub(r"\D", "", t)
    return 10 <= len(digits) <= 15


# ---------------------------------------------------------------------------
# Валидаторы проекта
# ---------------------------------------------------------------------------

def valid_project_title(text: str) -> bool:
    t = (text or "").strip()
    if not (3 <= len(t) <= 100):
        return False
    if letters_count(t) < 2:
        return False
    if has_repeated_run(t) or looks_like_gibberish(t):
        return False
    return True


def project_description_issue(text: str):
    """None — всё ок, 'short' — слишком коротко/бессмысленно, 'long' — длиннее 500."""
    t = (text or "").strip()
    if len(t) > 500:
        return "long"
    if len(t) < 20:
        return "short"
    if letters_count(t) < 15:
        return "short"
    if t.lower() in {"бот", "проект", "стартап", "приложение", "сайт"}:
        return "short"
    if has_repeated_run(t) or looks_like_gibberish(t):
        return "short"
    return None


def valid_project_description(text: str) -> bool:
    return project_description_issue(text) is None


def valid_manual_field(text: str) -> bool:
    """Тематика / стадия / формат проекта, введённые вручную."""
    t = (text or "").strip()
    if len(t) < 3 or len(t) > 200:
        return False
    if letters_count(t) < 3:
        return False
    if has_repeated_run(t) or looks_like_gibberish(t):
        return False
    return True
