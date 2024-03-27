import aiosqlite

from config import DB_PATH

DEFAULT_CUSTOM_MOOD = "You're a helpful assistant. Speak user's language"
SQL_USERS_TABLE_QUERY = f'''CREATE TABLE IF NOT EXISTS users (
                            id INT PRIMARY KEY,
                            user_id INT NOT NULL,
                            peer_id INT NOT NULL,
                            ai_mood INT NOT NULL DEFAULT 1,
                            custom_mood TEXT NOT NULL DEFAULT "{DEFAULT_CUSTOM_MOOD}"
                        );'''
SQL_NEW_USER_QUERY = '''INSERT INTO users (user_id, peer_id)
                        VALUES (?,?);'''
SQL_DELETE_USER_QUERY = '''DELETE FROM users WHERE user_id=? AND peer_id=?'''


async def create_table() -> None:
    # Creating database file if it doesn't exist
    with open(DB_PATH, 'a'):
        pass

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(SQL_USERS_TABLE_QUERY)
        await db.commit()


async def create_account(user_id: int, peer_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(SQL_NEW_USER_QUERY, (user_id, peer_id))
        await db.commit()


async def delete_account(user_id: int, peer_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(SQL_DELETE_USER_QUERY, (user_id, peer_id))
        await db.commit()


async def is_registered(user_id: int, peer_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT EXISTS(SELECT 1 FROM users WHERE user_id=? AND peer_id=?);',
            (user_id, peer_id)
        ) as cur:
            user = await cur.fetchone()
    if user and user[0]:
        return True
    return False


async def update_value(user_id: int, peer_id: int, key: str, value) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {key}=? WHERE user_id=? AND peer_id=?",
            (value, user_id, peer_id)
        )
        await db.commit()


async def get_value(user_id: int, peer_id: int, key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f'SELECT {key} FROM users WHERE user_id=? AND peer_id=?',
            (user_id, peer_id)
        ) as cur:
            result = await cur.fetchone()
    if result is not None:
        return result[0]
