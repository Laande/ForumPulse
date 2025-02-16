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


class PaginatorView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed], timeout: int = 180):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.update_buttons()

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        await self.update_embed(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        await self.update_embed(interaction)

    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1

    async def update_embed(self, interaction: discord.Interaction):
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)