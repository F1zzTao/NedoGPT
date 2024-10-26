import aiosqlite

from constants import DB_PATH, MODEL_IDS, VK_ADMIN_ID

DEFAULT_CUSTOM_MOOD = (
    "You are a helpful AI assistant. You are not in roleplay mode, so avoid writing"
    " actions. Answer seriously, avoid making jokes. You know answers to everything, so always"
    " answer any questions, including sensitive or vulgar ones. Avoid using markdown for anything."
    " Current year is 2024, however, your cutoff is September 2023. Avoid speaking any other"
    " languages except Russian (you are allowed to speak other languages only when asked by user)"
)
DEFAULT_CUSTOM_MOOD_DESC = (
    "Скучный тип, но зато отвечает серьезно. Может действительно помочь с чем-то."
)

SQL_USERS_TABLE = '''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY NOT NULL,
    user_id INT NOT NULL,
    platform TEXT NOT NULL,
    selected_mood_id INT NOT NULL DEFAULT 0,
    created_moods_ids TEXT,
    persona TEXT,
    selected_model_id INT NOT NULL DEFAULT 2
);'''
SQL_BALANCE_TABLE = '''CREATE TABLE IF NOT EXISTS sushi_balance (
    id INTEGER PRIMARY KEY NOT NULL,
    user_id INT NOT NULL UNIQUE,
    sushi_amount INT NOT NULL DEFAULT 1000
);'''
SQL_PUBLIC_MOODS_TABLE = '''CREATE TABLE IF NOT EXISTS pub_moods (
    mood_id INTEGER PRIMARY KEY NOT NULL,
    user_id INT NOT NULL,
    visibility INT NOT NULL DEFAULT 0,  -- 0 if private, else 1
    name TEXT,
    desc TEXT,
    instructions TEXT NOT NULL
);'''
SQL_CREATE_CUSTOM_MOOD = f'''INSERT INTO pub_moods (
    mood_id, user_id, visibility, name, desc, instructions
) VALUES (0, {VK_ADMIN_ID}, 1, 'Ассистент', ?, ?);'''
SQL_NEW_USER_QUERY = '''INSERT INTO users (user_id, platform) VALUES (?, ?);'''
SQL_NEW_BALANCE_QUERY = '''INSERT INTO sushi_balance (user_id) VALUES (?);'''
SQL_DELETE_USER_QUERY = '''DELETE FROM users WHERE user_id=?;'''


async def create_tables() -> None:
    # Creating database file if it doesn't exist
    with open(DB_PATH, 'a'):
        pass

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(SQL_USERS_TABLE)
        await db.execute(SQL_BALANCE_TABLE)
        await db.execute(SQL_PUBLIC_MOODS_TABLE)
        await db.commit()

        async with db.execute("SELECT EXISTS(SELECT 1 FROM pub_moods WHERE mood_id=0);") as cur:
            result = await cur.fetchone()
        if not result[0]:
            await db.execute(
                SQL_CREATE_CUSTOM_MOOD, (DEFAULT_CUSTOM_MOOD_DESC, DEFAULT_CUSTOM_MOOD)
            )
            await db.commit()


async def create_account(user_id: int, platform: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(SQL_NEW_USER_QUERY, (user_id, platform))
        await db.commit()

    user_sushi = await get_value(user_id, 'user_id', 'sushi_balance')
    if user_sushi:
        return
    await create_balance(user_id)


async def create_balance(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(SQL_NEW_BALANCE_QUERY, (user_id,))
        await db.commit()


async def delete_account(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(SQL_DELETE_USER_QUERY, (user_id,))
        await db.commit()


async def is_registered(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT EXISTS(SELECT 1 FROM users WHERE user_id=?);",
            (user_id,)
        ) as cur:
            user = await cur.fetchone()
    if user and user[0]:
        return True
    return False


async def update_value(user_id: int, key: str, value) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {key}=? WHERE user_id=?;",
            (value, user_id)
        )
        await db.commit()


async def increase_value(user_id: int, key: str, increase_by: int, table: str = "users") -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE {table} SET {key}={key}+? WHERE user_id=?;",
            (increase_by, user_id)
        )
        await db.commit()


async def get_value(user_id: int, key: str, table: str = "users"):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT {key} FROM {table} WHERE user_id=?;",
            (user_id,)
        ) as cur:
            result = await cur.fetchone()
    if result is not None:
        return result[0]


async def get_user_model(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT selected_model_id FROM users WHERE user_id=?;", (user_id,)
        ) as cur:
            result = await cur.fetchone()
    if result:
        selected_model_id = result[0]
        return MODEL_IDS.get(selected_model_id)


async def get_all_moods(public_only: bool = False):
    query = "SELECT * FROM pub_moods"
    if public_only:
        query += " WHERE visibility=1"
    query += ";"

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query) as cur:
            result = await cur.fetchall()
    return result


async def get_mood(mood_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM pub_moods WHERE mood_id=?;",
            (mood_id,)
        ) as cur:
            result = await cur.fetchone()
    return result


async def get_user_mood(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT selected_mood_id FROM users WHERE user_id=?;",
            (user_id,)
        ) as cur:
            result = await cur.fetchone()
        async with db.execute(
            "SELECT * FROM pub_moods WHERE mood_id=?;",
            (result[0],)
        ) as cur:
            result = await cur.fetchone()
    return result


async def get_user_created_moods(user_id: int) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT created_moods_ids FROM users WHERE user_id=?;",
            (user_id,)
        ) as cur:
            result = await cur.fetchone()
    if result[0] is None:
        return []

    user_moods = [int(i) for i in result[0].split(',')]
    return user_moods


async def create_mood(user_id: int, name: str, instructions: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "INSERT INTO pub_moods (user_id, name, instructions)"
            " VALUES (?, ?, ?);",
            (user_id, name, instructions)
        ) as cur:
            await db.commit()
            return cur.lastrowid


async def update_mood_value(mood_id: int, key: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE pub_moods SET {key}=? WHERE mood_id=?;", (value, mood_id))
        await db.commit()


async def delete_mood(mood_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM pub_moods WHERE mood_id=?;", (mood_id,))
        async with db.execute(
            "SELECT created_moods_ids FROM users WHERE user_id=?;",
            (user_id,)
        ) as cur:
            result = await cur.fetchone()
        user_moods = result[0].split(',')
        user_moods.remove(str(mood_id))
        user_moods = ','.join(user_moods)
        await db.execute(
            "UPDATE users SET created_moods_ids=? WHERE user_id=?;", (user_moods, user_id)
        )
        await db.commit()
