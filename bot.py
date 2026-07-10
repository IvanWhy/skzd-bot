import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.enums import ParseMode
from aiohttp import web
import os
import ast

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # ID канала для публикаций # ID канала для публикаций

# Проверка, что токен задан
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения!")

# Преобразуем ADMIN_CHAT_ID из строки в список
if isinstance(ADMIN_CHAT_ID, str):
    ADMIN_CHAT_ID = ast.literal_eval(ADMIN_CHAT_ID)
elif ADMIN_CHAT_ID is None:
    raise ValueError("❌ ADMIN_CHAT_ID не найден в переменных окружения!")
    
# ==================== БАЗА ДАННЫХ ====================
TRAIN_SERIES = {
    "Пассажирские электровозы": ["ЭП20", "ЭП1М", "ЭП1", "ЧС4Т", "ЧС4", "ЭП1П"],
    "Грузовые электровозы": ["2ЭС5К", "ВЛ80Т", "2ЭС4К", "ВЛ80С", "3ЭС5К", "ВЛ10", "ВЛ10У", "ВЛ11", "3ЭС5С", "2ЭС5С", "2ЭС5"],
    "Тепловозы": ["ТЭП70БС", "ТЭП70", "2ТЭ10М", "ТЭМ2", "2ТЭ116", "2ТЭ116У", "3ТЭ116У", "2ТЭ25КМ", "АЧ2", "АС01"],
    "Пригородный ПС": ["ЭД4М", "ЭД9М", "ЭС1", "ЭС2ГП", "РА1", "РА2", "РА3"]             
}

STATIONS = [
    "Азов", "Батайск", "Волгоград-1", "Волгоград-2", "Волгодонская",
    "Горячий ключ", "Ейск", "Зверево", "Кавказская", "Каменская",
    "Керчь", "Кисловодск", "Краснодар-1", "Краснодар-2", "Красный Сулин",
    "Крымск", "Лихая", "Минеральные Воды", "Морозовская", "Новороссийск",
    "Новочеркасск", "Первомайская", "Ростов-Берег", "Ростов-Главный", "Сальск",
    "Сочи", "Ставрополь", "Староминская-Тимашевская", "Таганрог", "Таганрог-пасс",
    "Тимашевск", "Тихорецкая", "Туапсе", "Шахтная"
]

DIRECTIONS = [
    "на Азов", "на Батайск", "на Волгоград", "на Волгодонск", "на Горячий ключ",
    "на Ейск", "на Кавказскую", "на Керчь", "на Краснодар", "на Крымск",
    "на Лихую", "на Минеральные Воды", "на Новороссийск", "на Новочеркасск", "на Ростов",
    "на Ростов-берег", "на Сальск", "на Сочи", "на Ставрополь", "на Таганрог",
    "на Тимашевск", "на Тихорецкую"
]

SCHEDULES = {
    "020С": {"name": "Тихий Дон", "route": "Москва — Ростов", "link": "https://rasp.yandex.ru/thread/R_020S_112"},
    "019С": {"name": "Тихий Дон", "route": "Ростов - Москва", "link": "https://rasp.yandex.ru/thread/R_019S_112"},
    "104В": {"name": "Двухэтажный состав", "route": "Москва — Адлер", "link": "https://rasp.yandex.ru/thread/R_104V_112"},
    "104Ж": {"name": "Двухэтажный состав", "route": "Адлер - Москва", "link": "https://rasp.yandex.ru/thread/R_104ZH_112"},
    "102М": {"name": "Обычный ПДС", "route": "Москва — Адлер", "link": "https://rasp.yandex.ru/thread/R_102M_112"},
    "102С": {"name": "Обычный ПДС", "route": "Адлер - Москва", "link": "https://rasp.yandex.ru/thread/R_102S_112"},
    "030С": {"name": "Премиум", "route": "Москва — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_030S_112"},
    "030Й": {"name": "Премиум", "route": "Новороссийск - Москва", "link": "https://rasp.yandex.ru/thread/R_030J_112"},
    "092М": {"name": "Таврия", "route": "Москва — Севастополь", "link": "https://rasp.yandex.ru/thread/R_092M_63438"},
    "092С": {"name": "Таврия", "route": "Севастополь - Москва", "link": "https://rasp.yandex.ru/thread/R_092S_63438"},
    "028М": {"name": "Таврия/двухэтажный состав", "route": "Москва — Симферополь", "link": "https://rasp.yandex.ru/thread/R_028M_63438"},
    "027С": {"name": "Таврия/двухэтажный состав", "route": "Симферополь - Москва", "link": "https://rasp.yandex.ru/thread/R_028S_63438"},
    "012М": {"name": "Фирменный, Анапа-Москва", "route": "Москва — Анапа", "link": "https://rasp.yandex.ru/thread/R_012M_112"},
    "011Э": {"name": "Фирменный, Анапа-Москва", "route": "Анапа - Москва", "link": "https://rasp.yandex.ru/thread/R_011YE_112"}, 
    "018М": {"name": "Обычный ПДС", "route": "Москва — Симферополь", "link": "https://rasp.yandex.ru/thread/R_018M_63438"},
    "018Й": {"name": "Обычный ПДС", "route": "Симферополь - Москва", "link": "https://rasp.yandex.ru/thread/R_018J_63438"},
    "007А": {"name": "Таврия", "route": "Санкт-Петербург — Керчь", "link": "https://rasp.yandex.ru/thread/R_007A_63438"},
    "008С": {"name": "Таврия", "route": "Керчь - Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_008S_63438"},
    "068Х": {"name": "Обычный ПДС", "route": "Москва — Керчь", "link": "https://rasp.yandex.ru/thread/R_068X_63438"},
    "068С": {"name": "Таврия", "route": "Керчь - Москва", "link": "https://rasp.yandex.ru/thread/R_068S_63438"},
    "004М": {"name": "Фирменный, Кавказ/двухэтажный состав", "route": "Москва — Кисловодск", "link": "https://rasp.yandex.ru/thread/R_004M_112"},
    "930Я": {"name": "Жемчужина Кавказа", "route": "Москва — Москва Казанская Тур", "link": "https://rasp.yandex.ru/thread/R_930YA_112"}
}

LOCO_NICKNAMES = {
    "ЭП20-001": " «Олимп»🟠🔵", "ЭП20-002": " «Буревестник»🟢⚪️", "ЭП20-003": " «Новопид»⚫️🔴",
    "ЭП20-004": " «Новопид»⚫️🔴", "ЭП20-005": " «Новопид»⚫️🔴", "ЭП20-006": " «Буревестник»🟢⚪️",
    "ЭП20-007": " «Новопид»⚫️🔴", "ЭП20-008": " «Новопид»⚫️🔴", "ЭП20-009": " «Новопид»⚫️🔴",
    "ЭП20-010": " «Новопид»⚫️🔴", "ЭП20-014": " «Новопид»⚫️🔴", "ЭП20-016": " «Новопид»⚫️🔴",
    "ЭП20-022": " «Новопид»⚫️🔴", "ЭП20-046": " «Новопид»⚫️🔴", "ЭП20-047": " «Новопид»⚫️🔴",
    "ЭП20-052": " «Новопид»⚫️🔴", "ЭП20-067": " «Новопид»⚫️🔴", "ЭП20-074": " «Новопид»⚫️🔴",
    "2ЭС4К-036": "🟢", "2ЭС4К-055": "🟢", "2ЭС4К-066": "🟢", "2ЭС4К-106": "🟢", 
    "2ЭС4К-121": "🟢", "2ЭС4К-131": "🟢",
    "ЭП1М-411": "🔵 «Голубой»", "ЭП1М-423": "🔵 «Голубой»", "ЭП1М-437": "🔵 «Голубой»",
    "ЭП1М-444": "🔵 «Голубой»", "ЭП1М-454": "🔵 «Голубой»", "ЭП1М-491": "🔵 «Голубой»",
    "ЭП1М-525": "🔵 «Голубой»", "ЭП1М-549": "🔵 «Голубой»", "ЭП1М-555": "🔵 «Голубой»",
    "ЭП1М-556": "🔵 «Голубой»", "ЭП1М-598": "🔵 «Голубой»", "ЭП1М-611": "🔵 «Голубой»",
    "ЭП1М-637": "🔵 «Голубой»", "ЭП1М-651": "🟢🔵 «Жемчужина Кавказа»", "ЭП1М-662": "🔵 «Голубой»",
    "ЭП1М-688": "🟢🔵 «Жемчужина Кавказа»",
    "3ЭС5К-1131": "🖤🔴 «НТС»", "3ЭС5К-1133": "🖤🔴 «НТС»", "3ЭС5К-1134": "🖤🔴 «НТС»",
    "3ЭС5К-1135": "🖤🔴 «НТС»", "3ЭС5К-1136": "🖤🔴 «НТС»", "3ЭС5К-1137": "🖤🔴 «НТС»",
    "3ЭС5К-1138": "🖤🔴 «НТС»", "3ЭС5К-1139": "🖤🔴 «НТС»", "3ЭС5К-1140": "🖤🔴 «НТС»",
    "3ЭС5К-1141": "🖤🔴 «НТС»", "3ЭС5К-1142": "🖤🔴 «НТС»", "3ЭС5К-1143": "🖤🔴 «НТС»",
    "3ЭС5К-1144": "🖤🔴 «НТС»",
    "2ЭС5К-555": "🔵 «ТрансОйл»", "2ЭС5К-556": "🔵 «ТрансОйл»", "2ЭС5К-557": "🔵 «ТрансОйл»",
    "2ЭС5К-558": "🔵 «ТрансОйл»", "2ЭС5К-559": "🔵 «ТрансОйл»", "2ЭС5К-560": "🔵 «ТрансОйл»",
    "2ЭС5К-561": "🔵 «ТрансОйл»", "2ЭС5К-562": "🔵 «ТрансОйл»", "2ЭС5К-563": "🔵 «ТрансОйл»",
    "2ЭС5К-564": "🔵 «ТрансОйл»", "2ЭС5К-590": "🔵 «ТрансОйл»",
    "ВЛ80С-1382": "🟢🟡 «ГЖД»", "ВЛ80С-1580": "🟢🟡 «ГЖД»", "ВЛ80С-1913": "🟢🟡 «ГЖД»",
    "ВЛ80С-2127": "🟢🟡 «ГЖД»", "ВЛ80С-693": "🟢", "ВЛ80С-841": "🟢", "ВЛ80С-1097": "🟢",
    "ВЛ80С-1226": "🟢", "ВЛ80С-1271": "🟢", "ВЛ80С-1311": "🟢", "ВЛ80С-1357": "🟢",
    "ВЛ80С-1449": "🟢", "ВЛ80С-1732": "🟢", "ВЛ80С-2034": "🟢", "ВЛ80С-2051": "🟢",
    "ВЛ80С-2196": "🟢", "ВЛ80С-2217": "🟢", "ВЛ80С-2221": "🟢", "ВЛ80С-2227": "🟢",
    "ВЛ80С-2230": "🟢", "ВЛ80С-2241": "🟢", "ВЛ80С-2602": "🟢"
}

BLACKLIST = set()

# ==================== КОНСТАНТЫ КНОПОК (единый источник истины) ====================
BTN_ADD_MULTIPLE = "➕ Добавить еще один ПС"
BTN_ADD_TRANSFER = "➕ Добавить еще перегоняемый"
BTN_FINISH = "✅ Закончить"
BTN_BACK = "⬅️ Назад"
BTN_CANCEL_EDIT = "⬅️ Отмена"
BTN_NONE_LIST = "❌ Ничего из списка"
BTN_DELETE = "🗑 Удалить:"
BTN_DELETE_TRANSFER = "🗑 Удалить перегоняемый:"

BTN_SPLOTKA = "Сплотка 🚂🚂"
BTN_PEREGONKA = "Перегонка ➡️🚂"
BTN_PDS = "ПДС (пассажирский)"
BTN_GRUZ = "Грузовой поезд"
BTN_NO_INFO = "Нет информации"

# ==================== СОСТОЯНИЯ (FSM) ====================
class Form(StatesGroup):
    waiting_series_category = State()
    waiting_series = State()
    waiting_number = State()
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

user_data = {}

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def get_loco_name(series, number):
    full_name = f"{series}-{number}"
    if full_name in LOCO_NICKNAMES:
        return f"{full_name}{LOCO_NICKNAMES[full_name]}"
    return full_name

def format_station(station_name):
    station_lower = station_name.lower().strip()
    prefixes_to_skip = ["ст.", "ст ", "перегон", "о.п.", "о.п ", "о.п", "оп.", "оп ", "оп"]
    for prefix in prefixes_to_skip:
        if station_lower.startswith(prefix):
            return station_name
    return f"ст. {station_name}"

def find_train_by_query(query: str):
    query = query.strip().upper()
    results = []
    for train_num, info in SCHEDULES.items():
        name = info["name"].upper()
        route = info["route"].upper()
        train_num_upper = train_num.upper()
        
        if query == train_num_upper:
            return [(train_num, info)]
        
        train_digits = ''.join(c for c in train_num if c.isdigit())
        if train_digits and train_digits in query:
            results.append((train_num, info))
            continue
        
        if name in query or query in name:
            results.append((train_num, info))
            continue
        
        route_clean = route.replace(" ", "").replace("—", "").replace("-", "")
        query_clean = query.replace(" ", "").replace("—", "").replace("-", "")
        if route_clean and (route_clean in query_clean or query_clean in route_clean):
            results.append((train_num, info))
            continue
    return results

def build_summary(user_id: int) -> str:
    data = user_data[user_id]
    today = datetime.now().strftime("%d.%m.%Y")
    train_info = ""
    
    if data.get("is_multiple"):
        multiple_units = data.get("multiple_units", [])
        if multiple_units:
            loco_list = "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in multiple_units])
            train_info = f"🚂🚂 <b>Сплотка:</b>\n{loco_list}"
        else:
            train_info = "🚂🚂 Сплотка (пусто)"
            
    elif data.get("is_transfer"):
        transfer_data = data.get("transfer_data", {})
        main_loco = transfer_data.get("main", {})
        towed_locos = transfer_data.get("towed", [])
        transfer_train_type = data.get("transfer_train_type", BTN_NO_INFO)
        transfer_train_number = data.get("transfer_train_number", "")
        
        if main_loco and towed_locos:
            main_name = get_loco_name(main_loco["series"], main_loco["number"])
            towed_list = "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in towed_locos])
            train_info = f"➡️🚂 <b>Перегонка:</b>\n  🚂 Основной: {main_name}\n  🚂 Перегоняемые:\n{towed_list}\n"
            
            if transfer_train_type == BTN_GRUZ:
                train_info += "  🚛 Под грузовым поездом"
            elif transfer_train_type == BTN_PDS and transfer_train_number and transfer_train_number != BTN_NO_INFO:
                if transfer_train_number in SCHEDULES:
                    schedule = SCHEDULES[transfer_train_number]
                    train_info += f"  🚆 Под поездом {transfer_train_number} «{schedule['name']}» ({schedule['route']})\n  📅 <a href='{schedule['link']}'>Расписание</a>"
                else:
                    train_info += f"  🚆 Под поездом {transfer_train_number}"
            else:
                train_info += "  🤷 Поезд неизвестен"
        else:
            train_info = "➡️🚂 Перегонка (неполные данные)"
            
    else:
        if data["train_type"] == BTN_PDS and data["train_number"] != BTN_NO_INFO:
            train_num = data["train_number"]
            if train_num in SCHEDULES:
                schedule = SCHEDULES[train_num]
                train_info = f"🚆 Поезд {train_num} «{schedule['name']}» ({schedule['route']})\n📅 <a href='{schedule['link']}'>Расписание</a>"
            else:
                train_info = f"🚆 Поезд {train_num}"
        elif data["train_type"] == BTN_GRUZ:
            train_info = "🚛 Грузовой поезд"
        else:
            train_info = "🤷 Тип поезда неизвестен"
    
    has_photo = "photo_id" in data
    summary = f"📋 <b>Проверьте правильность информации:</b>\n\n"
    
    if not (data.get("is_multiple") or data.get("is_transfer")):
        summary += f"🚂 <b>ПС:</b> {get_loco_name(data['series'], data['number'])}\n"
    
    summary += (
        f"{train_info}\n"
        f"🗺 <b>Направление:</b> {data['direction']}\n"
        f"📌 <b>Место:</b> {format_station(data['station'])}\n"
        f"🕒 <b>Актуальность:</b> {data['time']} ({today})\n"
        f"📸 <b>Фото:</b> {'есть' if has_photo else 'нет'}"
    )
    return summary

async def return_to_summary(message: types.Message, state: FSMContext, success_text: str):
    summary = build_summary(message.from_user.id)
    await message.answer(
        f"{success_text}\n\n{summary}",
        reply_markup=get_confirmation_keyboard(),
        disable_web_page_preview=True,
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_confirmation)

# ==================== КЛАВИАТУРЫ ====================
def get_series_categories_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cat)] for cat in TRAIN_SERIES.keys()], resize_keyboard=True)

def get_series_keyboard(category):
    keyboard, row = [], []
    for series in TRAIN_SERIES[category]:
        row.append(KeyboardButton(text=series))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    keyboard.append([KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_train_type_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=BTN_PDS)],
        [KeyboardButton(text=BTN_GRUZ)],
        [KeyboardButton(text=BTN_SPLOTKA)],
        [KeyboardButton(text=BTN_PEREGONKA)],
        [KeyboardButton(text=BTN_NO_INFO)]
    ], resize_keyboard=True)

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

def get_confirmation_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Да, всё верно")],
        [KeyboardButton(text="❌ Нет, изменить")]
    ], resize_keyboard=True)

def get_edit_fields_keyboard(is_multiple=False, is_transfer=False):
    if is_multiple:
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=BTN_SPLOTKA), KeyboardButton(text="Тип поезда")],
            [KeyboardButton(text="Направление"), KeyboardButton(text="Место")],
            [KeyboardButton(text="Актуальность"), KeyboardButton(text=BTN_CANCEL_EDIT)]
        ], resize_keyboard=True)
    elif is_transfer:
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=BTN_PEREGONKA), KeyboardButton(text="Поезд перегонки")],
            [KeyboardButton(text="Направление"), KeyboardButton(text="Место")],
            [KeyboardButton(text="Актуальность"), KeyboardButton(text=BTN_CANCEL_EDIT)]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="ПС"), KeyboardButton(text="Номер ПС")],
            [KeyboardButton(text="Тип поезда"), KeyboardButton(text="Номер поезда")],
            [KeyboardButton(text="Направление"), KeyboardButton(text="Место")],
            [KeyboardButton(text="Актуальность"), KeyboardButton(text=BTN_CANCEL_EDIT)]
        ], resize_keyboard=True)

def get_multiple_action_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=BTN_ADD_MULTIPLE)],
        [KeyboardButton(text=BTN_FINISH)]
    ], resize_keyboard=True)

def get_edit_multiple_keyboard(multiple_units):
    keyboard = [[KeyboardButton(text=f"{BTN_DELETE} {get_loco_name(u['series'], u['number'])}")] for u in multiple_units]
    keyboard.append([KeyboardButton(text=BTN_ADD_MULTIPLE), KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_transfer_action_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=BTN_ADD_TRANSFER)],
        [KeyboardButton(text=BTN_FINISH)]
    ], resize_keyboard=True)

def get_edit_transfer_keyboard(transfer_data):
    keyboard = []
    main_loco = transfer_data.get("main", {})
    if main_loco:
        keyboard.append([KeyboardButton(text=f"🚂 Основной: {get_loco_name(main_loco['series'], main_loco['number'])} (изменить)")])
    for u in transfer_data.get("towed", []):
        keyboard.append([KeyboardButton(text=f"{BTN_DELETE_TRANSFER} {get_loco_name(u['series'], u['number'])}")])
    keyboard.append([KeyboardButton(text=BTN_ADD_TRANSFER), KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish:{user_id}"), InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")],
        [InlineKeyboardButton(text="🚫 Забанить автора", callback_data=f"ban:{user_id}")]
    ])

# ==================== КОМАНДЫ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if message.from_user.id in BLACKLIST:
        await message.answer("Вы заблокированы и не можете использовать бота.")
        return
    await state.clear()
    user_data[message.from_user.id] = {}
    await message.answer("👋 Привет! Я бот-информатор канала о редких поездах СКЖД.\n\nДля начала выбери <b>категорию подвижного состава</b>:", reply_markup=get_series_categories_keyboard())
    await state.set_state(Form.waiting_series_category)

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    user_data.pop(message.from_user.id, None)
    await message.answer("Заполнение отменено. Чтобы начать заново, напиши /start", reply_markup=types.ReplyKeyboardRemove())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("📖 <b>Помощь по боту</b>\n\n/start - начать заполнение анкеты\n/cancel - отменить заполнение\n/help - показать эту справку")

@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if message.from_user.id not in admin_ids:
        await message.answer("❌ У вас нет прав.")
        return
    args = message.text.split()
    if len(args) < 2:
        if not BLACKLIST: await message.answer("📋 Черный список пуст.")
        else: await message.answer(f"📋 Забаненные:\n" + "\n".join([f"• {uid}" for uid in BLACKLIST]))
        return
    try:
        uid = int(args[1])
        if uid in BLACKLIST:
            BLACKLIST.remove(uid)
            await message.answer(f"✅ Пользователь {uid} разбанен!")
            try: await bot.send_message(uid, "✅ Вы были разбанены.")
            except: pass
        else: await message.answer(f"⚠️ Пользователь {uid} не найден в черном списке.")
    except ValueError: await message.answer("❌ ID должен быть числом.")

@dp.message(Command("banlist"))
async def cmd_banlist(message: types.Message):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if message.from_user.id not in admin_ids:
        await message.answer("❌ У вас нет прав.")
        return
    if not BLACKLIST: await message.answer("📋 Черный список пуст.")
    else: await message.answer(f"📋 Забаненные:\n" + "\n".join([f"• {uid}" for uid in BLACKLIST]))

# ==================== ОСНОВНОЙ ПОТОК ====================
@dp.message(Form.waiting_series_category)
async def process_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES:
        await message.answer("❌ Пожалуйста, выбери категорию из списка:")
        return
    user_data[message.from_user.id]["category"] = message.text
    await message.answer(f"📂 Выбрана категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.waiting_series)

@dp.message(Form.waiting_series)
async def process_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_series_category)
        return
    category = user_data[message.from_user.id]["category"]
    if message.text not in TRAIN_SERIES[category]:
        await message.answer("❌ Пожалуйста, выбери серию из списка:")
        return
    user_data[message.from_user.id]["series"] = message.text
    await message.answer(f"🚂 Выбрана серия: <b>{message.text}</b>\n\nТеперь введи <b>номер ПС</b>:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.waiting_number)

@dp.message(Form.waiting_number)
async def process_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10:
        await message.answer("❌ Некорректный номер. Введи номер ПС:")
        return
    user_data[message.from_user.id]["number"] = number
    await message.answer(f"🔢 Номер ПС: <b>{number}</b>\n\nКакой это тип поезда?", reply_markup=get_train_type_keyboard())
    await state.set_state(Form.waiting_train_type)

@dp.message(Form.waiting_train_type)
async def process_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_PDS, BTN_GRUZ, BTN_SPLOTKA, BTN_PEREGONKA, BTN_NO_INFO]:
        await message.answer("❌ Пожалуйста, выбери тип поезда из списка:")
        return
    
    user_data[message.from_user.id]["train_type"] = tt
    user_data[message.from_user.id]["is_multiple"] = False
    user_data[message.from_user.id]["is_transfer"] = False
    
    if tt == BTN_PDS:
        await message.answer("🚆 Введи <b>номер поезда</b> или его часть (например: <code>104 Москва-Адлер</code> или <code>нет</code>):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_train_number)
    elif tt == BTN_GRUZ:
        user_data[message.from_user.id]["train_number"] = "Грузовой"
        await message.answer("🚛 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif tt == BTN_SPLOTKA:
        user_data[message.from_user.id]["is_multiple"] = True
        user_data[message.from_user.id]["multiple_units"] = [{"series": user_data[message.from_user.id]["series"], "number": user_data[message.from_user.id]["number"]}]
        await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n• {get_loco_name(user_data[message.from_user.id]['series'], user_data[message.from_user.id]['number'])}\n\nЧто дальше?", reply_markup=get_multiple_action_keyboard())
        await state.set_state(Form.waiting_multiple_action)
    elif tt == BTN_PEREGONKA:
        user_data[message.from_user.id]["is_transfer"] = True
        user_data[message.from_user.id]["transfer_data"] = {"main": {"series": user_data[message.from_user.id]["series"], "number": user_data[message.from_user.id]["number"]}, "towed": []}
        await message.answer(f"➡️🚂 <b>Перегонка:</b>\n\n🚂 <b>Основной:</b> {get_loco_name(user_data[message.from_user.id]['series'], user_data[message.from_user.id]['number'])}\n\nТеперь выбери <b>категорию ПС</b> для перегоняемого:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_transfer_towed_category)
    else:
        user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
        await message.answer("🤷 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)

# ==================== УМНЫЙ ПОИСК ПОЕЗДА ====================
@dp.message(Form.waiting_train_number)
async def process_train_number(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    if user_input.lower() == "нет":
        user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
        await message.answer("🚆 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
        return
    
    results = find_train_by_query(user_input)
    if len(results) == 0:
        user_data[message.from_user.id]["train_number"] = user_input.upper()
        await message.answer(f"ℹ️ Поезд <b>{user_input.upper()}</b> не найден в базе. Записан как есть.\n\n🚆 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif len(results) == 1:
        tn, info = results[0]
        user_data[message.from_user.id]["train_number"] = tn
        await message.answer(f"✅ Найден поезд: <b>{tn} «{info['name']}»</b>\n🗺 Маршрут: {info['route']}\n\n🚆 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    else:
        user_data[message.from_user.id]["found_trains"] = results
        kb = [[KeyboardButton(text=f"{tn} — {info['name']} ({info['route']})")] for tn, info in results]
        kb.append([KeyboardButton(text=BTN_NONE_LIST)])
        await message.answer(f"🔍 Найдено несколько поездов. Выбери нужный:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(Form.waiting_train_select)

@dp.message(Form.waiting_train_select)
async def process_train_select(message: types.Message, state: FSMContext):
    if message.text == BTN_NONE_LIST:
        await message.answer("✏️ Введи номер поезда вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_train_number_manual)
        return
    for tn, info in user_data[message.from_user.id].get("found_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["train_number"] = tn
            await message.answer(f"✅ Выбран поезд: <b>{tn} «{info['name']}»</b>\n\n🚆 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
            await state.set_state(Form.waiting_direction)
            return
    await message.answer("❌ Пожалуйста, выбери поезд из списка:")

@dp.message(Form.waiting_train_number_manual)
async def process_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20:
        await message.answer("❌ Некорректный номер. Попробуй ещё раз:")
        return
    user_data[message.from_user.id]["train_number"] = tn
    await message.answer(f"🚆 Номер поезда: <b>{tn}</b>\n\nВ какую сторону едет поезд?", reply_markup=get_directions_keyboard())
    await state.set_state(Form.waiting_direction)

# ==================== СПЛОТКА ====================
@dp.message(Form.waiting_multiple_action)
async def process_multiple_action(message: types.Message, state: FSMContext):
    action = message.text
    if action == BTN_ADD_MULTIPLE:
        await message.answer("📂 Выбери <b>категорию ПС</b> для следующего локомотива:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_multiple_series_category)
    elif action == BTN_FINISH:
        await message.answer("🗺 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    else:
        await message.answer("❌ Пожалуйста, выбери действие из списка:", reply_markup=get_multiple_action_keyboard())

@dp.message(Form.waiting_multiple_series_category)
async def process_multiple_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES:
        await message.answer("❌ Пожалуйста, выбери категорию из списка:")
        return
    user_data[message.from_user.id]["temp_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.waiting_multiple_series)

@dp.message(Form.waiting_multiple_series)
async def process_multiple_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_multiple_series_category)
        return
    category = user_data[message.from_user.id]["temp_category"]
    if message.text not in TRAIN_SERIES[category]:
        await message.answer("❌ Пожалуйста, выбери серию из списка:")
        return
    user_data[message.from_user.id]["temp_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nВведи <b>номер ПС</b>:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.waiting_multiple_number)

@dp.message(Form.waiting_multiple_number)
async def process_multiple_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10:
        await message.answer("❌ Некорректный номер. Введи номер ПС:")
        return
    user_data[message.from_user.id]["multiple_units"].append({"series": user_data[message.from_user.id]["temp_series"], "number": number})
    units = user_data[message.from_user.id]["multiple_units"]
    loco_list = "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units])
    await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n{loco_list}\n\n✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_series'], number)}</b>\n\nЧто дальше?", reply_markup=get_multiple_action_keyboard())
    await state.set_state(Form.waiting_multiple_action)

# ==================== ПЕРЕГОНКА ====================
@dp.message(Form.waiting_transfer_towed_category)
async def process_transfer_towed_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES:
        await message.answer("❌ Пожалуйста, выбери категорию из списка:")
        return
    user_data[message.from_user.id]["temp_towed_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b> для перегоняемого:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.waiting_transfer_towed_series)

@dp.message(Form.waiting_transfer_towed_series)
async def process_transfer_towed_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_transfer_towed_category)
        return
    category = user_data[message.from_user.id]["temp_towed_category"]
    if message.text not in TRAIN_SERIES[category]:
        await message.answer("❌ Пожалуйста, выбери серию из списка:")
        return
    user_data[message.from_user.id]["temp_towed_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nВведи <b>номер ПС</b> перегоняемого:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.waiting_transfer_towed_number)

@dp.message(Form.waiting_transfer_towed_number)
async def process_transfer_towed_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10:
        await message.answer("❌ Некорректный номер. Введи номер ПС:")
        return
    user_data[message.from_user.id]["transfer_data"]["towed"].append({"series": user_data[message.from_user.id]["temp_towed_series"], "number": number})
    td = user_data[message.from_user.id]["transfer_data"]
    towed_list = "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in td['towed']])
    await message.answer(f"➡️🚂 <b>Перегонка:</b>\n\n🚂 <b>Основной:</b> {get_loco_name(td['main']['series'], td['main']['number'])}\n🚂 <b>Перегоняемые:</b>\n{towed_list}\n\n✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_towed_series'], number)}</b>\n\nЧто дальше?", reply_markup=get_transfer_action_keyboard())
    await state.set_state(Form.waiting_transfer_action)

@dp.message(Form.waiting_transfer_action)
async def process_transfer_action(message: types.Message, state: FSMContext):
    action = message.text
    if action == BTN_ADD_TRANSFER:
        await message.answer("📂 Выбери <b>категорию ПС</b> для следующего перегоняемого:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_transfer_towed_category)
    elif action == BTN_FINISH:
        await message.answer("➡️🚂 Перегонка под каким поездом?\n\nВыбери тип поезда:", reply_markup=ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=BTN_GRUZ)],
            [KeyboardButton(text=BTN_PDS)],
            [KeyboardButton(text=BTN_NO_INFO)]
        ], resize_keyboard=True))
        await state.set_state(Form.waiting_transfer_train_type)
    else:
        await message.answer("❌ Пожалуйста, выбери действие из списка:", reply_markup=get_transfer_action_keyboard())

@dp.message(Form.waiting_transfer_train_type)
async def process_transfer_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_GRUZ, BTN_PDS, BTN_NO_INFO]:
        await message.answer("❌ Пожалуйста, выбери тип поезда из списка:")
        return
    user_data[message.from_user.id]["transfer_train_type"] = tt
    if tt == BTN_GRUZ:
        user_data[message.from_user.id]["transfer_train_number"] = "Грузовой"
        await message.answer("🗺 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif tt == BTN_PDS:
        await message.answer("🚆 Введи <b>номер поезда</b> или его часть (например: <code>104 Москва-Адлер</code> или <code>нет</code>):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_transfer_train_number)
    else:
        user_data[message.from_user.id]["transfer_train_number"] = BTN_NO_INFO
        await message.answer("🗺 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)

@dp.message(Form.waiting_transfer_train_number)
async def process_transfer_train_number(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    if user_input.lower() == "нет":
        user_data[message.from_user.id]["transfer_train_number"] = BTN_NO_INFO
        await message.answer("🗺 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
        return
    results = find_train_by_query(user_input)
    if len(results) == 0:
        user_data[message.from_user.id]["transfer_train_number"] = user_input.upper()
        await message.answer(f"ℹ️ Поезд <b>{user_input.upper()}</b> не найден. Записан как есть.\n\n🗺 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif len(results) == 1:
        tn, info = results[0]
        user_data[message.from_user.id]["transfer_train_number"] = tn
        await message.answer(f"✅ Найден поезд: <b>{tn} «{info['name']}»</b>\n\n🗺 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    else:
        user_data[message.from_user.id]["found_transfer_trains"] = results
        kb = [[KeyboardButton(text=f"{tn} — {info['name']} ({info['route']})")] for tn, info in results]
        kb.append([KeyboardButton(text=BTN_NONE_LIST)])
        await message.answer(f"🔍 Найдено несколько поездов. Выбери нужный:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(Form.waiting_transfer_train_select)

@dp.message(Form.waiting_transfer_train_select)
async def process_transfer_train_select(message: types.Message, state: FSMContext):
    if message.text == BTN_NONE_LIST:
        await message.answer("✏️ Введи номер поезда вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_transfer_train_number_manual)
        return
    for tn, info in user_data[message.from_user.id].get("found_transfer_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["transfer_train_number"] = tn
            await message.answer(f"✅ Выбран поезд: <b>{tn} «{info['name']}»</b>\n\n🗺 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
            await state.set_state(Form.waiting_direction)
            return
    await message.answer("❌ Пожалуйста, выбери поезд из списка:")

@dp.message(Form.waiting_transfer_train_number_manual)
async def process_transfer_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20:
        await message.answer("❌ Некорректный номер. Попробуй ещё раз:")
        return
    user_data[message.from_user.id]["transfer_train_number"] = tn
    await message.answer(f"🚆 Номер поезда: <b>{tn}</b>\n\nВ какую сторону едет поезд?", reply_markup=get_directions_keyboard())
    await state.set_state(Form.waiting_direction)

# ==================== НАПРАВЛЕНИЕ, СТАНЦИЯ, ВРЕМЯ ====================
@dp.message(Form.waiting_direction)
async def process_direction(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введи направление вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_direction_manual)
        return
    if message.text not in DIRECTIONS:
        await message.answer("❌ Пожалуйста, выбери направление из списка:")
        return
    user_data[message.from_user.id]["direction"] = message.text
    await message.answer("📍 Где вы заметили поезд? (Выберите станцию)", reply_markup=get_stations_keyboard())
    await state.set_state(Form.waiting_station)

@dp.message(Form.waiting_direction_manual)
async def process_direction_manual(message: types.Message, state: FSMContext):
    d = message.text.strip()
    if not d or len(d) > 50:
        await message.answer("❌ Некорректное направление. Попробуй ещё раз:")
        return
    user_data[message.from_user.id]["direction"] = d
    await message.answer(f"🗺 Направление: <b>{d}</b>\n\n📍 Где вы заметили поезд?", reply_markup=get_stations_keyboard())
    await state.set_state(Form.waiting_station)

@dp.message(Form.waiting_station)
async def process_station(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введи название станции/О.П. вручную (например: <b>перегон Лихая - Морозовская</b> или <b>о.п. Березовый</b>):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_station_manual)
        return
    if message.text not in STATIONS:
        await message.answer("❌ Пожалуйста, выбери станцию из списка:")
        return
    user_data[message.from_user.id]["station"] = message.text
    await message.answer("🕐 Во сколько вы заметили поезд?\n\nНапиши время в формате <b>ЧЧ:ММ</b> или нажми кнопку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏰ Сейчас", callback_data="time_now")]]))
    await state.set_state(Form.waiting_time)

@dp.message(Form.waiting_station_manual)
async def process_station_manual(message: types.Message, state: FSMContext):
    s = message.text.strip()
    if not s or len(s) > 100:
        await message.answer("❌ Некорректное название. Попробуй ещё раз:")
        return
    user_data[message.from_user.id]["station"] = s
    await message.answer(f"📍 Место: <b>{format_station(s)}</b>\n\n🕐 Во сколько вы заметили поезд?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏰ Сейчас", callback_data="time_now")]]))
    await state.set_state(Form.waiting_time)

@dp.message(Form.waiting_time)
async def process_time(message: types.Message, state: FSMContext):
    try:
        if ":" not in message.text: raise ValueError
        h, m = map(int, message.text.strip().split(":"))
        if h < 0 or h > 24 or m < 0 or m > 59 or (h == 24 and m != 0): raise ValueError
    except ValueError:
        await message.answer("❌ Неверный формат. Введи <b>ЧЧ:ММ</b> (например: 11:30):")
        return
    user_data[message.from_user.id]["time"] = f"{h:02d}:{m:02d}"
    await message.answer("📸 <b>Есть ли у вас фотоподтверждение?</b>\n\nОтправь фото или нажми кнопку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Нет фото", callback_data="no_photo")]]))
    await state.set_state(Form.waiting_photo)

@dp.callback_query(F.data == "time_now")
async def time_now_callback(callback: types.CallbackQuery, state: FSMContext):
    now = datetime.now()
    user_data[callback.from_user.id]["time"] = f"{now.hour:02d}:{now.minute:02d}"
    await callback.message.answer("📸 <b>Есть ли у вас фотоподтверждение?</b>\n\nОтправь фото или нажми кнопку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Нет фото", callback_data="no_photo")]]))
    await state.set_state(Form.waiting_photo)
    await callback.answer()

@dp.message(Form.waiting_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]["photo_id"] = message.photo[-1].file_id
    await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(), disable_web_page_preview=True)
    await state.set_state(Form.waiting_confirmation)

@dp.callback_query(F.data == "no_photo")
async def no_photo_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(build_summary(callback.from_user.id), reply_markup=get_confirmation_keyboard(), disable_web_page_preview=True)
    await state.set_state(Form.waiting_confirmation)
    await callback.answer()

# ==================== ПОДТВЕРЖДЕНИЕ ====================
@dp.message(Form.waiting_confirmation)
async def process_confirmation(message: types.Message, state: FSMContext):
    if message.text == "✅ Да, всё верно":
        data = user_data[message.from_user.id]
        today = datetime.now().strftime("%d.%m.%Y")
        
        train_info = ""
        if data.get("is_multiple"):
            units = data.get("multiple_units", [])
            train_info = "🚂🚂 <b>Сплотка:</b>\n" + "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units]) if units else "🚂🚂 Сплотка (пусто)"
        elif data.get("is_transfer"):
            td = data.get("transfer_data", {})
            main = td.get("main", {})
            towed = td.get("towed", [])
            t_type = data.get("transfer_train_type", BTN_NO_INFO)
            t_num = data.get("transfer_train_number", "")
            if main and towed:
                train_info = f"➡️🚂 <b>Перегонка:</b>\n  🚂 Основной: {get_loco_name(main['series'], main['number'])}\n  🚂 Перегоняемые:\n" + "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in towed]) + "\n"
                if t_type == BTN_GRUZ: train_info += "  🚛 Под грузовым поездом"
                elif t_type == BTN_PDS and t_num and t_num != BTN_NO_INFO:
                    if t_num in SCHEDULES:
                        s = SCHEDULES[t_num]
                        train_info += f"  🚆 Под поездом {t_num} «{s['name']}» ({s['route']})\n  📅 <a href='{s['link']}'>Расписание</a>"
                    else: train_info += f"  🚆 Под поездом {t_num}"
                else: train_info += "  🤷 Поезд неизвестен"
            else: train_info = "➡️🚂 Перегонка (неполные данные)"
        else:
            if data["train_type"] == BTN_PDS and data["train_number"] != BTN_NO_INFO:
                tn = data["train_number"]
                if tn in SCHEDULES:
                    s = SCHEDULES[tn]
                    train_info = f"🚆 Поезд {tn} «{s['name']}» ({s['route']})\n📅 <a href='{s['link']}'>Расписание</a>"
                else: train_info = f"🚆 Поезд {tn}"
            elif data["train_type"] == BTN_GRUZ: train_info = "🚛 Грузовой поезд"
            else: train_info = "🤷 Тип поезда неизвестен"
        
        admin_msg = f"🚂 <b>Новая заявка от @{message.from_user.username or message.from_user.first_name}</b>\n\n"
        if not (data.get("is_multiple") or data.get("is_transfer")):
            admin_msg += f"🚂 <b>ПС:</b> {get_loco_name(data['series'], data['number'])}\n"
        admin_msg += f"{train_info}\n🗺 <b>Направление:</b> {data['direction']}\n📌 <b>Место:</b> {format_station(data['station'])}\n🕒 <b>Актуальность:</b> {data['time']} ({today})"
        
        has_photo = "photo_id" in data
        admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
        for aid in admin_ids:
            try:
                if has_photo: await bot.send_photo(aid, photo=data["photo_id"], caption=admin_msg, reply_markup=get_admin_keyboard(message.from_user.id))
                else: await bot.send_message(aid, admin_msg, reply_markup=get_admin_keyboard(message.from_user.id))
            except Exception as e: logging.error(f"Ошибка отправки админу {aid}: {e}")
        
        await message.answer("✅ Спасибо! Информация отправлена администраторам.\n\nЧтобы отправить еще одну, напиши /start", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        user_data.pop(message.from_user.id, None)
        
    elif message.text == "❌ Нет, изменить":
        is_mult = user_data[message.from_user.id].get("is_multiple", False)
        is_trans = user_data[message.from_user.id].get("is_transfer", False)
        await message.answer("✏️ Какое поле вы хотите изменить?", reply_markup=get_edit_fields_keyboard(is_mult, is_trans))
        await state.set_state(Form.edit_what)
    else:
        await message.answer("Пожалуйста, выберите один из вариантов:")

# ==================== РЕДАКТИРОВАНИЕ ====================
@dp.message(Form.edit_what)
async def process_edit_what(message: types.Message, state: FSMContext):
    choice = message.text
    data = user_data[message.from_user.id]
    is_mult = data.get("is_multiple", False)
    is_trans = data.get("is_transfer", False)
    
    if choice == BTN_SPLOTKA and is_mult:
        await message.answer("🚂🚂 <b>Редактирование сплотки:</b>\n\nВыбери действие:", reply_markup=get_edit_multiple_keyboard(data.get("multiple_units", [])), parse_mode="HTML")
        await state.set_state(Form.edit_multiple_action)
        return
    if choice == BTN_PEREGONKA and is_trans:
        await message.answer("➡️🚂 <b>Редактирование перегонки:</b>\n\nВыбери действие:", reply_markup=get_edit_transfer_keyboard(data.get("transfer_data", {})), parse_mode="HTML")
        await state.set_state(Form.edit_transfer_action)
        return
    if choice == "Поезд перегонки" and is_trans:
        await message.answer("🚆 Выбери тип поезда для перегонки:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_GRUZ)], [KeyboardButton(text=BTN_PDS)], [KeyboardButton(text=BTN_NO_INFO)]], resize_keyboard=True))
        await state.set_state(Form.edit_transfer_train_type)
        return
        
    if choice == "ПС":
        await message.answer("📂 Выбери новую <b>категорию ПС</b>:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_series_category)
    elif choice == "Номер ПС":
        await message.answer(f"🔢 Текущий номер: <b>{data['number']}</b>\n\nВведи новый:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_number)
    elif choice == "Тип поезда":
        await message.answer("🚆 Выбери новый тип поезда:", reply_markup=get_train_type_keyboard())
        await state.set_state(Form.edit_train_type)
    elif choice == "Номер поезда":
        await message.answer("🚆 Введи новый номер поезда:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_train_number)
    elif choice == "Направление":
        await message.answer("🗺 Выбери новое направление:", reply_markup=get_directions_keyboard())
        await state.set_state(Form.edit_direction)
    elif choice == "Место":
        await message.answer("📍 Выбери новую станцию:", reply_markup=get_stations_keyboard())
        await state.set_state(Form.edit_station)
    elif choice == "Актуальность":
        await message.answer("🕐 Введи новое время в формате <b>ЧЧ:ММ</b>:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_time)
    elif choice == BTN_CANCEL_EDIT:
        await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(), disable_web_page_preview=True)
        await state.set_state(Form.waiting_confirmation)
    else:
        await message.answer("❌ Пожалуйста, выбери поле из списка:", reply_markup=get_edit_fields_keyboard(is_mult, is_trans))

# --- Редактирование Сплотки ---
@dp.message(Form.edit_multiple_action)
async def process_edit_multiple_action(message: types.Message, state: FSMContext):
    action = message.text
    units = user_data[message.from_user.id].get("multiple_units", [])
    if action == BTN_ADD_MULTIPLE:
        await message.answer("📂 Выбери <b>категорию ПС</b>:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_multiple_series_category)
    elif action.startswith(BTN_DELETE):
        name = action.replace(f"{BTN_DELETE} ", "")
        for i, u in enumerate(units):
            if get_loco_name(u['series'], u['number']) == name:
                units.pop(i); break
        if not units:
            user_data[message.from_user.id]["is_multiple"] = False
            user_data[message.from_user.id]["train_type"] = BTN_NO_INFO
            user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
            await return_to_summary(message, state, "✅ Сплотка удалена.")
        else:
            await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n" + "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units]) + "\n\n✅ Локомотив удален\n\nВыбери действие:", reply_markup=get_edit_multiple_keyboard(units), parse_mode="HTML")
    elif action == BTN_BACK:
        await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(), disable_web_page_preview=True)
        await state.set_state(Form.waiting_confirmation)
    else:
        await message.answer("❌ Пожалуйста, выбери действие:", reply_markup=get_edit_multiple_keyboard(units))

@dp.message(Form.edit_multiple_series_category)
async def process_edit_multiple_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES:
        await message.answer("❌ Пожалуйста, выбери категорию из списка:")
        return
    user_data[message.from_user.id]["temp_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.edit_multiple_series)

@dp.message(Form.edit_multiple_series)
async def process_edit_multiple_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_multiple_series_category)
        return
    category = user_data[message.from_user.id]["temp_category"]
    if message.text not in TRAIN_SERIES[category]:
        await message.answer("❌ Пожалуйста, выбери серию из списка:")
        return
    user_data[message.from_user.id]["temp_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nВведи <b>номер ПС</b>:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.edit_multiple_number)

@dp.message(Form.edit_multiple_number)
async def process_edit_multiple_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10:
        await message.answer("❌ Некорректный номер. Введи номер ПС:")
        return
    user_data[message.from_user.id]["multiple_units"].append({"series": user_data[message.from_user.id]["temp_series"], "number": number})
    units = user_data[message.from_user.id]["multiple_units"]
    await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n" + "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units]) + f"\n\n✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_series'], number)}</b>\n\nВыбери действие:", reply_markup=get_edit_multiple_keyboard(units), parse_mode="HTML")
    await state.set_state(Form.edit_multiple_action)

# --- Редактирование Перегонки ---
@dp.message(Form.edit_transfer_action)
async def process_edit_transfer_action(message: types.Message, state: FSMContext):
    action = message.text
    td = user_data[message.from_user.id].get("transfer_data", {})
    if action == BTN_ADD_TRANSFER:
        await message.answer("📂 Выбери <b>категорию ПС</b> для перегоняемого:", reply_markup=get_series_categories_keyboard())
        user_data[message.from_user.id]["is_editing_main"] = False
        await state.set_state(Form.edit_transfer_towed_category)
    elif action.startswith("🚂 Основной:"):
        await message.answer("📂 Выбери <b>категорию ПС</b> для нового основного:", reply_markup=get_series_categories_keyboard())
        user_data[message.from_user.id]["is_editing_main"] = True
        await state.set_state(Form.edit_transfer_towed_category)
    elif action.startswith(BTN_DELETE_TRANSFER):
        name = action.replace(f"{BTN_DELETE_TRANSFER} ", "")
        for i, u in enumerate(td.get("towed", [])):
            if get_loco_name(u['series'], u['number']) == name:
                td["towed"].pop(i); break
        if not td.get("towed"):
            user_data[message.from_user.id]["is_transfer"] = False
            user_data[message.from_user.id]["train_type"] = BTN_NO_INFO
            await return_to_summary(message, state, "✅ Перегонка удалена.")
        else:
            await message.answer(f"➡️🚂 <b>Перегонка:</b>\n\n🚂 <b>Основной:</b> {get_loco_name(td['main']['series'], td['main']['number'])}\n🚂 <b>Перегоняемые:</b>\n" + "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in td['towed']]) + "\n\n✅ Удален\n\nВыбери действие:", reply_markup=get_edit_transfer_keyboard(td), parse_mode="HTML")
    elif action == BTN_BACK:
        await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(), disable_web_page_preview=True)
        await state.set_state(Form.waiting_confirmation)
    else:
        await message.answer("❌ Пожалуйста, выбери действие:", reply_markup=get_edit_transfer_keyboard(td))

@dp.message(Form.edit_transfer_towed_category)
async def process_edit_transfer_towed_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES:
        await message.answer("❌ Пожалуйста, выбери категорию из списка:")
        return
    user_data[message.from_user.id]["temp_towed_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.edit_transfer_towed_series)

@dp.message(Form.edit_transfer_towed_series)
async def process_edit_transfer_towed_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_transfer_towed_category)
        return
    category = user_data[message.from_user.id]["temp_towed_category"]
    if message.text not in TRAIN_SERIES[category]:
        await message.answer("❌ Пожалуйста, выбери серию из списка:")
        return
    user_data[message.from_user.id]["temp_towed_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nВведи <b>номер ПС</b>:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.edit_transfer_towed_number)

@dp.message(Form.edit_transfer_towed_number)
async def process_edit_transfer_towed_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10:
        await message.answer("❌ Некорректный номер. Введи номер ПС:")
        return
    
    is_main = user_data[message.from_user.id].get("is_editing_main", False)
    if is_main:
        user_data[message.from_user.id]["transfer_data"]["main"] = {"series": user_data[message.from_user.id]["temp_towed_series"], "number": number}
        user_data[message.from_user.id]["is_editing_main"] = False
        msg = "✅ Основной изменен"
    else:
        user_data[message.from_user.id]["transfer_data"]["towed"].append({"series": user_data[message.from_user.id]["temp_towed_series"], "number": number})
        msg = f"✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_towed_series'], number)}</b>"
    
    td = user_data[message.from_user.id]["transfer_data"]
    await message.answer(f"➡️🚂 <b>Перегонка:</b>\n\n🚂 <b>Основной:</b> {get_loco_name(td['main']['series'], td['main']['number'])}\n🚂 <b>Перегоняемые:</b>\n" + "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in td['towed']]) + f"\n\n{msg}\n\nВыбери действие:", reply_markup=get_edit_transfer_keyboard(td), parse_mode="HTML")
    await state.set_state(Form.edit_transfer_action)

# --- Редактирование Поезда Перегонки ---
@dp.message(Form.edit_transfer_train_type)
async def process_edit_transfer_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_GRUZ, BTN_PDS, BTN_NO_INFO]:
        await message.answer("❌ Пожалуйста, выбери тип поезда из списка:")
        return
    user_data[message.from_user.id]["transfer_train_type"] = tt
    if tt == BTN_GRUZ:
        user_data[message.from_user.id]["transfer_train_number"] = "Грузовой"
        await return_to_summary(message, state, "✅ Поезд перегонки: <b>Грузовой</b>")
    elif tt == BTN_PDS:
        await message.answer("🚆 Введи номер поезда:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_transfer_train_number)
    else:
        user_data[message.from_user.id]["transfer_train_number"] = BTN_NO_INFO
        await return_to_summary(message, state, "✅ Поезд перегонки: <b>Нет информации</b>")

@dp.message(Form.edit_transfer_train_number)
async def process_edit_transfer_train_number(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    if user_input.lower() == "нет":
        user_data[message.from_user.id]["transfer_train_number"] = BTN_NO_INFO
        await return_to_summary(message, state, "✅ Поезд перегонки очищен")
        return
    results = find_train_by_query(user_input)
    if len(results) == 0:
        user_data[message.from_user.id]["transfer_train_number"] = user_input.upper()
        await return_to_summary(message, state, f"✅ Поезд перегонки: <b>{user_input.upper()}</b>")
    elif len(results) == 1:
        tn, info = results[0]
        user_data[message.from_user.id]["transfer_train_number"] = tn
        await return_to_summary(message, state, f"✅ Поезд перегонки: <b>{tn} «{info['name']}»</b>")
    else:
        user_data[message.from_user.id]["found_transfer_trains"] = results
        kb = [[KeyboardButton(text=f"{tn} — {info['name']} ({info['route']})")] for tn, info in results]
        kb.append([KeyboardButton(text=BTN_NONE_LIST)])
        await message.answer("🔍 Найдено несколько поездов. Выбери нужный:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(Form.edit_transfer_train_select)

@dp.message(Form.edit_transfer_train_select)
async def process_edit_transfer_train_select(message: types.Message, state: FSMContext):
    if message.text == BTN_NONE_LIST:
        await message.answer("✏️ Введи номер вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_transfer_train_number_manual)
        return
    for tn, info in user_data[message.from_user.id].get("found_transfer_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["transfer_train_number"] = tn
            await return_to_summary(message, state, f"✅ Поезд перегонки: <b>{tn} «{info['name']}»</b>")
            return
    await message.answer("❌ Пожалуйста, выбери поезд из списка:")

@dp.message(Form.edit_transfer_train_number_manual)
async def process_edit_transfer_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20:
        await message.answer("❌ Некорректный номер. Попробуй ещё раз:")
        return
    user_data[message.from_user.id]["transfer_train_number"] = tn
    await return_to_summary(message, state, f"✅ Поезд перегонки: <b>{tn}</b>")

# --- Стандартное редактирование ---
@dp.message(Form.edit_series_category)
async def edit_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES:
        await message.answer("❌ Пожалуйста, выбери категорию из списка:")
        return
    user_data[message.from_user.id]["category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.edit_series)

@dp.message(Form.edit_series)
async def edit_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_series_category)
        return
    category = user_data[message.from_user.id]["category"]
    if message.text not in TRAIN_SERIES[category]:
        await message.answer("❌ Пожалуйста, выбери серию из списка:")
        return
    user_data[message.from_user.id]["series"] = message.text
    await return_to_summary(message, state, f"✅ Серия изменена на <b>{message.text}</b>")

@dp.message(Form.edit_number)
async def edit_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10:
        await message.answer("❌ Некорректный номер. Введи номер ПС:")
        return
    user_data[message.from_user.id]["number"] = number
    await return_to_summary(message, state, f"✅ Номер ПС изменён на <b>{number}</b>")

@dp.message(Form.edit_train_type)
async def edit_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_PDS, BTN_GRUZ, BTN_SPLOTKA, BTN_PEREGONKA, BTN_NO_INFO]:
        await message.answer("❌ Пожалуйста, выбери тип поезда из списка:")
        return
    user_data[message.from_user.id]["train_type"] = tt
    if tt == BTN_PDS:
        await message.answer("🚆 Введи номер поезда:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_train_number)
    elif tt == BTN_GRUZ:
        user_data[message.from_user.id]["train_number"] = "Грузовой"
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип изменён на <b>Грузовой поезд</b>")
    elif tt == BTN_SPLOTKA:
        user_data[message.from_user.id]["is_multiple"] = True
        user_data[message.from_user.id]["is_transfer"] = False
        user_data[message.from_user.id]["multiple_units"] = []
        await message.answer("📂 Выбери <b>категорию ПС</b> для первого локомотива:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_multiple_series_category)
    elif tt == BTN_PEREGONKA:
        user_data[message.from_user.id]["is_transfer"] = True
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["transfer_data"] = {"main": {}, "towed": []}
        await message.answer("📂 Выбери <b>категорию ПС</b> для основного локомотива:", reply_markup=get_series_categories_keyboard())
        user_data[message.from_user.id]["is_editing_main"] = True
        await state.set_state(Form.edit_transfer_towed_category)
    else:
        user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип изменён на <b>Нет информации</b>")

@dp.message(Form.edit_train_number)
async def edit_train_number(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    if user_input.lower() == "нет":
        user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
        await return_to_summary(message, state, "✅ Номер поезда очищен")
        return
    results = find_train_by_query(user_input)
    if len(results) == 0:
        user_data[message.from_user.id]["train_number"] = user_input.upper()
        await return_to_summary(message, state, f"✅ Номер поезда: <b>{user_input.upper()}</b>")
    elif len(results) == 1:
        tn, info = results[0]
        user_data[message.from_user.id]["train_number"] = tn
        await return_to_summary(message, state, f"✅ Поезд: <b>{tn} «{info['name']}»</b>")
    else:
        user_data[message.from_user.id]["found_trains"] = results
        kb = [[KeyboardButton(text=f"{tn} — {info['name']} ({info['route']})")] for tn, info in results]
        kb.append([KeyboardButton(text=BTN_NONE_LIST)])
        await message.answer("🔍 Найдено несколько поездов. Выбери нужный:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(Form.edit_train_select)

@dp.message(Form.edit_train_select)
async def edit_train_select(message: types.Message, state: FSMContext):
    if message.text == BTN_NONE_LIST:
        await message.answer("✏️ Введи номер вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_train_number_manual)
        return
    for tn, info in user_data[message.from_user.id].get("found_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["train_number"] = tn
            await return_to_summary(message, state, f"✅ Поезд: <b>{tn} «{info['name']}»</b>")
            return
    await message.answer("❌ Пожалуйста, выбери поезд из списка:")

@dp.message(Form.edit_train_number_manual)
async def edit_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20:
        await message.answer("❌ Некорректный номер. Попробуй ещё раз:")
        return
    user_data[message.from_user.id]["train_number"] = tn
    await return_to_summary(message, state, f"✅ Номер поезда: <b>{tn}</b>")

@dp.message(Form.edit_direction)
async def edit_direction(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введи направление вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_direction_manual)
        return
    if message.text not in DIRECTIONS:
        await message.answer("❌ Пожалуйста, выбери направление из списка:")
        return
    user_data[message.from_user.id]["direction"] = message.text
    await return_to_summary(message, state, f"✅ Направление: <b>{message.text}</b>")

@dp.message(Form.edit_direction_manual)
async def edit_direction_manual(message: types.Message, state: FSMContext):
    d = message.text.strip()
    if not d or len(d) > 50:
        await message.answer("❌ Некорректное направление. Попробуй ещё раз:")
        return
    user_data[message.from_user.id]["direction"] = d
    await return_to_summary(message, state, f"✅ Направление: <b>{d}</b>")

@dp.message(Form.edit_station)
async def edit_station(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введи название станции/О.П. вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_station_manual)
        return
    if message.text not in STATIONS:
        await message.answer("❌ Пожалуйста, выбери станцию из списка:")
        return
    user_data[message.from_user.id]["station"] = message.text
    await return_to_summary(message, state, f"✅ Место: <b>{format_station(message.text)}</b>")

@dp.message(Form.edit_station_manual)
async def edit_station_manual(message: types.Message, state: FSMContext):
    s = message.text.strip()
    if not s or len(s) > 100:
        await message.answer("❌ Некорректное название. Попробуй ещё раз:")
        return
    user_data[message.from_user.id]["station"] = s
    await return_to_summary(message, state, f"✅ Место: <b>{format_station(s)}</b>")

@dp.message(Form.edit_time)
async def edit_time(message: types.Message, state: FSMContext):
    try:
        if ":" not in message.text: raise ValueError
        h, m = map(int, message.text.strip().split(":"))
        if h < 0 or h > 24 or m < 0 or m > 59 or (h == 24 and m != 0): raise ValueError
    except ValueError:
        await message.answer("❌ Неверный формат. Введи <b>ЧЧ:ММ</b>:")
        return
    user_data[message.from_user.id]["time"] = f"{h:02d}:{m:02d}"
    await return_to_summary(message, state, f"✅ Время: <b>{f'{h:02d}:{m:02d}'}</b>")

# ==================== ДЕЙСТВИЯ АДМИНОВ ====================
@dp.callback_query(F.data.startswith("publish:"))
async def admin_publish(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    if callback.message.photo:
        caption = callback.message.caption
        # Отправляем фото в канал С parse_mode
        if CHANNEL_ID:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=callback.message.photo[-1].file_id,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        await callback.message.edit_caption(
            caption=caption + "\n\n✅ <b>ОДОБРЕНО И ОПУБЛИКОВАНО</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        text = callback.message.text
        # Отправляем текст в канал С parse_mode
        if CHANNEL_ID:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=text,
                parse_mode=ParseMode.HTML
            )
        await callback.message.edit_text(
            text=text + "\n\n✅ <b>ОДОБРЕНО И ОПУБЛИКОВАНО</b>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        await bot.send_message(
            uid,
            "✅ Ваша информация одобрена администратором и опубликована в канале!\n\nСпасибо за помощь каналу! 🚂"
        )
    except:
        pass
    
    await callback.answer("✅ Пост опубликован в канале", show_alert=True)

@dp.callback_query(F.data.startswith("reject:"))
async def admin_reject(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ У вас нет прав", show_alert=True); return
    if callback.message.photo: await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>")
    else: await callback.message.edit_text(callback.message.text + "\n\n❌ <b>ОТКЛОНЕНО</b>")
    await callback.answer("❌ Пост отклонен", show_alert=True)
    try: await bot.send_message(uid, "❌ Ваша информация показалась недостоверной. Пожалуйста, проверьте данные и отправьте заново.")
    except: pass

@dp.callback_query(F.data.startswith("ban:"))
async def admin_ban(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ У вас нет прав", show_alert=True); return
    BLACKLIST.add(uid)
    if callback.message.photo: await callback.message.edit_caption(caption=callback.message.caption + "\n\n🚫 <b>АВТОР ЗАБАНЕН</b>")
    else: await callback.message.edit_text(callback.message.text + "\n\n🚫 <b>АВТОР ЗАБАНЕН</b>")
    await callback.answer("🚫 Пользователь забанен", show_alert=True)
    
# ==================== WEBHOOK ДЛЯ VERCEL ====================
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

WEBHOOK_URL = "https://skzd-bot.vercel.app/webhook"
WEBHOOK_PATH = "/webhook"

@app.on_event("startup")
async def on_startup():
    """Настройка webhook при запуске"""
    await bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=dp.resolve_used_update_types(),
    )
    print("✅ Webhook установлен!")

@app.on_event("shutdown")
async def on_shutdown():
    """Удаление webhook при остановке"""
    await bot.delete_webhook()
    print(" Webhook удален!")

@app.post("/webhook")
async def webhook(request: Request):
    """Обработка webhook от Telegram"""
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        return JSONResponse({"ok": True})
    except Exception as e:
        print(f"Error processing update: {e}")
        return JSONResponse({"ok": False}, status_code=500)
        
# Игнорируем эти ошибки
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

@dp.errors()
async def errors_handler(event: types.ErrorEvent):
    if isinstance(event.exception, TelegramBadRequest):
        if "message is not modified" in str(event.exception):
            return True  # Игнорируем
        if "query is too old" in str(event.exception):
            return True  # Игнорируем
    return False

@app.get("/")

async def root():
    """Главная страница"""
    return {"message": "Bot is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
