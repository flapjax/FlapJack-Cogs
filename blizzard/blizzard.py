import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
from __main__ import send_cmd_help
import aiohttp
import asyncio

try:  # check if BeautifulSoup4 is installed
    from bs4 import BeautifulSoup
    soup_available = True
except:
    soup_available = False

try:  # check if pypandoc is installed
    import pypandoc
    pypandoc_available = True
except:
    pypandoc_available = False

# Special thanks to judge2020 for telling me about pandoc, and offering their
# code as a reference: https://github.com/judge2020/BattleNetUpdateChecker

# This cog requires:
# BeautifulSoup4 :: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
# pypandoc :: https://pypi.python.org/pypi/pypandoc
# Pandoc :: http://pandoc.org/

# Patch note strings
base_url = 'https://us.battle.net/connect/en/app/'
product_url = '/patch-notes?productType='
hearthstone_abbr = 'wtcg'
overwatch_abbr = 'Pro'
starcraft2_abbr = 'sc2'
warcraft_abbr = 'WoW'
diablo_abbr = 'd3'
hots_abbr = 'heroes'
headers = {'User-Agent': 'Battle.net/1.0.8.4217'}


class Blizzard:

    """Blizzard Game Data"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="hearthstone", pass_context=True)
    async def hearthstone(self, ctx):
        """Hearthstone utilities"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @hearthstone.command(name="notes", pass_context=True)
    async def _notes_hearthstone(self, ctx):
        """Latest Hearthstone patch notes"""
        url = ''.join([base_url,
                       hearthstone_abbr,
                       product_url,
                       hearthstone_abbr])

        await self.print_patch_notes(url)

    @commands.group(name="overwatch", pass_context=True)
    async def overwatch(self, ctx):
        """Overwatch utilities"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @overwatch.command(name="stats", pass_context=True)
    async def _stats_overwatch(self, ctx, battletag, region=None):
        """Overwatch stats for your battletag (case sensitive and PC only!).
        Region is optional and will autodetect with this priority: kr>eu>us

        Example: [p]overwatch stats CoolDude#1234 kr
        """

        battletag = battletag.replace("#", "-")
        url = 'https://owapi.net/api/v3/u/' + battletag + '/stats'
        header = {"User-Agent": "flapjackcogs/1.0"}
        async with aiohttp.ClientSession(headers=header) as session:
            async with session.get(url) as resp:
                stats = await resp.json()

        if 'error' in stats:
            await self.bot.say(''.join(['Could not fetch your statistics. ',
                                        'Battletags are case sensitive ',
                                        'and require a 4-digit identifier ',
                                        '(e.g. CoolDude#1234)']))
            return

        if region is None:
            if stats['kr']:
                region = 'kr'
                region_full = 'Asia'
            elif stats['eu']:
                region = 'eu'
                region_full = 'Europe'
            elif stats['us']:
                region = 'us'
                region_full = 'US'
            else:
                await self.bot.say('That battletag has no stats in any region.')
                return

        if stats[region] is None:
            await self.bot.say(''.join(['That battletag exists, but I could not ',
                                        'find stats for the region specified. ',
                                        'Try a different region ',
                                        '<us/eu/kr> or leave that field blank '
                                        'so I can autodetect the region.']))
            return

        url = 'https://playoverwatch.com/en-us/career/pc/' + region + '/' + battletag
        battletag = battletag.replace("-", "#")
        comp = stats[region]['stats']['competitive']
        qplay = stats[region]['stats']['quickplay']
        thumb_url = comp['overall_stats']['avatar']
        icon_url = 'http://i.imgur.com/xU2iv6U.png'
        #icon_url = comp['overall_stats']['rank_image']
        comp_stats = ''.join(['Wins: ', str(int(round(comp['game_stats']['games_won']))),
                              '\nElims: ', str(int(round(comp['average_stats']['eliminations_avg']))),
                              '\nDeaths: ', str(int(round(comp['average_stats']['deaths_avg']))),
                              '\nDamage: ', str(int(round(comp['average_stats']['damage_done_avg']))),
                              '\nHeal: ', str(int(round(comp['average_stats']['healing_done_avg'])))])

        qplay_stats = ''.join(['Wins: ', str(int(round(qplay['game_stats']['games_won']))),
                               '\nElims: ', str(int(round(qplay['average_stats']['eliminations_avg']))),
                               '\nDeaths: ', str(int(round(qplay['average_stats']['deaths_avg']))),
                               '\nDamage: ', str(int(round(qplay['average_stats']['damage_done_avg']))),
                               '\nHeal: ', str(int(round(qplay['average_stats']['healing_done_avg'])))])

        embed = discord.Embed(title='Overwatch Stats (PC-' + region_full + ')\n', color=0xFAA02E)
        embed.set_author(name=battletag, url=url, icon_url=icon_url)
        embed.set_thumbnail(url=thumb_url)
        embed.add_field(name='Competitive', value=comp_stats, inline=True)
        embed.add_field(name='Quick Play', value=qplay_stats, inline=True)
        embed.set_footer(text='Elims, Deaths, Damage, and Heal are avg per game.')
        await self.bot.say(embed=embed)

    @overwatch.command(name="notes", pass_context=True)
    async def _notes_overwatch(self, ctx):
        """Latest Overwatch patch notes"""
        url = ''.join([base_url,
                       overwatch_abbr,
                       product_url,
                       overwatch_abbr])

        await self.print_patch_notes(url)

    @commands.group(name="starcraft2", pass_context=True)
    async def starcraft2(self, ctx):
        """Starcraft2 utilities"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @starcraft2.command(name="notes", pass_context=True)
    async def _notes_starcraft2(self, ctx):
        """Latest Starcraft2 patch notes"""
        url = ''.join([base_url,
                       starcraft2_abbr,
                       product_url,
                       starcraft2_abbr])

        await self.print_patch_notes(url)

    @commands.group(name="warcraft", pass_context=True)
    async def warcraft(self, ctx):
        """World of Warcraft utilities"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @warcraft.command(name="notes", pass_context=True)
    async def _notes_warcraft(self, ctx):
        """Latest World of Warcraft patch notes"""

        url = ''.join([base_url,
                       warcraft_abbr,
                       product_url,
                       warcraft_abbr])

        await self.print_patch_notes(url)

    @commands.group(name="diablo3", pass_context=True)
    async def diablo3(self, ctx):
        """Diablo3 utilities"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @diablo3.command(name="notes", pass_context=True)
    async def _notes_diablo3(self, ctx):
        """Latest Diablo3 patch notes"""
        url = ''.join([base_url,
                       diablo_abbr,
                       product_url,
                       diablo_abbr])

        await self.print_patch_notes(url)

    @commands.group(name="hots", pass_context=True)
    async def hots(self, ctx):
        """Heroes of the Storm utilities"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @hots.command(name="notes", pass_context=True)
    async def _notes_hots(self, ctx):
        """Latest Heroes of the Storm patch notes"""
        url = ''.join([base_url,
                       hots_abbr,
                       product_url,
                       hots_abbr])

        await self.print_patch_notes(url)

    async def print_patch_notes(self, url):
        try:
            async with aiohttp.get(url, headers=headers) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            html_notes = soup.find('div', {"class": "patch-notes-interior"})
            text_notes = pypandoc.convert_text(html_notes, 'plain',
                                               format='html',
                                               extra_args=['--wrap=none'])
            # Removal/replacement of odd characters
            text_notes = text_notes.replace('&nbsp;', ' ')
            text_notes = text_notes.replace('&apos;', "'")
            msg_list = pagify(text_notes, delims=["\n"])
            for msg in msg_list:
                await self.bot.say(msg)
                await asyncio.sleep(1)

        except:
            await self.bot.say("I couldn't find any patch notes.")


def setup(bot):
    if soup_available and pypandoc_available:
        bot.add_cog(Blizzard(bot))
    else:
        if not soup_available:
            error_text += "You need to run `pip install beautifulsoup4`\n"
        if not pypandoc_available:
            error_text += "You need to run `pip install pypandoc`\n"
        raise RuntimeError(error_text)
