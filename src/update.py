import discord
import asyncio
import time

from src import db
from src.utils import get_channel, time_format
from src.config import BOT_GUILD_ID, STATUS_CHANNEL_ID


async def forum_update(bot: discord.Client):
    time_start = time.perf_counter()
    server_ids = await db.get_servers()
    tasks = [process_server(server_id, bot) for server_id in server_ids]
    results = await asyncio.gather(*tasks)
    
    active_servers = sum(1 for r in results if r > 0)
    total_unarchived = sum(results)
    
    total_time = time.perf_counter() - time_start
    res_msg = f"Forum update completed: {total_unarchived} thread{'s' if total_unarchived > 1 else ''} unarchived in {active_servers} server{'s' if active_servers > 1 else ''} ({time_format(total_time)})"

    guild = bot.get_guild(BOT_GUILD_ID)
    channel = guild.get_channel(STATUS_CHANNEL_ID) if guild else None
    if channel:
        await channel.send(res_msg)
    else:
        print(res_msg)


async def check_still_exist(server_id: int, bot: discord.Client):
    server_ids = await db.get_servers()
    for server_id in server_ids:
        guild = bot.get_guild(server_id)
        if not guild:
            await db.remove_server(server_id)
            continue

        channels = await db.get_channels(server_id)
        for channel_id in channels['category'] + channels['forum'] + channels['post']:
            channel = guild.get_channel(channel_id)
            if not channel:
                await db.remove_channel(server_id, channel_id)


async def process_server(server_id: int, bot: discord.Client) -> int:
    already_check = set()
    unarchived_threads = 0

    await check_still_exist(server_id, bot)

    posts = await db.get_posts_for_server(server_id)
    for post_id in posts:
        if post_id not in already_check:
            already_check.add(post_id)
            if await update_post(post_id, bot):
                unarchived_threads += 1

    forums = await db.get_forums_for_server(server_id)
    for forum_id in forums:
        channel = bot.get_channel(forum_id)
        if channel:
            unarchived_threads += await update_forum(channel, bot, already_check)

    categories = await db.get_categories_for_server(server_id)
    for category_id in categories:
        channel = bot.get_channel(category_id)
        if channel:
            unarchived_threads += await update_category(channel, bot, already_check)

    return unarchived_threads


async def update_category(category: discord.CategoryChannel, bot: discord.Client, already_check: set) -> int:
    count = 0
    for channel in category.channels:
        if isinstance(channel, discord.ForumChannel):
            count += await update_forum(channel, bot, already_check)
    return count


async def update_forum(forum: discord.ForumChannel, bot: discord.Client, already_check: set) -> int:
    count = 0
    try:
        async for thread in forum.archived_threads(limit=None):
            if thread.id not in already_check:
                already_check.add(thread.id)
                if await update_post(thread.id, bot):
                    count += 1
    except discord.errors.Forbidden:
        pass
    return count


async def update_post(thread_id: int, bot: discord.Client) -> bool:
    try:
        thread = await bot.fetch_channel(thread_id)
        if thread.archived:
            await thread.edit(archived=False)
            return True
    except discord.errors.NotFound:
        return False


async def get_monitored_posts(bot: discord.Client) -> set:
    post_set = set()
    channels = await db.list_all_channels()
    for item_id, category_type in channels:
        channel = await get_channel(item_id, bot)
        
        if not channel:
            continue
        
        if category_type == 'forum':
            for thread in channel.threads:
                post_set.add(thread.id)
            try:
                async for thread in channel.archived_threads(limit=None):
                    post_set.add(thread.id)
            except discord.errors.Forbidden:
                pass

        elif category_type == 'category':
            for forum in channel.channels:
                if isinstance(forum, discord.ForumChannel):
                    for thread in forum.threads:
                        post_set.add(thread.id)

        elif category_type == 'post':
            post_set.add(item_id)

    return post_set