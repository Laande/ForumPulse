import os
import re
from .config import TOKEN_FILE

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


def save_token(f, token: str):
    if token:
        f.write(token)
        print("Token has been saved.")
    else:
        print(f"Token not provided. You can manually add it in the '{TOKEN_FILE}' file.")


async def get_channel(channel_input: str, bot):
    if channel_input.isdigit():
        return bot.get_channel(int(channel_input))
    else:
        match = re.match(r'<#(\d+)>', channel_input)
        return bot.get_channel(int(match.group(1))) if match else None