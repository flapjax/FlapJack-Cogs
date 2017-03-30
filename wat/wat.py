import re
import discord
from discord.ext import commands


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
        pattern = re.compile(r'w+h*[aou]+t+')
        if pattern.match(content[0]):
            async for before in self.bot.logs_from(message.channel, limit=10,
                                                   before=message):
                author = before.author
                name = author.display_name
                content = before.clean_content
                if not author.bot and not pattern.match(content)\
                        and not self.is_command(before):
                    emoji = "\N{CHEERING MEGAPHONE}"
                    msg = "**{0} said, {1}   {2}   {1}**".format(name, emoji,
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
