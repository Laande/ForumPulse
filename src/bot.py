import time
import discord
from discord import app_commands
from discord.ext import tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src import db
from src.config import BOT_GUILD_ID, SERVER_CHANNEL_ID
from src.utils import load_token, get_channel, extract_id, time_format
from src.update import forum_update, process_server, get_monitored_posts


class MyBot(discord.Client):
    intents = discord.Intents.default()
    intents.guilds = True
    intents.message_content = True
    intents.reactions = True

    def __init__(self):
        super().__init__(intents=self.intents)
        self.tree = app_commands.CommandTree(self)
        self.scheduler = AsyncIOScheduler()

    async def on_ready(self):
        print(f'Connected as {self.user}')
        await self.tree.sync()
        await db.setup()
        
        self.start_scheduler()
        self.update_bot_status.start()
    
    def start_scheduler(self):
        self.scheduler.add_job(forum_update, CronTrigger(day_of_week='sun', hour=12, minute=0), args=[self])
        self.scheduler.add_job(forum_update, CronTrigger(day_of_week='wed', hour=12, minute=0), args=[self])
        self.scheduler.start()
    
    async def on_guild_join(self, guild: discord.Guild):
        if guild_log := bot.get_guild(BOT_GUILD_ID):
            if channel_log := guild_log.get_channel(SERVER_CHANNEL_ID):
                await channel_log.send(
                    f"✅ Joined a new server: **{guild.name}** (ID: {guild.id})\n"
                    f"👥 Members: {guild.member_count}\n"
                    f"📁 Channels: {len(guild.channels)}"
                )

    async def on_guild_remove(self, guild: discord.Guild):
        if guild_log := bot.get_guild(BOT_GUILD_ID):
            if channel_log := guild_log.get_channel(SERVER_CHANNEL_ID):
                await channel_log.send(f"❌ Removed from server: **{guild.name}** (ID: {guild.id})")
    
    @tasks.loop(hours=1)
    async def update_bot_status(self):
        await self.wait_until_ready()
        post_set = await get_monitored_posts(self)
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"over {len(post_set)} posts"))


bot = MyBot()


async def add_to_db(server_id, channel_type, channel_id):
    res = await db.add_element(server_id, channel_type, channel_id)
    if res:
        return f"<#{channel_id}> added."
    else:
        return f"<#{channel_id}> already in the db."


@bot.tree.command(name="add_category", description="Add a category to monitor")
@app_commands.describe(category="The category to add (use #channel or ID)")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels=True)
async def add_category(interaction: discord.Interaction, category: str):
    category_channel = await get_channel(category, bot)

    if isinstance(category_channel, discord.CategoryChannel):
        msg = await add_to_db(interaction.guild.id, 'category', category_channel.id)
        await interaction.response.send_message(msg)
    else:
        await interaction.response.send_message("The provided category is invalid or not a category.", ephemeral=True)


@add_category.autocomplete('category')
async def autocomplete_categories(interaction: discord.Interaction, current: str):
    categories = [channel for channel in interaction.guild.channels if isinstance(channel, discord.CategoryChannel)]
    return [
        app_commands.Choice(name=category.name, value=str(category.id))
        for category in categories
        if current.lower() in category.name.lower()
    ]


@bot.tree.command(name="add_forum", description="Add a specific forum to monitor")
@app_commands.describe(forum="The forum to add (use #channel or ID)")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels=True)
async def add_forum(interaction: discord.Interaction, forum: str):
    forum_channel = await get_channel(forum, bot)

    if isinstance(forum_channel, discord.ForumChannel):
        msg = await add_to_db(interaction.guild.id, 'forum', forum_channel.id)
        await interaction.response.send_message(msg)
    else:
        await interaction.response.send_message("The provided forum is invalid or not a forum.", ephemeral=True)


@add_forum.autocomplete('forum')
async def autocomplete_forum(interaction: discord.Interaction, current: str):
    forums = [channel for channel in interaction.guild.channels if isinstance(channel, discord.ForumChannel)]
    return [
        app_commands.Choice(name=forum.name, value=str(forum.id))
        for forum in forums
        if current.lower() in forum.name.lower()
    ]


@bot.tree.command(name="add_post", description="Add a specific post to monitor")
@app_commands.describe(post="The post to add (use #channel or ID)")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels=True)
async def add_post(interaction: discord.Interaction, post: str):
    post_channel = await get_channel(post, bot)

    if isinstance(post_channel, discord.threads.Thread):
        msg = await add_to_db(interaction.guild.id, 'post', post_channel.id)
        await interaction.response.send_message(msg)
    else:
        await interaction.response.send_message("The provided post is invalid or not a post.", ephemeral=True)


@add_post.autocomplete('post')
async def autocomplete_post(interaction: discord.Interaction, current: str):
    posts = []

    for channel in interaction.guild.channels:
        if isinstance(channel, discord.ForumChannel):
            for thread in channel.threads:
                posts.append(thread)

    return [
        app_commands.Choice(name=post.name, value=str(post.id))
        for post in posts
        if current.lower() in post.name.lower()
    ]


@bot.tree.command(name="list_channels", description="List all channels.")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels=True)
async def list_channels(interaction: discord.Interaction):
    channels_by_category = await db.get_channels(interaction.guild.id)
    response = ""

    for category_type, item_ids in channels_by_category.items():
        if item_ids:
            response += f"**{category_type.capitalize()}**:\n"
            for item_id in item_ids:
                response += f"- <#{item_id}>\n"
            response += "\n"

    if not any(channels_by_category.values()):
        response = "No channel found."

    await interaction.response.send_message(response)


@bot.tree.command(name="remove_channel", description="Remove a channel.")
@app_commands.describe(channel="The channel to remove (use #channel or ID)")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels=True)
async def remove_channel(interaction: discord.Interaction, channel: str):
    channel = extract_id(channel)
    if not await db.channel_exists(interaction.guild.id, channel):
        await interaction.response.send_message(f"Channel <#{channel}> (`{channel}`) not found in the database.")
    else:
        await db.remove_channel(interaction.guild.id, channel)
        await interaction.response.send_message(f"<#{channel}> has been removed.")


@bot.tree.command(name="info", description="Get information about the bot and its functionalities.")
async def info(interaction: discord.Interaction):
    info_message = (
        "This bot is designed to keep forums active.\n"
        "The bot runs 2 times per week to unarchive or add a reaction to all monitored posts and then remove it.\n\n"
        "**Commands:** *(They all need manage channels permission)*\n"
        "- </add_category:1290079934060040272>: Add all forums in the category.\n"
        "- </add_forum:1290079934060040273>: Add a specific forum.\n"
        "- </add_post:1290079934060040274>: Add a specific post.\n"
        "- </list_channels:1290086788114944062>: List all channels in the db.\n"
        "- </remove_channel:1290086788114944063>: Remove a channel from the db.\n"
        "- </run_update:1292600854297444362>: Update tracked chanels\n\n."
        "Support server: https://discord.gg/3b3qvn2aTc"
    )
    await interaction.response.send_message(info_message)


@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.cooldown(1, 7200, key=lambda i: i.guild_id)  # Cooldown of 2 hoors per server
@bot.tree.command(name="run_update", description="Update tracked channels.")
async def run_update(interaction: discord.Interaction):
    await interaction.response.defer()
    t_start = time.perf_counter()
    channels_number = await process_server(interaction.guild.id, bot)
    t_total = time.perf_counter() - t_start
    await interaction.followup.send(f"{channels_number} channels up in {time_format(t_total)}.")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes_left = round(error.retry_after / 60)
        await interaction.response.send_message(f"Command is on cooldown. Try again in {minutes_left} minute{'s' if minutes_left > 1 else ''}.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while executing the command.", ephemeral=True)


def run():
    token = load_token()
    bot.run(token)