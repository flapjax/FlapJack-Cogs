import re

import aiohttp
from bs4 import BeautifulSoup
from redbot.core import commands
from tabulate import tabulate


class CryptoPrice(commands.Cog):

    """Fetches cryptocurrency information"""

    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://coinmarketcap.com/"
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.command()
    async def cprice(self, ctx, currency: str=None):
        """Fetch price data for cryptocurrencies matching your query.
        If currency is omitted, will display top 5 by market cap."""

        if currency is None:
            search = 'id'
        else:
            search = currency

        search = search.replace(' ', '-').lower()
        results = []

        for i in range(1, 11):
            url = self.base_url + str(i)
            async with self.session.get(url) as response:
                cryptosoup = BeautifulSoup(await response.text(), "html.parser")
            results.extend(cryptosoup.find_all("tr", id=re.compile(search)))
            if len(results) > 3:
                break

        if len(results) == 0:
            await ctx.send("Couldn't find a currency matching your query.")
        elif len(results) <= 10:
            text = self.make_table(results)
            await ctx.send("```" + text + "```")
        else:
            if currency is None:
                results = results[:5]
                text = self.make_table(results)
                await ctx.send("```" + text + "```")
            else:
                text = ('Your query matched {} results. Try adding more '
                        'characters to your search.'.format(len(results)))

                await ctx.send(text)

    def make_table(self, results, limit: int=None):
        headers = ['Name', 'Price (USD)', 'Price (BTC)', '24h Change (USD)']
        rows = []            
        for row in results:
            column = []
            column.append(row.find("td", class_="currency-name").a.get_text().strip())
            column.append(row.find("a", class_="price").get_text().strip())
            column.append(row.find("a", class_="price")['data-btc'])
            column.append(row.find("td", class_="percent-change").get_text().strip())
            rows.append(column)

        # Handy sorting thing that could be used to limit results
        if limit:
            rows.sort(key=lambda column: len(column[0]))
            rows = rows[:limit]

        text = tabulate(rows, headers=headers, floatfmt='.8f')
        return text
