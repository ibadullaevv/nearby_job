-- Ma'lumotlar bazasi sxemasi

-- Foydalanuvchilar jadvali
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    phone VARCHAR(20),
    is_employer BOOLEAN DEFAULT FALSE,
    is_admin BOOLEAN DEFAULT FALSE,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vakansiyalar jadvali
CREATE TABLE IF NOT EXISTS vacancies (
    id SERIAL PRIMARY KEY,
    employer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    salary_from INTEGER,
    salary_to INTEGER,
    salary_type VARCHAR(50) DEFAULT 'monthly', -- hourly, daily, monthly
    work_schedule VARCHAR(100), -- to'liq/qisman kun, smenali
    experience_required VARCHAR(100), -- tajriba talab etilmaydi, 1-3 yil, etc
    address TEXT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    contact_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT FALSE,
    is_promoted BOOLEAN DEFAULT FALSE,
    promotion_type VARCHAR(50), -- top, urgent, highlight
    promotion_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Obunalar jadvali
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    radius_km INTEGER DEFAULT 10,
    salary_from INTEGER,
    keywords TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Statistika jadvali
CREATE TABLE IF NOT EXISTS statistics (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    total_users INTEGER DEFAULT 0,
    total_employers INTEGER DEFAULT 0,
    total_vacancies INTEGER DEFAULT 0,
    active_vacancies INTEGER DEFAULT 0,
    new_users_today INTEGER DEFAULT 0,
    new_vacancies_today INTEGER DEFAULT 0
);

-- To'lovlar jadvali
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    vacancy_id INTEGER REFERENCES vacancies(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    service_type VARCHAR(50) NOT NULL, -- promotion_type
    status VARCHAR(50) DEFAULT 'pending', -- pending, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indekslar
CREATE INDEX IF NOT EXISTS idx_vacancies_location ON vacancies(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_vacancies_active ON vacancies(is_active, is_approved);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_location ON subscriptions(latitude, longitude);

-- Masofani hisoblash funksiyasi (Haversine formula)
CREATE OR REPLACE FUNCTION calculate_distance(
    lat1 DECIMAL, lon1 DECIMAL,
    lat2 DECIMAL, lon2 DECIMAL
) RETURNS DECIMAL AS $$
BEGIN
    RETURN (
        6371 * acos(
            cos(radians(lat1)) *
            cos(radians(lat2)) *
            cos(radians(lon2) - radians(lon1)) +
            sin(radians(lat1)) *
            sin(radians(lat2))
        )
    );
END;
$$ LANGUAGE plpgsql;