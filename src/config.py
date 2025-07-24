import os
from dotenv import load_dotenv

load_dotenv()

# Bot sozlamalari
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))

# Ma'lumotlar bazasi sozlamalari
DATABASE_URL = os.getenv('DATABASE_URL')

# Geolokatsiya sozlamalari
MAX_DISTANCE_KM = 50  # Maksimal masofani km da
DEFAULT_CITY = "Toshkent"

# Pullik xizmatlar narxlari (so'm)
PROMOTION_PRICES = {
    'top': 10000,  # Yuqoriga chiqarish
    'urgent': 15000,  # Tezkor e'lon
    'highlight': 5000,  # Ajratib ko'rsatish
}

# Pagintatsiya
VACANCIES_PER_PAGE = 5