from aiogram.fsm.state import State, StatesGroup


class Book(StatesGroup):
    barber = State()
    service = State()
    date = State()
    time = State()
    phone = State()
    confirm = State()


class Manual(StatesGroup):
    barber = State()
    service = State()
    date = State()
    time = State()
    name = State()
    phone = State()


class Block(StatesGroup):
    barber = State()
    date = State()
    start = State()
    end = State()
    confirm = State()


class Settings(StatesGroup):
    value = State()
    location = State()


class StaffAdd(StatesGroup):
    name = State()


class Review(StatesGroup):
    comment = State()


class Broadcast(StatesGroup):
    content = State()
    confirm = State()


class Svc(StatesGroup):
    edit_name = State()
    edit_price = State()
    add_name = State()
    add_price = State()


class Hours(StatesGroup):
    start = State()
    end = State()
    lunch = State()
    lunch_len = State()
