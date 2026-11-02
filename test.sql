CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS common_words (
    id SERIAL PRIMARY KEY,
    russian_word TEXT NOT NULL,
    english_word TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS user_words (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    russian_word TEXT NOT NULL,
    english_word TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS learning_stats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word_id INTEGER NOT NULL,
    word_type VARCHAR(20) NOT NULL,
    correct_answers INTEGER NOT NULL DEFAULT 0,
    total_attempts INTEGER NOT NULL DEFAULT 0,
    last_reviewed TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO common_words (russian_word, english_word) VALUES
('Привет', 'Hello'),
('Книга', 'Book'),
('Время', 'Time'),
('Работа', 'Work'),
('Жизнь', 'Life'),
('Друг', 'Friend'),
('Дом', 'House'),
('Город', 'City'),
('Семья', 'Family'),
('Школа', 'School')
ON CONFLICT DO NOTHING;