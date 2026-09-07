from aiogram.fsm.state import State, StatesGroup


class ProfileForm(StatesGroup):
    entering_full_name = State()
    entering_university = State()
    choosing_role = State()
    entering_role_custom = State()
    entering_stack = State()
    entering_format = State()
    choosing_status = State()
    entering_socials = State()
    entering_phone = State()
    entering_projects = State()


class ProjectForm(StatesGroup):
    entering_title = State()
    entering_description = State()
    choosing_roles = State()
    entering_role_custom = State()
    entering_topic = State()
    entering_stage = State()
    entering_format = State()


class BrowseForm(StatesGroup):
    choosing_role = State()
    choosing_experience = State()
    entering_stack = State()
    entering_employment = State()
    entering_time = State()
    confirming_filter = State()
    viewing_cards = State()


class ReviewForm(StatesGroup):
    entering_text = State()
