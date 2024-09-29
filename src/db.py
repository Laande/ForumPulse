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


async def add_element(server_id, category_type, item_id):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT OR IGNORE INTO servers (server_id) VALUES (?)", (server_id,))
        await db.execute("INSERT INTO categories (server_id, category_type, item_id) VALUES (?, ?, ?)",
                         (server_id, category_type, item_id))
        await db.commit()