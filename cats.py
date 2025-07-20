import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import random
import requests
from collections import Counter
import re

load_dotenv()

TOKEN = os.getenv('TOKEN')
THE_CAT_API = os.getenv('THE_CAT_API')
NASA_API = os.getenv('NASA_API_KEY')

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Reply Keyboard ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Котики')],
        [KeyboardButton(text='Случайная картинка NASA')],
        [KeyboardButton(text='SpaceX: Последний запуск')],
        [KeyboardButton(text='SpaceX: Ближайший запуск')],
        [KeyboardButton(text='SpaceX: Ракеты')],
        [KeyboardButton(text='SpaceX: О компании')],
    ],
    resize_keyboard=True
)

# --- TheCatAPI ---
def get_cat_breeds():
    url = 'https://api.thecatapi.com/v1/breeds'
    headers = {'x-api-key': THE_CAT_API}
    response = requests.get(url, headers=headers)
    try:
        return response.json()
    except Exception:
        return []

def get_cat_image_by_breed(breed_id):
    url = f'https://api.thecatapi.com/v1/images/search?breed_ids={breed_id}'
    headers = {'x-api-key': THE_CAT_API}
    response = requests.get(url, headers=headers)
    try:
        data = response.json()
        if isinstance(data, list) and len(data) > 0 and 'url' in data[0]:
            return data[0]['url']
        else:
            return None
    except Exception:
        return None

def get_breed_info(breed_name):
    breeds = get_cat_breeds()
    if not isinstance(breeds, list):
        return None
    for breed in breeds:
        if isinstance(breed, dict) and breed.get('name', '').lower() == breed_name.lower():
            return breed
    return None

# --- NASA APOD ---
def get_apod():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    random_date = start_date + (end_date - start_date) * random.random()
    date_str = random_date.strftime("%Y-%m-%d")
    url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API}&date={date_str}"
    response = requests.get(url)
    return response.json()

# --- Swagger Petstore ---
PETSTORE_URL = 'https://petstore.swagger.io/v2'

def get_petstore_pets_by_status(status='available'):
    url = f"{PETSTORE_URL}/pet/findByStatus?status={status}"
    response = requests.get(url)
    try:
        return response.json()
    except Exception:
        return []

def get_petstore_pet_photo(pet_id):
    url = f"{PETSTORE_URL}/pet/{pet_id}"
    response = requests.get(url)
    try:
        pet = response.json()
        # В Petstore нет прямого фото, но есть поле photoUrls
        if 'photoUrls' in pet and pet['photoUrls']:
            return pet['photoUrls'][0]
        else:
            return None
    except Exception:
        return None

def add_petstore_pet(name, status='available'):
    url = f"{PETSTORE_URL}/pet"
    data = {
        "name": name,
        "photoUrls": [],
        "status": status
    }
    response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    return response.json()

def is_valid_image_url(url):
    return isinstance(url, str) and url.startswith('http') and (
        url.endswith('.jpg') or url.endswith('.jpeg') or url.endswith('.png') or url.endswith('.gif'))

SPACEX_API = 'https://api.spacexdata.com/v4'

# --- SpaceX API ---
def get_spacex_latest_launch():
    url = f'{SPACEX_API}/launches/latest'
    response = requests.get(url)
    return response.json()

def get_spacex_next_launch():
    url = f'{SPACEX_API}/launches/next'
    response = requests.get(url)
    return response.json()

def get_spacex_rockets():
    url = f'{SPACEX_API}/rockets'
    response = requests.get(url)
    return response.json()

def get_spacex_company():
    url = f'{SPACEX_API}/company'
    response = requests.get(url)
    return response.json()

# --- Handlers ---
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer('Привет! Я мультибот! Выбери действие на клавиатуре:', reply_markup=main_kb)

@dp.message(F.text == 'Котики')
async def ask_cat_breed(message: Message):
    try:
        breeds = get_cat_breeds()
        if not (isinstance(breeds, list) and breeds):
            await message.answer('Не удалось получить список пород.', reply_markup=main_kb)
            return
        # Показываем максимум 10 пород для удобства
        breed_buttons = [[KeyboardButton(text=breed['name'])] for breed in breeds[:10] if 'name' in breed]
        breeds_kb = ReplyKeyboardMarkup(keyboard=breed_buttons + [[KeyboardButton(text='Назад')]], resize_keyboard=True)
        await message.answer('Выбери породу кота:', reply_markup=breeds_kb)
    except Exception as e:
        await message.answer(f'Произошла ошибка при получении списка пород: {e}', reply_markup=main_kb)

@dp.message(F.text == 'Случайная картинка NASA')
async def send_random_apod(message: Message):
    try:
        apod = get_apod()
        photo_url = apod.get('url')
        title = apod.get('title', '')
        explanation = apod.get('explanation', '')
        caption = f"{title}\n\n{explanation}"
        if len(caption) > 1000:
            short_caption = f"{title}\n\n{explanation[:950]}..."
            await message.answer_photo(photo=photo_url, caption=short_caption, reply_markup=main_kb)
            await message.answer(f"Продолжение описания:\n{explanation[950:]}", reply_markup=main_kb)
        else:
            await message.answer_photo(photo=photo_url, caption=caption, reply_markup=main_kb)
    except Exception as e:
        await message.answer(f'Произошла ошибка при получении картинки NASA: {e}', reply_markup=main_kb)

@dp.message(F.text == 'SpaceX: Последний запуск')
async def send_spacex_latest_launch(message: Message):
    try:
        launch = get_spacex_latest_launch()
        name = launch.get('name', 'Неизвестно')
        date_utc = launch.get('date_utc', 'Неизвестно')
        success = launch.get('success')
        status = 'Успех' if success else 'Неудача' if success is not None else 'Неизвестно'
        details = launch.get('details', 'Нет описания')
        links = launch.get('links', {})
        webcast = links.get('webcast')
        patch = links.get('patch', {}).get('large')
        text = f"Последний запуск SpaceX:\nНазвание: {name}\nДата: {date_utc}\nСтатус: {status}\nОписание: {details}"
        if patch and is_valid_image_url(patch):
            await message.answer_photo(photo=patch, caption=text[:1000], reply_markup=main_kb)
        else:
            await message.answer(text, reply_markup=main_kb)
        if webcast:
            await message.answer(f'Видео запуска: {webcast}', reply_markup=main_kb)
    except Exception as e:
        await message.answer(f'Ошибка при получении данных о последнем запуске: {e}', reply_markup=main_kb)

@dp.message(F.text == 'SpaceX: Ближайший запуск')
async def send_spacex_next_launch(message: Message):
    try:
        launch = get_spacex_next_launch()
        name = launch.get('name', 'Неизвестно')
        date_utc = launch.get('date_utc', 'Неизвестно')
        details = launch.get('details', 'Нет описания')
        links = launch.get('links', {})
        patch = links.get('patch', {}).get('large')
        text = f"Ближайший запуск SpaceX:\nНазвание: {name}\nДата: {date_utc}\nОписание: {details}"
        if patch and is_valid_image_url(patch):
            await message.answer_photo(photo=patch, caption=text[:1000], reply_markup=main_kb)
        else:
            await message.answer(text, reply_markup=main_kb)
    except Exception as e:
        await message.answer(f'Ошибка при получении данных о ближайшем запуске: {e}', reply_markup=main_kb)

@dp.message(F.text == 'SpaceX: Ракеты')
async def send_spacex_rockets(message: Message):
    try:
        rockets = get_spacex_rockets()
        if not rockets:
            await message.answer('Не удалось получить список ракет.', reply_markup=main_kb)
            return
        # Показываем максимум 5 ракет
        for rocket in rockets[:5]:
            name = rocket.get('name', 'Неизвестно')
            desc = rocket.get('description', 'Нет описания')
            img = rocket.get('flickr_images', [])
            text = f"Ракета: {name}\n{desc[:900]}"
            if img and is_valid_image_url(img[0]):
                await message.answer_photo(photo=img[0], caption=text[:1000], reply_markup=main_kb)
            else:
                await message.answer(text, reply_markup=main_kb)
    except Exception as e:
        await message.answer(f'Ошибка при получении списка ракет: {e}', reply_markup=main_kb)

@dp.message(F.text == 'SpaceX: О компании')
async def send_spacex_company(message: Message):
    try:
        company = get_spacex_company()
        name = company.get('name', 'SpaceX')
        founder = company.get('founder', 'Неизвестно')
        founded = company.get('founded', 'Неизвестно')
        employees = company.get('employees', 'Неизвестно')
        summary = company.get('summary', '')
        text = f"{name}\nОснователь: {founder}\nГод основания: {founded}\nСотрудников: {employees}\n\n{summary}"
        await message.answer(text[:4096], reply_markup=main_kb)
    except Exception as e:
        await message.answer(f'Ошибка при получении информации о компании: {e}', reply_markup=main_kb)

# --- Котики по породе ---
@dp.message(F.text.in_([breed['name'] for breed in get_cat_breeds() if 'name' in breed]))
async def send_cat_info_by_button(message: Message):
    try:
        breed_name = message.text
        breed_info = get_breed_info(breed_name)
        if breed_info:
            breed_id = breed_info['id']
            cat_image_url = get_cat_image_by_breed(breed_id)
            info = (f"Информация о породе кота:\n"
                    f"Название породы: {breed_info['name']}\n"
                    f"Описание породы: {breed_info['description']}\n"
                    f"Продолжительность жизни: {breed_info['life_span']} лет"
                    )
            if is_valid_image_url(cat_image_url):
                await message.answer_photo(photo=cat_image_url, caption=info, reply_markup=main_kb)
            elif cat_image_url:
                await message.answer(info + f"\n(Это не ссылка на изображение: {cat_image_url})", reply_markup=main_kb)
            else:
                await message.answer(info + "\n(Изображение не найдено)", reply_markup=main_kb)
        else:
            await message.answer('Порода не найдена.', reply_markup=main_kb)
    except Exception as e:
        await message.answer(f'Произошла ошибка при получении информации о породе: {e}', reply_markup=main_kb)

# --- Обработчик кнопки 'Назад' ---
@dp.message(F.text == 'Назад')
async def back_to_main_keyboard(message: Message):
    await message.answer('Вы вернулись в главное меню.', reply_markup=main_kb)

async def main():
   await dp.start_polling(bot)

if __name__ == '__main__':
   asyncio.run(main())