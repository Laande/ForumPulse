import discord

from src import db
from src.config import EMOJI, BOT_GUILD_ID, STATUS_CHANNEL_ID

already_check = set()

async def weekly_forum_update(bot):
    server_ids = await db.get_servers()
    for server_id in server_ids:
        await process_server(server_id, bot)
    
    res_msg = f"Weekly forum update completed for {len(server_ids)} server{'s' if len(server_ids) > 1 else ''}."
    
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
    global already_check
    already_check = set()
    
    await check_stil_exist(server_id, bot)
    
    posts = await db.get_posts_for_server(server_id)
    for post_id in posts:
        await update_post(post_id, bot)

    forums = await db.get_forums_for_server(server_id)
    for forum_id in forums:
        await update_forum(bot.get_channel(forum_id), bot)

    categories = await db.get_categories_for_server(server_id)
    for category_id in categories:
        await update_category(bot.get_channel(category_id), bot)
    
    return len(already_check)


async def update_category(category: discord.CategoryChannel, bot):
    for channel in category.channels:
        if isinstance(channel, discord.ForumChannel):
            await update_forum(channel, bot)


async def update_forum(forum: discord.ForumChannel, bot):
    for thread in forum.threads:
        await update_post(thread.id, bot)
    
    async for thread in forum.archived_threads(limit=None):
        await update_post(thread.id, bot)


async def update_post(thread_id: int, bot: discord.Client):
    global already_check
    if thread_id in already_check:
        return

    already_check.add(thread_id)
    thread = await bot.fetch_channel(thread_id)
    if thread.archived:
        await thread.edit(archived=False)
    else:
        message = await thread.fetch_message(thread_id)
        await message.add_reaction(EMOJI)
        await message.remove_reaction(EMOJI, bot.user)


async def get_monitored_posts(bot):
    post_set = set()
    async for channels in db.list_all_channels():
        item_id, category_type = channels
        channel = await db.get_channels(item_id, bot)

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