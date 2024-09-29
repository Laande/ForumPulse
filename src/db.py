import aiosqlite
from .config import DATABASE


async def setup():
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
        async with db.execute("SELECT 1 FROM categories WHERE server_id = ? AND item_id = ?", 
                              (server_id, item_id)) as cursor:
            exists = await cursor.fetchone()
            if exists:
                return False

        await db.execute("INSERT OR IGNORE INTO servers (server_id) VALUES (?)", (server_id,))
        await db.execute("INSERT INTO categories (server_id, category_type, item_id) VALUES (?, ?, ?)",
                         (server_id, category_type, item_id))
        await db.commit()
        return True


async def get_channels(server_id):
    channels_by_category = {
        'category': [],
        'forum': [],
        'post': []
    }

    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT category_type, item_id FROM categories WHERE server_id = ?", (server_id,)) as cursor:
            async for row in cursor:
                category_type, item_id = row
                channels_by_category[category_type].append(item_id)

    return channels_by_category


async def remove_channel(server_id, item_id):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM categories WHERE server_id = ? AND item_id = ?", 
                         (server_id, item_id))
        await db.commit()


async def channel_exists(server_id, item_id):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT 1 FROM categories WHERE server_id = ? AND item_id = ?",
                              (server_id, item_id)) as cursor:
            return await cursor.fetchone() is not None