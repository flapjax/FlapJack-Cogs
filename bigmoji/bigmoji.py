import io
import os
import unicodedata

import cairosvg

import aiohttp
from discord.ext import commands


class Bigmoji:

    """Emoji tools"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    @commands.command(name="bigmoji", pass_context=True)
    async def bigmoji(self, ctx, emoji):
        """Post a large .png of an emoji"""
        channel = ctx.message.channel

        if emoji[0] == '<':
            custom = True
            name = emoji.split(':')[1]
            emoji = emoji.split(':')[2][:-1]
            url = 'https://cdn.discordapp.com/emojis/' + emoji + '.png'
        else:
            custom = False
            chars = []
            name = []
            for char in emoji:
                chars.append(str(hex(ord(char)))[2:])
                name.append(unicodedata.name(char))
            name = '_'.join(name)
            url = 'https://twemoji.maxcdn.com/2/svg/' + '-'.join(chars) + '.svg'

        async with self.session.get(url) as resp:
            if resp.status != 200:
                await self.bot.say('Emoji not found.')
                return
            if custom:
                img = io.BytesIO(await resp.read())
            else:
                output = cairosvg.svg2png(bytestring=await resp.read(), parent_width=1024, parent_height=1024)
                img = io.BytesIO(output)

        await self.bot.send_file(channel, img, filename=name + '.png')

    def __unload(self):
        self.session.close()


def setup(bot):
    n = Bigmoji(bot)
    bot.add_cog(n)
