import discord
from discord import app_commands
import aiosqlite

from src.config import DATABASE
from src.utils import load_token, get_channel
from src.db import setup_db
from src.update import weekly_forum_update


class MyBot(discord.Client):
    intents = discord.Intents.default()
    intents.guilds = True
    intents.message_content = True
    intents.reactions = True

    def __init__(self):
        super().__init__(intents=self.intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Connected as {self.user}')
        await self.tree.sync()
        await setup_db()
        weekly_forum_update.start(bot)


bot = MyBot()


@bot.tree.command(name="add_category", description="Add a category to monitor")
@app_commands.describe(category="The category to add (use #channel or ID)")
@app_commands.guild_only()
async def add_category(interaction: discord.Interaction, category: str):
    category_channel = await get_channel(category, bot)

    if isinstance(category_channel, discord.CategoryChannel):
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("INSERT OR IGNORE INTO servers (server_id) VALUES (?)", (interaction.guild.id,))
            await db.execute("INSERT INTO categories (server_id, category_type, item_id) VALUES (?, ?, ?)", 
                             (interaction.guild.id, 'category', category_channel.id))
            await db.commit()
        await interaction.response.send_message(f"Category {category_channel.name} added.")
    else:
        await interaction.response.send_message("The provided category is invalid or not a category.", ephemeral=True)


@bot.tree.command(name="add_forum", description="Add a specific forum to monitor")
@app_commands.describe(forum="The forum to add (use #channel or ID)")
@app_commands.guild_only()
async def add_forum(interaction: discord.Interaction, forum: str):
    forum_channel = await get_channel(forum, bot)

    if isinstance(forum_channel, discord.ForumChannel):
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("INSERT OR IGNORE INTO servers (server_id) VALUES (?)", (interaction.guild.id,))
            await db.execute("INSERT INTO categories (server_id, category_type, item_id) VALUES (?, ?, ?)", 
                             (interaction.guild.id, 'forum', forum_channel.id))
            await db.commit()
        await interaction.response.send_message(f"Forum {forum_channel.name} added.")
    else:
        await interaction.response.send_message("The provided forum is invalid or not a forum.", ephemeral=True)


@bot.tree.command(name="add_post", description="Add a specific post to monitor")
@app_commands.describe(post_id="The post to add (use #channel or ID)")
@app_commands.guild_only()
async def add_post(interaction: discord.Interaction, post_id: str):
    post_channel = await get_channel(post_id, bot)

    if isinstance(post_channel, discord.ForumChannel):
        post_id = post_channel.id
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("INSERT OR IGNORE INTO servers (server_id) VALUES (?)", (interaction.guild.id,))
            await db.execute("INSERT INTO categories (server_id, category_type, item_id) VALUES (?, ?, ?)", 
                             (interaction.guild.id, 'post', post_id))
            await db.commit()
        await interaction.response.send_message(f"Post with ID {post_id} added.")
    else:
        await interaction.response.send_message("The provided post is invalid or not a post.", ephemeral=True)


@bot.tree.command(name="info", description="Get information about the bot and its functionalities.")
async def info(interaction: discord.Interaction):
    info_message = (
        "This bot is designed to keep forums active.\n\n"
        "**Commands:**\n"
        "- </add_category:1290055778031632506>: Add all forums in the category.\n"
        "- </add_forum:1290055778031632507>: Add a specific forum.\n"
        "- </add_post:1290055778031632508>: Add a specific.\n\n"
        "The bot runs weekly to add a reaction to all monitored posts and then remove it."
    )
    await interaction.response.send_message(info_message)


if __name__ == "__main__":
    token = load_token()
    bot.run(token)