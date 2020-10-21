import io
import json
import random
import re

import aiohttp
import datetime
import discord
from bs4 import BeautifulSoup
from redbot.core import commands


DATE_RE = r"^([0-9][0-9]|19[0-9][0-9]|20[0-9][0-9])(\.|-|\/)([1-9]|0[1-9]|1[0-2])(\.|-|\/)([1-9]|0[1-9]|1[0-9]|2[0-9]|3[0-1])$"


class Comics(commands.Cog):
    """Print random comics from popular sources"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
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

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
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

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
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

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
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

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
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

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
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

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
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

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
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

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
    async def dilbert(self, ctx, date: str = None):
        """Dilbert

        Random, or specify a date in YYYY-MM-DD format (2020-01-15).
        Examples:
        \t`[p]dilbert`\t\tFetches random comic
        \t`[p]dilbert 2020-1-15`\tFetches comic for Jan 15, 2020
        """
        if date:
            date_match = re.match(DATE_RE, date)
            if not date_match:
                return await ctx.send("That doesn't seem like a valid date. Try a format like `2020-01-15`.")
            date = date_match[0]
        else:
            start_date = datetime.date(1989, 4, 16)
            end_date = datetime.datetime.today().date()
            date = self._fetch_random_date(start_date, end_date)

        url = f"https://dilbert.com/strip/{date}"

        async with ctx.typing():
            async with self.session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                script_tag = soup.find("script", type="application/ld+json")
                tag = script_tag.string.lstrip().rstrip()
                tag = tag.replace("\n", " ").replace("\r", " ")
                tag = re.sub(" +", " ", tag)
                try:
                    comic_info = json.loads(tag)
                except json.decoder.JSONDecodeError:
                    return await ctx.send("I can't read that comic page.")

            image_url = comic_info.get("image", None)

            if image_url:
                async with self.session.get(comic_info["image"]) as response:
                    img = io.BytesIO(await response.read())
                    
                return await ctx.send(file=discord.File(img, f"dilbert-{date}.png"))

            return await ctx.send("I can't read that comic page.")

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
    async def calvin(self, ctx, date: str = None):
        """Calvin and Hobbes

        Random, or specify a date in YYYY-MM-DD format (1995-12-31).
        The valid date range for this comic is 1985-11-18 to 1995-12-31.
        
        Examples:
        \t`[p]calvin`\t\tFetches random comic
        \t`[p]calvin 1995-12-31`\tFetches comic for Dec 31, 1995
        """
        bad_date_message = "That doesn't seem like a valid date. Try a format like `1995-12-31`."
        start_date = datetime.date(1985, 11, 18)
        end_date = datetime.date(1995, 12, 31)

        if date:
            split_date = str(date).split("-") # (YYYY, MM, DD)
            try:
                supplied_date = datetime.date(int(split_date[0]), int(split_date[1]), int(split_date[2]))
            except ValueError:
                return await ctx.send(bad_date_message)
            if not start_date <= supplied_date <= end_date:
                return await ctx.send("This comic can only be used on dates between 11-18-1985 and 12-31-1995.")
            date_match = re.match(DATE_RE, date)
            if not date_match:
                return await ctx.send(bad_date_message)
            date = date_match[0]
        else:
            date = self._fetch_random_date(start_date, end_date)

        split_date = str(date).split("-")
        url = f"https://www.gocomics.com/calvinandhobbes/{split_date[0]}/{split_date[1]}/{split_date[2]}"
        async with ctx.typing():
            async with self.session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                a = soup.find_all("img", class_="lazyload img-fluid")
                for item in a:
                    i = item.get('data-srcset')
                    if i.startswith("https://assets.amuniversal.com/"):
                        url = i.split()[0]
            if url:
                async with self.session.get(url) as response:
                    img = io.BytesIO(await response.read())
                    
                return await ctx.send(file=discord.File(img, f"calvin-{date}.png"))

            return await ctx.send("I can't read that comic page.")

    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
    async def garfield(self, ctx, date: str = None):
        """Garfield

        Random, or specify a date in YYYY-MM-DD format (1995-12-31).
        The valid date range for this comic is 1978-06-19 to today.
        
        Examples:
        \t`[p]garfield`\t\tFetches random comic
        \t`[p]garfield 1978-06-19`\tFetches comic for Jun 19, 1978
        """
        bad_date_message = "That doesn't seem like a valid date. Try a format like `1994-06-16`."
        start_date = datetime.date(1978, 6, 19)
        end_date = datetime.datetime.today().date()

        if date:
            split_date = str(date).split("-") # (YYYY, MM, DD)
            try:
                supplied_date = datetime.date(int(split_date[0]), int(split_date[1]), int(split_date[2]))
            except ValueError:
                return await ctx.send(bad_date_message) 
            if not start_date <= supplied_date <= end_date:
                return await ctx.send("This comic can only be used on dates between 1978-06-19 and today.")
            date_match = re.match(DATE_RE, date)
            if not date_match:
                return await ctx.send(bad_date_message)
            date = date_match[0]
        else:
            date = self._fetch_random_date(start_date, end_date)

        split_date = str(date).split("-")
        url = f"https://www.gocomics.com/garfield/{split_date[0]}/{split_date[1]}/{split_date[2]}"
        async with ctx.typing():
            async with self.session.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            img_url = soup.find(property='og:image')['content']
            async with self.session.get(img_url) as response:
                img = io.BytesIO(await response.read())

            await ctx.send(file=discord.File(img, f"garfield-{date}.png"))

    @staticmethod
    def _fetch_random_date(start_date, end_date):
        time_between_dates = end_date - start_date
        days_between_dates = time_between_dates.days
        random_number_of_days = random.randrange(days_between_dates)
        date = start_date + datetime.timedelta(days=random_number_of_days)
        return date
