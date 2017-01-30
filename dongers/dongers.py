import discord
from discord.ext import commands

import random
import aiohttp

try:  # check if BeautifulSoup4 is installed
    from bs4 import BeautifulSoup
    soupAvailable = True
except:
    soupAvailable = False

# Update this if more donger pages are added in the future.
donger_pages = 40


class Dongers:

    """Cog that does dongers"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def donger(self):
        """Print a random donger in chat"""

        # Access random donger page
        url = "http://dongerlist.com/page/" + str(random.randint(1,
                                                                 donger_pages))

        async with aiohttp.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
        try:
            donger_list = soup.find_all("textarea", "donger")
            await self.bot.say(random.choice(donger_list).get_text())

        except:
            await self.bot.say("I couldn't find any dongers. ¯\_(ツ)_/¯")


def setup(bot):
    if soupAvailable:
        bot.add_cog(Dongers(bot))
    else:
        raise RuntimeError("You need to run `pip3 install beautifulsoup4`")
