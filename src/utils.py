import os
import re
import discord
from src.config import TOKEN_FILE, PERMISSIONS_TO_CHECK


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


def check_perms(channel: discord.abc.GuildChannel, inherited: set[str]) -> list[str]:
    perms = channel.permissions_for(channel.guild.me)
    return [p for p in PERMISSIONS_TO_CHECK if not getattr(perms, p, False) and p not in inherited]


def format_perms(perms: list[str]) -> str:
    return ", ".join(f"`{p}`" for p in perms)


async def permissions_report(guild: discord.Guild, tracked: list[tuple[int, str]]) -> discord.Embed:
    global_missing = {p for p in PERMISSIONS_TO_CHECK if not getattr(guild.me.guild_permissions, p, False)}
    tracked_by_type = {"category": set(), "forum": set()}
    for item_id, ctype in tracked:
        if ctype != "post":
            tracked_by_type[ctype].add(item_id)

    channels_by_id = {c.id: c for c in guild.channels}
    errors = {"Category": [], "Forum": [], "Channel": []}
    cat_missing = {}
    forums_in_categories = set()

    embed = discord.Embed(color=discord.Color.orange())
    if global_missing:
        embed.add_field(name="Global Server Permissions", value=f"Missing: {format_perms(global_missing)}", inline=False)

    for cat_id in tracked_by_type["category"]:
        category = channels_by_id.get(cat_id)
        if not category:
            errors["Category"].append(f"Category ID `{cat_id}` not found (maybe deleted?)")
            continue

        missing = check_perms(category, global_missing)
        cat_missing[cat_id] = set(missing)
        if missing:
            errors["Category"].append(f"**{category.name}** missing: {format_perms(missing)}")

        inherited = global_missing | cat_missing[cat_id]
        for child in category.channels:
            if isinstance(child, discord.ForumChannel):
                forums_in_categories.add(child.id)
            missing = check_perms(child, inherited)
            if missing:
                kind = "Forum" if isinstance(child, discord.ForumChannel) else "Channel"
                errors[kind].append(f"**<#{child.id}>** missing: {format_perms(missing)}")

    for forum_id in tracked_by_type["forum"] - forums_in_categories:
        forum = channels_by_id.get(forum_id)
        if not forum:
            errors["Forum"].append(f"**<#{forum_id}>** not found (maybe deleted?)")
            continue

        inherited = global_missing | cat_missing.get(forum.category_id, set())
        missing = check_perms(forum, inherited)
        if missing:
            errors["Forum"].append(f"**<#{forum.id}>** missing: {format_perms(missing)}")

    for kind, lines in errors.items():
        if lines:
            embed.add_field(name=f"{kind}s" if len(lines) > 1 else kind, value="\n".join(lines), inline=False)

    return embed