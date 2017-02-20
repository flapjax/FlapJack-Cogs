import os
import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
from cogs.utils import checks
from .utils.dataIO import dataIO
from __main__ import send_cmd_help
import re
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
wowtoken_url = 'https://wowtoken.info/'
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
        self.settings_path = "data/blizzard/settings.json"
        self.settings = dataIO.load_json(self.settings_path)

    @commands.group(name="blizzard", pass_context=True)
    async def blizzard(self, ctx):
        """Change blizzard cog settings."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @blizzard.command(name="apikey", pass_context=True)
    @checks.is_owner()
    async def _apikey_blizzard(self, ctx, key: str):
        """Set the cog's battle.net API key, required for some statistics.
        (get one at https://dev.battle.net/)
        Use a direct message to keep the key secret."""

        self.settings['apikey'] = key
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('API key set.')

    @commands.group(name="battletag", pass_context=True)
    async def battletag(self, ctx):
        """Change your battletag settings."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @battletag.command(name="set", pass_context=True)
    async def _set_battletag(self, ctx, tag: str):
        """Set your battletag"""

        pattern = re.compile(r'.#\d{4}\Z')
        if pattern.search(tag) is None:
            await self.bot.say("That doesn't look like a valid battletag.")
            return
        uid = ctx.message.author.id
        self.settings['battletags'][uid] = tag
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Your battletag has been set.")

    @battletag.command(name="clear", pass_context=True)
    async def _clear_battletag(self, ctx):
        """Remove your battletag"""

        uid = ctx.message.author.id
        if self.settings['battletags'].pop(uid, None) is not None:
            await self.bot.say("Your battletag has been removed.")
        else:
            await self.bot.say("I had no battletag stored for you.")
        dataIO.save_json(self.settings_path, self.settings)

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
    async def _stats_overwatch(self, ctx, tag: str=None, region: str=None):
        """Overwatch stats for your battletag (case sensitive and PC only!).
        If battletag is ommitted, bot will use your battletag if stored.
        Region is optional and will autodetect with this priority: kr>eu>us

        Example: [p]overwatch stats CoolDude#1234 kr
        """

        uid = ctx.message.author.id
        # Little hack to detect if region was entered, but not battletag
        if (tag in ['kr', 'eu', 'us']) and (region is None):
            region = tag
            tag = None

        if tag is None:
            if uid in self.settings['battletags']:
                tag = self.settings['battletags'][uid]
            else:
                await self.bot.say(''.join(['You did not provide a battletag ',
                                            'and I do not have one stored for you.']))
                return

        tag = tag.replace("#", "-")
        url = 'https://owapi.net/api/v3/u/' + tag + '/stats'
        header = {"User-Agent": "flapjackcogs/1.0"}
        async with aiohttp.ClientSession(headers=header) as session:
            async with session.get(url) as resp:
                stats = await resp.json()

        if 'error' in stats:
            await self.bot.say(''.join(['Could not fetch your statistics. ',
                                        'Battletags are case sensitive ',
                                        'and require a 4-digit identifier ',
                                        '(e.g. CoolDude#1234)',
                                        'Or, you may have an invalid tag ',
                                        'on file.']))
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

        url = 'https://playoverwatch.com/en-us/career/pc/' + region + '/' + tag
        tag = tag.replace("-", "#")
        comp = stats[region]['stats']['competitive']
        qplay = stats[region]['stats']['quickplay']
        thumb_url = comp['overall_stats']['avatar']
        tier = comp['overall_stats']['tier']
        if tier == 'bronze':
            icon_url = 'http://i.imgur.com/B4IR72H.png'
        elif tier == 'silver':
            icon_url = 'http://i.imgur.com/1mOpjRc.png'
        elif tier == 'gold':
            icon_url = 'http://i.imgur.com/lCTsNwo.png'
        elif tier == 'platinum':
            icon_url = 'http://i.imgur.com/nDVHAbp.png'
        elif tier == 'diamond':
            icon_url = 'http://i.imgur.com/fLmIC70.png'
        elif tier == 'master':
            icon_url = 'http://i.imgur.com/wjf0lEc.png'
        elif tier == 'grandmaster':
            icon_url = 'http://i.imgur.com/5ApGiZs.png'
        else:
            icon_url = 'http://i.imgur.com/xU2iv6U.png'

        comp_stats = ''.join(['**Wins:** ', str(int(round(comp['game_stats']['games_won']))),
                              '\n**Avg Elim:** ', str(int(round(comp['average_stats']['eliminations_avg']))),
                              '\n**Avg Death:** ', str(int(round(comp['average_stats']['deaths_avg']))),
                              '\n**Avg Dmg:** ', str(int(round(comp['average_stats']['damage_done_avg']))),
                              '\n**Avg Heal:** ', str(int(round(comp['average_stats']['healing_done_avg'])))])

        qplay_stats = ''.join(['**Wins:** ', str(int(round(qplay['game_stats']['games_won']))),
                               '\n**Avg Elim:** ', str(int(round(qplay['average_stats']['eliminations_avg']))),
                               '\n**Avg Death:** ', str(int(round(qplay['average_stats']['deaths_avg']))),
                               '\n**Avg Dmg:** ', str(int(round(qplay['average_stats']['damage_done_avg']))),
                               '\n**Avg Heal:** ', str(int(round(qplay['average_stats']['healing_done_avg'])))])

        embed = discord.Embed(title='Overwatch Stats (PC-' + region_full + ')', color=0xFAA02E)
        embed.set_author(name=tag, url=url, icon_url=icon_url)
        embed.set_thumbnail(url=thumb_url)
        embed.add_field(name='__Competitive__', value=comp_stats, inline=True)
        embed.add_field(name='__Quick Play__', value=qplay_stats, inline=True)
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

    @warcraft.command(name="token", pass_context=True)
    async def _token_warcraft(self, ctx, realm: str='na'):
        """WoW Token Prices"""

        url = ''.join([wowtoken_url])

        if realm.lower() not in ['na', 'eu', 'cn', 'tw', 'kr']:
            await self.bot.say("'" + realm + "' is not a valid realm.")
            return

        await self.print_token(url, realm)

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

    @diablo3.command(name="stats", pass_context=True)
    async def _stats_diablo3(self, ctx, tag: str=None):
        """Diablo3 stats for your battletag.
        If battletag is ommitted, bot will use your battletag if stored.

        Example: [p]diablo3 stats CoolDude#1234
        """

        uid = ctx.message.author.id
        if tag is None:
            if uid in self.settings['battletags']:
                tag = self.settings['battletags'][uid]
            else:
                await self.bot.say(''.join(['You did not provide a battletag ',
                                            'and I do not have one stored for you.']))
                return

        if 'apikey' not in self.settings:
            await self.bot.say(''.join(['The bot owner has not provided a ',
                                        'battle.net API key, which is ',
                                        'required for Diablo 3 stats.']))
            return

        key = self.settings['apikey']
        tag = tag.replace("#", "-")
        url = 'https://us.api.battle.net/d3/profile/' + tag + '/?locale=en_US&apikey=' + key
        header = {"User-Agent": "flapjackcogs/1.0"}
        async with aiohttp.ClientSession(headers=header) as session:
            async with session.get(url) as resp:
                stats = await resp.json()

        if 'code' in stats:
            await self.bot.say("I coulnd't find Diablo 3 stats for that battletag.")
            return

        tag = tag.replace("-", "#")
        thumb_url = 'http://i.imgur.com/5WYDHHZ.png'

        paragon = ''.join([':leaves:Seasonal: ', str(stats['paragonLevelSeason']),
                           '\n:leaves:Seasonal Hardcore: ', str(stats['paragonLevelSeasonHardcore']),
                           '\nNon-Seasonal: ', str(stats['paragonLevel']),
                           '\nNon-Seasonal Hardcore: ', str(stats['paragonLevelHardcore'])])

        hero_txt = ''
        for hero in stats['heroes']:
            hero_txt += ''.join([':leaves:' if hero['seasonal'] else '', hero['name'], ' - lvl ', str(hero['level']), ' ', hero['class'], ' - hardcore' if hero['hardcore'] else '', ' (RIP)\n' if hero['dead'] else '\n'])

        if not hero_txt:
            await self.bot.say("You don't have any Diablo 3 heroes.")
            return

        kills = "Lifetime monster kills: " + str(stats['kills']['monsters'])

        embed = discord.Embed(title='Diablo 3 Stats', color=0xCC2200)
        embed.set_author(name=tag)
        embed.set_thumbnail(url=thumb_url)
        embed.add_field(name='__Paragon__', value=paragon, inline=False)
        embed.add_field(name='__Heroes__', value=hero_txt, inline=False)
        embed.set_footer(text=kills)
        await self.bot.say(embed=embed)

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

    async def print_token(self, url, realm):

        header = {"User-Agent": "flapjackcogs/1.0"}
        thumb_url = 'http://wowtokenprices.com/assets/wowtokeninterlaced.png'

        try:
            async with aiohttp.get(url, headers=header) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            desc = soup.find('div', {"class": "mui-panel realm-panel", "id": realm.lower() + "-panel"}).h2.string
            buy_price = soup.find('td', {"class": "buy-price", "id": realm.upper() + "-buy"}).string
            day_lo = soup.find('span', {"id": realm.upper() + "-24min"}).string
            day_hi = soup.find('span', {"id": realm.upper() + "-24max"}).string
            updated = soup.find('td', {"id": realm.upper() + "-updatedhtml"}).string

            embed = discord.Embed(title='WoW Token Info', description=desc, colour=0xFFD966)
            embed.set_thumbnail(url=thumb_url)
            embed.add_field(name='Buy Price', value=buy_price, inline=False)
            embed.add_field(name='24-Hour Range', value=day_lo + ' - ' + day_hi, inline=False)
            embed.set_footer(text='Updated: ' + updated)

            await self.bot.say(embed=embed)

        except:
            await self.bot.say("Error finding WoW token prices.")


def check_folders():
    folder = "data/blizzard"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {'battletags': {}}
    if not dataIO.is_valid_json("data/blizzard/settings.json"):
        print("Creating default blizzard settings.json...")
        dataIO.save_json("data/blizzard/settings.json", default)


def setup(bot):
    if soup_available and pypandoc_available:
        check_folders()
        check_files()
        n = Blizzard(bot)
        bot.add_cog(n)
    else:
        if not soup_available:
            error_text += "You need to run `pip install beautifulsoup4`\n"
        if not pypandoc_available:
            error_text += "You need to run `pip install pypandoc`\n"
        raise RuntimeError(error_text)
