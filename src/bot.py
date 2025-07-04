import time
import discord
from discord import app_commands
from discord.ext import tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src import db, utils, update
from src.config import BOT_GUILD_ID, SERVER_CHANNEL_ID, USER_ID


class MyBot(discord.Client):
    intents = discord.Intents.default()
    intents.guilds = True
    intents.message_content = True
    intents.reactions = True

    def __init__(self):
        super().__init__(intents=self.intents)
        self.tree = app_commands.CommandTree(self)
        self.scheduler = AsyncIOScheduler()
        self.ready = False

    async def on_ready(self):
        if self.ready:
            return
        self.ready = True
        print(f'Connected as {self.user}')
        await self.tree.sync()
        await db.setup()
        
        self.start_scheduler()
        self.update_bot_status.start()
    
    def start_scheduler(self):
        self.scheduler.add_job(update.forum_update, CronTrigger(hour=0, minute=0, second=0), args=[self])
        self.scheduler.add_job(update.forum_update, CronTrigger(hour=12, minute=0, second=0), args=[self])
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
        post_set = await update.get_monitored_posts(self)
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"over {len(post_set)} posts"))
    
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        if not before.archived and after.archived:
            is_monitored = await db.is_monitored(after.guild.id, after.id)
            if is_monitored:
                try:
                    await after.edit(archived=False)
                    print(f"[DEBUG] {after.name} ({after.id}) unarchived automatically.")
                except discord.Forbidden:
                    pass


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
    category_channel = await utils.get_channel(category, bot)

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
    forum_channel = await utils.get_channel(forum, bot)

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
    post_channel = await utils.get_channel(post, bot)

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
    channel = utils.extract_id(channel)
    if not await db.channel_exists(interaction.guild.id, channel):
        await interaction.response.send_message(f"Channel <#{channel}> (`{channel}`) not found in the database.")
    else:
        await db.remove_channel(interaction.guild.id, channel)
        await interaction.response.send_message(f"<#{channel}> has been removed.")


@bot.tree.command(name="info", description="Get information about the bot and its functionalities.")
async def info(interaction: discord.Interaction):
    info_message = (
        "This bot is designed to keep forums active.\n"
        "The bot runs every day to unarchive or add a reaction to all monitored posts and then remove it.\n\n"
        "**Commands:** *(They all need manage channels permission)*\n"
        "- </add_category:1290079934060040272>: Add all forums in the category.\n"
        "- </add_forum:1290079934060040273>: Add a specific forum.\n"
        "- </add_post:1290079934060040274>: Add a specific post.\n"
        "- </list_channels:1290086788114944062>: List all channels.\n"
        "- </remove_channel:1290086788114944063>: Remove a channel.\n"
        "- </run_update:1292600854297444362>: Update tracked chanels.\n\n"
        "[Support server](<https://discord.gg/3b3qvn2aTc>)"
    )
    await interaction.response.send_message(info_message)


@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.cooldown(1, 7200, key=lambda i: i.guild_id)  # Cooldown of 2 hoors per server
@bot.tree.command(name="run_update", description="Update tracked channels.")
async def run_update(interaction: discord.Interaction):
    await interaction.response.defer()
    t_start = time.perf_counter()
    channels_number = await update.process_server(interaction.guild.id, bot)
    t_total = time.perf_counter() - t_start
    await interaction.followup.send(f"{channels_number} channels up in {utils.time_format(t_total)}.")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes_left = round(error.retry_after / 60)
        await interaction.response.send_message(f"Command is on cooldown. Try again in {minutes_left} minute{'s' if minutes_left > 1 else ''}.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while executing the command.", ephemeral=True)


@app_commands.check(lambda interaction: interaction.user.id == USER_ID)
@bot.tree.command(name="stats", description="Get statistics about the bot.")
async def server_stats(interaction: discord.Interaction):
    guilds = await db.get_servers()
    total_guild = len(guilds)
    total_thread = len(await update.get_monitored_posts(bot))
    
    embeds = []
    current_embed = discord.Embed(title="📊 Bot Statistics", color=discord.Color.blue())
    current_embed.add_field(name=utils.pluralize("Total Server", total_guild), value=total_guild, inline=True)
    current_embed.add_field(name=utils.pluralize("Total Thread", total_thread), value=total_thread, inline=True)
    field_count = 2
    
    for guild_id in guilds:
        guild = bot.get_guild(guild_id)
        if not guild:
            continue
        registered_categories = set(await db.get_categories_for_server(guild_id))
        registered_forums = set(await db.get_forums_for_server(guild_id))
        registered_threads = set(await db.get_posts_for_server(guild_id))
        
        for category_id in registered_categories:
            category = guild.get_channel(category_id)
            if category and isinstance(category, discord.CategoryChannel):
                registered_forums.update(forum.id for forum in category.forums if forum.id not in registered_forums and isinstance(forum, discord.ForumChannel))
        
        total_threads = len(registered_threads)
        for forum_id in registered_forums:
            forum = guild.get_channel(forum_id)
            if forum and isinstance(forum, discord.ForumChannel):
                total_threads += sum(1 for thread in forum.threads if thread not in registered_threads)

        if field_count >= 25:
            embeds.append(current_embed)
            current_embed = discord.Embed(title="📊 Bot Statistics", color=discord.Color.blue())
            field_count = 0

        if total_threads:
            current_embed.add_field(name=f"🏕️ {guild.name} ({guild_id})", value=f"{total_threads} {utils.pluralize('thread', total_threads)}", inline=False)
            field_count += 1
    
    embeds.append(current_embed)

    if embeds:
        view = utils.PaginatorView(embeds)
        await interaction.response.send_message(embed=embeds[0], view=view)
    else:
        await interaction.response.send_message("No data found.")


def update_on_ready():
    @bot.event
    async def on_ready():
        if bot.ready:
            return
        bot.ready = True
        await update.forum_update(bot)


def run(start_init = False):
    if start_init:
        update_on_ready()
    
    token = utils.load_token()
    bot.run(token)