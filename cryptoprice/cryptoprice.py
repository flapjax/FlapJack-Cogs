import re

import aiohttp
from redbot.core import commands
#from discord.ext import commands

from bs4 import BeautifulSoup
from tabulate import tabulate


class CryptoPrice(commands.Cog):

    """Fetches cryptocurrency information"""

    def __init__(self):
        self.url = "https://coinmarketcap.com/"
        #self.session = aiohttp.ClientSession()
        
    def __unload(self):
        self.session.close()

    @commands.command()
    async def cprice(self, ctx, currency: str=None):
        """Fetch price data for cryptocurrencies matching your query.
        If currency is omitted, will display top 5 by market cap."""
        self.session = aiohttp.ClientSession()
        if currency is None:
            search = 'id'
        else:
            search = currency

        search = search.replace(' ', '-').lower()
        size = 0
        i = 1
        while size == 0 and i <= 10:
            self.url = "https://coinmarketcap.com/%s" % str(i)
            async with self.session.get(self.url) as response:
                cryptosoup = BeautifulSoup(await response.text(), "html.parser")
            results = cryptosoup.find_all("tr", id=re.compile(search))
            size = len(results)
            if size > 0:
                break
            i += 1

        if size == 0:
            await ctx.send("Couldn't find a currency matching your query.")
        elif size <= 5:
            text = self.make_table(results)
            await ctx.send("```" + text + "```")

        else:
            if currency is None:
                results = results[:5]
                text = self.make_table(results)
                await ctx.send("```" + text + "```")
            else:
                text = ('Your query matched {} results. Try adding more '
                        'characters to your search.'.format(size))

                await ctx.send(text)
        self.session.close()

    def make_table(self, results, limit: int=None):
        headers = ['Name', 'Price (USD)', 'Price (BTC)', '24h Change (USD)']
        rows = []            
        for row in results:
            column = []
            btc_price = str(row.find("a", class_="price"))
            print(btc_price)
            if btc_price:
                soup = BeautifulSoup(btc_price, "html.parser")
                btc = str(soup.a['data-btc'])
                str_satoshi = "{:.10f}".format(float(btc))
                #str_satoshi = str(satoshi)
                print(str_satoshi)
            column.append(row.find("td", class_="currency-name").a.get_text().strip())
            #column.append(row.find("td", class_="market-cap").get_text().strip())
            column.append(row.find("a", class_="price").get_text().strip())
            column.append(str_satoshi)
            #column.append(row.select('a[data-supply]')[0].get_text().strip())
            #column.append(row.find("a", class_="volume").get_text().strip())
            column.append(row.find("td", class_="percent-change").get_text().strip())
            rows.append(column)

        # Handy sorting thing that could be used to limit results
        if limit:
            rows.sort(key=lambda column: len(column[0]))
            rows = rows[:limit]

        text = tabulate(rows, headers=headers, floatfmt='.8f')
        return text

