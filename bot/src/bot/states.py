from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    choose_role = State()
    onboard_nl_profile = State()
    onboard_confirm = State()
    view_program = State()
    view_detail = State()
    support_chat = State()
    expert_invite_entry = State()  # waiting for invite code after "I'm an expert" click
    expert_dashboard = State()
    expert_evaluation = State()
