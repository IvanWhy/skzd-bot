import asyncio
import logging
from datetime import datetime, timezone, timedelta
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
CHANNEL_ID = os.getenv("CHANNEL_ID")
MAIN_ADMIN_ID = int(os.getenv("MAIN_ADMIN_ID", 0))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения!")

if isinstance(ADMIN_CHAT_ID, str):
    ADMIN_CHAT_ID = ast.literal_eval(ADMIN_CHAT_ID)
elif ADMIN_CHAT_ID is None:
    raise ValueError("❌ ADMIN_CHAT_ID не найден в переменных окружения!")

# ==================== БАЗА ДАННЫХ ====================
TRAIN_SERIES = {
    "Пассажирские электровозы": ["ЭП20", "ЭП1М", "ЭП1", "ЧС4Т", "ЧС4", "ЭП1П"],
    "Грузовые электровозы": ["2ЭС5К", "ВЛ80Т", "2ЭС4К", "ВЛ80С", "3ЭС5К", "ВЛ10", "ВЛ10У", "ВЛ11", "3ЭС5С", "2ЭС5С", "2ЭС5"],
    "Тепловозы": ["ТЭП70БС", "ТЭП70", "2ТЭ10М", "ТЭМ2", "2ТЭ116", "2ТЭ116У", "3ТЭ116У", "2ТЭ25КМ", "АЧ2", "АС01", "ЧМЭ3"],
    "МВПС": ["ЭД4М", "ЭД9М", "ЭД9МК", "ЭС1", "ЭС2ГП", "РА1", "РА2", "РА3"]             
}

STATIONS = [
    "Азов", "Батайск", "Волгоград-1", "Волгоград-2", "Волгодонская",
    "Горячий ключ", "Ейск", "Зверево", "Кавказская", "Каменская",
    "Керчь", "Кисловодск", "Краснодар-1", "Краснодар-2", "Красный Сулин",
    "Крымск", "Каневская", "Лихая", "Минеральные Воды", "Морозовская", "Майкоп", "Новороссийск",
    "Новочеркасск", "Первомайская", "Ростов-Берег", "Ростов-Главный", "Сальск",
    "Сочи", "Ставрополь", "Староминская-Тимашевская", "Таганрог", "Таганрог-пасс",
    "Тимашевск", "Тихорецкая", "Туапсе", "Шахтная"
]

DIRECTIONS = [
    "на Азов", "на Адлер", "на Батайск", "на Волгоград", "на Волгодонск", "на Горячий ключ",
    "на Ейск", "на Кавказскую", "на Керчь", "на Краснодар", "на Крымск", "на Каневскую",
    "на Лихую", "на Минеральные Воды", "на Майкоп", "на Новороссийск", "на Новочеркасск", "на Ростов",
    "на Ростов-берег", "на Сальск", "на Сочи", "на Ставрополь", "на Таганрог",
    "на Тимашевск", "на Тихорецкую"
]

SCHEDULES = {
    "028М": {"name": "Таврия/двухэтажный состав", "route": "Москва — Симферополь", "link": "https://rasp.yandex.ru/thread/R_028M_63438"},
    "027С": {"name": "Таврия/двухэтажный состав", "route": "Симферополь — Москва", "link": "https://rasp.yandex.ru/thread/R_027S_63438"},
    "018М": {"name": "Обычный ПДС", "route": "Москва — Симферополь", "link": "https://rasp.yandex.ru/thread/R_018M_63438"},
    "018Й": {"name": "Обычный ПДС", "route": "Симферополь — Москва", "link": "https://rasp.yandex.ru/thread/R_018J_63438"},
    "454М": {"name": "Обычный ПДС", "route": "Москва — Симферополь", "link": "https://rasp.yandex.ru/thread/R_454M_112"},
    "180А": {"name": "Таврия", "route": "Санкт-Петербург — Симферополь", "link": "https://rasp.yandex.ru/thread/R_180A_112"},
    "179С": {"name": "Таврия", "route": "Симферополь — Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_179S_112"},
    "092М": {"name": "Таврия", "route": "Москва — Севастополь", "link": "https://rasp.yandex.ru/thread/R_092M_63438"},
    "092С": {"name": "Таврия", "route": "Севастополь — Москва", "link": "https://rasp.yandex.ru/thread/R_092S_63438"},
    "007А": {"name": "Таврия", "route": "Санкт-Петербург — Керчь", "link": "https://rasp.yandex.ru/thread/R_007A_63438"},
    "008С": {"name": "Таврия", "route": "Керчь — Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_008S_63438"},
    "068Х": {"name": "Обычный ПДС", "route": "Москва — Керчь", "link": "https://rasp.yandex.ru/thread/R_068X_63438"},
    "068С": {"name": "Таврия", "route": "Керчь — Москва", "link": "https://rasp.yandex.ru/thread/R_068S_63438"},
    "020С": {"name": "Тихий Дон", "route": "Москва — Ростов", "link": "https://rasp.yandex.ru/thread/R_020S_112"},
    "019С": {"name": "Тихий Дон", "route": "Ростов — Москва", "link": "https://rasp.yandex.ru/thread/R_019S_112"},
    "104В": {"name": "Двухэтажный состав", "route": "Москва — Адлер", "link": "https://rasp.yandex.ru/thread/R_104V_112"},
    "104Ж": {"name": "Двухэтажный состав", "route": "Адлер — Москва", "link": "https://rasp.yandex.ru/thread/R_104ZH_112"},
    "102М": {"name": "Обычный ПДС", "route": "Москва — Адлер", "link": "https://rasp.yandex.ru/thread/R_102M_112"},
    "102С": {"name": "Обычный ПДС", "route": "Адлер — Москва", "link": "https://rasp.yandex.ru/thread/R_102S_112"},
    "084М": {"name": "Обычный ПДС", "route": "Москва — Адлер", "link": "https://rasp.yandex.ru/thread/R_084M_112"},
    "472М": {"name": "Обычный ПДС", "route": "Москва — Адлер", "link": "https://rasp.yandex.ru/thread/R_472M_112"},
    "083Э": {"name": "Обычный ПДС", "route": "Адлер — Москва", "link": "https://rasp.yandex.ru/thread/R_083E_112"},
    "101С": {"name": "Обычный ПДС", "route": "Адлер — Москва", "link": "https://rasp.yandex.ru/thread/R_101S_112"},
    "471С": {"name": "Обычный ПДС", "route": "Адлер — Москва", "link": "https://rasp.yandex.ru/thread/R_471S_112"},
    "103Ж": {"name": "Двухэтажный состав", "route": "Адлер — Москва", "link": "https://rasp.yandex.ru/thread/R_103ZH_112"},
    "030С": {"name": "Премиум", "route": "Москва — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_030S_112"},
    "030Й": {"name": "Премиум", "route": "Новороссийск — Москва", "link": "https://rasp.yandex.ru/thread/R_030J_112"},
    "249С": {"name": "Обычный ПДС", "route": "Новороссийск — Москва", "link": "https://rasp.yandex.ru/thread/R_249S_112"},
    "233С": {"name": "Обычный ПДС", "route": "Новороссийск — Москва", "link": "https://rasp.yandex.ru/thread/R_233S_112"},
    "287С": {"name": "Обычный ПДС", "route": "Новороссийск — Москва", "link": "https://rasp.yandex.ru/thread/R_287S_112"},
    "288М": {"name": "Обычный ПДС", "route": "Москва — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_288M_112"},
    "434М": {"name": "Обычный ПДС", "route": "Москва — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_434M_112"},
    "126Э": {"name": "Обычный ПДС", "route": "Москва — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_126E_112"},
    "012М": {"name": "Анапа-Москва", "route": "Москва — Анапа", "link": "https://rasp.yandex.ru/thread/R_012M_112"},
    "011Э": {"name": "Анапа-Москва", "route": "Анапа — Москва", "link": "https://rasp.yandex.ru/thread/R_011E_112"},
    "152М": {"name": "Обычный ПДС", "route": "Москва — Анапа", "link": "https://rasp.yandex.ru/thread/R_152M_112"},
    "156М": {"name": "Обычный ПДС", "route": "Москва — Анапа", "link": "https://rasp.yandex.ru/thread/R_156M_112"},
    "110В": {"name": "Обычный ПДС", "route": "Москва — Анапа", "link": "https://rasp.yandex.ru/thread/R_110V_112"},
    "109С": {"name": "Обычный ПДС", "route": "Анапа — Москва", "link": "https://rasp.yandex.ru/thread/R_109S_112"},
    "217С": {"name": "Обычный ПДС", "route": "Анапа — Москва", "link": "https://rasp.yandex.ru/thread/R_217S_112"},
    "155С": {"name": "Обычный ПДС", "route": "Анапа — Москва", "link": "https://rasp.yandex.ru/thread/R_155S_112"},
    "567С": {"name": "Обычный ПДС", "route": "Анапа — Москва", "link": "https://rasp.yandex.ru/thread/R_567S_112"},
    "004М": {"name": "Кавказ/двухэтажный состав", "route": "Москва — Кисловодск", "link": "https://rasp.yandex.ru/thread/R_004M_112"},
    "003С": {"name": "Кавказ/двухэтажный состав", "route": "Кисловодск — Москва", "link": "https://rasp.yandex.ru/thread/R_003S_112"},
    "144М": {"name": "Обычный ПДС", "route": "Москва — Кисловодск", "link": "https://rasp.yandex.ru/thread/R_144M_112"},
    "143Й": {"name": "Обычный ПДС", "route": "Кисловодск — Москва", "link": "https://rasp.yandex.ru/thread/R_143ZH_112"},
    "050А": {"name": "Обычный ПДС", "route": "Санкт-Петербург — Кисловодск", "link": "https://rasp.yandex.ru/thread/R_050A_112"},
    "049С": {"name": "Обычный ПДС", "route": "Кисловодск — Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_049S_112"},
    "230Й": {"name": "Обычный ПДС", "route": "Самара — Кисловодск", "link": "https://rasp.yandex.ru/thread/R_230ZH_112"},
    "810С": {"name": "Ласточка", "route": "Ростов-на-Дону — Кисловодск", "link": "https://rasp.yandex.ru/thread/R_810S_112"},
    "061С": {"name": "Эльбрус", "route": "Нальчик — Москва", "link": "https://rasp.yandex.ru/thread/R_061S_112"},
    "062М": {"name": "Обычный ПДС", "route": "Москва — Нальчик", "link": "https://rasp.yandex.ru/thread/R_062M_112"},
    "035С": {"name": "Северная Пальмира/двухэтажный состав", "route": "Адлер — Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_035S_112"},
    "036А": {"name": "Северная Пальмира/двухэтажный состав", "route": "Санкт-Петербург — Адлер", "link": "https://rasp.yandex.ru/thread/R_036A_112"},
    "121С": {"name": "Обычный ПДС", "route": "Новороссийск — Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_121S_112"},
    "122В": {"name": "Обычный ПДС", "route": "Санкт-Петербург — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_122V_112"},
    "260А": {"name": "Обычный ПДС", "route": "Санкт-Петербург — Анапа", "link": "https://rasp.yandex.ru/thread/R_260A_112"},
    "278А": {"name": "Обычный ПДС", "route": "Санкт-Петербург — Анапа", "link": "https://rasp.yandex.ru/thread/R_278A_112"},
    "259А": {"name": "Обычный ПДС", "route": "Санкт-Петербург — Анапа", "link": "https://rasp.yandex.ru/thread/R_259A_112"},
    "259Э": {"name": "Обычный ПДС", "route": "Анапа — Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_259E_112"},
    "246А": {"name": "Обычный ПДС", "route": "Санкт-Петербург — Ейск", "link": "https://rasp.yandex.ru/thread/R_246A_112"},
    "480А": {"name": "Обычный ПДС", "route": "Санкт-Петербург — Сухум", "link": "https://rasp.yandex.ru/thread/R_480A_112"},
    "479С": {"name": "Обычный ПДС", "route": "Сухум — Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_479S_112"},
    "136А": {"name": "Обычный ПДС", "route": "Санкт-Петербург — Махачкала", "link": "https://rasp.yandex.ru/thread/R_136A_112"},
    "135С": {"name": "Обычный ПДС", "route": "Махачкала — Санкт-Петербург", "link": "https://rasp.yandex.ru/thread/R_135S_112"},
    "642Ж": {"name": "Обычный ПДС", "route": "Адлер — Ростов-на-Дону", "link": "https://rasp.yandex.ru/thread/R_642ZH_112"},
    "642С": {"name": "Обычный ПДС", "route": "Ростов-на-Дону — Адлер", "link": "https://rasp.yandex.ru/thread/R_642S_112"},
    "442Э": {"name": "Обычный ПДС", "route": "Адлер — Ростов-на-Дону", "link": "https://rasp.yandex.ru/thread/R_442E_112"},
    "442С": {"name": "Обычный ПДС", "route": "Ростов-на-Дону — Адлер", "link": "https://rasp.yandex.ru/thread/R_442S_112"},
    "120С": {"name": "Обычный ПДС", "route": "Ростов-на-Дону — Таганрог", "link": "https://rasp.yandex.ru/thread/R_120S_112"},
    "806Р": {"name": "Ласточка", "route": "Таганрог — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_806R_112"},
    "806Э": {"name": "Ласточка", "route": "Новороссийск — Таганрог", "link": "https://rasp.yandex.ru/thread/R_806E_112"},
    "808С": {"name": "Ласточка", "route": "Ростов-на-Дону — Аэропорт Сочи", "link": "https://rasp.yandex.ru/thread/R_808S_112"},
    "153Э": {"name": "Обычный ПДС", "route": "Ростов-на-Дону — Москва", "link": "https://rasp.yandex.ru/thread/R_153E_112"},
    "492С": {"name": "Обычный ПДС", "route": "Адлер — Казань", "link": "https://rasp.yandex.ru/thread/R_492S_112"},
    "491Э": {"name": "Обычный ПДС", "route": "Казань — Адлер", "link": "https://rasp.yandex.ru/thread/R_491E_112"},
    "360Ч": {"name": "Обычный ПДС", "route": "Калининград — Адлер", "link": "https://rasp.yandex.ru/thread/R_360CH_112"},
    "360С": {"name": "Обычный ПДС", "route": "Адлер — Калининград", "link": "https://rasp.yandex.ru/thread/R_360S_112"},
    "359С": {"name": "Обычный ПДС", "route": "Адлер — Калининград", "link": "https://rasp.yandex.ru/thread/R_359S_112"},
    "014С": {"name": "Обычный ПДС", "route": "Сириус (Имеретинский курорт) — Саратов", "link": "https://rasp.yandex.ru/thread/R_014S_112"},
    "014Ж": {"name": "Обычный ПДС", "route": "Саратов — Сириус (Имеретинский курорт)", "link": "https://rasp.yandex.ru/thread/R_014ZH_112"},
    "223С": {"name": "Обычный ПДС", "route": "Анапа — Саратов", "link": "https://rasp.yandex.ru/thread/R_223S_112"},
    "469С": {"name": "Обычный ПДС", "route": "Новороссийск — Саратов", "link": "https://rasp.yandex.ru/thread/R_469S_112"},
    "289С": {"name": "Обычный ПДС", "route": "Анапа — Екатеринбург", "link": "https://rasp.yandex.ru/thread/R_289S_112"},
    "290Э": {"name": "Обычный ПДС", "route": "Екатеринбург — Анапа", "link": "https://rasp.yandex.ru/thread/R_290E_112"},
    "525С": {"name": "Обычный ПДС", "route": "Новороссийск — Екатеринбург", "link": "https://rasp.yandex.ru/thread/R_525S_112"},
    "477С": {"name": "Обычный ПДС", "route": "Адлер — Челябинск", "link": "https://rasp.yandex.ru/thread/R_477S_112"},
    "478У": {"name": "Обычный ПДС", "route": "Челябинск — Адлер", "link": "https://rasp.yandex.ru/thread/R_478U_112"},
    "326Э": {"name": "Обычный ПДС", "route": "Пермь — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_326E_112"},
    "115Э": {"name": "Обычный ПДС", "route": "Адлер — Томск", "link": "https://rasp.yandex.ru/thread/R_115E_112"},
    "116Н": {"name": "Обычный ПДС", "route": "Томск — Адлер", "link": "https://rasp.yandex.ru/thread/R_116N_112"},
    "507С": {"name": "Обычный ПДС", "route": "Новороссийск — Ижевск", "link": "https://rasp.yandex.ru/thread/R_507S_112"},
    "520У": {"name": "Обычный ПДС", "route": "Орск — Анапа", "link": "https://rasp.yandex.ru/thread/R_520U_112"},
    "118Й": {"name": "Обычный ПДС", "route": "Самара — Адлер", "link": "https://rasp.yandex.ru/thread/R_118ZH_112"},
    "114М": {"name": "Обычный ПДС", "route": "Москва — Краснодар", "link": "https://rasp.yandex.ru/thread/R_114M_112"},
    "506В": {"name": "Обычный ПДС", "route": "Тамбов — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_506V_112"},
    "513С": {"name": "Обычный ПДС", "route": "Анапа — Тамбов", "link": "https://rasp.yandex.ru/thread/R_513S_112"},
    "460В": {"name": "Обычный ПДС", "route": "Тамбов — Адлер", "link": "https://rasp.yandex.ru/thread/R_460V_112"},
    "459С": {"name": "Обычный ПДС", "route": "Адлер — Тамбов", "link": "https://rasp.yandex.ru/thread/R_459S_112"},
    "283С": {"name": "Обычный ПДС", "route": "Анапа — Череповец", "link": "https://rasp.yandex.ru/thread/R_283S_112"},
    "535С": {"name": "Обычный ПДС", "route": "Анапа — Смоленск", "link": "https://rasp.yandex.ru/thread/R_535S_112"},
    "187С": {"name": "Обычный ПДС", "route": "Новороссийск — Архангельск", "link": "https://rasp.yandex.ru/thread/R_187S_112"},
    "079С": {"name": "Обычный ПДС", "route": "Сириус (Имеретинский курорт) — Архангельск", "link": "https://rasp.yandex.ru/thread/R_079S_112"},
    "293С": {"name": "Обычный ПДС", "route": "Анапа — Мурманск", "link": "https://rasp.yandex.ru/thread/R_293S_112"},
    "294А": {"name": "Обычный ПДС", "route": "Мурманск — Анапа", "link": "https://rasp.yandex.ru/thread/R_294A_112"},
    "286А": {"name": "Обычный ПДС", "route": "Мурманск — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_286A_112"},
    "285С": {"name": "Обычный ПДС", "route": "Новороссийск — Мурманск", "link": "https://rasp.yandex.ru/thread/R_285S_112"},
    "309С": {"name": "Обычный ПДС", "route": "Адлер — Воркута", "link": "https://rasp.yandex.ru/thread/R_309S_112"},
    "310С": {"name": "Обычный ПДС", "route": "Воркута — Адлер", "link": "https://rasp.yandex.ru/thread/R_310S_112"},
    "258Я": {"name": "Обычный ПДС", "route": "Печора — Сириус (Имеретинский курорт)", "link": "https://rasp.yandex.ru/thread/R_258YA_112"},
    "490Б": {"name": "Обычный ПДС", "route": "Минск — Анапа", "link": "https://rasp.yandex.ru/thread/R_490B_112"},
    "301С": {"name": "Обычный ПДС", "route": "Адлер — Минск", "link": "https://rasp.yandex.ru/thread/R_301S_112"},
    "303С": {"name": "Обычный ПДС", "route": "Сухум — Москва", "link": "https://rasp.yandex.ru/thread/R_303S_112"},
    "304М": {"name": "Обычный ПДС", "route": "Москва — Сухум", "link": "https://rasp.yandex.ru/thread/R_304M_112"},
    "340Г": {"name": "Обычный ПДС", "route": "Нижний Новгород — Новороссийск", "link": "https://rasp.yandex.ru/thread/R_340G_112"},
    "037С": {"name": "Обычный ПДС", "route": "Сириус (Имеретинский курорт) — Нижний Новгород", "link": "https://rasp.yandex.ru/thread/R_037S_112"},
    "038Г": {"name": "Обычный ПДС", "route": "Нижний Новгород — Сириус (Имеретинский курорт)", "link": "https://rasp.yandex.ru/thread/R_038G_112"},
    "381С": {"name": "Обычный ПДС", "route": "Гудермес — Москва", "link": "https://rasp.yandex.ru/thread/R_381S_112"},
    "382Я": {"name": "Обычный ПДС", "route": "Москва — Гудермес", "link": "https://rasp.yandex.ru/thread/R_382YA_112"},
    "558Х": {"name": "Двухэтажный состав", "route": "Москва — Сириус (Имеретинский курорт)", "link": "https://rasp.yandex.ru/thread/R_558KH_112"},
    "044М": {"name": "Двухэтажный состав", "route": "Москва — Сириус (Имеретинский курорт)", "link": "https://rasp.yandex.ru/thread/R_044M_112"},
    "043С": {"name": "Двухэтажный состав", "route": "Сириус (Имеретинский курорт) — Москва", "link": "https://rasp.yandex.ru/thread/R_043S_112"},
    "547С": {"name": "Обычный ПДС", "route": "Сириус (Имеретинский курорт) — Белгород", "link": "https://rasp.yandex.ru/thread/R_547S_112"},
    "930Я": {"name": "Жемчужина Кавказа", "route": "Москва — Москва Казанская Тур", "link": "https://rasp.yandex.ru/thread/R_930YA_112"},
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
ACTIVE_USERS = set()  # Храним в памяти (сбросится при рестарте, но работает на Vercel)

def add_active_user(user_id):
    ACTIVE_USERS.add(user_id)

# ==================== КОНСТАНТЫ КНОПОК ====================
BTN_ADD_MULTIPLE = "➕ Добавить еще один ПС"
BTN_ADD_TRANSFER = "➕ Добавить еще перегоняемый"
BTN_FINISH = "✅ Закончить"
BTN_BACK = "⬅️ Назад"
BTN_CANCEL_EDIT = "⬅️ Отмена"
BTN_NONE_LIST = "❌ Ничего из списка"
BTN_DELETE = "🗑 Удалить:"
BTN_DELETE_TRANSFER = "🗑 Удалить перегоняемый:"
BTN_ADD_DESCRIPTION = "✏️ Добавить описание"
BTN_SKIP_DESCRIPTION = "⏭️ Пропустить"
BTN_REJECT_FAKE = "❌ Недостоверно"
BTN_REJECT_DUPLICATE = "🔁 Дубликат"
BTN_REJECT_NO_PHOTO = "📷 Нет фото"
BTN_REJECT_CUSTOM = "✏️ Своя причина"
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

REJECT_REASONS = {
    "fake": "❌ Недостоверная информация",
    "duplicate": "🔁 Дубликат (уже было)",
    "nophoto": "📷 Нет фотоподтверждения",
}

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

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

MOSCOW_TZ = timezone(timedelta(hours=3))
def get_moscow_now():
    return datetime.now(MOSCOW_TZ)

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
        if query == train_num_upper: return [(train_num, info)]
        train_digits = ''.join(c for c in train_num if c.isdigit())
        if train_digits and train_digits in query:
            results.append((train_num, info)); continue
        if name in query or query in name:
            results.append((train_num, info)); continue
        route_clean = route.replace(" ", "").replace("—", "").replace("-", "")
        query_clean = query.replace(" ", "").replace("—", "").replace("-", "")
        if route_clean and (route_clean in query_clean or query_clean in route_clean):
            results.append((train_num, info)); continue
    return results

def build_train_info(data: dict) -> str:
    train_info = ""
    if data.get("is_multiple"):
        multiple_units = data.get("multiple_units", [])
        if multiple_units:
            loco_list = "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in multiple_units])
            train_info = f"🚂🚂 <b>Сплотка:</b>\n{loco_list}"
        else: train_info = "🚂🚂 Сплотка (пусто)"
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
            if transfer_train_type == BTN_GRUZ: train_info += "  🚛 Под грузовым поездом"
            elif transfer_train_type == BTN_PDS and transfer_train_number and transfer_train_number != BTN_NO_INFO:
                if transfer_train_number in SCHEDULES:
                    schedule = SCHEDULES[transfer_train_number]
                    train_info += f'  🚆 Под поездом {transfer_train_number} «{schedule["name"]}» ({schedule["route"]})\n  📅 <a href="{schedule["link"]}">Расписание</a>'
                else: train_info += f"  🚆 Под поездом {transfer_train_number}"
            else: train_info += "  🤷 Поезд неизвестен"
        else: train_info = "➡️🚂 Перегонка (неполные данные)"
    else:
        if data["train_type"] == BTN_PDS and data["train_number"] != BTN_NO_INFO:
            train_num = data["train_number"]
            if train_num in SCHEDULES:
                schedule = SCHEDULES[train_num]
                train_info = f'🚆 Поезд {train_num} «{schedule["name"]}» ({schedule["route"]})\n📅 <a href="{schedule["link"]}">Расписание</a>'
            else: train_info = f"🚆 Поезд {train_num}"
        elif data["train_type"] == BTN_GRUZ: train_info = "🚛 Грузовой поезд"
        elif data["train_type"] == BTN_REZERV: train_info = "🔄 Резерв (свой ход)"
        elif data["train_type"] == BTN_LAB: train_info = "🔬 Лаборатория / Рельсосмазыватель"
        elif data["train_type"] == BTN_KHOZ: train_info = "🛠 Хозяйственный поезд"
        else: train_info = "🤷 Тип поезда неизвестен"
    return train_info

def build_summary(user_id: int) -> str:
    data = user_data[user_id]
    today = get_moscow_now().strftime("%d.%m.%Y")
    train_info = build_train_info(data)
    has_photo = "photo_id" in data
    summary = f"📋 <b>Проверьте правильность информации:</b>\n\n"
    if not (data.get("is_multiple") or data.get("is_transfer")):
        summary += f"🚂 <b>ПС:</b> {get_loco_name(data['series'], data['number'])}\n"
    summary += (f"{train_info}\n" f"🗺 <b>Направление:</b> {data['direction']}\n" f"📌 <b>Место:</b> {format_station(data['station'])}\n" f"🕒 <b>Актуальность:</b> {data['time']} ({today})\n" f"📸 <b>Фото:</b> {'есть' if has_photo else 'нет'}")
    if data.get("description"): summary += f"\n\n📝 <b>Описание:</b> {data['description']}"
    return summary

def build_channel_message(data: dict) -> str:
    today = get_moscow_now().strftime("%d.%m.%Y")
    train_info = build_train_info(data)
    message = ""
    if not (data.get("is_multiple") or data.get("is_transfer")):
        message += f"🚂 <b>ПС:</b> {get_loco_name(data['series'], data['number'])}\n"
    message += train_info + "\n" + f"🗺 <b>Направление:</b> {data['direction']}\n" + f"📌 <b>Место:</b> {format_station(data['station'])}\n" + f"🕒 <b>Актуальность:</b> {data['time']} ({today})"
    if data.get("description"): message += f"\n\n📝 <b>Описание:</b> {data['description']}"
    return message

def build_admin_message(data: dict, user) -> str:
    today = get_moscow_now().strftime("%d.%m.%Y")
    train_info = build_train_info(data)
    admin_msg = f"🚂 <b>Новая заявка от @{user.username or user.first_name}</b>\n\n"
    if not (data.get("is_multiple") or data.get("is_transfer")):
        admin_msg += f"🚂 <b>ПС:</b> {get_loco_name(data['series'], data['number'])}\n"
    admin_msg += f"{train_info}\n" + f"🗺 <b>Направление:</b> {data['direction']}\n" + f"📌 <b>Место:</b> {format_station(data['station'])}\n" + f"🕒 <b>Актуальность:</b> {data['time']} ({today})"
    if data.get("description"): admin_msg += f"\n\n📝 <b>Описание:</b> {data['description']}"
    return admin_msg

async def return_to_summary(message: types.Message, state: FSMContext, success_text: str):
    summary = build_summary(message.from_user.id)
    await message.answer(f"{success_text}\n\n{summary}", reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True, parse_mode="HTML")
    await state.set_state(Form.waiting_confirmation)

# ==================== КЛАВИАТУРЫ ====================
def get_series_categories_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=cat)] for cat in TRAIN_SERIES.keys()], resize_keyboard=True)

def get_series_keyboard(category):
    keyboard, row = [], []
    for series in TRAIN_SERIES[category]:
        row.append(KeyboardButton(text=series))
        if len(row) == 2: keyboard.append(row); row = []
    if row: keyboard.append(row)
    keyboard.append([KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_train_type_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=BTN_PDS)], [KeyboardButton(text=BTN_GRUZ)], 
        [KeyboardButton(text=BTN_REZERV)], [KeyboardButton(text=BTN_LAB)],
        [KeyboardButton(text=BTN_KHOZ)],
        [KeyboardButton(text=BTN_SPLOTKA)], [KeyboardButton(text=BTN_PEREGONKA)], [KeyboardButton(text=BTN_NO_INFO)]
    ], resize_keyboard=True)

def get_number_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=BTN_UNKNOWN_NUMBER)],
        [KeyboardButton(text=BTN_BACK)]
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

def get_confirmation_keyboard(with_description=False):
    if with_description:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Да, всё верно")], [KeyboardButton(text=BTN_ADD_DESCRIPTION)], [KeyboardButton(text="❌ Нет, изменить")]], resize_keyboard=True)
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Да, всё верно")], [KeyboardButton(text="❌ Нет, изменить")]], resize_keyboard=True)

def get_edit_fields_keyboard(is_multiple=False, is_transfer=False):
    if is_multiple:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_SPLOTKA), KeyboardButton(text="Тип поезда")], [KeyboardButton(text="Направление"), KeyboardButton(text="Место")], [KeyboardButton(text="Актуальность"), KeyboardButton(text=BTN_CANCEL_EDIT)]], resize_keyboard=True)
    elif is_transfer:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_PEREGONKA), KeyboardButton(text="Поезд перегонки")], [KeyboardButton(text="Направление"), KeyboardButton(text="Место")], [KeyboardButton(text="Актуальность"), KeyboardButton(text=BTN_CANCEL_EDIT)]], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="ПС"), KeyboardButton(text="Номер ПС")], [KeyboardButton(text="Тип поезда"), KeyboardButton(text="Номер поезда")], [KeyboardButton(text="Направление"), KeyboardButton(text="Место")], [KeyboardButton(text="Актуальность"), KeyboardButton(text=BTN_CANCEL_EDIT)]], resize_keyboard=True)

def get_multiple_action_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_ADD_MULTIPLE)], [KeyboardButton(text=BTN_FINISH)]], resize_keyboard=True)

def get_edit_multiple_keyboard(multiple_units):
    keyboard = [[KeyboardButton(text=f"{BTN_DELETE} {get_loco_name(u['series'], u['number'])}")] for u in multiple_units]
    keyboard.append([KeyboardButton(text=BTN_ADD_MULTIPLE), KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_transfer_action_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_ADD_TRANSFER)], [KeyboardButton(text=BTN_FINISH)]], resize_keyboard=True)

def get_edit_transfer_keyboard(transfer_data):
    keyboard = []
    main_loco = transfer_data.get("main", {})
    if main_loco: keyboard.append([KeyboardButton(text=f"🚂 Основной: {get_loco_name(main_loco['series'], main_loco['number'])} (изменить)")])
    for u in transfer_data.get("towed", []): keyboard.append([KeyboardButton(text=f"{BTN_DELETE_TRANSFER} {get_loco_name(u['series'], u['number'])}")])
    keyboard.append([KeyboardButton(text=BTN_ADD_TRANSFER), KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish:{user_id}")],
        [InlineKeyboardButton(text=BTN_REJECT_FAKE, callback_data=f"reject:{user_id}:fake"), InlineKeyboardButton(text=BTN_REJECT_DUPLICATE, callback_data=f"reject:{user_id}:duplicate")],
        [InlineKeyboardButton(text=BTN_REJECT_NO_PHOTO, callback_data=f"reject:{user_id}:nophoto"), InlineKeyboardButton(text=BTN_REJECT_CUSTOM, callback_data=f"reject:{user_id}:custom")],
        [InlineKeyboardButton(text="🚫 Забанить автора", callback_data=f"ban:{user_id}")]
    ])

# ==================== КОМАНДЫ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    add_active_user(message.from_user.id)
    if message.from_user.id in BLACKLIST:
        await message.answer("Вы заблокированы и не можете использовать бота."); return
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
    if message.from_user.id not in admin_ids: await message.answer("❌ У вас нет прав."); return
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
    if message.from_user.id not in admin_ids: await message.answer("❌ У вас нет прав."); return
    if not BLACKLIST: await message.answer("📋 Черный список пуст.")
    else: await message.answer(f"📋 Забаненные:\n" + "\n".join([f"• {uid}" for uid in BLACKLIST]))

@dp.message(Command("admin_msg"))
async def cmd_admin_msg(message: types.Message, state: FSMContext):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if message.from_user.id not in admin_ids: 
        await message.answer("❌ У вас нет прав."); return
    await message.answer("✏️ Напишите сообщение, которое будет отправлено всем администраторам:")
    await state.set_state(Form.waiting_admin_msg)

@dp.message(Form.waiting_admin_msg)
async def process_admin_msg(message: types.Message, state: FSMContext):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    text = message.text.strip()
    success_count = 0
    for aid in admin_ids:
        try:
            await bot.send_message(aid, f"📢 <b>Сообщение от админа:</b>\n\n{text}")
            success_count += 1
        except Exception as e:
            logging.error(f"Ошибка отправки админу {aid}: {e}")
    await message.answer(f"✅ Сообщение отправлено {success_count} администраторам.")
    await state.clear()

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if message.from_user.id not in admin_ids: 
        await message.answer("❌ У вас нет прав."); return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Использование: /broadcast <текст рассылки>")
        return
    
    text = args[1].strip()
    users = ACTIVE_USERS  # ИСПРАВЛЕНО: используем память, а не файл
    
    if not users:
        await message.answer("⚠️ Список пользователей пуст. Возможно, бот был перезагружен, и никто не нажимал /start после этого.")
        return

    await message.answer(f"⏳ Начинаю рассылку {len(users)} пользователям...")
    
    success_count = 0
    for uid in users:
        try:
            await bot.send_message(uid, f"📢 <b>Важное сообщение от администрации:</b>\n\n{text}")
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.warning(f"Не удалось отправить пользователю {uid}: {e}")
            
    await message.answer(f"✅ Рассылка завершена! Доставлено: {success_count} из {len(users)}")

# ==================== ОСНОВНОЙ ПОТОК ====================
@dp.message(Form.waiting_series_category)
async def process_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Пожалуйста, выбери категорию из списка:"); return
    user_data[message.from_user.id]["category"] = message.text
    await message.answer(f"📂 Выбрана категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.waiting_series)

@dp.message(Form.waiting_series)
async def process_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_series_category); return
    category = user_data[message.from_user.id]["category"]
    if message.text not in TRAIN_SERIES[category]: await message.answer("❌ Пожалуйста, выбери серию из списка:"); return
    user_data[message.from_user.id]["series"] = message.text
    await message.answer(f"🚂 Выбрана серия: <b>{message.text}</b>\n\nТеперь введи <b>номер ПС</b> (только цифры) или нажми кнопку:", reply_markup=get_number_keyboard())
    await state.set_state(Form.waiting_number)

@dp.message(Form.waiting_number)
async def process_number(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer(f"🚂 Выбрана серия: <b>{user_data[message.from_user.id]['series']}</b>\n\nТеперь введи <b>номер ПС</b>:", reply_markup=get_number_keyboard())
        return
    if message.text == BTN_UNKNOWN_NUMBER:
        user_data[message.from_user.id]["number"] = "Номер неизвестен"
        await message.answer("🔢 Номер ПС: <b>Номер неизвестен</b>\n\nКакой это тип поезда?", reply_markup=get_train_type_keyboard())
        await state.set_state(Form.waiting_train_type)
        return
    
    number = message.text.strip()
    if not number.isdigit() or len(number) > 10:
        await message.answer("❌ Некорректный номер. Введи только цифры (или нажми 'Номер неизвестен'):")
        return
    user_data[message.from_user.id]["number"] = number
    await message.answer(f"🔢 Номер ПС: <b>{number}</b>\n\nКакой это тип поезда?", reply_markup=get_train_type_keyboard())
    await state.set_state(Form.waiting_train_type)

@dp.message(Form.waiting_train_type)
async def process_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_PDS, BTN_GRUZ, BTN_REZERV, BTN_LAB, BTN_KHOZ, BTN_SPLOTKA, BTN_PEREGONKA, BTN_NO_INFO]:
        await message.answer("❌ Пожалуйста, выбери тип поезда из списка:"); return
    
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
    elif tt == BTN_REZERV:
        user_data[message.from_user.id]["train_number"] = "Резерв"
        await message.answer("🔄 В какую сторону едет локомотив?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif tt == BTN_LAB:
        user_data[message.from_user.id]["train_number"] = "Лаборатория"
        await message.answer("🔬 В какую сторону движется лаборатория?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    elif tt == BTN_KHOZ:
        user_data[message.from_user.id]["train_number"] = "Хозяйственный"
        await message.answer("🛠 В какую сторону движется хозяйственный поезд?", reply_markup=get_directions_keyboard())
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

@dp.message(Form.waiting_train_number)
async def process_train_number(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    if user_input.lower() == "нет":
        user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
        await message.answer("🚆 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction); return
    
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
        await state.set_state(Form.waiting_train_number_manual); return
    for tn, info in user_data[message.from_user.id].get("found_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["train_number"] = tn
            await message.answer(f"✅ Выбран поезд: <b>{tn} «{info['name']}»</b>\n\n🚆 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
            await state.set_state(Form.waiting_direction); return
    await message.answer("❌ Пожалуйста, выбери поезд из списка:")

@dp.message(Form.waiting_train_number_manual)
async def process_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20: await message.answer("❌ Некорректный номер. Попробуй ещё раз:"); return
    user_data[message.from_user.id]["train_number"] = tn
    await message.answer(f"🚆 Номер поезда: <b>{tn}</b>\n\nВ какую сторону едет поезд?", reply_markup=get_directions_keyboard())
    await state.set_state(Form.waiting_direction)

@dp.message(Form.waiting_multiple_action)
async def process_multiple_action(message: types.Message, state: FSMContext):
    action = message.text
    if action == BTN_ADD_MULTIPLE:
        await message.answer("📂 Выбери <b>категорию ПС</b> для следующего локомотива:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_multiple_series_category)
    elif action == BTN_FINISH:
        await message.answer("🗺 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
        await state.set_state(Form.waiting_direction)
    else: await message.answer("❌ Пожалуйста, выбери действие из списка:", reply_markup=get_multiple_action_keyboard())

@dp.message(Form.waiting_multiple_series_category)
async def process_multiple_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Пожалуйста, выбери категорию из списка:"); return
    user_data[message.from_user.id]["temp_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.waiting_multiple_series)

@dp.message(Form.waiting_multiple_series)
async def process_multiple_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_multiple_series_category); return
    category = user_data[message.from_user.id]["temp_category"]
    if message.text not in TRAIN_SERIES[category]: await message.answer("❌ Пожалуйста, выбери серию из списка:"); return
    user_data[message.from_user.id]["temp_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nВведи <b>номер ПС</b>:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.waiting_multiple_number)

@dp.message(Form.waiting_multiple_number)
async def process_multiple_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10: await message.answer("❌ Некорректный номер. Введи номер ПС:"); return
    user_data[message.from_user.id]["multiple_units"].append({"series": user_data[message.from_user.id]["temp_series"], "number": number})
    units = user_data[message.from_user.id]["multiple_units"]
    loco_list = "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units])
    await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n{loco_list}\n\n✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_series'], number)}</b>\n\nЧто дальше?", reply_markup=get_multiple_action_keyboard())
    await state.set_state(Form.waiting_multiple_action)

@dp.message(Form.waiting_transfer_towed_category)
async def process_transfer_towed_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Пожалуйста, выбери категорию из списка:"); return
    user_data[message.from_user.id]["temp_towed_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b> для перегоняемого:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.waiting_transfer_towed_series)

@dp.message(Form.waiting_transfer_towed_series)
async def process_transfer_towed_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.waiting_transfer_towed_category); return
    category = user_data[message.from_user.id]["temp_towed_category"]
    if message.text not in TRAIN_SERIES[category]: await message.answer("❌ Пожалуйста, выбери серию из списка:"); return
    user_data[message.from_user.id]["temp_towed_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nВведи <b>номер ПС</b> перегоняемого:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.waiting_transfer_towed_number)

@dp.message(Form.waiting_transfer_towed_number)
async def process_transfer_towed_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10: await message.answer("❌ Некорректный номер. Введи номер ПС:"); return
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
        await message.answer("➡️🚂 Перегонка под каким поездом?\n\nВыбери тип поезда:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_GRUZ)], [KeyboardButton(text=BTN_PDS)], [KeyboardButton(text=BTN_NO_INFO)]], resize_keyboard=True))
        await state.set_state(Form.waiting_transfer_train_type)
    else: await message.answer("❌ Пожалуйста, выбери действие из списка:", reply_markup=get_transfer_action_keyboard())

@dp.message(Form.waiting_transfer_train_type)
async def process_transfer_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_GRUZ, BTN_PDS, BTN_NO_INFO]: await message.answer("❌ Пожалуйста, выбери тип поезда из списка:"); return
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
        await state.set_state(Form.waiting_direction); return
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
        await state.set_state(Form.waiting_transfer_train_number_manual); return
    for tn, info in user_data[message.from_user.id].get("found_transfer_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["transfer_train_number"] = tn
            await message.answer(f"✅ Выбран поезд: <b>{tn} «{info['name']}»</b>\n\n🗺 В какую сторону едет поезд?", reply_markup=get_directions_keyboard())
            await state.set_state(Form.waiting_direction); return
    await message.answer("❌ Пожалуйста, выбери поезд из списка:")

@dp.message(Form.waiting_transfer_train_number_manual)
async def process_transfer_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20: await message.answer("❌ Некорректный номер. Попробуй ещё раз:"); return
    user_data[message.from_user.id]["transfer_train_number"] = tn
    await message.answer(f"🚆 Номер поезда: <b>{tn}</b>\n\nВ какую сторону едет поезд?", reply_markup=get_directions_keyboard())
    await state.set_state(Form.waiting_direction)

@dp.message(Form.waiting_direction)
async def process_direction(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введи направление вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_direction_manual); return
    if message.text not in DIRECTIONS: await message.answer("❌ Пожалуйста, выбери направление из списка:"); return
    user_data[message.from_user.id]["direction"] = message.text
    await message.answer("📍 Где вы заметили поезд? (Выберите станцию)", reply_markup=get_stations_keyboard())
    await state.set_state(Form.waiting_station)

@dp.message(Form.waiting_direction_manual)
async def process_direction_manual(message: types.Message, state: FSMContext):
    d = message.text.strip()
    if not d or len(d) > 50: await message.answer("❌ Некорректное направление. Попробуй ещё раз:"); return
    user_data[message.from_user.id]["direction"] = d
    await message.answer(f"🗺 Направление: <b>{d}</b>\n\n📍 Где вы заметили поезд?", reply_markup=get_stations_keyboard())
    await state.set_state(Form.waiting_station)

@dp.message(Form.waiting_station)
async def process_station(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введи название станции/О.П. вручную (например: <b>перегон Лихая - Морозовская</b> или <b>о.п. Березовый</b>):", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.waiting_station_manual); return
    if message.text not in STATIONS: await message.answer("❌ Пожалуйста, выбери станцию из списка:"); return
    user_data[message.from_user.id]["station"] = message.text
    await message.answer("🕐 Во сколько вы заметили поезд?\n\nНапиши время в формате <b>ЧЧ:ММ</b> или нажми кнопку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏰ Сейчас", callback_data="time_now")]]))
    await state.set_state(Form.waiting_time)

@dp.message(Form.waiting_station_manual)
async def process_station_manual(message: types.Message, state: FSMContext):
    s = message.text.strip()
    if not s or len(s) > 100: await message.answer("❌ Некорректное название. Попробуй ещё раз:"); return
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
        await message.answer("❌ Неверный формат. Введи <b>ЧЧ:ММ</b> (например: 11:30):"); return
    user_data[message.from_user.id]["time"] = f"{h:02d}:{m:02d}"
    await message.answer("📸 <b>Есть ли у вас фотоподтверждение?</b>\n\nОтправь фото или нажми кнопку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Нет фото", callback_data="no_photo")]]))
    await state.set_state(Form.waiting_photo)

@dp.callback_query(F.data == "time_now")
async def time_now_callback(callback: types.CallbackQuery, state: FSMContext):
    now = get_moscow_now()
    user_data[callback.from_user.id]["time"] = f"{now.hour:02d}:{now.minute:02d}"
    await callback.message.answer("📸 <b>Есть ли у вас фотоподтверждение?</b>\n\nОтправь фото или нажми кнопку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Нет фото", callback_data="no_photo")]]))
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
    await message.answer("✏️ Напиши описание (до 500 символов).\nНапример: <i>Ехал с хвоста поезда, заметил на перегоне...</i>", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_SKIP_DESCRIPTION)]], resize_keyboard=True))
    await state.set_state(Form.waiting_description)

@dp.message(Form.waiting_description)
async def save_description(message: types.Message, state: FSMContext):
    if message.text == BTN_SKIP_DESCRIPTION:
        user_data[message.from_user.id]["description"] = None
    else:
        text = message.text.strip()
        if len(text) > 500:
            await message.answer("❌ Слишком длинно. Максимум 500 символов. Попробуй ещё раз:"); return
        user_data[message.from_user.id]["description"] = text
    
    await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
    await state.set_state(Form.waiting_confirmation)

@dp.message(Form.waiting_confirmation)
async def process_confirmation(message: types.Message, state: FSMContext):
    if message.text == "✅ Да, всё верно":
        data = user_data[message.from_user.id]
        channel_msg = build_channel_message(data)
        admin_msg = build_admin_message(data, message.from_user)
        pending_publications[message.from_user.id] = {"text": channel_msg, "photo_id": data.get("photo_id")}
        admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
        for aid in admin_ids:
            try:
                if data.get("photo_id"): await bot.send_photo(aid, photo=data["photo_id"], caption=admin_msg, reply_markup=get_admin_keyboard(message.from_user.id))
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
    else: await message.answer("Пожалуйста, выберите один из вариантов:")

# ==================== РЕДАКТИРОВАНИЕ ====================
@dp.message(Form.edit_what)
async def process_edit_what(message: types.Message, state: FSMContext):
    choice = message.text
    data = user_data[message.from_user.id]
    is_mult = data.get("is_multiple", False)
    is_trans = data.get("is_transfer", False)
    if choice == BTN_SPLOTKA and is_mult:
        await message.answer("🚂🚂 <b>Редактирование сплотки:</b>\n\nВыбери действие:", reply_markup=get_edit_multiple_keyboard(data.get("multiple_units", [])), parse_mode="HTML")
        await state.set_state(Form.edit_multiple_action); return
    if choice == BTN_PEREGONKA and is_trans:
        await message.answer("➡️🚂 <b>Редактирование перегонки:</b>\n\nВыбери действие:", reply_markup=get_edit_transfer_keyboard(data.get("transfer_data", {})), parse_mode="HTML")
        await state.set_state(Form.edit_transfer_action); return
    if choice == "Поезд перегонки" and is_trans:
        await message.answer("🚆 Выбери тип поезда для перегонки:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_GRUZ)], [KeyboardButton(text=BTN_PDS)], [KeyboardButton(text=BTN_NO_INFO)]], resize_keyboard=True))
        await state.set_state(Form.edit_transfer_train_type); return
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
        await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
        await state.set_state(Form.waiting_confirmation)
    else: await message.answer("❌ Пожалуйста, выбери поле из списка:", reply_markup=get_edit_fields_keyboard(is_mult, is_trans))

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
            if get_loco_name(u['series'], u['number']) == name: units.pop(i); break
        if not units:
            user_data[message.from_user.id]["is_multiple"] = False
            user_data[message.from_user.id]["train_type"] = BTN_NO_INFO
            user_data[message.from_user.id]["train_number"] = BTN_NO_INFO
            await return_to_summary(message, state, "✅ Сплотка удалена.")
        else:
            await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n" + "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units]) + "\n\n✅ Локомотив удален\n\nВыбери действие:", reply_markup=get_edit_multiple_keyboard(units), parse_mode="HTML")
    elif action == BTN_BACK:
        await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
        await state.set_state(Form.waiting_confirmation)
    else: await message.answer("❌ Пожалуйста, выбери действие:", reply_markup=get_edit_multiple_keyboard(units))

@dp.message(Form.edit_multiple_series_category)
async def process_edit_multiple_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Пожалуйста, выбери категорию из списка:"); return
    user_data[message.from_user.id]["temp_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.edit_multiple_series)

@dp.message(Form.edit_multiple_series)
async def process_edit_multiple_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_multiple_series_category); return
    category = user_data[message.from_user.id]["temp_category"]
    if message.text not in TRAIN_SERIES[category]: await message.answer("❌ Пожалуйста, выбери серию из списка:"); return
    user_data[message.from_user.id]["temp_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nВведи <b>номер ПС</b>:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.edit_multiple_number)

@dp.message(Form.edit_multiple_number)
async def process_edit_multiple_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10: await message.answer("❌ Некорректный номер. Введи номер ПС:"); return
    user_data[message.from_user.id]["multiple_units"].append({"series": user_data[message.from_user.id]["temp_series"], "number": number})
    units = user_data[message.from_user.id]["multiple_units"]
    await message.answer(f"🚂🚂 <b>Сплотка:</b>\n\n" + "\n".join([f"• {get_loco_name(u['series'], u['number'])}" for u in units]) + f"\n\n✅ Добавлен: <b>{get_loco_name(user_data[message.from_user.id]['temp_series'], number)}</b>\n\nВыбери действие:", reply_markup=get_edit_multiple_keyboard(units), parse_mode="HTML")
    await state.set_state(Form.edit_multiple_action)

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
            if get_loco_name(u['series'], u['number']) == name: td["towed"].pop(i); break
        if not td.get("towed"):
            user_data[message.from_user.id]["is_transfer"] = False
            user_data[message.from_user.id]["train_type"] = BTN_NO_INFO
            await return_to_summary(message, state, "✅ Перегонка удалена.")
        else:
            await message.answer(f"➡️🚂 <b>Перегонка:</b>\n\n🚂 <b>Основной:</b> {get_loco_name(td['main']['series'], td['main']['number'])}\n🚂 <b>Перегоняемые:</b>\n" + "\n".join([f"  • {get_loco_name(u['series'], u['number'])}" for u in td['towed']]) + "\n\n✅ Удален\n\nВыбери действие:", reply_markup=get_edit_transfer_keyboard(td), parse_mode="HTML")
    elif action == BTN_BACK:
        await message.answer(build_summary(message.from_user.id), reply_markup=get_confirmation_keyboard(with_description=True), disable_web_page_preview=True)
        await state.set_state(Form.waiting_confirmation)
    else: await message.answer("❌ Пожалуйста, выбери действие:", reply_markup=get_edit_transfer_keyboard(td))

@dp.message(Form.edit_transfer_towed_category)
async def process_edit_transfer_towed_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Пожалуйста, выбери категорию из списка:"); return
    user_data[message.from_user.id]["temp_towed_category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.edit_transfer_towed_series)

@dp.message(Form.edit_transfer_towed_series)
async def process_edit_transfer_towed_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_transfer_towed_category); return
    category = user_data[message.from_user.id]["temp_towed_category"]
    if message.text not in TRAIN_SERIES[category]: await message.answer("❌ Пожалуйста, выбери серию из списка:"); return
    user_data[message.from_user.id]["temp_towed_series"] = message.text
    await message.answer(f"🚂 Серия: <b>{message.text}</b>\n\nВведи <b>номер ПС</b>:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.edit_transfer_towed_number)

@dp.message(Form.edit_transfer_towed_number)
async def process_edit_transfer_towed_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10: await message.answer("❌ Некорректный номер. Введи номер ПС:"); return
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

@dp.message(Form.edit_transfer_train_type)
async def process_edit_transfer_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    if tt not in [BTN_GRUZ, BTN_PDS, BTN_NO_INFO]: await message.answer("❌ Пожалуйста, выбери тип поезда из списка:"); return
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
        await return_to_summary(message, state, "✅ Поезд перегонки очищен"); return
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
        await state.set_state(Form.edit_transfer_train_number_manual); return
    for tn, info in user_data[message.from_user.id].get("found_transfer_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["transfer_train_number"] = tn
            await return_to_summary(message, state, f"✅ Поезд перегонки: <b>{tn} «{info['name']}»</b>"); return
    await message.answer("❌ Пожалуйста, выбери поезд из списка:")

@dp.message(Form.edit_transfer_train_number_manual)
async def process_edit_transfer_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20: await message.answer("❌ Некорректный номер. Попробуй ещё раз:"); return
    user_data[message.from_user.id]["transfer_train_number"] = tn
    await return_to_summary(message, state, f"✅ Поезд перегонки: <b>{tn}</b>")

@dp.message(Form.edit_series_category)
async def edit_series_category(message: types.Message, state: FSMContext):
    if message.text not in TRAIN_SERIES: await message.answer("❌ Пожалуйста, выбери категорию из списка:"); return
    user_data[message.from_user.id]["category"] = message.text
    await message.answer(f"📂 Категория: <b>{message.text}</b>\n\nТеперь выбери <b>серию ПС</b>:", reply_markup=get_series_keyboard(message.text))
    await state.set_state(Form.edit_series)

@dp.message(Form.edit_series)
async def edit_series(message: types.Message, state: FSMContext):
    if message.text == BTN_BACK:
        await message.answer("📂 Выбери категорию ПС:", reply_markup=get_series_categories_keyboard())
        await state.set_state(Form.edit_series_category); return
    category = user_data[message.from_user.id]["category"]
    if message.text not in TRAIN_SERIES[category]: await message.answer("❌ Пожалуйста, выбери серию из списка:"); return
    user_data[message.from_user.id]["series"] = message.text
    await return_to_summary(message, state, f"✅ Серия изменена на <b>{message.text}</b>")

@dp.message(Form.edit_number)
async def edit_number(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not number or len(number) > 10: await message.answer("❌ Некорректный номер. Введи номер ПС:"); return
    user_data[message.from_user.id]["number"] = number
    await return_to_summary(message, state, f"✅ Номер ПС изменён на <b>{number}</b>")

@dp.message(Form.edit_train_type)
async def edit_train_type(message: types.Message, state: FSMContext):
    tt = message.text
    # ИСПРАВЛЕНО: добавлен BTN_KHOZ в список разрешенных
    if tt not in [BTN_PDS, BTN_GRUZ, BTN_REZERV, BTN_LAB, BTN_KHOZ, BTN_SPLOTKA, BTN_PEREGONKA, BTN_NO_INFO]:
        await message.answer("❌ Пожалуйста, выбери тип поезда из списка:"); return
    user_data[message.from_user.id]["train_type"] = tt
    if tt == BTN_PDS:
        await message.answer("🚆 Введи номер поезда:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_train_number)
    elif tt == BTN_GRUZ:
        user_data[message.from_user.id]["train_number"] = "Грузовой"
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип изменён на <b>Грузовой поезд</b>")
    elif tt == BTN_REZERV:
        user_data[message.from_user.id]["train_number"] = "Резерв"
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип изменён на <b>Резерв</b>")
    elif tt == BTN_LAB:
        user_data[message.from_user.id]["train_number"] = "Лаборатория"
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип изменён на <b>Лаборатория</b>")
    elif tt == BTN_KHOZ:
        user_data[message.from_user.id]["train_number"] = "Хозяйственный"
        user_data[message.from_user.id]["is_multiple"] = False
        user_data[message.from_user.id]["is_transfer"] = False
        await return_to_summary(message, state, "✅ Тип изменён на <b>Хозяйственный</b>")
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
        await return_to_summary(message, state, "✅ Номер поезда очищен"); return
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
        await state.set_state(Form.edit_train_number_manual); return
    for tn, info in user_data[message.from_user.id].get("found_trains", []):
        if message.text == f"{tn} — {info['name']} ({info['route']})":
            user_data[message.from_user.id]["train_number"] = tn
            await return_to_summary(message, state, f"✅ Поезд: <b>{tn} «{info['name']}»</b>"); return
    await message.answer("❌ Пожалуйста, выбери поезд из списка:")

@dp.message(Form.edit_train_number_manual)
async def edit_train_number_manual(message: types.Message, state: FSMContext):
    tn = message.text.strip().upper()
    if not tn or len(tn) > 20: await message.answer("❌ Некорректный номер. Попробуй ещё раз:"); return
    user_data[message.from_user.id]["train_number"] = tn
    await return_to_summary(message, state, f"✅ Номер поезда: <b>{tn}</b>")

@dp.message(Form.edit_direction)
async def edit_direction(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введи направление вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_direction_manual); return
    if message.text not in DIRECTIONS: await message.answer("❌ Пожалуйста, выбери направление из списка:"); return
    user_data[message.from_user.id]["direction"] = message.text
    await return_to_summary(message, state, f"✅ Направление: <b>{message.text}</b>")

@dp.message(Form.edit_direction_manual)
async def edit_direction_manual(message: types.Message, state: FSMContext):
    d = message.text.strip()
    if not d or len(d) > 50: await message.answer("❌ Некорректное направление. Попробуй ещё раз:"); return
    user_data[message.from_user.id]["direction"] = d
    await return_to_summary(message, state, f"✅ Направление: <b>{d}</b>")

@dp.message(Form.edit_station)
async def edit_station(message: types.Message, state: FSMContext):
    if message.text == "✏️ Ввести вручную":
        await message.answer("✏️ Введи название станции/О.П. вручную:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Form.edit_station_manual); return
    if message.text not in STATIONS: await message.answer("❌ Пожалуйста, выбери станцию из списка:"); return
    user_data[message.from_user.id]["station"] = message.text
    await return_to_summary(message, state, f"✅ Место: <b>{format_station(message.text)}</b>")

@dp.message(Form.edit_station_manual)
async def edit_station_manual(message: types.Message, state: FSMContext):
    s = message.text.strip()
    if not s or len(s) > 100: await message.answer("❌ Некорректное название. Попробуй ещё раз:"); return
    user_data[message.from_user.id]["station"] = s
    await return_to_summary(message, state, f"✅ Место: <b>{format_station(s)}</b>")

@dp.message(Form.edit_time)
async def edit_time(message: types.Message, state: FSMContext):
    try:
        if ":" not in message.text: raise ValueError
        h, m = map(int, message.text.strip().split(":"))
        if h < 0 or h > 24 or m < 0 or m > 59 or (h == 24 and m != 0): raise ValueError
    except ValueError:
        await message.answer("❌ Неверный формат. Введи <b>ЧЧ:ММ</b>:"); return
    user_data[message.from_user.id]["time"] = f"{h:02d}:{m:02d}"
    await return_to_summary(message, state, f"✅ Время: <b>{f'{h:02d}:{m:02d}'}</b>")

# ==================== ДЕЙСТВИЯ АДМИНОВ ====================
@dp.callback_query(F.data.startswith("publish:"))
async def admin_publish(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ У вас нет прав", show_alert=True); return
    
    if uid not in pending_publications:
        await callback.answer("⚠️ Эта заявка уже обработана другим администратором!", show_alert=True)
        return

    pub_data = pending_publications.pop(uid, None)
    if pub_data:
        channel_text = pub_data["text"]
        channel_photo = pub_data.get("photo_id")
        if CHANNEL_ID:
            try:
                if channel_photo: await bot.send_photo(chat_id=CHANNEL_ID, photo=channel_photo, caption=channel_text, parse_mode=ParseMode.HTML)
                else: await bot.send_message(chat_id=CHANNEL_ID, text=channel_text, parse_mode=ParseMode.HTML)
            except Exception as e: logging.error(f"Ошибка публикации в канал: {e}")
    
    if callback.message.photo: await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ <b>ОДОБРЕНО И ОПУБЛИКОВАНО</b>", parse_mode=ParseMode.HTML)
    else: await callback.message.edit_text(text=callback.message.text + "\n\n✅ <b>ОДОБРЕНО И ОПУБЛИКОВАНО</b>", parse_mode=ParseMode.HTML)
    
    try: await bot.send_message(uid, "✅ Ваша информация одобрена администратором и опубликована в канале!\n\nСпасибо за помощь каналу! 🚂")
    except: pass
    await callback.answer("✅ Пост опубликован в канале", show_alert=True)

@dp.callback_query(F.data.startswith("reject:"))
async def admin_reject(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    uid = int(parts[1])
    reason_code = parts[2] if len(parts) > 2 else None
    
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ У вас нет прав", show_alert=True); return
    
    if uid not in pending_publications:
        await callback.answer("⚠️ Эта заявка уже обработана другим администратором!", show_alert=True)
        return
        
    pending_publications.pop(uid, None)
    
    reason_text = ""
    if reason_code and reason_code in REJECT_REASONS:
        reason_text = REJECT_REASONS[reason_code]
    elif reason_code == "custom":
        pending_rejections[uid] = {
            "admin_id": callback.from_user.id,
            "message_id": callback.message.message_id,
            "chat_id": callback.message.chat.id,
            "is_photo": bool(callback.message.photo),
            "original_caption": callback.message.caption if callback.message.photo else None,
            "original_text": callback.message.text if not callback.message.photo else None,
            "user_id": uid,
            "time": get_moscow_now().strftime("%H:%M")
        }
        await callback.message.answer("✏️ Напишите причину отклонения (до 300 символов):", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_REJECT_CANCEL, callback_data=f"cancel_reject:{uid}")]]))
        await callback.answer()
        return
    else:
        reason_text = "Причина не указана"
    
    # Уведомляем пользователя
    user_mention = "пользователь"
    try:
        if callback.message.caption and "от @" in callback.message.caption:
            user_mention = "@" + callback.message.caption.split("от @")[1].split("</b>")[0]
        elif callback.message.text and "от @" in callback.message.text:
            user_mention = "@" + callback.message.text.split("от @")[1].split("</b>")[0]
        await bot.send_message(uid, f"❌ Ваша заявка отклонена.\n\n<b>Причина:</b> {reason_text}\n\nВы можете отправить новую заявку командой /start", parse_mode=ParseMode.HTML)
    except:
        pass
    
    # УВЕДОМЛЕНИЕ ГЛАВНОМУ АДМИНУ
    if MAIN_ADMIN_ID and reason_text:
        try:
            admin_username = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
            await bot.send_message(
                MAIN_ADMIN_ID,
                f"🚫 <b>Заявка отклонена</b>\n\n"
                f"👤 <b>Пользователь:</b> {user_mention}\n"
                f"👮 <b>Отклонил:</b> {admin_username}\n"
                f"⏰ <b>Время:</b> {get_moscow_now().strftime('%H:%M')}\n"
                f"📋 <b>Причина:</b> {reason_text}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Ошибка уведомления главному админу: {e}")
    
    # Редактируем сообщение в чате админов
    if callback.message.photo:
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n❌ <b>ОТКЛОНЕНО</b>\nПричина: {reason_text}", parse_mode=ParseMode.HTML)
    else:
        await callback.message.edit_text(text=callback.message.text + f"\n\n❌ <b>ОТКЛОНЕНО</b>\nПричина: {reason_text}", parse_mode=ParseMode.HTML)
    
    await callback.answer("❌ Заявка отклонена", show_alert=True)

@dp.callback_query(F.data.startswith("cancel_reject:"))
async def cancel_reject(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids: await callback.answer("❌ У вас нет прав", show_alert=True); return
    pending_rejections.pop(uid, None)
    await callback.message.delete()
    await callback.answer("Отменено")

@dp.callback_query(F.data.startswith("ban:"))
async def admin_ban(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if callback.from_user.id not in admin_ids: await callback.answer("❌ У вас нет прав", show_alert=True); return
    
    if uid in admin_ids:
        await callback.answer("❌ Нельзя забанить другого администратора!", show_alert=True)
        return
    
    BLACKLIST.add(uid)
    pending_publications.pop(uid, None)
    if callback.message.photo: await callback.message.edit_caption(caption=callback.message.caption + "\n\n🚫 <b>АВТОР ЗАБАНЕН</b>", parse_mode=ParseMode.HTML)
    else: await callback.message.edit_text(text=callback.message.text + "\n\n🚫 <b>АВТОР ЗАБАНЕН</b>", parse_mode=ParseMode.HTML)
    await callback.answer("🚫 Пользователь забанен", show_alert=True)

# ==================== WEBHOOK ДЛЯ VERCEL ====================
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()
WEBHOOK_URL = "https://skzd-bot.vercel.app/webhook"

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(url=WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
    print("✅ Webhook установлен!")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    print(" Webhook удален!")

webhook_installed = False

@app.post("/webhook")
async def webhook(request: Request):
    global webhook_installed
    if not webhook_installed:
        try:
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url != WEBHOOK_URL:
                await bot.set_webhook(url=WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
                print("✅ Webhook переустановлен!")
            webhook_installed = True
        except Exception as e: print(f"❌ Ошибка установки webhook: {e}")
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        return JSONResponse({"ok": True})
    except Exception as e:
        print(f"Error processing update: {e}")
        return JSONResponse({"ok": False}, status_code=500)

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

@dp.errors()
async def errors_handler(event: types.ErrorEvent):
    if isinstance(event.exception, TelegramBadRequest):
        if "message is not modified" in str(event.exception): return True
        if "query is too old" in str(event.exception): return True
    return False

@app.get("/")
@app.head("/")
async def root():
    return {"message": "Bot is running!"}

@dp.message(F.text)
async def handle_reject_reason(message: types.Message):
    admin_ids = ADMIN_CHAT_ID if isinstance(ADMIN_CHAT_ID, list) else [ADMIN_CHAT_ID]
    if message.from_user.id not in admin_ids:
        return
    
    for uid, data in list(pending_rejections.items()):
        if data["admin_id"] == message.from_user.id:
            reason_text = message.text.strip()[:300]
            
            try:
                if data["is_photo"]:
                    original_caption = data.get("original_caption") or ""
                    await bot.edit_message_caption(chat_id=data["chat_id"], message_id=data["message_id"], 
                                                  caption=original_caption + f"\n\n❌ <b>ОТКЛОНЕНО</b>\nПричина: {reason_text}", 
                                                  parse_mode=ParseMode.HTML)
                else:
                    original_text = data.get("original_text") or ""
                    await bot.edit_message_text(chat_id=data["chat_id"], message_id=data["message_id"], 
                                               text=original_text + f"\n\n❌ <b>ОТКЛОНЕНО</b>\nПричина: {reason_text}", 
                                               parse_mode=ParseMode.HTML)
            except Exception as e:
                logging.error(f"Ошибка редактирования сообщения: {e}")
            
            try:
                await bot.send_message(uid, f"❌ Ваша заявка отклонена.\n\n<b>Причина:</b> {reason_text}\n\nВы можете отправить новую заявку командой /start", parse_mode=ParseMode.HTML)
            except:
                pass
            
            # УВЕДОМЛЕНИЕ ГЛАВНОМУ АДМИНУ
            if MAIN_ADMIN_ID:
                try:
                    admin_username = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
                    user_mention = f"@{data.get('user_mention', 'пользователь')}"
                    reject_time = data.get("time", get_moscow_now().strftime("%H:%M"))
                    
                    await bot.send_message(
                        MAIN_ADMIN_ID,
                        f"🚫 <b>Заявка отклонена</b>\n\n"
                        f"👤 <b>Пользователь:</b> {user_mention}\n"
                        f"👮 <b>Отклонил:</b> {admin_username}\n"
                        f"⏰ <b>Время:</b> {reject_time}\n"
                        f"📋 <b>Причина:</b> {reason_text}",
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logging.error(f"Ошибка уведомления главному админу: {e}")
            
            pending_rejections.pop(uid, None)
            await message.answer("✅ Причина отклонения отправлена пользователю.")
            return

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
