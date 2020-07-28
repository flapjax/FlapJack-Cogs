import io
import random
import re

import aiohttp
import discord
from bs4 import BeautifulSoup
from redbot.core import commands


class Comics(commands.Cog):
    """Print random comics from popular sources"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.command(pass_context=True)
    async def ohno(self, ctx):
        """Webcomic Name"""

        url = "http://webcomicname.com/random"

        async with ctx.typing():
            async with self.session.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            img_url = soup.find(property='og:image')['content']

            async with self.session.get(img_url) as response:
                img = io.BytesIO(await response.read())

            await ctx.send(file=discord.File(img, 'ohno.png'))

    @commands.command(pass_context=True)
    async def smbc(self, ctx):
        """Saturday Morning Breakfast Cereal"""

        url = "http://www.smbc-comics.com/comic/archive"

        async with ctx.typing():
            async with self.session.get(url, headers={'Connection': 'keep-alive'}) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")
			
            all_comics = soup.find('select', attrs = {'name': 'comic'})
            all_comics_url_stubs = [option['value'] for option in all_comics.findChildren()]

            random_comic = random.choice(all_comics_url_stubs)
            comic_url = f"http://www.smbc-comics.com/{random_comic}"

            async with self.session.get(comic_url, headers={'Connection': 'keep-alive'}) as resp:
                soup = BeautifulSoup(await resp.text(), "html.parser")
                img_url = soup.find(property='og:image')['content']
                extra_url = soup.find(id='aftercomic').img['src']

            async with self.session.get(img_url) as response:
                img = io.BytesIO(await response.read())

            await ctx.send(file=discord.File(img, 'smbc.png'))

    @commands.command(pass_context=True)
    async def pbf(self, ctx):
        """The Perry Bible Fellowship"""

        url = "http://pbfcomics.com/random"

        async with ctx.typing():
            async with self.session.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            img_url = soup.find(property='og:image')['content']

            async with self.session.get(img_url) as response:
                img = io.BytesIO(await response.read())

            await ctx.send(file=discord.File(img, 'pbf.png'))

    @commands.command(pass_context=True)
    async def cah(self, ctx):
        """Cyanide and Happiness"""

        url = "http://explosm.net/comics/random"

        async with ctx.typing():
            async with self.session.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            img_url = soup.find(property='og:image')['content']

            async with self.session.get(img_url) as response:
                img = io.BytesIO(await response.read())

            await ctx.send(file=discord.File(img, 'cah.png'))

    @commands.command(pass_context=True)
    async def xkcd(self, ctx):
        """XKCD"""

        url = "https://c.xkcd.com/random/comic/"
        phrase = r"Image URL \(for hotlinking\/embedding\)\:.*"

        async with ctx.typing():
            async with self.session.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            img_url = soup.find(string=re.compile(phrase))
            img_url = 'https://' + img_url.split('https://')[1].rstrip()

            async with self.session.get(img_url) as response:
                img = io.BytesIO(await response.read())

            await ctx.send(file=discord.File(img, 'xkcd.png'))

    @commands.command(pass_context=True)
    async def mrls(self, ctx):
        """Mr. Lovenstein"""

        url = "http://www.mrlovenstein.com/shuffle"

        async with ctx.typing():
            async with self.session.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            img_url = f"http://www.mrlovenstein.com{soup.find(id='comic_main_image')['src']}"

            async with self.session.get(img_url) as response:
                img = io.BytesIO(await response.read())

            await ctx.send(file=discord.File(img, 'mrls.png'))

    @commands.command(pass_context=True)
    async def chainsaw(self, ctx):
        """Chainsawsuit"""

        url = "http://chainsawsuit.com/comic/random/?random&nocache=1"

        async with ctx.typing():
            async with self.session.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            img_url = soup.find(property='og:image')['content']

            async with self.session.get(img_url) as response:
                img = io.BytesIO(await response.read())

            await ctx.send(file=discord.File(img, 'chainsawsuit.png'))

    @commands.command(pass_context=True)
    async def sarah(self, ctx):
        """Sarah's Scribbles"""

        url = "http://www.gocomics.com/random/sarahs-scribbles"

        async with ctx.typing():
            async with self.session.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            img_url = soup.find(property='og:image')['content']

            async with self.session.get(img_url) as response:
                img = io.BytesIO(await response.read())

            await ctx.send(file=discord.File(img, 'sarahsscribbles.png'))
