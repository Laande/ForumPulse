import os
import re
import discord
from src.config import TOKEN_FILE


def load_token() -> str:
    if not os.path.exists(TOKEN_FILE):
        print(f"Token file '{TOKEN_FILE}' does not exist. Please enter your token:")
        token = input("Token: ").strip()
        save_token(token)
    
    with open(TOKEN_FILE, 'r') as f:
        token = f.read().strip()
        if not token:
            print(f"The token file '{TOKEN_FILE}' is empty. Please enter your token:")
            token = input("Token: ").strip()
            save_token(token)
    
    return token


def save_token(token: str) -> None:
    if token:
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
            print("Token has been saved.")
    else:
        print(f"Token not provided. You can manually add it in the '{TOKEN_FILE}' file.")
        exit(1)


def extract_id(channel_input: str) -> int:
    if channel_input.isdigit():
        return int(channel_input)
    else:
        match = re.match(r'<#(\d+)>', channel_input)
        return int(match.group(1)) if match else None


async def get_channel(channel_input: str, bot: discord.Client) -> discord.abc.GuildChannel:
    if not isinstance(channel_input, int):
        channel_input = extract_id(channel_input)
    if channel_input is None:
        return None
    else:
        return bot.get_channel(channel_input)


def time_format(total_time: int) -> str:
    if total_time < 60:
        return f"{total_time:.0f}s"
    elif total_time < 3600:
        total_time = total_time / 60
        return f"{total_time:.2f}m"
    else:
        total_time = total_time / 3600
        return f"{total_time:.2f}h"


def pluralize(word: str, count: int) -> str:
    return f"{word}{'s' if count > 1 else ''}"


def format_guild_stats(guild: discord.Guild, registered_forums: set, registered_threads: set) -> str:
    guild_info = ""

    # Process forums in categories
    for category in guild.categories:
        forum_count = sum(1 for channel in category.channels if isinstance(channel, discord.ForumChannel) and channel.id in registered_forums)
        if forum_count:
            guild_info += f"📁 **{category.name}** - {forum_count} {pluralize('forum', forum_count)}\n"

        # Process threads in forums
        for channel in category.channels:
            if isinstance(channel, discord.ForumChannel) and channel.id in registered_forums:
                threads_count = sum(1 for thread in channel.threads)
                if threads_count:
                    guild_info += f"↪ 💬 **{channel.name}** - {threads_count} {pluralize('thread', threads_count)}\n"

    # Process uncategorized forums
    uncategorized_forums = [channel for channel in guild.channels if isinstance(channel, discord.ForumChannel) and channel.category is None and channel.id in registered_forums]
    if uncategorized_forums:
        guild_info += "🗂 **Uncategorized Forums**\n"
        for forum in uncategorized_forums:
            threads_count_db = [thread for thread in forum.threads if thread.id in registered_threads]
            threads_count_channel = [thread for thread in forum.threads if thread.id not in threads_count_db]
            threads_count = len(threads_count_db) + len(threads_count_channel)
            guild_info += f"↪ 💬 **{forum.name}** - {threads_count} {pluralize('thread', threads_count)}\n"
        
        # Process threads not in a forum
        threads_count_outside_channel = 0
        for thread_id in registered_threads:
            thread = guild.get_thread(thread_id)
            if thread and thread.parent_id not in registered_forums:
                threads_count_outside_channel += 1

        if threads_count_outside_channel:
            guild_info += f"↪ 💬 **{threads_count_outside_channel}** {pluralize('thread', threads_count_outside_channel)} not in a tracked forum\n"

    return guild_info if guild_info else "No forums found"