import io
import re

import aiohttp
from discord.ext import commands

try:
    from bs4 import BeautifulSoup
    reqs_avail = True
except:
    reqs_avail = False


class Comics:
    """Print random comics from popular sources"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    @commands.command(pass_context=True)
    async def ohno(self, ctx):
        """Webcomic Name"""

        url = "http://webcomicname.com/random"

        async with self.session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")

        img_url = soup.find(property='og:image')['content']

        async with self.session.get(img_url) as response:
            img = io.BytesIO(await response.read())

        await self.bot.send_file(ctx.message.channel, img, filename='ohno.png')

    @commands.command(pass_context=True)
    async def smbc(self, ctx):
        """Saturday Morning Breakfast Cereal"""

        url = "http://www.smbc-comics.com/random.php"

        async with self.session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")

        img_url = soup.find(property='og:image')['content']
        extra_url = soup.find(id='aftercomic').img['src']

        async with self.session.get(img_url) as response:
            img = io.BytesIO(await response.read())

        await self.bot.send_file(ctx.message.channel, img, filename='smbc.gif')

    @commands.command(pass_context=True)
    async def pbf(self, ctx):
        """The Perry Bible Fellowship"""

        url = "http://pbfcomics.com/random"

        async with self.session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")

        img_url = soup.find(property='og:image')['content']

        async with self.session.get(img_url) as response:
            img = io.BytesIO(await response.read())

        await self.bot.send_file(ctx.message.channel, img, filename='pbf.png')

    @commands.command(pass_context=True)
    async def cah(self, ctx):
        """Cyanide and Happiness"""

        url = "http://explosm.net/comics/random"

        async with self.session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")

        img_url = soup.find(property='og:image')['content']

        async with self.session.get(img_url) as response:
            img = io.BytesIO(await response.read())

        await self.bot.send_file(ctx.message.channel, img, filename='cah.png')

    @commands.command(pass_context=True)
    async def xkcd(self, ctx):
        """XKCD"""

        url = "https://c.xkcd.com/random/comic/"
        phrase = "Image URL \(for hotlinking\/embedding\)\:"

        async with self.session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")

        img_url = soup.find(string=re.compile(phrase))
        img_url = 'https://' + img_url.split('https://')[1].rstrip()

        async with self.session.get(img_url) as response:
            img = io.BytesIO(await response.read())

        await self.bot.send_file(ctx.message.channel, img, filename='xkcd.png')

    @commands.command(pass_context=True)
    async def mrls(self, ctx):
        """Mr. Lovenstein"""

        url = "http://www.mrlovenstein.com/shuffle"

        async with self.session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")

        img_url = 'http://www.mrlovenstein.com' \
            + soup.find(id='comic_main_image')['src']

        async with self.session.get(img_url) as response:
            img = io.BytesIO(await response.read())

        await self.bot.send_file(ctx.message.channel, img, filename='mrls.gif')

    @commands.command(pass_context=True)
    async def chainsaw(self, ctx):
        """Chainsawsuit"""

        url = "http://chainsawsuit.com/comic/random/?random&nocache=1"

        async with self.session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")

        img_url = soup.find(property='og:image')['content']

        async with self.session.get(img_url) as response:
            img = io.BytesIO(await response.read())

        await self.bot.send_file(ctx.message.channel, img,
                                 filename='chainsawsuit.png')

    @commands.command(pass_context=True)
    async def sarah(self, ctx):
        """Sarah's Scribbles"""

        url = "http://www.gocomics.com/random/sarahs-scribbles"

        async with self.session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")

        img_url = soup.find(property='og:image')['content']

        async with self.session.get(img_url) as response:
            img = io.BytesIO(await response.read())

        await self.bot.send_file(ctx.message.channel, img,
                                 filename='sarahsscribbles.gif')                    

    def __unload(self):
        self.session.close()


def setup(bot):
    if reqs_avail:
        bot.add_cog(Comics(bot))
    else:
        raise RuntimeError("You are missing reqirements. Please run:\n"
                           "`pip3 install beautifulsoup4`")
