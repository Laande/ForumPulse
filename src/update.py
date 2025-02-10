import discord
import asyncio
import time

from src import db
from src.utils import get_channel, time_format
from src.config import EMOJI, BOT_GUILD_ID, STATUS_CHANNEL_ID


async def forum_update(bot):
    time_start = time.perf_counter()
    server_ids = await db.get_servers()
    tasks = [process_server(server_id, bot) for server_id in server_ids]
    results = await asyncio.gather(*tasks)
    total_time = time.perf_counter() - time_start
    res_msg = f"Forum update completed for {len(server_ids)} server{'s' if len(server_ids) > 1 else ''} in {time_format(total_time)}."
    
    guild = bot.get_guild(BOT_GUILD_ID)
    channel = guild.get_channel(STATUS_CHANNEL_ID) if guild else None
    if channel:
        await channel.send(res_msg)
    else:
        print(res_msg)


async def check_stil_exist(server_id, bot):
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


async def process_server(server_id, bot):
    already_check = set()
    
    await check_stil_exist(server_id, bot)
    
    posts = await db.get_posts_for_server(server_id)
    for post_id in posts:
        await update_post(post_id, bot, already_check)

    forums = await db.get_forums_for_server(server_id)
    for forum_id in forums:
        channel = bot.get_channel(forum_id)
        if channel:
            await update_forum(channel, bot, already_check)

    categories = await db.get_categories_for_server(server_id)
    for category_id in categories:
        channel = bot.get_channel(category_id)
        if channel:
            await update_category(channel, bot, already_check)
    
    return len(already_check)


async def update_category(category: discord.CategoryChannel, bot, already_check: set):
    for channel in category.channels:
        if isinstance(channel, discord.ForumChannel):
            await update_forum(channel, bot, already_check)


async def update_forum(forum: discord.ForumChannel, bot, already_check: set):
    for thread in forum.threads:
        await update_post(thread.id, bot, already_check)

    try: 
        async for thread in forum.archived_threads(limit=None):
            await update_post(thread.id, bot, already_check)
    except discord.errors.Forbidden:
        pass


async def update_post(thread_id: int, bot: discord.Client, already_check: set):
    if thread_id in already_check:
        return

    already_check.add(thread_id)
    thread = await bot.fetch_channel(thread_id)
    if thread.archived:
        try:
            await thread.edit(archived=False)
        except discord.errors.Forbidden:
            pass
    else:
        try:
            message = await thread.fetch_message(thread_id)
            await message.add_reaction(EMOJI)
            await message.remove_reaction(EMOJI, bot.user)
        except discord.errors.NotFound:
            pass


async def get_monitored_posts(bot):
    post_set = set()
    channels = await db.list_all_channels()
    for item_id, category_type in channels:
        channel = await get_channel(item_id, bot)
        
        if not channel:
            print(f"Channel {item_id} not found.")
            continue

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