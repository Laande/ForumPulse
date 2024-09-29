import aiosqlite
from .config import DATABASE


async def setup_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS servers (
                            server_id INTEGER PRIMARY KEY)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS categories (
                            server_id INTEGER,
                            category_type TEXT,
                            item_id INTEGER,
                            FOREIGN KEY(server_id) REFERENCES servers(server_id))''')
        await db.commit()