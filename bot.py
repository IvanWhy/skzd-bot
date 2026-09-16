import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import os
import ast
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")
MAIN_ADMIN_ID = int(os.getenv("MAIN_ADMIN_ID", 0))

if not BOT_TOKEN: raise ValueError("BOT_TOKEN не найден!")
if isinstance(ADMIN_CHAT_ID, str): ADMIN_CHAT_ID = ast.literal_eval(ADMIN_CHAT_ID)
elif ADMIN_CHAT_ID is None: raise ValueError("ADMIN_CHAT_ID не найден!")

TRAIN_SERIES = {
    "Пассажирские электровозы": ["ЭП20", "ЭП1М", "ЭП1", "ЧС4Т", "ЧС4", "ЭП1П"],
    "Грузовые электровозы": ["2ЭС5К", "ВЛ80Т", "2ЭС4К", "ВЛ80С", "3ЭС5К", "ВЛ10", "ВЛ10У", "ВЛ11", "3ЭС5С", "2ЭС5С", "2ЭС5"],
    "Тепловозы": ["ТЭП70БС", "ТЭП70", "2ТЭ10М", "ТЭМ2", "2ТЭ116", "2ТЭ116У", "3ТЭ116У", "2ТЭ25КМ", "АЧ2", "АС01", "ЧМЭ3", "ТЭМ18", "ТЭМ18Д", "ТЭМ18ДМ"],
    "МВПС": ["ЭД4М", "ЭД9М", "ЭД9МК", "ЭС1", "ЭС2ГП", "РА1", "РА2", "РА3"]
}

STATIONS = ["Азов", "Батайск", "Волгоград-1", "Волгоград-2", "Волгодонская", "Горячий ключ", "Ейск", "Зверево", "Кавказская", "Каменская", "Керчь", "Кисловодск", "Краснодар-1", "Краснодар-2", "Красный Сулин", "Крымск", "Каневская", "Лихая", "Минеральные Воды", "Морозовская", "Майкоп", "Новороссийск", "Новочеркасск", "Первомайская", "Ростов-Берег", "Ростов-Главный", "Сальск", "Сочи", "Ставрополь", "Староминская-Тимашевская", "Таганрог", "Таганрог-пасс", "Тимашевск", "Тихорецкая", "Туапсе", "Шахтная"]

DIRECTIONS = ["на Азов", "на Адлер", "на Батайск", "на Волгоград", "на Волгодонск", "на Горячий ключ", "на Ейск", "на Кавказскую", "на Керчь", "на Краснодар", "на Крымск", "на Каневскую", "на Лихую", "на Минеральные Воды", "на Майкоп", "на Новороссийск", "на Новочеркасск", "на Ростов", "на Ростов-берег", "на Сальск", "на Сочи", "на Ставрополь", "на Староминскую", "на Таганрог", "на Тимашевск", "на Тихорецкую", "на Туапсе"]

SCHEDULES = {
    "028М": {"name": "Таврия/двухэтажный состав", "route": "Москва — Симферополь", "link": "https://rasp.yandex.ru/thread/R_028M_63438"},
    "027С": {"name": "Таврия/двухэтажный состав", "route": "Симферополь — Москва", "link": "https://rasp.yandex.ru/thread/R_027S_63438"},
    "020С": {"name": "Тихий Дон", "route": "Москва — Ростов", "link": "https://rasp.yandex.ru/thread/R_020S_112"},
    "019С": {"name": "Тихий Дон", "route": "Ростов — Москва", "link": "https://rasp.yandex.ru/thread/R_019S_112"},
    "104В": {"name": "Двухэтажный состав", "route": "Москва — Адлер", "link": "https://rasp.yandex.ru/thread/R_104V_112"},
    "104Ж": {"name": "Двухэтажный состав", "route": "Адлер — Москва", "link": "https://rasp.yandex.ru/thread/R_104ZH_112"},
    "102М": {"name": "Обычный ПДС", "route": "Москва — Адлер", "link": "https://rasp.yandex.ru/thread/R_102M_112"},
    "102С": {"name": "Обычный ПДС", "route": "Адлер — Москва", "link": "https://rasp.yandex.ru/thread/R_102S_112"},
    "030С": {"name": "Премиум", "route": "Москва — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_030S_112"},
    "030Й": {"name": "Премиум", "route": "Новороссийск — Москва", "link": "https://rasp.yandex.ru/thread/R_030J_112"},
    "012М": {"name": "Анапа-Москва", "route": "Москва — Анапа", "link": "https://rasp.yandex.ru/thread/R_012M_112"},
    "011Э": {"name": "Анапа-Москва", "route": "Анапа — Москва", "link": "https://rasp.yandex.ru/thread/R_011E_112"},
    "004М": {"name": "Кавказ/двухэтажный состав", "route": "Москва — Кисловодск", "link": "https://rasp.yandex.ru/thread/R_004M_112"},
    "003С": {"name": "Кавказ/двухэтажный состав", "route": "Кисловодск — Москва", "link": "https://rasp.yandex.ru/thread/R_003S_112"},
    "810С": {"name": "Ласточка", "route": "Ростов-на-Дону — Кисловодск", "link": "https://rasp.yandex.ru/thread/R_810S_112"},
    "035С": {"name": "Северная Пальмира/двухэтажный состав", "route": "Адлер — Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_035S_112"},
    "036А": {"name": "Северная Пальмира/двухэтажный состав", "route": "Санкт-Петербург — Адлер", "link": "https://rasp.yandex.ru/thread/R_036A_112"},
    "642Ж": {"name": "Обычный ПДС", "route": "Адлер — Ростов-на-Дону", "link": "https://rasp.yandex.ru/thread/R_642ZH_112"},
    "642С": {"name": "Обычный ПДС", "route": "Ростов-на-Дону — Адлер", "link": "https://rasp.yandex.ru/thread/R_642S_112"},
    "808С": {"name": "Ласточка", "route": "Ростов-на-Дону — Аэропорт Сочи", "link": "https://rasp.yandex.ru/thread/R_808S_112"},
    "558Х": {"name": "Двухэтажный состав", "route": "Москва — Сириус", "link": "https://rasp.yandex.ru/thread/R_558KH_112"},
    "044М": {"name": "Двухэтажный состав", "route": "Москва — Сириус", "link": "https://rasp.yandex.ru/thread/R_044M_112"},
    "043С": {"name": "Двухэтажный состав", "route": "Сириус — Москва", "link": "https://rasp.yandex.ru/thread/R_043S_112"}
}

LOCO_NICKNAMES = {
    "ЭП20-001": " «Олимп»🟠🔵", "ЭП20-002": " «Буревестник»🟢️", "ЭП20-003": " «Новопид»⚫️🔴",
    "ЭП1М-411": "🔵 «Голубой»", "ЭП1М-423": "🔵 «Голубой»", "ЭП1М-437": "🔵 «Голубой»",
    "ЭП1М-444": "🔵 «Голубой»", "ЭП1М-454": "🔵 «Голубой»", "ЭП1М-491": "🔵 «Голубой»",
    "ЭП1М-525": "🔵 «Голубой»", "ЭП1М-549": "🔵 «Голубой»", "ЭП1М-555": "🔵 «Голубой»",
    "ЭП1М-556": "🔵 «Голубой»", "ЭП1М-598": " «Голубой»", "ЭП1М-611": "🔵 «Голубой»",
    "ЭП1М-637": "🔵 «Голубой»", "ЭП1М-651": "🟢🔵 «Жемчужина Кавказа»", "ЭП1М-662": "🔵 «Голубой»",
    "ЭП1М-688": "🟢 «Жемчужина Кавказа»",
    "3ЭС5К-1131": "🖤🔴 «НТС»", "3ЭС5К-1133": "🖤🔴 «НТС»", "3ЭС5К-1134": "🖤🔴 «НТС»",
    "3ЭС5К-1135": "🖤🔴 «НТС»", "3ЭС5К-1136": "🖤🔴 «НТС»", "3ЭС5К-1137": "🖤🔴 «НТС»",
    "3ЭС5К-1138": "🖤🔴 «НТС»", "3ЭС5К-1139": "🖤🔴 «НТС»", "3ЭС5К-1140": "🖤🔴 «НТС»",
    "3ЭС5К-1141": "🖤🔴 «НТС»", "3ЭС5К-1142": "🖤🔴 «НТС»", "3ЭС5К-1143": "🖤🔴 «НТС»",
    "3ЭС5К-1144": "🖤 «НТС»",
    "2ЭС5К-555": "🔵 «ТрансОйл»", "2ЭС5К-556": "🔵 «ТрансОйл»", "2ЭС5К-557": "🔵 «ТрансОйл»",
    "2ЭС5К-558": "🔵 «ТрансОйл»", "2ЭС5К-559": "🔵 «ТрансОйл»", "2ЭС5К-560": "🔵 «ТрансОйл»",
    "2ЭС5К-561": "🔵 «ТрансОйл»", "2ЭС5К-562": " «ТрансОйл»", "2ЭС5К-563": "🔵 «ТрансОйл»",
    "2ЭС5К-564": " «ТрансОйл»", "2ЭС5К-590": "🔵 «ТрансОйл»",
    "ВЛ80С-1382": "🟡 «ГЖД»", "ВЛ80С-1580": "🟡 «ГЖД»", "ВЛ80С-1913": "🟡 «ГЖД»",
    "ВЛ80С-2127": "🟢🟡 «ГЖД»", "ВЛ80С-693": "🟢", "ВЛ80С-841": "🟢", "ВЛ80С-1097": "🟢",
    "ВЛ80С-1226": "🟢", "ВЛ80С-1271": "🟢", "ВЛ80С-1311": "🟢", "ВЛ80С-1357": "🟢",
    "ВЛ80С-1449": "🟢", "ВЛ80С-1732": "🟢", "ВЛ80С-2034": "🟢", "ВЛ80С-2051": "",
    "ВЛ80С-2196": "🟢", "ВЛ80С-2217": "", "ВЛ80С-2221": "🟢", "ВЛ80С-2227": "🟢",
    "ВЛ80С-2230": "🟢", "ВЛ80С-2241": "", "ВЛ80С-2602": "🟢"
}

BLACKLIST = set()
ACTIVE_USERS = set()

def add_active_user(user_id): ACTIVE_USERS.add(user_id)

BTN_ADD_MULTIPLE = "➕ Добавить еще один ПС"
BTN_ADD_TRANSFER = " Добавить еще перегоняемый"
BTN_FINISH = "✅ Закончить"
BTN_BACK = "️ Назад"
BTN_CANCEL_EDIT = "️ Отмена"
BTN_NONE_LIST = "❌ Ничего из списка"
BTN_DELETE = "🗑 Удалить:"
BTN_DELETE_TRANSFER = "🗑 Удалить перегоняемый:"
BTN_ADD_DESCRIPTION = "✏️ Добавить описание"
BTN_SKIP_DESCRIPTION = "⏭️ Пропустить"
BTN_REJECT_FAKE = "❌ Недостоверно"
BTN_REJECT_DUPLICATE = "🔁 Дубликат"
BTN_REJECT_NO_PHOTO = " Нет фото"
BTN_REJECT_CUSTOM = "️ Своя причина"
BTN_REJECT_CANCEL = "⬅️ Отмена"
BTN_UNKNOWN_NUMBER = "Номер неизвестен"

BTN_PDS = "ПДС"
BTN_GRUZ = "Грузовой поезд"
BTN_REZERV = "Резерв"
BTN_KHOZ = "Хозяйственный"
BTN_LAB = "Лаборатория"
BTN_SPLOTKA = "Сплотка"
BTN_PEREGONKA = "Перегонка"
BTN_NO_INFO = "Нет информации"

REJECT_REASONS = {"fake": "❌ Недостоверная информация", "duplicate": "🔁 Дубликат (уже было)", "nophoto": "📷 Нет фотоподтверждения"}

class Form(StatesGroup):
    waiting_series_category = State()
    waiting_series = State()
    waiting_number = State()
    waiting_loco_color = State()
    waiting_train_type = State()
    waiting_train_number = State()
    waiting_train_select = State()
    waiting_train_number_manual = State()
    waiting_direction = State()
    waiting_direction_manual = State()
    waiting_station = State()
    waiting_station_manual = State()
    waiting_time = State()
    waiting_photo = State()
    waiting_confirmation = State()
    waiting_description = State()
    waiting_multiple_series_category = State()
    waiting_multiple_series = State()
    waiting_multiple_number = State()
    waiting_multiple_action = State()
    waiting_transfer_towed_category = State()
    waiting_transfer_towed_series = State()
    waiting_transfer_towed_number = State()
    waiting_transfer_action = State()
    waiting_transfer_train_type = State()
    waiting_transfer_train_number = State()
    waiting_transfer_train_select = State()
    waiting_transfer_train_number_manual = State()
    edit_what = State()
    edit_series_category = State()
    edit_series = State()
    edit_number = State()
    edit_train_type = State()
    edit_train_number = State()
    edit_train_select = State()
    edit_train_number_manual = State()
    edit_direction = State()
    edit_direction_manual = State()
    edit_station = State()
    edit_station_manual = State()
    edit_time = State()
    edit_multiple_action = State()
    edit_multiple_series_category = State()
    edit_multiple_series = State()
    edit_multiple_number = State()
    edit_transfer_action = State()
    edit_transfer_towed_category = State()
    edit_transfer_towed_series = State()
    edit_transfer_towed_number = State()
    edit_transfer_train_type = State()
    edit_transfer_train_number = State()
    edit_transfer_train_select = State()
    edit_transfer_train_number_manual = State()
    waiting_admin_msg = State()

user_data = {}
pending_publications = {}
pending_rejections = {}

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

MOSCOW_TZ = timezone(timedelta(hours=3))
def get_moscow_now(): return datetime.now(MOSCOW_TZ)

def get_loco_name(series, number):
    full_name = f"{series}-{number}"
    if full_name in LOCO_NICKNAMES: return f"{full_name}{LOCO_NICKNAMES[full_name]}"
    return full_name

def format_station(station_name):
    station_lower = station_name.lower().strip()
    for prefix in ["ст.", "ст ", "перегон", "о.п.", "о.п ", "о.п", "оп.", "оп ", "оп"]:
        if station_lower.startswith(prefix): return station_name
    return f"ст. {station_name}"

def find_train_by_query(query: str):
    query = query.strip().upper()
    results = []
    for train_num, info in SCHEDULES.items():
        if query == train_num.upper(): return [(train_num, info)]
        train_digits = ''.join(c for c in train_num if c.isdigit())
        if train_digits and train_digits in query: results.append((train_num, info)); continue
        if info["name"].upper() in query or query in info["name"].upper(): results.append((train_num, info)); continue
        route_clean = info["route"].replace(" ", "").replace("—", "").replace("-", "")
        query_clean = query.replace(" ", "").replace("—", "").replace("-", "")
        if route_clean and (route_clean in query_clean or query_clean in route_clean): results.append((train_num, info))
    return results

def build_train_info(data: dict) -> str:
    if data.get("is_multiple"):
        units = data.get("multiple_units", [])
        if units: return f"🚂🚂 <b>Сплотка:</b>\n" + "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units])
        return "🚂 Сплотка (пусто)"
    elif data.get("is_transfer"):
        td = data.get("transfer_data", {})
        main = td.get("main", {})
        towed = td.get("towed", [])
        if main and towed:
            info = f"➡️ <b>Перегонка:</b>\n  🚂 Основной: {get_loco_name(main['series'], main['number'])}\n  🚂 Перегоняемые:\n" + "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in towed])
            if data.get("transfer_train_type") == BTN_GRUZ: info += "\n  🚛 Под грузовым поездом"
            elif data.get("transfer_train_type") == BTN_PDS and data.get("transfer_train_number") and data.get("transfer_train_number") != BTN_NO_INFO:
                tn = data["transfer_train_number"]
                if tn in SCHEDULES: info += f"\n  🚆 Под поездом {tn} «{SCHEDULES[tn]['name']}»\n  📅 <a href=\"{SCHEDULES[tn]['link']}\">Расписание</a>"
                else: info += f"\n  🚆 Под поездом {tn}"
            else: info += "\n  🤷 Поезд неизвестен"
            return info
        return "➡️🚂 Перегонка (неполные данные)"
    else:
        if data["train_type"] == BTN_PDS and data["train_number"] != BTN_NO_INFO:
            tn = data["train_number"]
            if tn in SCHEDULES: return f'🚆 Поезд {tn} «{SCHEDULES[tn]["name"]}» ({SCHEDULES[tn]["route"]})\n📅 <a href="{SCHEDULES[tn]["link"]}">Расписание</a>'
            return f"🚆 Поезд {tn}"
        elif data["train_type"] == BTN_GRUZ: return "🚛 Грузовой поезд"
        elif data["train_type"] == BTN_REZERV: return "🔄 Резерв (свой ход)"
        elif data["train_type"] == BTN_LAB: return "🔬 Лаборатория / Рельсосмазыватель"
        elif data["train_type"] == BTN_KHOZ: return "🛠 Хозяйственный поезд"
        return "🤷 Тип поезда неизвестен"

def build_summary(user_id: int) -> str:
    data = user_data[user_id]
    today = get_moscow_now().strftime("%d.%m.%Y")
    has_photo = "photo_id" in data
    summary = "📋 <b>Проверьте правильность информации:</b>\n\n"
    if not (data.get("is_multiple") or data.get("is_transfer")):
        ps_name = get_loco_name(data['series'], data['number'])
        if data['number'] == "Номер неизвестен":
            if data.get("loco_color"): ps_name = f"{data['series']} ({data['loco_color']})"
            else: ps_name = f"{data['series']} (номер неизвестен)"
        summary += f"🚂 <b>ПС:</b> {ps_name}\n"
    summary += f"{build_train_info(data)}\n🗺 <b>Направление:</b> {data['direction']}\n📌 <b>Место:</b> {format_station(data['station'])}\n🕒 <b>Актуальность:</b> {data['time']} ({today})\n📸 <b>Фото:</b> {'есть' if has_photo else 'нет'}"
    if data.get("description"): summary += f"\n\n📝 <b>Описание:</b> {data['description']}"
    return summary

def build_channel_message(data: dict) -> str:
    today = get_moscow_now().strftime("%d.%m.%Y")
    message = ""
    if not (data.get("is_multiple") or data.get("is_transfer")):
        ps_name = get_loco_name(data['series'], data['number'])
        if data['number'] == "Номер неизвестен":
            if data.get("loco_color"): ps_name = f"{data['series']} ({data['loco_color']})"
            else: ps_name = f"{data['series']} (номер неизвестен)"
        message += f"🚂 <b>ПС:</b> {ps_name}\n"
    message += f"{build_train_info(data)}\n🗺 <b>Направление:</b> {data['direction']}\n📌 <b>Место:</b> {format_station(data['station'])}\n🕒 <b>Актуальность:</b> {data['time']} ({today})"
    if data.get("description"): message += f"\n\n📝 <b>Описание:</b> {data['description']}"
    return message

def build_admin_message(data: dict, user) -> str:
    today = get_moscow_now().strftime("%d.%m.%Y")
    admin_msg = f"🚂 <b>Новая заявка от @{user.username or user.first_name}</b>\n\n"
    if not (data.get("is_multiple") or data.get("is_transfer")):
        ps_name = get_loco_name(data['series'], data['number'])
        if data['number'] == "Номер неизвестен":
            if data.get("loco_color"): ps_name = f"{data['series']} ({data['loco_color']})"
            else: ps_name = f"{data['series']} (номер неизвестен)"
        admin_msg += f"🚂 <b>ПС:</b> {ps_name}\n"
    admin_msg += f"{build_train_info(data)}\n <b>Направление:</b> {data['direction']}\n📌 <b>Место:</b> {format_station(data['station'])}\n🕒 <b>Актуальность:</b> {data['time']} ({today})"
    if data.get("description"): admin_msg += f"\n\n📝 <b>Описание:</b> {data['description']}"
    return admin_msg

async def return_to_summary(message: types.Message, state: FSMContext, success_text: str):
    await message.answer(f"{success_text}\n\n{build_summary(message.from_user.id)}", reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True, parse_mode="HTML")
    await state.set_state(Form.waiting_confirmation)

def get_series_categories_keyboard(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cat)] for cat in TRAIN_SERIES.keys()], resize_keyboard=True)

def get_series_keyboard(category):
    keyboard, row = [], []
    for series in TRAIN_SERIES[category]:
        row.append(KeyboardButton(text=series))
        if len(row) == 2: keyboard.append(row); row = []
    if row: keyboard.append(row)
    keyboard.append([KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_train_type_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_PDS)], [KeyboardButton(text=BTN_GRUZ)], [KeyboardButton(text=BTN_REZERV)], [KeyboardButton(text=BTN_LAB)], [KeyboardButton(text=BTN_KHOZ)], [KeyboardButton(text=BTN_SPLOTKA)], [KeyboardButton(text=BTN_PEREGONKA)], [KeyboardButton(text=BTN_NO_INFO)]], resize_keyboard=True)

def get_number_keyboard(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_UNKNOWN_NUMBER)], [KeyboardButton(text=BTN_BACK)]], resize_keyboard=True)

def get_directions_keyboard():
    keyboard, row = [], []
    for d in DIRECTIONS:
        row.append(KeyboardButton(text=d))
        if len(row) == 2: keyboard.append(row); row = []
    if row: keyboard.append(row)
    keyboard.append([KeyboardButton(text="✏️ Ввести вручную")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_stations_keyboard():
    keyboard, row = [], []
    for s in STATIONS:
        row.append(KeyboardButton(text=s))
        if len(row) == 2: keyboard.append(row); row = []
    if row: keyboard.append(row)
    keyboard.append([KeyboardButton(text="✏️ Ввести вручную")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_confirmation_keyboard(with_description=False):
    if with_description: return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Да, всё верно")], [KeyboardButton(text=BTN_ADD_DESCRIPTION)], [KeyboardButton(text="❌ Нет, изменить")]], resize_keyboard=True)
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Да, всё верно")], [KeyboardButton(text="❌ Нет, изменить")]], resize_keyboard=True)

def get_edit_fields_keyboard(is_multiple=False, is_transfer=False):
    if is_multiple: return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_SPLOTKA), KeyboardButton(text="Тип поезда")], [KeyboardButton(text="Направление"), KeyboardButton(text="Место")], [KeyboardButton(text="Актуальность"), KeyboardButton(text=BTN_CANCEL_EDIT)]], resize_keyboard=True)
    elif is_transfer: return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_PEREGONKA), KeyboardButton(text="Поезд перегонки")], [KeyboardButton(text="Направление"), KeyboardButton(text="Место")], [KeyboardButton(text="Актуальность"), KeyboardButton(text=BTN_CANCEL_EDIT)]], resize_keyboard=True)
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="ПС"), KeyboardButton(text="Номер ПС")], [KeyboardButton(text="Тип поезда"), KeyboardButton(text="Номер поезда")], [KeyboardButton(text="Направление"), KeyboardButton(text="Место")], [KeyboardButton(text="Актуальность"), KeyboardButton(text=BTN_CANCEL_EDIT)]], resize_keyboard=True)

def get_multiple_action_keyboard(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_ADD_MULTIPLE)], [KeyboardButton(text=BTN_FINISH)]], resize_keyboard=True)

def get_edit_multiple_keyboard(units):
    keyboard = [[KeyboardButton(text=f"{BTN_DELETE} {get_loco_name(u['series'], u['number'])}")] for u in units]
    keyboard.append([KeyboardButton(text=BTN_ADD_MULTIPLE), KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_transfer_action_keyboard(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_ADD_TRANSFER)], [KeyboardButton(text=BTN_FINISH)]], resize_keyboard=True)

def get_edit_transfer_keyboard(td):
    keyboard = []
    main = td.get("main", {})
    if main: keyboard.append([KeyboardButton(text=f"🚂 Основной: {get_loco_name(main['series'], main['number'])} (изменить)")])
    for u in td.get("towed", []): keyboard.append([KeyboardButton(text=f"{BTN_DELETE_TRANSFER} {get_loco_name(u['series'], u['number'])}")])
    keyboard.append([KeyboardButton(text=BTN_ADD_TRANSFER), KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish:{user_id}")],
        [InlineKeyboardButton(text=BTN_REJECT_FAKE, callback_data=f"reject:{user_id}:fake"), InlineKeyboardButton(text=BTN_REJECT_DUPLICATE, callback_data=f"reject:{user_id}:duplicate")],
        [InlineKeyboardButton(text=BTN_REJECT_NO_PHOTO, callback_data=f"reject:{user_id}:nophoto"), InlineKeyboardButton(text=BTN_REJECT_CUSTOM, callback_data=f"reject:{user_id}:custom")],
        [InlineKeyboardButton(text="🚫 Забанить автора", callback_data=f"ban:{user_id}")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    add_active_user(message.from_user.id)
    if message.from_user.id in BLACKLIST: await message.answer("Вы заблокированы."); return
    await state.clear()
    user_data[message.from_user.id] = {}
    await message.answer("👋 Привет! Я бот-информатор канала о редких поездах СКЖД.\n\nДля начала выбери <b>категорию подвижного состава</b>:", reply_markup=get_series_categories_keyboard())
    await state.set_state(Form.waiting_series_category)

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    user_data.pop(message.from_user.id, None)
    await message.answer("Заполнение отменено. Напиши /start", reply_markup=types.ReplyKeyboardRemove())

@dp.message(Command("help"))
async def cmd_help(message: types.Message): await message.answer("📖 <b>Помощь:</b>\n/start - начать\n/cancel - отмена\n/help - справка")

@dp.message(Command("admin_msg"))
async def cmd_admin_msg(message: types.Message, state: FSMContext):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if message.from_user.id not in admin_ids: await message.answer("❌ Нет прав."); return
    await message.answer("✏️ Напишите сообщение для админов:")
    await state.set_state(Form.waiting_admin_msg)

@dp.message(Form.waiting_admin_msg)
async def process_admin_msg(message: types.Message, state: FSMContext):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    text = message.text.strip()
    count = 0
    for aid in admin_ids:
        try: await bot.send_message(aid, f"📢 <b>От админа:</b>\n\n{text}"); count += 1
        except: pass
    await message.answer(f"✅ Отправлено {count} админам.")
    await state.clear()

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if message.from_user.id not in admin_ids: await message.answer("❌ Нет прав."); return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: await message.answer("❌ Использование: /broadcast <текст>"); return
    text = args[1].strip()
    if not ACTIVE_USERS: await message.answer("⚠️ Нет пользователей."); return
    await message.answer(f"⏳ Рассылка {len(ACTIVE_USERS)} пользователям...")
    count = 0
    for uid in ACTIVE_USERS:
        try: await bot.send_message(uid, f"📢 <b>От администрации:</b>\n\n{text}"); count += 1
        except: pass
    await message.answer(f"✅ Доставлено: {count}/{len(ACTIVE_USERS)}")

@dp.message(Form.waiting_series_category)
async def process_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Выберите из списка:"); return
    user_data[message.from_user.id]["category"] = message.text
    await message.answer(f" Категория: <b>{message.text}</b>\n\nВыберите серию:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.waiting_series)

@dp.message(Form.waiting_series)
async def process_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("Выберите категорию:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_series_category); return
    cat = user_data[message.from_user.id]["category"]
    if message.text not in TRAIN_SERIES[cat]: await message.answer("❌ Выберите из списка:"); return
    user_data[message.from_user.id]["series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nВведите номер или нажмите кнопку:", reply_markup=get_number_keyboard())
    await state.set_state(Form.waiting_number)

@dp.message(Form.waiting_number)
async def process_number(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer(f"🚂 Серия: <b>{user_data[message.from_user.id]['series']}</b>\n\nВведите номер:", reply_markup=get_number_keyboard()); return
    if message.text == BTN_UNKNOWN_NUMBER:
        user_data[message.from_user.id]["number"] = "Номер неизвестен"
        await message.answer("🎨 <b>Укажите окрас:</b>\n\nНапример: <i>голубой, без названия, в рекламе</i>\n\nИли нажмите '⏭️ Пропустить':", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⏭️ Пропустить")]], resize_keyboard=True))
        await state.set_state(Form.waiting_loco_color); return
    num = message.text.strip()
    if not num.isdigit() or len(num) > 10: await message.answer("❌ Введите только цифры:"); return
    user_data[message.from_user.id]["number"] = num
    await message.answer(f" Номер: <b>{num}</b>\n\nТип поезда?", reply_markup=get_train_type_keyboard())
    await state.set_state(Form.waiting_train_type)

@dp.message(Form.waiting_loco_color)
async def process_loco_color(message: types.Message, state: FSMContext):
    if message.text == "⏭️ Пропустить": user_data[message.from_user.id]["loco_color"] = None
    else:
        color = message.text.strip()
        if len(color) > 50: await message.answer("❌ Коротко (до 50 символов):"); return
        user_data[message.from_user.id]["loco_color"] = color
    series = user_data[message.from_user.id]["series"]
    ps_name = f"{series} ({user_data[message.from_user.id].get('loco_color')})" if user_data[message.from_user.id].get("loco_color") else series
    await message.answer(f"🚂 <b>ПС:</b> {ps_name}\n\nТип поезда?", reply_markup=get_train_type_keyboard())
    await state.set_state(Form.waiting_train_type)

@dp.message(Form.waiting_train_type)
async def process_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_PDS, BTN_GRUZ, BTN_REZERV, BTN_LAB, BTN_KHOZ, BTN_SPLOTKA, BTN_PEREGONKA, BTN_NO_INFO]: await message.answer("❌ Выберите из списка:"); return
    user_data[message.from_user.id]["train_type"] = tt
    user_data[message.from_user.id]["is_multiple"] = False
    user_data[message.from_user.id]["is_transfer"] = False
    if tt == BTN_PDS:
        await message.answer("🚆 Введите номер поезда или часть:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_train_number)
    elif tt == BTN_GRUZ:
        user_data[message.from_user.id]["train_number"] = "Грузовой"
        await message.answer("🚛 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif tt == BTN_REZERV:
        user_data[message.from_user.id]["train_number"] = "Резерв"
        await message.answer("🔄 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif tt == BTN_LAB:
        user_data[message.from_user.id]["train_number"] = "Лаборатория"
        await message.answer("🔬 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif tt == BTN_KHOZ:
        user_data[message.from_user.id]["train_number"] = "Хозяйственный"
        await message.answer("🛠 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif tt == BTN_SPLOTKA:
        user_data[message.from_user.id]["is_multiple"] = True
        user_data[message.from_user.id]["multiple_units"] = [{"series": user_data[message.from_user.id]["series"], "number": user_data[message.from_user.id]["number"]}]
        await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n• {get_loco_name(user_data[message.from_user.id]['series'], user_data[message.from_user.id]['number'])}\n\nЧто дальше?", reply_markup=get_multiple_action_keyboard())
        await state.set_state(Form.waiting_multiple_action)
    elif tt == BTN_PEREGONKA:
        user_data[message.from_user.id]["is_transfer"] = True
        user_data[message.from_user.id]["transfer_data"] = {"main": {"series": user_data[message.from_user.id]["series"], "number": user_data[message.from_user.id]["number"]}, "towed": []}
        await message.answer(f"➡️🚂 <b>Перегонка:</b>\n\n <b>Основной:</b> {get_loco_name(user_data[message.from_user.id]['series'], user_data[message.from_user.id]['number'])}\n\nКатегория для перегоняемого:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_transfer_towed_category)
    else:
        user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
        await message.answer("🤷 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)

@dp.message(Form.waiting_train_number)
async def process_train_number(message: types.Message, state: FSMContext):
    if message.text.strip().lower() == "нет":
        user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
        await message.answer(" Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction); return
    results = find_train_by_query(message.text.strip())
    if len(results) == 0:
        user_data[message.from_user.id]["train_number"] = message.text.strip().upper()
        await message.answer(f"ℹ️ Поезд <b>{message.text.strip().upper()}</b> не найден.\n\n🚆 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif len(results) == 1:
        tn, info = results[0]
        user_data[message.from_user.id]["train_number"] = tn
        await message.answer(f"✅ Поезд: <b>{tn} «{info['name']}»</b>\n\n Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    else:
        user_data[message.from_user.id]["found_trains"] = results
        kb = [[KeyboardButton(text=f"{tn} — {info['name']} ({info['route']})")] for tn, info in results]
        kb.append([KeyboardButton(text=BTN_NONE_LIST)])
        await message.answer("🔍 Найдено несколько:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(Form.waiting_train_select)

@dp.message(Form.waiting_train_select)
async def process_train_select(message: types.Message, state: FSMContext):
    if message.text == BTN_NONE_LIST:
        await message.answer("️ Введите номер:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_train_number_manual); return
    for tn, info in user_data[message.from_user.id].get("found_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["train_number"] = tn
            await message.answer(f"✅ Поезд: <b>{tn} «{info['name']}»</b>\n\n🚆 Направление?", reply_markup=get_directions_keyboard())
            await state.set_state(Form.waiting_direction); return
    await message.answer("❌ Выберите из списка:")

@dp.message(Form.waiting_train_number_manual)
async def process_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["train_number"] = tn
    await message.answer(f"🚆 Номер: <b>{tn}</b>\n\nНаправление?", reply_markup=get_directions_keyboard())
    await state.set_state(Form.waiting_direction)

@dp.message(Form.waiting_multiple_action)
async def process_multiple_action(message: types.Message, state: FSMContext):
    if message.text == BTN_ADD_MULTIPLE:
        await message.answer("📂 Категория для следующего:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_multiple_series_category)
    elif message.text == BTN_FINISH:
        await message.answer("🗺 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    else: await message.answer("❌ Выберите действие:", reply_markup=get_multiple_action_keyboard())

@dp.message(Form.waiting_multiple_series_category)
async def process_multiple_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Выберите из списка:"); return
    user_data[message.from_user.id]["temp_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nСерия:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.waiting_multiple_series)

@dp.message(Form.waiting_multiple_series)
async def process_multiple_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer(" Категория:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_multiple_series_category); return
    cat = user_data[message.from_user.id]["temp_category"]
    if message.text not in TRAIN_SERIES[cat]: await message.answer(" Выберите из списка:"); return
    user_data[message.from_user.id]["temp_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nНомер:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.waiting_multiple_number)

@dp.message(Form.waiting_multiple_number)
async def process_multiple_number(message: types.Message, state: FSMContext):
    num = message.text.strip()
    if not num or len(num) > 10: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["multiple_units"].append({"series": user_data[message.from_user.id]["temp_series"], "number": num})
    units = user_data[message.from_user.id]["multiple_units"]
    await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n" + "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units]) + f"\n\n✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_series'], num)}</b>\n\nЧто дальше?", reply_markup=get_multiple_action_keyboard())
    await state.set_state(Form.waiting_multiple_action)

@dp.message(Form.waiting_transfer_towed_category)
async def process_transfer_towed_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Выберите из списка:"); return
    user_data[message.from_user.id]["temp_towed_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nСерия для перегоняемого:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.waiting_transfer_towed_series)

@dp.message(Form.waiting_transfer_towed_series)
async def process_transfer_towed_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Категория:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_transfer_towed_category); return
    cat = user_data[message.from_user.id]["temp_towed_category"]
    if message.text not in TRAIN_SERIES[cat]: await message.answer("❌ Выберите из списка:"); return
    user_data[message.from_user.id]["temp_towed_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nНомер перегоняемого:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.waiting_transfer_towed_number)

@dp.message(Form.waiting_transfer_towed_number)
async def process_transfer_towed_number(message: types.Message, state: FSMContext):
    num = message.text.strip()
    if not num or len(num) > 10: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["transfer_data"]["towed"].append({"series": user_data[message.from_user.id]["temp_towed_series"], "number": num})
    td = user_data[message.from_user.id]["transfer_data"]
    await message.answer(f"➡️🚂 <b>Перегонка:</b>\n\n🚂 <b>Основной:</b> {get_loco_name(td['main']['series'], td['main']['number'])}\n🚂 <b>Перегоняемые:</b>\n" + "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in td['towed']]) + f"\n\n✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_towed_series'], num)}</b>\n\nЧто дальше?", reply_markup=get_transfer_action_keyboard())
    await state.set_state(Form.waiting_transfer_action)

@dp.message(Form.waiting_transfer_action)
async def process_transfer_action(message: types.Message, state: FSMContext):
    if message.text == BTN_ADD_TRANSFER:
        await message.answer("📂 Категория для следующего:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_transfer_towed_category)
    elif message.text == BTN_FINISH:
        await message.answer("️🚂 Перегонка под каким поездом?\n\nТип поезда:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_GRUZ)], [KeyboardButton(text=BTN_PDS)], [KeyboardButton(text=BTN_NO_INFO)]], resize_keyboard=True))
        await state.set_state(Form.waiting_transfer_train_type)
    else: await message.answer("❌ Выберите действие:", reply_markup=get_transfer_action_keyboard())

@dp.message(Form.waiting_transfer_train_type)
async def process_transfer_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_GRUZ, BTN_PDS, BTN_NO_INFO]: await message.answer("❌ Выберите из списка:"); return
    user_data[message.from_user.id]["transfer_train_type"] = tt
    if tt == BTN_GRUZ:
        user_data[message.from_user.id]["transfer_train_number"] = "Грузовой"
        await message.answer("🗺 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif tt == BTN_PDS:
        await message.answer(" Введите номер поезда:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_transfer_train_number)
    else:
        user_data[message.from_user.id]["transfer_train_number"] = BTN_NO_INFO
        await message.answer(" Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)

@dp.message(Form.waiting_transfer_train_number)
async def process_transfer_train_number(message: types.Message, state: FSMContext):
    if message.text.strip().lower() == "нет":
        user_data[message.from_user.id]["transfer_train_number"] = BTN_NO_INFO
        await message.answer("🗺 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction); return
    results = find_train_by_query(message.text.strip())
    if len(results) == 0:
        user_data[message.from_user.id]["transfer_train_number"] = message.text.strip().upper()
        await message.answer(f"ℹ️ Поезд <b>{message.text.strip().upper()}</b> не найден.\n\n🗺 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif len(results) == 1:
        tn, info = results[0]
        user_data[message.from_user.id]["transfer_train_number"] = tn
        await message.answer(f"✅ Поезд: <b>{tn} «{info['name']}»</b>\n\n🗺 Направление?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    else:
        user_data[message.from_user.id]["found_transfer_trains"] = results
        kb = [[KeyboardButton(text=f"{tn} — {info['name']} ({info['route']})")] for tn, info in results]
        kb.append([KeyboardButton(text=BTN_NONE_LIST)])
        await message.answer("🔍 Найдено несколько:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(Form.waiting_transfer_train_select)

@dp.message(Form.waiting_transfer_train_select)
async def process_transfer_train_select(message: types.Message, state: FSMContext):
    if message.text == BTN_NONE_LIST:
        await message.answer("✏️ Введите номер:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_transfer_train_number_manual); return
    for tn, info in user_data[message.from_user.id].get("found_transfer_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["transfer_train_number"] = tn
            await message.answer(f"✅ Поезд: <b>{tn} «{info['name']}»</b>\n\n Направление?", reply_markup=get_directions_keyboard())
            await state.set_state(Form.waiting_direction); return
    await message.answer("❌ Выберите из списка:")

@dp.message(Form.waiting_transfer_train_number_manual)
async def process_transfer_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["transfer_train_number"] = tn
    await message.answer(f"🚆 Номер: <b>{tn}</b>\n\nНаправление?", reply_markup=get_directions_keyboard())
    await state.set_state(Form.waiting_direction)

@dp.message(Form.waiting_direction)
async def process_direction(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введите направление:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_direction_manual); return
    if message.text not in DIRECTIONS: await message.answer("❌ Выберите из списка:"); return
    user_data[message.from_user.id]["direction"] = message.text
    await message.answer("📍 Где заметили поезд?", reply_markup=get_stations_keyboard())
    await state.set_state(Form.waiting_station)

@dp.message(Form.waiting_direction_manual)
async def process_direction_manual(message: types.Message, state: FSMContext):
    d = message.text.strip()
    if not d or len(d) > 50: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["direction"] = d
    await message.answer(f"🗺 Направление: <b>{d}</b>\n\n📍 Где заметили?", reply_markup=get_stations_keyboard())
    await state.set_state(Form.waiting_station)

@dp.message(Form.waiting_station)
async def process_station(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введите станцию/О.П.:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_station_manual); return
    if message.text not in STATIONS: await message.answer(" Выберите из списка:"); return
    user_data[message.from_user.id]["station"] = message.text
    await message.answer("🕐 Во сколько?\n\nФормат <b>ЧЧ:ММ</b> или кнопка:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏰ Сейчас", callback_data="time_now")]]))
    await state.set_state(Form.waiting_time)

@dp.message(Form.waiting_station_manual)
async def process_station_manual(message: types.Message, state: FSMContext):
    s = message.text.strip()
    if not s or len(s) > 100: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["station"] = s
    await message.answer(f"📍 Место: <b>{format_station(s)}</b>\n\n🕐 Во сколько?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏰ Сейчас", callback_data="time_now")]]))
    await state.set_state(Form.waiting_time)

@dp.message(Form.waiting_time)
async def process_time(message: types.Message, state: FSMContext):
    try:
        if ":" not in message.text: raise ValueError
        h, m = map(int, message.text.strip().split(":"))
        if h < 0 or h > 24 or m < 0 or m > 59 or (h == 24 and m != 0): raise ValueError
    except ValueError: await message.answer("❌ Формат <b>ЧЧ:ММ</b>:"); return
    user_data[message.from_user.id]["time"] = f"{h:02d}:{m:02d}"
    await message.answer(" <b>Есть фото?</b>\n\nОтправьте или нажмите:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=" Нет фото", callback_data="no_photo")]]))
    await state.set_state(Form.waiting_photo)

@dp.callback_query(F.data == "time_now")
async def time_now_callback(callback: types.CallbackQuery, state: FSMContext):
    now = get_moscow_now()
    user_data[callback.from_user.id]["time"] = f"{now.hour:02d}:{now.minute:02d}"
    await callback.message.answer("📸 <b>Есть фото?</b>\n\nОтправьте или нажмите:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Нет фото", callback_data="no_photo")]]))
    await state.set_state(Form.waiting_photo)
    await callback.answer()

@dp.message(Form.waiting_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]["photo_id"] = message.photo[-1].file_id
    await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
    await state.set_state(Form.waiting_confirmation)

@dp.callback_query(F.data == "no_photo")
async def no_photo_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(build_summary(callback.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
    await state.set_state(Form.waiting_confirmation)
    await callback.answer()

@dp.message(Form.waiting_confirmation, F.text == BTN_ADD_DESCRIPTION)
async def ask_description(message: types.Message, state: FSMContext):
    await message.answer("✏️ Описание (до 500 символов):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_SKIP_DESCRIPTION)]], resize_keyboard=True))
    await state.set_state(Form.waiting_description)

@dp.message(Form.waiting_description)
async def save_description(message: types.Message, state: FSMContext):
    if message.text == BTN_SKIP_DESCRIPTION: user_data[message.from_user.id]["description"] = None
    else:
        text = message.text.strip()
        if len(text) > 500: await message.answer("❌ Длинно. Макс 500 символов:"); return
        user_data[message.from_user.id]["description"] = text
    await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
    await state.set_state(Form.waiting_confirmation)

@dp.message(Form.waiting_confirmation)
async def process_confirmation(message: types.Message, state: FSMContext):
    if message.text == "✅ Да, всё верно":
        data = user_data[message.from_user.id]
        pending_publications[message.from_user.id] = {"text": build_channel_message(data), "photo_id": data.get("photo_id")}
        admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
        for aid in admin_ids:
            try:
                if data.get("photo_id"): await bot.send_photo(aid, photo=data["photo_id"], caption=build_admin_message(data, message.from_user), reply_markup=get_admin_keyboard(message.from_user.id))
                else: await bot.send_message(aid, build_admin_message(data, message.from_user), reply_markup=get_admin_keyboard(message.from_user.id))
            except Exception as e: logging.error(f"Ошибка: {e}")
        await message.answer("✅ Отправлено админам.\n\n/start для новой", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        user_data.pop(message.from_user.id, None)
    elif message.text == "❌ Нет, изменить":
        await message.answer("✏️ Что изменить?", reply_markup=get_edit_fields_keyboard(user_data[message.from_user.id].get("is_multiple", False), user_data[message.from_user.id].get("is_transfer", False)))
        await state.set_state(Form.edit_what)
    else: await message.answer("Выберите вариант:")

@dp.message(Form.edit_what)
async def process_edit_what(message: types.Message, state: FSMContext):
    data = user_data[message.from_user.id]
    is_mult = data.get("is_multiple", False)
    is_trans = data.get("is_transfer", False)
    if message.text == BTN_SPLOTKA and is_mult:
        await message.answer("🚂🚂 <b>Сплотка:</b>", reply_markup=get_edit_multiple_keyboard(data.get("multiple_units", [])), parse_mode="HTML")
        await state.set_state(Form.edit_multiple_action); return
    if message.text == BTN_PEREGONKA and is_trans:
        await message.answer("➡️ <b>Перегонка:</b>", reply_markup=get_edit_transfer_keyboard(data.get("transfer_data", {})), parse_mode="HTML")
        await state.set_state(Form.edit_transfer_action); return
    if message.text == "Поезд перегонки" and is_trans:
        await message.answer(" Тип поезда:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_GRUZ)], [KeyboardButton(text=BTN_PDS)], [KeyboardButton(text=BTN_NO_INFO)]], resize_keyboard=True))
        await state.set_state(Form.edit_transfer_train_type); return
    if message.text == "ПС":
        await message.answer("📂 Категория:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_series_category)
    elif message.text == "Номер ПС":
        await message.answer(f"🔢 Текущий: <b>{data['number']}</b>\n\nНовый:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_number)
    elif message.text == "Тип поезда":
        await message.answer("🚆 Тип:", reply_markup=get_train_type_keyboard())
        await state.set_state(Form.edit_train_type)
    elif message.text == "Номер поезда":
        await message.answer("🚆 Номер:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_train_number)
    elif message.text == "Направление":
        await message.answer("🗺 Направление:", reply_markup=get_directions_keyboard())
        await state.set_state(Form.edit_direction)
    elif message.text == "Место":
        await message.answer("📍 Станция:", reply_markup=get_stations_keyboard())
        await state.set_state(Form.edit_station)
    elif message.text == "Актуальность":
        await message.answer("🕐 Время (ЧЧ:ММ):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_time)
    elif message.text == BTN_CANCEL_EDIT:
        await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
        await state.set_state(Form.waiting_confirmation)
    else: await message.answer("❌ Выберите поле:", reply_markup=get_edit_fields_keyboard(is_mult, is_trans))

@dp.message(Form.edit_multiple_action)
async def process_edit_multiple_action(message: types.Message, state: FSMContext):
    units = user_data[message.from_user.id].get("multiple_units", [])
    if message.text == BTN_ADD_MULTIPLE:
        await message.answer(" Категория:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_multiple_series_category)
    elif message.text.startswith(BTN_DELETE):
        name = message.text.replace(f"{BTN_DELETE} ", "")
        for i, u in enumerate(units):
            if get_loco_name(u['series'], u['number']) == name: units.pop(i); break
        if not units:
            user_data[message.from_user.id]["is_multiple"] = False
            user_data[message.from_user.id]["train_type"] = BTN_NO_INFO
            user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
            await return_to_summary(message, state, "✅ Сплотка удалена.")
        else:
            await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n" + "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units]) + "\n\n✅ Удален", reply_markup=get_edit_multiple_keyboard(units), parse_mode="HTML")
    elif message.text == BTN_BACK:
        await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
        await state.set_state(Form.waiting_confirmation)
    else: await message.answer("❌ Выберите:", reply_markup=get_edit_multiple_keyboard(units))

@dp.message(Form.edit_multiple_series_category)
async def process_edit_multiple_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer(" Выберите:"); return
    user_data[message.from_user.id]["temp_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nСерия:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.edit_multiple_series)

@dp.message(Form.edit_multiple_series)
async def process_edit_multiple_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Категория:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_multiple_series_category); return
    cat = user_data[message.from_user.id]["temp_category"]
    if message.text not in TRAIN_SERIES[cat]: await message.answer("❌ Выберите:"); return
    user_data[message.from_user.id]["temp_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nНомер:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.edit_multiple_number)

@dp.message(Form.edit_multiple_number)
async def process_edit_multiple_number(message: types.Message, state: FSMContext):
    num = message.text.strip()
    if not num or len(num) > 10: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["multiple_units"].append({"series": user_data[message.from_user.id]["temp_series"], "number": num})
    units = user_data[message.from_user.id]["multiple_units"]
    await message.answer(f"🚂 <b>Сплотка:</b>\n\n" + "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units]) + f"\n\n✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_series'], num)}</b>", reply_markup=get_edit_multiple_keyboard(units), parse_mode="HTML")
    await state.set_state(Form.edit_multiple_action)

@dp.message(Form.edit_transfer_action)
async def process_edit_transfer_action(message: types.Message, state: FSMContext):
    td = user_data[message.from_user.id].get("transfer_data", {})
    if message.text == BTN_ADD_TRANSFER:
        await message.answer(" Категория:", reply_markup=get_series_categories_keyboard())
        user_data[message.from_user.id]["is_editing_main"] = False
        await state.set_state(Form.edit_transfer_towed_category)
    elif message.text.startswith("🚂 Основной:"):
        await message.answer("📂 Категория для основного:", reply_markup=get_series_categories_keyboard())
        user_data[message.from_user.id]["is_editing_main"] = True
        await state.set_state(Form.edit_transfer_towed_category)
    elif message.text.startswith(BTN_DELETE_TRANSFER):
        name = message.text.replace(f"{BTN_DELETE_TRANSFER} ", "")
        for i, u in enumerate(td.get("towed", [])):
            if get_loco_name(u['series'], u['number']) == name: td["towed"].pop(i); break
        if not td.get("towed"):
            user_data[message.from_user.id]["is_transfer"] = False
            user_data[message.from_user.id]["train_type"] = BTN_NO_INFO
            await return_to_summary(message, state, "✅ Перегонка удалена.")
        else:
            await message.answer(f"➡️🚂 <b>Перегонка:</b>\n\n🚂 <b>Основной:</b> {get_loco_name(td['main']['series'], td['main']['number'])}\n🚂 <b>Перегоняемые:</b>\n" + "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in td['towed']]) + "\n\n✅ Удален", reply_markup=get_edit_transfer_keyboard(td), parse_mode="HTML")
    elif message.text == BTN_BACK:
        await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
        await state.set_state(Form.waiting_confirmation)
    else: await message.answer("❌ Выберите:", reply_markup=get_edit_transfer_keyboard(td))

@dp.message(Form.edit_transfer_towed_category)
async def process_edit_transfer_towed_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Выберите:"); return
    user_data[message.from_user.id]["temp_towed_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nСерия:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.edit_transfer_towed_series)

@dp.message(Form.edit_transfer_towed_series)
async def process_edit_transfer_towed_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Категория:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_transfer_towed_category); return
    cat = user_data[message.from_user.id]["temp_towed_category"]
    if message.text not in TRAIN_SERIES[cat]: await message.answer("❌ Выберите:"); return
    user_data[message.from_user.id]["temp_towed_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nНомер:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.edit_transfer_towed_number)

@dp.message(Form.edit_transfer_towed_number)
async def process_edit_transfer_towed_number(message: types.Message, state: FSMContext):
    num = message.text.strip()
    if not num or len(num) > 10: await message.answer("❌ Некорректно:"); return
    is_main = user_data[message.from_user.id].get("is_editing_main", False)
    if is_main:
        user_data[message.from_user.id]["transfer_data"]["main"] = {"series": user_data[message.from_user.id]["temp_towed_series"], "number": num}
        user_data[message.from_user.id]["is_editing_main"] = False
        msg = "✅ Основной изменен"
    else:
        user_data[message.from_user.id]["transfer_data"]["towed"].append({"series": user_data[message.from_user.id]["temp_towed_series"], "number": num})
        msg = f"✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_towed_series'], num)}</b>"
    td = user_data[message.from_user.id]["transfer_data"]
    await message.answer(f"➡️ <b>Перегонка:</b>\n\n🚂 <b>Основной:</b> {get_loco_name(td['main']['series'], td['main']['number'])}\n🚂 <b>Перегоняемые:</b>\n" + "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in td['towed']]) + f"\n\n{msg}", reply_markup=get_edit_transfer_keyboard(td), parse_mode="HTML")
    await state.set_state(Form.edit_transfer_action)

@dp.message(Form.edit_transfer_train_type)
async def process_edit_transfer_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_GRUZ, BTN_PDS, BTN_NO_INFO]: await message.answer("❌ Выберите:"); return
    user_data[message.from_user.id]["transfer_train_type"] = tt
    if tt == BTN_GRUZ:
        user_data[message.from_user.id]["transfer_train_number"] = "Грузовой"
        await return_to_summary(message, state, "✅ Поезд: <b>Грузовой</b>")
    elif tt == BTN_PDS:
        await message.answer("🚆 Номер:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_transfer_train_number)
    else:
        user_data[message.from_user.id]["transfer_train_number"] = BTN_NO_INFO
        await return_to_summary(message, state, "✅ Поезд: <b>Нет информации</b>")

@dp.message(Form.edit_transfer_train_number)
async def process_edit_transfer_train_number(message: types.Message, state: FSMContext):
    if message.text.strip().lower() == "нет":
        user_data[message.from_user.id]["transfer_train_number"] = BTN_NO_INFO
        await return_to_summary(message, state, "✅ Очищен"); return
    results = find_train_by_query(message.text.strip())
    if len(results) == 0:
        user_data[message.from_user.id]["transfer_train_number"] = message.text.strip().upper()
        await return_to_summary(message, state, f"✅ Поезд: <b>{message.text.strip().upper()}</b>")
    elif len(results) == 1:
        tn, info = results[0]
        user_data[message.from_user.id]["transfer_train_number"] = tn
        await return_to_summary(message, state, f"✅ Поезд: <b>{tn} «{info['name']}»</b>")
    else:
        user_data[message.from_user.id]["found_transfer_trains"] = results
        kb = [[KeyboardButton(text=f"{tn} — {info['name']} ({info['route']})")] for tn, info in results]
        kb.append([KeyboardButton(text=BTN_NONE_LIST)])
        await message.answer("🔍 Найдено:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(Form.edit_transfer_train_select)

@dp.message(Form.edit_transfer_train_select)
async def process_edit_transfer_train_select(message: types.Message, state: FSMContext):
    if message.text == BTN_NONE_LIST:
        await message.answer("️ Введите:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_transfer_train_number_manual); return
    for tn, info in user_data[message.from_user.id].get("found_transfer_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["transfer_train_number"] = tn
            await return_to_summary(message, state, f"✅ Поезд: <b>{tn} «{info['name']}»</b>"); return
    await message.answer("❌ Выберите:")

@dp.message(Form.edit_transfer_train_number_manual)
async def process_edit_transfer_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["transfer_train_number"] = tn
    await return_to_summary(message, state, f"✅ Поезд: <b>{tn}</b>")

@dp.message(Form.edit_series_category)
async def edit_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Выберите:"); return
    user_data[message.from_user.id]["category"] = message.text
    await message.answer(f" Категория: <b>{message.text}</b>\n\nСерия:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.edit_series)

@dp.message(Form.edit_series)
async def edit_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Категория:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_series_category); return
    cat = user_data[message.from_user.id]["category"]
    if message.text not in TRAIN_SERIES[cat]: await message.answer(" Выберите:"); return
    user_data[message.from_user.id]["series"] = message.text
    await return_to_summary(message, state, f"✅ Серия: <b>{message.text}</b>")

@dp.message(Form.edit_number)
async def edit_number(message: types.Message, state: FSMContext):
    num = message.text.strip()
    if not num or len(num) > 10: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["number"] = num
    await return_to_summary(message, state, f"✅ Номер: <b>{num}</b>")

@dp.message(Form.edit_train_type)
async def edit_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_PDS, BTN_GRUZ, BTN_REZERV, BTN_LAB, BTN_KHOZ, BTN_SPLOTKA, BTN_PEREGONKA, BTN_NO_INFO]: await message.answer("❌ Выберите:"); return
    user_data[message.from_user.id]["train_type"] = tt
    if tt == BTN_PDS:
        await message.answer("🚆 Номер:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_train_number)
    elif tt == BTN_GRUZ:
        user_data[message.from_user.id]["train_number"] = "Грузовой"
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип: <b>Грузовой</b>")
    elif tt == BTN_REZERV:
        user_data[message.from_user.id]["train_number"] = "Резерв"
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип: <b>Резерв</b>")
    elif tt == BTN_LAB:
        user_data[message.from_user.id]["train_number"] = "Лаборатория"
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип: <b>Лаборатория</b>")
    elif tt == BTN_KHOZ:
        user_data[message.from_user.id]["train_number"] = "Хозяйственный"
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип: <b>Хозяйственный</b>")
    elif tt == BTN_SPLOTKA:
        user_data[message.from_user.id]["is_multiple"] = True
        user_data[message.from_user.id]["is_transfer"] = False
        user_data[message.from_user.id]["multiple_units"] = []
        await message.answer("📂 Категория:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_multiple_series_category)
    elif tt == BTN_PEREGONKA:
        user_data[message.from_user.id]["is_transfer"] = True
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["transfer_data"] = {"main": {}, "towed": []}
        await message.answer("📂 Категория:", reply_markup=get_series_categories_keyboard())
        user_data[message.from_user.id]["is_editing_main"] = True
        await state.set_state(Form.edit_transfer_towed_category)
    else:
        user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип: <b>Нет информации</b>")

@dp.message(Form.edit_train_number)
async def edit_train_number(message: types.Message, state: FSMContext):
    if message.text.strip().lower() == "нет":
        user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
        await return_to_summary(message, state, "✅ Очищен"); return
    results = find_train_by_query(message.text.strip())
    if len(results) == 0:
        user_data[message.from_user.id]["train_number"] = message.text.strip().upper()
        await return_to_summary(message, state, f"✅ Номер: <b>{message.text.strip().upper()}</b>")
    elif len(results) == 1:
        tn, info = results[0]
        user_data[message.from_user.id]["train_number"] = tn
        await return_to_summary(message, state, f"✅ Поезд: <b>{tn} «{info['name']}»</b>")
    else:
        user_data[message.from_user.id]["found_trains"] = results
        kb = [[KeyboardButton(text=f"{tn} — {info['name']} ({info['route']})")] for tn, info in results]
        kb.append([KeyboardButton(text=BTN_NONE_LIST)])
        await message.answer("🔍 Найдено:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(Form.edit_train_select)

@dp.message(Form.edit_train_select)
async def edit_train_select(message: types.Message, state: FSMContext):
    if message.text == BTN_NONE_LIST:
        await message.answer("✏️ Введите:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_train_number_manual); return
    for tn, info in user_data[message.from_user.id].get("found_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["train_number"] = tn
            await return_to_summary(message, state, f"✅ Поезд: <b>{tn} «{info['name']}»</b>"); return
    await message.answer("❌ Выберите:")

@dp.message(Form.edit_train_number_manual)
async def edit_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["train_number"] = tn
    await return_to_summary(message, state, f"✅ Номер: <b>{tn}</b>")

@dp.message(Form.edit_direction)
async def edit_direction(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введите:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_direction_manual); return
    if message.text not in DIRECTIONS: await message.answer("❌ Выберите:"); return
    user_data[message.from_user.id]["direction"] = message.text
    await return_to_summary(message, state, f"✅ Направление: <b>{message.text}</b>")

@dp.message(Form.edit_direction_manual)
async def edit_direction_manual(message: types.Message, state: FSMContext):
    d = message.text.strip()
    if not d or len(d) > 50: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["direction"] = d
    await return_to_summary(message, state, f"✅ Направление: <b>{d}</b>")

@dp.message(Form.edit_station)
async def edit_station(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("️ Введите:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_station_manual); return
    if message.text not in STATIONS: await message.answer("❌ Выберите:"); return
    user_data[message.from_user.id]["station"] = message.text
    await return_to_summary(message, state, f"✅ Место: <b>{format_station(message.text)}</b>")

@dp.message(Form.edit_station_manual)
async def edit_station_manual(message: types.Message, state: FSMContext):
    s = message.text.strip()
    if not s or len(s) > 100: await message.answer("❌ Некорректно:"); return
    user_data[message.from_user.id]["station"] = s
    await return_to_summary(message, state, f"✅ Место: <b>{format_station(s)}</b>")

@dp.message(Form.edit_time)
async def edit_time(message: types.Message, state: FSMContext):
    try:
        if ":" not in message.text: raise ValueError
        h, m = map(int, message.text.strip().split(":"))
        if h < 0 or h > 24 or m < 0 or m > 59 or (h == 24 and m != 0): raise ValueError
    except ValueError: await message.answer("❌ Формат ЧЧ:ММ:"); return
    user_data[message.from_user.id]["time"] = f"{h:02d}:{m:02d}"
    await return_to_summary(message, state, f"✅ Время: <b>{f'{h:02d}:{m:02d}'}</b>")

@dp.callback_query(F.data.startswith("publish:"))
async def admin_publish(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids: await callback.answer("❌ Нет прав", show_alert=True); return
    if uid not in pending_publications: await callback.answer("⚠️ Уже обработано", show_alert=True); return
    pub_data = pending_publications.pop(uid, None)
    if pub_data and CHANNEL_ID:
        try:
            if pub_data.get("photo_id"): await bot.send_photo(CHANNEL_ID, photo=pub_data["photo_id"], caption=pub_data["text"], parse_mode=ParseMode.HTML)
            else: await bot.send_message(CHANNEL_ID, text=pub_data["text"], parse_mode=ParseMode.HTML)
        except Exception as e: logging.error(f"Ошибка: {e}")
    
    # УВЕДОМЛЕНИЕ ГЛАВНОМУ АДМИНУ
    if MAIN_ADMIN_ID:
        try:
            admin_un = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
            user_mention = "пользователь"
            try:
                if callback.message.caption and "от @" in callback.message.caption: user_mention = "@" + callback.message.caption.split("от @")[1].split("</b>")[0]
                elif callback.message.text and "от @" in callback.message.text: user_mention = "@" + callback.message.text.split("от @")[1].split("</b>")[0]
            except: pass
            await bot.send_message(MAIN_ADMIN_ID, f"✅ <b>Одобрено</b>\n\n👤 <b>Автор:</b> {user_mention}\n <b>Админ:</b> {admin_un}\n⏰ <b>Время:</b> {get_moscow_now().strftime('%H:%M')}", parse_mode=ParseMode.HTML)
        except Exception as e: logging.error(f"Ошибка уведомления: {e}")
    
    if callback.message.photo: await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ <b>ОПУБЛИКОВАНО</b>", parse_mode=ParseMode.HTML)
    else: await callback.message.edit_text(text=callback.message.text + "\n\n✅ <b>ОПУБЛИКОВАНО</b>", parse_mode=ParseMode.HTML)
    try: await bot.send_message(uid, "✅ Опубликовано!")
    except: pass
    await callback.answer("✅ Опубликовано", show_alert=True)

@dp.callback_query(F.data.startswith("reject:"))
async def admin_reject(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    uid = int(parts[1])
    reason_code = parts[2] if len(parts) > 2 else None
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids: await callback.answer("❌ Нет прав", show_alert=True); return
    if uid not in pending_publications: await callback.answer("⚠️ Уже обработано", show_alert=True); return
    pending_publications.pop(uid, None)
    reason_text = ""
    if reason_code and reason_code in REJECT_REASONS: reason_text = REJECT_REASONS[reason_code]
    elif reason_code == "custom":
        pending_rejections[uid] = {"admin_id": callback.from_user.id, "message_id": callback.message.message_id, "chat_id": callback.message.chat.id, "is_photo": bool(callback.message.photo), "original_caption": callback.message.caption if callback.message.photo else None, "original_text": callback.message.text if not callback.message.photo else None, "user_id": uid, "time": get_moscow_now().strftime("%H:%M")}
        await callback.message.answer("✏️ Причина (до 300 символов):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_REJECT_CANCEL, callback_data=f"cancel_reject:{uid}")]]))
        await callback.answer(); return
    else: reason_text = "Причина не указана"
    user_mention = "пользователь"
    try:
        if callback.message.caption and "от @" in callback.message.caption: user_mention = "@" + callback.message.caption.split("от @")[1].split("</b>")[0]
        elif callback.message.text and "от @" in callback.message.text: user_mention = "@" + callback.message.text.split("от @")[1].split("</b>")[0]
        await bot.send_message(uid, f" Отклонено.\n\n<b>Причина:</b> {reason_text}", parse_mode=ParseMode.HTML)
    except: pass
    if MAIN_ADMIN_ID and reason_text:
        try:
            admin_un = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
            await bot.send_message(MAIN_ADMIN_ID, f"🚫 <b>Отклонено</b>\n\n👤 <b>Автор:</b> {user_mention}\n <b>Админ:</b> {admin_un}\n⏰ <b>Время:</b> {get_moscow_now().strftime('%H:%M')}\n📋 <b>Причина:</b> {reason_text}", parse_mode=ParseMode.HTML)
        except Exception as e: logging.error(f"Ошибка: {e}")
    if callback.message.photo: await callback.message.edit_caption(caption=callback.message.caption + f"\n\n❌ <b>ОТКЛОНЕНО</b>\nПричина: {reason_text}", parse_mode=ParseMode.HTML)
    else: await callback.message.edit_text(text=callback.message.text + f"\n\n❌ <b>ОТКЛОНЕНО</b>\nПричина: {reason_text}", parse_mode=ParseMode.HTML)
    await callback.answer("❌ Отклонено", show_alert=True)

@dp.callback_query(F.data.startswith("cancel_reject:"))
async def cancel_reject(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids: await callback.answer("❌ Нет прав", show_alert=True); return
    pending_rejections.pop(uid, None)
    await callback.message.delete()
    await callback.answer("Отменено")

@dp.callback_query(F.data.startswith("ban:"))
async def admin_ban(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids: await callback.answer("❌ Нет прав", show_alert=True); return
    if uid in admin_ids: await callback.answer("❌ Нельзя банить админа!", show_alert=True); return
    BLACKLIST.add(uid)
    pending_publications.pop(uid, None)
    if callback.message.photo: await callback.message.edit_caption(caption=callback.message.caption + "\n\n🚫 <b>ЗАБАНЕН</b>", parse_mode=ParseMode.HTML)
    else: await callback.message.edit_text(text=callback.message.text + "\n\n🚫 <b>ЗАБАНЕН</b>", parse_mode=ParseMode.HTML)
    await callback.answer("🚫 Забанен", show_alert=True)

app = FastAPI()
WEBHOOK_URL = "https://skzd-bot.vercel.app/webhook"

@app.on_event("startup")
async def on_startup():
    try:
        await bot.set_webhook(url=WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
        print("✅ Webhook установлен!")
    except Exception as e: print(f"❌ Ошибка: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    print("👋 Webhook удален!")

webhook_installed = False

@app.post("/webhook")
async def webhook(request: Request):
    global webhook_installed
    if not webhook_installed:
        try:
            info = await bot.get_webhook_info()
            if info.url != WEBHOOK_URL:
                await bot.set_webhook(url=WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
                print("✅ Webhook обновлен!")
            webhook_installed = True
        except Exception as e: print(f"❌ Ошибка: {e}")
    try:
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
        return JSONResponse({"ok": True})
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse({"ok": False}, status_code=500)

from aiogram.exceptions import TelegramBadRequest

@dp.errors()
async def errors_handler(event: types.ErrorEvent):
    if isinstance(event.exception, TelegramBadRequest):
        if "message is not modified" in str(event.exception): return True
        if "query is too old" in str(event.exception): return True
    return False

@app.get("/")
@app.head("/")
async def root(): return {"message": "Bot is running! 🚂"}

@dp.message(F.text)
async def handle_reject_reason(message: types.Message):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if message.from_user.id not in admin_ids: return
    for uid, data in list(pending_rejections.items()):
        if data["admin_id"] == message.from_user.id:
            reason_text = message.text.strip()[:300]
            try:
                if data["is_photo"]:
                    orig = data.get("original_caption") or ""
                    await bot.edit_message_caption(chat_id=data["chat_id"], message_id=data["message_id"], caption=orig + f"\n\n❌ <b>ОТКЛОНЕНО</b>\nПричина: {reason_text}", parse_mode=ParseMode.HTML)
                else:
                    orig = data.get("original_text") or ""
                    await bot.edit_message_text(chat_id=data["chat_id"], message_id=data["message_id"], text=orig + f"\n\n❌ <b>ОТКЛОНЕНО</b>\nПричина: {reason_text}", parse_mode=ParseMode.HTML)
            except Exception as e: logging.error(f"Ошибка: {e}")
            try: await bot.send_message(uid, f"❌ Отклонено.\n\n<b>Причина:</b> {reason_text}", parse_mode=ParseMode.HTML)
            except: pass
            if MAIN_ADMIN_ID:
                try:
                    admin_un = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
                    user_mention = f"@{data.get('user_mention', 'пользователь')}"
                    await bot.send_message(MAIN_ADMIN_ID, f" <b>Отклонено</b>\n\n👤 <b>Автор:</b> {user_mention}\n👮 <b>Админ:</b> {admin_un}\n <b>Время:</b> {data.get('time', get_moscow_now().strftime('%H:%M'))}\n📋 <b>Причина:</b> {reason_text}", parse_mode=ParseMode.HTML)
                except Exception as e: logging.error(f"Ошибка: {e}")
            pending_rejections.pop(uid, None)
            await message.answer("✅ Отправлено.")
            return

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
