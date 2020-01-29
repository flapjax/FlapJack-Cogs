import random

import aiohttp
from redbot.core import commands

from bs4 import BeautifulSoup


class Dongers(commands.Cog):

    """Cog that does dongers"""

    def __init__(self, bot):
        self.bot = bot
        self.donger_pages = 40
        self.session = aiohttp.ClientSession()

    @commands.command()
    async def donger(self, ctx):
        """Print a random donger in chat"""

        # Access random donger page
        url = "http://dongerlist.com/page/" + str(random.randint(1, self.donger_pages))

        async with self.session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
        try:
            donger_list = soup.find_all("textarea", "donger")
            await ctx.send(random.choice(donger_list).get_text())

        except:
            await ctx.send("I couldn't find any dongers. ¯\_(ツ)_/¯")

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())
