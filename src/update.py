import discord
import aiosqlite
import asyncio
from discord.ext import tasks
from .config import DATABASE, RUN_EVERY, EMOJI
from .utils import get_channel


already_check = set()


@tasks.loop(hours=RUN_EVERY)
async def weekly_forum_update(bot):
    async with aiosqlite.connect(DATABASE) as db:
        servers = await db.execute("SELECT server_id FROM servers")
        server_ids = [row[0] for row in await servers.fetchall()]

        for server_id in server_ids:
            print(f"Updating {server_id}")
            await process_server(db, server_id, bot)
        
        print("All servers are up")


async def process_server(db, server_id, bot):
    global already_check
    already_check = set()
    
    async with db.execute("SELECT item_id FROM categories WHERE server_id = ? AND category_type = 'post'", (server_id,)) as cursor:
        posts = await cursor.fetchall()
        for post in posts:
            post_id = post[0]
            await update_post(post_id, bot)

    async with db.execute("SELECT item_id FROM categories WHERE server_id = ? AND category_type = 'forum'", (server_id,)) as cursor:
        forums = await cursor.fetchall()
        for forum in forums:
            forum_id = forum[0]
            await update_forum(bot.get_channel(forum_id), bot)

    async with db.execute("SELECT item_id FROM categories WHERE server_id = ? AND category_type = 'category'", (server_id,)) as cursor:
        categories = await cursor.fetchall()
        for category in categories:
            category_id = category[0]
            await update_category(bot.get_channel(category_id), bot)


async def update_category(category: discord.CategoryChannel, bot):
    for channel in category.channels:
        if isinstance(channel, discord.ForumChannel):
            await update_forum(channel, bot)


async def update_forum(forum: discord.ForumChannel, bot):
    for thread in forum.threads:
        await update_post(thread.id, bot)


async def update_post(thread_id: int, bot: discord.Client):
    global already_check
    
    if thread_id in already_check:
        return

    thread = await bot.fetch_channel(thread_id)
    message = await thread.fetch_message(thread_id)
    
    await message.add_reaction(EMOJI)
    await asyncio.sleep(2)
    await message.remove_reaction(EMOJI, bot.user)
    
    print(f"Post {thread_id} updated.")
    already_check.add(thread_id)


async def get_monitored_posts(bot):
    post_set = set()

    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT item_id, category_type FROM categories") as cursor:
            async for row in cursor:
                item_id, category_type = row
                channel = await get_channel(item_id, bot)

                if category_type == 'forum':
                    for thread in channel.threads:
                        post_set.add(thread.id)

                elif category_type == 'category':
                    for forum in channel.channels:
                        if isinstance(forum, discord.ForumChannel):
                            for thread in forum.threads:
                                post_set.add(thread.id)

                elif category_type == 'post':
                    post_set.add(item_id)

    return post_set

@tasks.loop(hours=1)
async def update_bot_status(bot):
    await bot.wait_until_ready()
    post_set = await get_monitored_posts(bot)

    total_posts = len(post_set)
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name=f"over {total_posts} posts"
    ))
    print(f"Bot status updated to watching over {total_posts} posts.")