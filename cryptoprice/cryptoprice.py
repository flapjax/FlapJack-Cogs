import re

import aiohttp
from discord.ext import commands

try:
    from bs4 import BeautifulSoup
    from tabulate import tabulate
    reqs_avail = True
except:
    reqs_avail = False


class CryptoPrice:

    """Fetches cryptocurrency information"""

    def __init__(self, bot):
        self.bot = bot
        self.url = "https://coinmarketcap.com/"
        self.session = aiohttp.ClientSession()
        
    def __unload(self):
        self.session.close()

    @commands.command()
    async def cprice(self, *, currency: str=None):
        """Fetch price data for cryptocurrencies matching your query.
        If currency is omitted, will display top 5 by market cap."""

        if currency is None:
            search = 'id'
        else:
            search = currency

        search = search.replace(' ', '-').lower()

        async with self.session.get(self.url) as response:
            cryptosoup = BeautifulSoup(await response.text(), "html.parser")

        results = cryptosoup.find_all("tr", id=re.compile(search))
        size = len(results)

        if size == 0:
            await self.bot.say("Couldn't find a currency matching your query.")

        elif size <= 5:
            text = self.make_table(results)
            await self.bot.say("```" + text + "```")

        else:
            if currency is None:
                results = results[:5]
                text = self.make_table(results)
                await self.bot.say("```" + text + "```")
            else:
                text = ('Your query matched {} results. Try adding more '
                        'characters to your search.'.format(size))

                await self.bot.say(text)

    def make_table(self, results, limit: int=None):
        headers = ['Name', 'Price', '24h Change']    
        rows = []            
        for row in results:
            column = []
            column.append(row.find("td", class_="currency-name").a.get_text().strip())
            #column.append(row.find("td", class_="market-cap").get_text().strip())
            column.append(row.find("a", class_="price").get_text().strip())
            #column.append(row.select('a[data-supply]')[0].get_text().strip())
            #column.append(row.find("a", class_="volume").get_text().strip())
            column.append(row.find("td", class_="percent-change").get_text().strip())
            rows.append(column)

        # Handy sorting thing that could be used to limit results
        if limit:
            rows.sort(key=lambda column: len(column[0]))
            rows = rows[:limit]

        text = tabulate(rows, headers=headers)
        return text


def setup(bot):
    if reqs_avail:
        bot.add_cog(CryptoPrice(bot))
    else:
        raise RuntimeError("You are missing reqirements. Please run:\n"
                           "`pip3 install beautifulsoup4`\n"
                           "`pip3 install tabulate`")
