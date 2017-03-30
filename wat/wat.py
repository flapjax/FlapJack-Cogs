import re
import discord
from discord.ext import commands


class Wat:

    """Repeat messages when other users are having trouble hearing"""

    def __init__(self, bot):
        self.bot = bot

    async def msg_listener(self, message):

        if message.author == self.bot.user:
            return
        if self.is_command(message):
            return
        content = message.content.lower().split()
        if len(content) != 1:
            return
        if re.match(r'w+h*[aeiou]+t+', content[0]):
            async for before in self.bot.logs_from(message.channel, limit=10,
                                                   before=message):
                author = before.author.display_name
                content = before.clean_content
                if author != self.bot.user and not re.match(r'w+h*[aeiou]+t+',
                                                            content):
                    emoji = "\N{CHEERING MEGAPHONE}"
                    msg = "**{0} said, {1}   {2}   {1}**".format(author, emoji, 
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
