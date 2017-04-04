import re

import discord
from discord.ext import commands

from .utils.chat_formatting import escape_mass_mentions


class Wat:

    """Repeat messages when other users are having trouble hearing"""

    def __init__(self, bot):
        self.bot = bot

    async def msg_listener(self, message):
        if message.author.bot:
            return
        if self.is_command(message):
            return
        content = message.content.lower().split()
        if len(content) != 1:
            return

        pattern = re.compile(r'w+h*[aou]+t+[?!]*', re.IGNORECASE)
        if pattern.fullmatch(content[0]):
            async for before in self.bot.logs_from(message.channel, limit=5,
                                                   before=message):
                author = before.author
                name = author.display_name
                content = escape_mass_mentions(before.content)
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


def setup(bot):
    n = Wat(bot)
    bot.add_cog(n)
    bot.add_listener(n.msg_listener, "on_message")
