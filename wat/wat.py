import os
import re

from discord.ext import commands

from __main__ import send_cmd_help

from .utils import checks
from .utils.dataIO import dataIO


class Wat:

    """Repeat messages when other users are having trouble hearing"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/wat/settings.json"
        self.settings = dataIO.load_json(self.settings_path)

    @commands.group(name="watignore", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def watignore(self, ctx):
        """Change Wat cog ignore settings."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @watignore.command(name="server", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _watignore_server(self, ctx):
        """Ignore/Unignore the current server"""

        server = ctx.message.server
        if server.id in self.settings['ignore_servers']:
            self.settings['ignore_servers'].remove(server.id)
            await self.bot.say("wot? Ok boss, I will no longer "
                               "ignore this server.")
        else:
            self.settings['ignore_servers'].append(server.id)
            await self.bot.say("what? Fine, I will ignore "
                               "this server.")
        dataIO.save_json(self.settings_path, self.settings)

    @watignore.command(name="channel", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _watignore_channel(self, ctx):
        """Ignore/Unignore the current channel"""

        channel = ctx.message.channel
        if channel.id in self.settings['ignore_channels']:
            self.settings['ignore_channels'].remove(channel.id)
            await self.bot.say("wut? Ok, I will no longer "
                               "ignore this channel.")
        else:
            self.settings['ignore_channels'].append(channel.id)
            await self.bot.say("wat? Alright, I will ignore "
                               "this channel.")
        dataIO.save_json(self.settings_path, self.settings)

    async def on_message(self, message):
        if message.server is None:
            return
        if message.author.bot:
            return
        if self.is_command(message):
            return
        content = message.content.lower().split()
        if len(content) != 1:
            return
        if message.server.id in self.settings['ignore_servers']:
            return
        if message.channel.id in self.settings['ignore_channels']:
            return

        pattern = re.compile(r'w+h*[aou]+t+[?!]*', re.IGNORECASE)
        if pattern.fullmatch(content[0]):
            async for before in self.bot.logs_from(message.channel, limit=5,
                                                   before=message):
                author = before.author
                name = author.display_name
                content = before.clean_content
                if not author.bot\
                        and not self.is_command(before)\
                        and not author == message.author\
                        and not pattern.fullmatch(content):
                    emoji = "\N{CHEERING MEGAPHONE}"
                    msg = "{0} said, **{1}   {2}**".format(name, emoji,
                                                                 content)
                    await self.bot.send_message(message.channel, msg)
                    break

    # Credit to Twentysix26's trigger cog
    def is_command(self, msg):
        if callable(self.bot.command_prefix):
            prefixes = self.bot.command_prefix(self.bot, msg)
        else:
            prefixes = self.bot.command_prefix
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False


def check_folders():
    folder = "data/wat"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {'ignore_channels': [], 'ignore_servers': []}
    if not dataIO.is_valid_json("data/wat/settings.json"):
        print("Creating default wat settings.json...")
        dataIO.save_json("data/wat/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Wat(bot))
