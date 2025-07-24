import asyncpg
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from config import DATABASE_URL


class Database:
    def __init__(self):
        self.pool = None

    async def create_pool(self):
        """Ma'lumotlar bazasi ulanish poolini yaratish"""
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self.init_database()

    async def init_database(self):
        """Ma'lumotlar bazasini boshlang'ich holatga keltirish"""
        async with self.pool.acquire() as conn:
            # SQL faylni o'qish va bajarish
            with open('database.sql', 'r', encoding='utf-8') as f:
                await conn.execute(f.read())

    # FOYDALANUVCHILAR BILAN ISHLASH

    async def get_or_create_user(self, telegram_id: int, username: str = None,
                                 first_name: str = None) -> Dict:
        """Foydalanuvchini olish yoki yaratish"""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1", telegram_id
            )

            if not user:
                user = await conn.fetchrow(
                    """INSERT INTO users (telegram_id, username, first_name) 
                       VALUES ($1, $2, $3) RETURNING *""",
                    telegram_id, username, first_name
                )

            return dict(user)

    async def update_user_location(self, telegram_id: int, latitude: float,
                                   longitude: float, location_name: str = None):
        """Foydalanuvchi lokatsiyasini yangilash"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE users SET latitude = $1, longitude = $2, 
                   location_name = $3, updated_at = CURRENT_TIMESTAMP 
                   WHERE telegram_id = $4""",
                latitude, longitude, location_name, telegram_id
            )

    async def update_user_phone(self, telegram_id: int, phone: str):
        """Foydalanuvchi telefon raqamini yangilash"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE users SET phone = $1, updated_at = CURRENT_TIMESTAMP 
                   WHERE telegram_id = $2""",
                phone, telegram_id
            )

    async def set_user_as_employer(self, telegram_id: int):
        """Foydalanuvchini ish beruvchi qilib belgilash"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE users SET is_employer = TRUE, updated_at = CURRENT_TIMESTAMP 
                   WHERE telegram_id = $1""",
                telegram_id
            )

    # VAKANSIYALAR BILAN ISHLASH

    async def create_vacancy(self, employer_id: int, title: str, description: str,
                             salary_from: int = None, salary_to: int = None,
                             salary_type: str = 'monthly', work_schedule: str = None,
                             experience_required: str = None, address: str = None,
                             latitude: float = None, longitude: float = None,
                             phone: str = None, contact_name: str = None) -> int:
        """Vakansiya yaratish"""
        async with self.pool.acquire() as conn:
            vacancy_id = await conn.fetchval(
                """INSERT INTO vacancies 
                   (employer_id, title, description, salary_from, salary_to, 
                    salary_type, work_schedule, experience_required, address, 
                    latitude, longitude, phone, contact_name)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                   RETURNING id""",
                employer_id, title, description, salary_from, salary_to,
                salary_type, work_schedule, experience_required, address,
                latitude, longitude, phone, contact_name
            )
            return vacancy_id

    async def get_vacancy(self, vacancy_id: int) -> Optional[Dict]:
        """Vakansiyani ID bo'yicha olish"""
        async with self.pool.acquire() as conn:
            vacancy = await conn.fetchrow(
                """SELECT v.*, u.first_name as employer_name, u.username as employer_username
                   FROM vacancies v 
                   JOIN users u ON v.employer_id = u.id 
                   WHERE v.id = $1""",
                vacancy_id
            )
            return dict(vacancy) if vacancy else None

    async def get_nearby_vacancies(self, latitude: float, longitude: float,
                                   radius_km: int = 50, salary_from: int = None,
                                   offset: int = 0, limit: int = 5) -> List[Dict]:
        """Yaqin atrofdagi vakansiyalarni olish"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT v.*, u.first_name as employer_name, u.username as employer_username,
                       calculate_distance(v.latitude, v.longitude, $1, $2) as distance
                FROM vacancies v 
                JOIN users u ON v.employer_id = u.id 
                WHERE v.is_active = TRUE AND v.is_approved = TRUE
                AND calculate_distance(v.latitude, v.longitude, $1, $2) <= $3
            """
            params = [latitude, longitude, radius_km]

            if salary_from:
                query += " AND (v.salary_from >= $4 OR v.salary_to >= $4)"
                params.append(salary_from)

            query += " ORDER BY v.is_promoted DESC, distance ASC OFFSET $%d LIMIT $%d" % (
                len(params) + 1, len(params) + 2
            )
            params.extend([offset, limit])

            vacancies = await conn.fetch(query, *params)
            return [dict(v) for v in vacancies]

    async def get_pending_vacancies(self) -> List[Dict]:
        """Tasdiqlashni kutayotgan vakansiyalar"""
        async with self.pool.acquire() as conn:
            vacancies = await conn.fetch(
                """SELECT v.*, u.first_name as employer_name, u.username as employer_username
                   FROM vacancies v 
                   JOIN users u ON v.employer_id = u.id 
                   WHERE v.is_approved = FALSE 
                   ORDER BY v.created_at ASC"""
            )
            return [dict(v) for v in vacancies]

    async def approve_vacancy(self, vacancy_id: int):
        """Vakansiyani tasdiqlash"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE vacancies SET is_approved = TRUE WHERE id = $1",
                vacancy_id
            )

    async def reject_vacancy(self, vacancy_id: int):
        """Vakansiyani rad etish"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE vacancies SET is_active = FALSE WHERE id = $1",
                vacancy_id
            )

    async def promote_vacancy(self, vacancy_id: int, promotion_type: str,
                              duration_days: int = 7):
        """Vakansiyani reklama qilish"""
        async with self.pool.acquire() as conn:
            expires_at = datetime.now() + timedelta(days=duration_days)
            await conn.execute(
                """UPDATE vacancies 
                   SET is_promoted = TRUE, promotion_type = $1, 
                       promotion_expires_at = $2 
                   WHERE id = $3""",
                promotion_type, expires_at, vacancy_id
            )

    # OBUNALAR BILAN ISHLASH

    async def create_subscription(self, user_id: int, latitude: float,
                                  longitude: float, radius_km: int = 10,
                                  salary_from: int = None, keywords: str = None):
        """Obuna yaratish"""
        async with self.pool.acquire() as conn:
            # Eski obunani o'chirish
            await conn.execute(
                "DELETE FROM subscriptions WHERE user_id = $1", user_id
            )

            # Yangi obuna yaratish
            await conn.execute(
                """INSERT INTO subscriptions 
                   (user_id, latitude, longitude, radius_km, salary_from, keywords)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                user_id, latitude, longitude, radius_km, salary_from, keywords
            )

    async def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        """Foydalanuvchi obunasini olish"""
        async with self.pool.acquire() as conn:
            subscription = await conn.fetchrow(
                "SELECT * FROM subscriptions WHERE user_id = $1 AND is_active = TRUE",
                user_id
            )
            return dict(subscription) if subscription else None

    async def get_subscribers_for_vacancy(self, vacancy_id: int) -> List[Dict]:
        """Vakansiya uchun obunachlarni topish"""
        async with self.pool.acquire() as conn:
            vacancy = await self.get_vacancy(vacancy_id)
            if not vacancy:
                return []

            subscribers = await conn.fetch(
                """SELECT s.*, u.telegram_id 
                   FROM subscriptions s
                   JOIN users u ON s.user_id = u.id
                   WHERE s.is_active = TRUE 
                   AND calculate_distance(s.latitude, s.longitude, $1, $2) <= s.radius_km
                   AND (s.salary_from IS NULL OR $3 >= s.salary_from)""",
                vacancy['latitude'], vacancy['longitude'],
                vacancy['salary_from'] or 0
            )
            return [dict(s) for s in subscribers]

    # STATISTIKA

    async def get_statistics(self) -> Dict:
        """Statistikani olish"""
        async with self.pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            total_employers = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE is_employer = TRUE"
            )
            total_vacancies = await conn.fetchval("SELECT COUNT(*) FROM vacancies")
            active_vacancies = await conn.fetchval(
                "SELECT COUNT(*) FROM vacancies WHERE is_active = TRUE AND is_approved = TRUE"
            )
            pending_vacancies = await conn.fetchval(
                "SELECT COUNT(*) FROM vacancies WHERE is_approved = FALSE"
            )

            return {
                'total_users': total_users,
                'total_employers': total_employers,
                'total_vacancies': total_vacancies,
                'active_vacancies': active_vacancies,
                'pending_vacancies': pending_vacancies
            }

    async def close(self):
        """Ma'lumotlar bazasi ulanishini yopish"""
        if self.pool:
            await self.pool.close()


# Global database instance
db = Database()