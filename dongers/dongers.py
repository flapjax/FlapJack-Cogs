import random

import aiohttp
from discord.ext import commands

from bs4 import BeautifulSoup


class Dongers:

    """Cog that does dongers"""

    def __init__(self, bot):
        self.bot = bot
        self.donger_pages = 40

    @commands.command()
    async def donger(self, ctx):
        """Print a random donger in chat"""

        # Access random donger page
        url = "http://dongerlist.com/page/" + str(random.randint(1, self.donger_pages))

        async with aiohttp.request("GET", url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
        try:
            donger_list = soup.find_all("textarea", "donger")
            await ctx.send(random.choice(donger_list).get_text())

        except:
            await ctx.send("I couldn't find any dongers. ¯\_(ツ)_/¯")
