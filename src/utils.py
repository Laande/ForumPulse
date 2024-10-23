import os
import re
import discord
from src.config import TOKEN_FILE

def load_token() -> str:
    if not os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'w') as f:
            print(f"Token file '{TOKEN_FILE}' does not exist. Please enter your token:")
            token = input("Token: ").strip()
            save_token(f, token)
    
    with open(TOKEN_FILE, 'r') as f:
        token = f.read().strip()
        if not token:
            print(f"The token file '{TOKEN_FILE}' is empty. Please enter your token:")
            token = input("Token: ").strip()
            save_token(f, token)
    
    return token


def save_token(f, token: str) -> None:
    if token:
        f.write(token)
        print("Token has been saved.")
    else:
        print(f"Token not provided. You can manually add it in the '{TOKEN_FILE}' file.")


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
        return await bot.get_channel(channel_input)

def time_format(total_time) -> str:
    if total_time < 60:
        return f"{total_time:.0f}s"
    elif total_time < 3600:
        total_time = total_time / 60
        return f"{total_time:.2f}m"
    else:
        total_time = total_time / 3600
        return f"{total_time:.2f}h"