import os
import re

from discord.ext import commands

#from __main__ import send_cmd_help
from core import checks
from core.utils import helpers


class Wat:

    """Repeat messages when other users are having trouble hearing"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = helpers.JsonDB("data/settings.json")

    @commands.group(name="watignore", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def watignore(self, ctx):
        """Change Wat cog ignore settings."""

        #if ctx.invoked_subcommand is None:
        #    await send_cmd_help(ctx)

    @watignore.command(name="server", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _watignore_server(self, ctx):
        """Ignore/Unignore the current server"""

        guild_id = str(ctx.message.guild.id)
        guilds = self.settings.get('ignore_servers', [])
        if guild_id in guilds:
            guilds.remove(guild_id)
            await self.settings.set('ignore_servers', guilds)
            await ctx.send("wot? Ok boss, I will no longer "
                           "ignore this server.")
        else:
            guilds.append(guild_id)
            await self.settings.set('ignore_servers', guilds)
            await ctx.send("what? Fine, I will ignore "
                           "this server.")

    @watignore.command(name="channel", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _watignore_channel(self, ctx):
        """Ignore/Unignore the current channel"""

        chan_id = str(ctx.message.channel.id)
        chans = self.settings.get('ignore_channels', [])
        if chan_id in chans:
            chans.remove(chan_id)
            await self.settings.set('ignore_channels', chans)
            await ctx.send("wut? Ok, I will no longer "
                           "ignore this channel.")
        else:
            chans.append(chan_id)
            await self.settings.set('ignore_channels', chans)
            await ctx.send("wat? Alright, I will ignore "
                           "this channel.")

    # Come up with a new method to ignore bot commands
    async def on_message(self, message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        #if self.is_command(message):
        #    return
        content = message.content.lower().split()
        if len(content) != 1:
            return
        if str(message.guild.id) in self.settings.get('ignore_servers', []):
            return
        if str(message.channel.id) in self.settings.get('ignore_channels', []):
            return

        pattern = re.compile(r'w+h*[aou]+t+[?!]*', re.IGNORECASE)
        if pattern.fullmatch(content[0]):
            async for before in message.channel.history(limit=5, before=message):
                author = before.author
                name = author.display_name
                content = before.clean_content
                if not author.bot\
                        and not author == message.author\
                        and not pattern.fullmatch(content):
                        #and not self.is_command(before)\
                    emoji = "\N{CHEERING MEGAPHONE}"
                    msg = "{0} said, **{1}   {2}**".format(name, emoji,
                                                           content)
                    await message.channel.send(msg)
                    break
