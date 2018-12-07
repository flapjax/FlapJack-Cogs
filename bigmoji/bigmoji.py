import asyncio
import functools
import io
import unicodedata

import aiohttp
import discord
from redbot.core import commands

try:
    import cairosvg
    svg_convert = 'cairo'
except:
    try:
        from wand.image import Image
        svg_convert = 'wand'
    except:
        svg_convert = None

BaseCog = getattr(commands, "Cog", object)


class Bigmoji(BaseCog):

    """Emoji tools"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        if svg_convert == 'cairo':
            print('Using CairoSVG for svg conversion.')
        elif svg_convert == 'wand':
            print('Using wand for svg conversion.')
        else:
            print('Failed to import svg converter. Standard emoji '
                  'will be limited to 72x72 png.')

    def __unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.command(name="bigmoji", pass_context=True)
    async def bigmoji(self, ctx, emoji):
        """Post a large .png of an emoji"""
        channel = ctx.channel
        convert = False
        if emoji[0] == '<':
            # custom Emoji
            name = emoji.split(':')[1]
            emoji_name = emoji.split(':')[2][:-1]
            if emoji.split(':')[0] == '<a':
                # animated custom emoji
                url = 'https://cdn.discordapp.com/emojis/' + emoji_name + '.gif'
                name += '.gif'
            else:
                url = 'https://cdn.discordapp.com/emojis/' + emoji_name + '.png'
                name += '.png'
        else:
            chars = []
            name = []
            for char in emoji:
                chars.append(str(hex(ord(char)))[2:])
                try:
                    name.append(unicodedata.name(char))
                except ValueError:
                    # Sometimes occurs when the unicodedata library cannot
                    # resolve the name, however the image still exists
                    name.append("none")
            name = '_'.join(name) + '.png'
            if svg_convert is not None:
                url = 'https://twemoji.maxcdn.com/2/svg/' + '-'.join(chars) + '.svg'
                convert = True
            else:
                url = 'https://twemoji.maxcdn.com/2/72x72/' + '-'.join(chars) + '.png'

        async with self.session.get(url) as resp:
            if resp.status != 200:
                await ctx.send('Emoji not found.')
                return
            img = await resp.read()

        if convert:
            task = functools.partial(Bigmoji.generate, img)
            task = self.bot.loop.run_in_executor(None, task)

            try:
                img = await asyncio.wait_for(task, timeout=15)
            except asyncio.TimeoutError:
                await ctx.send("Image creation timed out.")
                return
        else:
            img = io.BytesIO(img)

        await ctx.send(file=discord.File(img, name))

    @staticmethod
    def generate(img):
        # Designed to be run in executor to avoid blocking
        if svg_convert == 'cairo':
            kwargs = {'parent_width': 1024,
                      'parent_height': 1024}
            return io.BytesIO(cairosvg.svg2png(bytestring=img, **kwargs))
        elif svg_convert == 'wand':
            with Image(blob=img, format='svg', resolution=2160) as bob:
                return bob.make_blob('png')
        else:
            return io.BytesIO(img)
