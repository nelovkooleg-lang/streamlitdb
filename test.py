import os
import random
import psycopg2
import streamlit as st
from psycopg2.extras import RealDictCursor

# ============================================================
# ПОДКЛЮЧЕНИЕ И БАЗА ДАННЫХ
# ============================================================

def get_connection():
    os.environ['PGLANGUAGE'] = 'en'
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='streamlitdb',
    )
    conn.set_client_encoding("UTF8")
    return conn
def init_database():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                with open('test.sql', 'r', encoding='utf-8') as sql_file:
                    sql = sql_file.read()
                    cur.execute(sql)
                    conn.commit()
    except Exception as e:
        print(e)
def login_user(username:str):
    #TODO: Реализовать вход пользователя
    #Если пользователь существует - вернуть его id
    #Если нет - создать нового и вернуть его id
    username = username.strip()
    if not username:
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE username = %s;', (username,))
            user = cur.fetchone()
            if user:
                return user[0]
            cur.execute('INSERT INTO users(username) VALUES (%s) RETURNING id;', (username,))
            new_user = cur.fetchone()
            conn.commit()
            return new_user[0] if new_user else None

def get_user_words(user_id):
    """
    TODO: Получить все слова пользователя (общие + персональные)
    Возвращает список словарей: [{'id': 1, 'russian_word': 'красный', 'english_word': 'red', 'word_type': 'common'}, ...]
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = '''
                SELECT id, NULL as user_id, russian_word, english_word,'common' AS word_type
                FROM common_words
                UNION ALL
                SELECT id, user_id, russian_word, english_word,'personal' AS word_type
                FROM user_words
                WHERE user_id = %s
                ORDER BY russian_word;
                '''
            cur.execute(query, (user_id,))
            return cur.fetchall()

def add_personal_word(user_id, russian_word, english_word):
    russian_word = russian_word.strip()
    english_word = english_word.strip()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM user_words WHERE user_id = %s AND russian_word = %s AND english_word = %s;', (user_id,russian_word, english_word,))
            if cur.fetchone():
                return False

            cur.execute(
                '''
                INSERT INTO user_words (user_id, russian_word, english_word)
                VALUES (%s, %s, %s);
                ''',
                (user_id, russian_word, english_word),
            )
            conn.commit()
            return True

def delete_personal_word(user_id, word_id):
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'DELETE FROM user_words WHERE id = %s AND user_id = %s;',
                        (word_id, user_id),
                    )
                    if cur.rowcount > 0:
                        conn.commit()
                        return True
                    return False
def update_stats(user_id, word_id, word_type, is_correct):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM learning_stats WHERE user_id = %s AND word_id = %s AND word_type = %s;', (user_id, word_id, word_type))
            stat_row = cur.fetchone()
            correct_inc = 1 if is_correct else 0
            total_inc = 1
            if stat_row:
                cur.execute(
                    '''
                    UPDATE learning_stats
                    SET correct_answers = correct_answers + %s, total_answers = total_answers + %s
                    WHERE id = %s;
                    ''',
                    (correct_inc, total_inc, stat_row),
                    )
            else:
                cur.execute(
                    '''
                    INSERT INTO learning_stats (user_id, word_id, word_type, correct_answers, total_answers)
                    VALUES (%s, %s, %s, %s, %s);
                    ''',
                    (user_id, word_id, word_type, correct_inc, total_inc)
                )
                conn.commit()
def get_statistics(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = 'SELECT SUM(correct_answers), SUM(total_attempts) FROM learning_stats WHERE user_id = %s;'
            cur.execute(query, (user_id,))
            result = cur.fetchone()
            if not result or result[0] is None or result[1] is None:
                return {
                    'correct_answers': 0,
                    'total_attempts': 0,
                    'success_percentage': 0.0
                }
            correct = result[0]
            total = result[1]
            percent = round((correct / total) * 100, 1) if total > 0 else 0.0
            return {
                'correct_answers':correct,
                'total_attempts':total,
                'success_percentage':percent
                    }
        # ============================================================
        # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
        # ============================================================

def generate_options(correct_word, all_words):
            wrong_options_pool = [word for word in all_words if word != correct_word]
            while len(wrong_options_pool) < 3:
                wrong_options_pool.append('_')
            options = random.sample(wrong_options_pool, 3)
            options.append(correct_word)
            random.shuffle(options)
            return options

        # ============================================================
        # ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
        # ============================================================

def render_sidebar():
    st.sidebar.title('Вход')
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if st.session_state.user_id is None:
        input_name = st.sidebar.text_input('Введите ваше имя:', key='login_input')
        if st.sidebar.button('Войти'):
            if input_name.strip():
                user_id = login_user(input_name)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.username = input_name
                    st.rerun()
            else:
                st.sidebar.error('Имя не может быть пустым!')
        else:
            st.sidebar.success(f'Привет, {st.session_state.username}!')
            stats = get_statistics(st.session_state.user_id)
            st.sidebar.write(
                f'📊 Прогресс: {stats['correct_answers']}/{stats['total_attempts']} ({stats['success_percentage']}%)')
            if st.sidebar.button('Выйти'):
                st.session_state.user_id = None
                st.session_state.username = None
                st.rerun()


def render_study_tab(words):
    st.header('📖 Изучение слов')
    if not words:
        st.info('В словаре пока нет слов.')
        return
    if 'current_word_index' not in st.session_state:
        st.session_state.current_word_index = 0
    if 'quiz_options' not in st.session_state:
        st.session_state.quiz_options = None
    if 'answer_submitted' not in st.session_state:
        st.session_state.answer_submitted = False
    if st.session_state.current_word_index >= len(words):
        st.session_state.current_word_index = 0
    current_word = words[st.session_state.current_word_index]
    all_english_words = [w['english_word'] for w in words]
    if st.session_state.quiz_options is None:
        st.session_state.quiz_options = generate_options(current_word['english_word'], all_english_words)
    st.subheader(f'Как переводится слово: **{current_word['russian_word'].upper()}**?')
    col1, col2 = st.columns(2)
    options = st.session_state.quiz_options

    def check_answer(selected_option, current_word):
        st.session_state.answer_submitted = True
        is_correct = (selected_option == current_word['english_word'])
        st.session_state.is_correct = is_correct
        word_type = current_word.get('type', 'personal')
        update_stats(st.session_state.user_id, current_word, is_correct, word_type)
        update_stats(st.session_state.user_id, current_word['id'], word_type, is_correct)
        if is_correct:
            st.toast('Правильно!', icon='✅')
        else:
            st.toast(f'Неверно! Правильный ответ: {current_word['english_word']}', icon='🚨')

        col1, col2 = st.columns(2)
        with col1:
            st.button(
                options[0],
                use_container_width=True,
                disabled=st.session_state.answer_submitted,
                key='btn_opt_0',
                on_click=check_answer,
                args=(options[0], current_word)
            )
            st.button(
                options[1],
                use_container_width=True,
                disabled=st.session_state.answer_submitted,
                key='btn_opt_1',
                on_click=check_answer,
                args=(options[1], current_word)
            )
        with col2:
            st.button(
                options[2],
                use_container_width=True,
                disabled=st.session_state.answer_submitted,
                key='btn_opt_2',
                on_click=check_answer,
                args=(options[2], current_word)
            )

            st.button(
                options[3],
                use_container_width=True,
                disabled=st.session_state.answer_submitted,
                key='btn_opt_3',
                on_click=check_answer,
                args=(options[3], current_word)
            )

def render_add_word_tab():
    st.header('➕ Добавить новое слово')
    if not st.session_state.get('user_id'):
        st.warning('Пожалуйста, авторизуйтесь в боковой панели.')
        return
    with st.form('add_word_form', clear_on_submit=True):
        rus_word = st.text_input('Слово на русском:')
        eng_word = st.text_input('Перевод на английском:')
        submit_button = st.form_submit_button('Добавить в мой словарь')
        if submit_button:
            if rus_word.strip() and eng_word.strip():
                success = add_personal_word(st.session_state.user_id, rus_word, eng_word)
                if success:
                    st.success(f'🤝 Слово «{rus_word.strip()}» успешно добавлено!')
                else:
                    st.error('⚠️ Такое слово уже есть в вашем словаре.')
            else:
                st.error('Оба поля должны быть заполнены!')


def render_delete_word_tab(words):
    st.header('Удаление слов')
    if not st.session_state.get('user_id'):
        st.warning('Пожалуйста, авторизуйтесь в боковой панели.')
        return
    personal_words = [w for w in words if w.get('type') == 'personal' or 'user_id' in w]
    if not personal_words:
        st.info("У вас пока нет добавленных персональных слов для удаления.")
        return
    options_dict = {f'{w['russian_word']} — {w['english_word']}': w['id'] for w in personal_words}

    selected_display = st.selectbox('Выберите слово, которое хотите удалить:', list(options_dict.keys()))
    word_id_to_delete = options_dict[selected_display]
    confirm = st.checkbox('Я уверен, что хочу удалить это слово')
    if st.button('Удалить слово', type='primary', disabled=not confirm):
        success = delete_personal_word(st.session_state.user_id, word_id_to_delete)
        if success:
            st.success('Слово успешно удалено!')
            st.rerun()
        else:
            st.error('Не удалось удалить слово. Возможно, оно уже было удалено.')

def render_statistics_tab(user_id):
    st.header('📊 Ваша статистика')
    if not user_id:
        st.warning('Авторизуйтесь, чтобы увидеть свой прогресс.')
        return
    stats = get_statistics(user_id)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label='Всего попыток (ответов)', value=stats['total_attempts'])
    with col2:
        st.metric(label='Правильных ответов', value=stats['correct_answers'])
    with col3:
        st.metric(label='Успешность', value=f"{stats['success_percentage']}%")

    # st.subheader('📋 История последних ответов')
    # with get_connection() as conn:
    #     with conn.cursor() as cur:
    #         cur.execute(
    #             '''
    #             SELECT word_type, is_correct, answered_at
    #             FROM statistics_log
    #             WHERE user_id = %s
    #             ORDER BY answered_at DESC
    #             LIMIT 10;
    #             ''',
    #             (user_id,)
    #         )
    #         logs = cur.fetchall()

    # if logs:
    #     history_data = []
    #     for row in logs:
    #         status = '✅ Правильно' if row[1] else 'Ошибка'
    #         w_type = 'Личное' if row[0] == 'personal' else 'Общее'
    #         history_data.append({'Тип слова': w_type, 'Результат': status, 'Время': row[2].strftime("%Y-%m-%d %H:%M")})
    #
    #     st.table(history_data)
    # else:
    #     st.info('Вы еще не проходили тесты. История пуста.')

def render_schema():
    st.header('Схема базы данных')
    st.write('Ниже представлена архитектура таблиц PostgreSQL, используемая в приложении:')
    schema_markdown = '''
        ### 1. Таблица `users` (Пользователи)
        * `id` (SERIAL, PRIMARY KEY) — Уникальный ID пользователя
        * `username` (VARCHAR, UNIQUE) — Имя/логин пользователя

        ### 2. Таблица `user_words` (Личные слова)
        * `id` (SERIAL, PRIMARY KEY) — Уникальный ID записи
        * `user_id` (INTEGER, FOREIGN KEY) — Ссылка на создателя из таблицы `users`
        * `russian_word` (VARCHAR) — Слово на русском языке
        * `english_word` (VARCHAR) — Перевод на английском

        ### 3. Таблица `learninng_stats` (Агрегированная статистика)
        * `id` (SERIAL, PRIMARY KEY)
        * `user_id` (INTEGER, FOREIGN KEY) — Ссылка на `users`
        * `word_id` (INTEGER) — ID слова (из общего словаря или личного)
        * `word_type` (VARCHAR) — Категория слова ('common' / 'personal')
        * `correct_answers` (INTEGER) — Количество успешных угадываний
        * `total_answers` (INTEGER) — Всего попыток ответа
        '''
    st.markdown(schema_markdown)


    # ============================================================
    # ГЛАВНАЯ ФУНКЦИЯ
    # ============================================================

def main():
    st.set_page_config(
        page_title='EnglishCard',
        page_icon='🇬🇧',
        layout='centered'
    )
    st.title('🎴 EnglishCard — Изучай английский с удовольствием!')
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    init_database()
    render_sidebar()
    if st.session_state.user_id is not None:
        words = get_user_words(st.session_state.user_id)
        study_tab, add_tab, delete_tab, stats_tab, schema_tab = st.tabs([
            '📖 Изучение',
            '➕ Добавить слово',
            '🗑️ Удалить слово',
            '📊 Статистика',
            '🗄️ Схема БД',
        ])

        with study_tab:
            render_study_tab(words)

        with add_tab:
            render_add_word_tab()

        with delete_tab:
            render_delete_word_tab(words)

        with stats_tab:
            render_statistics_tab(st.session_state.user_id)

        with schema_tab:
            render_schema()
    else:
        st.info('👋 Добро пожаловать в EnglishCard!')
        st.write(
            '''
            Это интерактивное приложение для эффективного запоминания английских слов. 

            **Что вы можете делать после авторизации:**
            * 🧠 Проходить викторины по карточкам слов.
            * ➕ Создавать свой собственный персональный словарь.
            * 📊 Отслеживать личный прогресс и процент правильных ответов.

            Пожалуйста, **введите ваше имя в боковой панели слева**, чтобы войти в свой аккаунт или создать новый профиль!
            '''
        )


if __name__ == "__main__":
    main()