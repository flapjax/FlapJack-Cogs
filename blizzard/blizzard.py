import asyncio
import re
from copy import copy
from numbers import Number

import aiohttp
import bleach
import discord
from bs4 import BeautifulSoup
from redbot.core import Config, checks, commands
from discord.ext.commands import formatter

# Special thanks to judge2020 for telling me about this method for getting
# patch notes. https://github.com/judge2020/BattleNetUpdateChecker
# Embed menus are modified version of the menu cog written by Awoonar Dust#7332
# https://github.com/Lunar-Dust/Dusty-Cogs/


class Blizzard(commands.Cog):

    """Blizzard Game Utilities"""

    default_global_settings = {
        "notes_format": "paged",
        "notes_timeout": 60
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=62869734)
        self.conf.register_global(
            **self.default_global_settings
        )
        self.session = aiohttp.ClientSession()
        self.base_url = 'https://us.battle.net/connect/en/app/'
        self.product_url = '/patch-notes?productType='
        self.wowtoken_url = 'http://wowtokenprices.com'
        self.patch_urls = {
            'hearthstone': 'https://us.battle.net/hearthstone/en/blog/',
            'overwatch': 'https://playoverwatch.com/en-us/game/patch-notes/pc/',
            'starcraft2': 'https://us.battle.net/sc2/en/game/patch-notes/',
            'warcraft': 'https://us.battle.net/wow/en/game/patch-notes/',
            'diablo3': 'https://us.battle.net/d3/en/game/patch-notes/',
            'hots': 'https://us.battle.net/heroes/en/blog/'
        }
        self.header = {"User-Agent": "flapjackcogs/1.0"}
        self.patch_header = {'User-Agent': 'Battle.net/1.0.8.4217'}
        self.abbr = {
            'hearthstone': 'wtcg',
            'overwatch': 'Pro',
            'starcraft2': 'sc2',
            'warcraft': 'WoW',
            'diablo3': 'd3',
            'hots': 'heroes'
        }
        self.thumbs = {
            'hearthstone': 'http://i.imgur.com/uK0AlGb.png',
            'overwatch': 'https://i.imgur.com/YZ4w2ey.png',
            'starcraft2': 'https://i.imgur.com/ErDVIMO.png',
            'warcraft': 'https://i.imgur.com/nrGZdB7.png',
            'diablo3': 'https://i.imgur.com/5WYDHHZ.png',
            'hots': 'https://i.imgur.com/NSMkOsA.png'
        }
        self.emoji = {
            "next": "\N{BLACK RIGHTWARDS ARROW}",
            "back": "\N{LEFTWARDS BLACK ARROW}",
            "no": "\N{CROSS MARK}"
        }
        self.expired_embed = discord.Embed(title="This menu has exipred due "
                                           "to inactivity.")

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def show_menu(self, ctx, message, messages, page):
        if message:
            await message.edit(content=messages[page])
            return message
        else:
            return await ctx.send(messages[page])

    async def _info_menu(self, ctx, messages, **kwargs):
        page = kwargs.get("page", 0)
        timeout = kwargs.get("timeout", 60)
        emoji = kwargs.get("emoji", self.emoji)
        message = kwargs.get("message", None)
        choices = len(messages)

        reactions_needed = True if message is None else False

        message = await self.show_menu(ctx, message, messages, page)

        if reactions_needed:
            await message.add_reaction(str(emoji['back']))
            await message.add_reaction(str(emoji['no']))
            await message.add_reaction(str(emoji['next']))

        # See if there's a way to check reaction add and remove at same time.
        def check(r, u):
            return r.message.id == message.id and u == ctx.message.author

        try:
            (r, u) = await self.bot.wait_for('reaction_add', check=check, timeout=timeout)
        except asyncio.TimeoutError:
            return [None, message]

        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.emoji]

        if react == "next":
            page += 1
        elif react == "back":
            page -= 1
        elif react == "no":
            return ["no", message]

        if page < 0:
            page = choices - 1

        if page == choices:
            page = 0

        try:
            await message.remove_reaction(emoji[react], u)
        except discord.errors.Forbidden:
            await ctx.send('I require the "manage messages" permission '
                           'to make these menus work.')
            return ["no", message]

        return await self._info_menu(
            ctx, messages,
            page=page,
            timeout=timeout,
            emoji=emoji,
            message=message)

    def dictgrab(self, my_dict, *keys):
        temp_dict = copy(my_dict)
        for key in keys:
            temp_dict = temp_dict.get(key)
            if temp_dict is None:
                return '-'
        if isinstance(temp_dict, Number):
            return str(round(temp_dict))
        else:
            return '-'

    @commands.group(name="blizzard", pass_context=True)
    async def blizzard(self, ctx):
        """Change blizzard cog settings."""
        pass

    @blizzard.command(name="apikey", pass_context=True)
    @checks.is_owner()
    async def _apikey_blizzard(self, ctx, key: str):
        """Set the cog's battle.net API key, required for Diablo statistics.
        (get one at https://dev.battle.net/)
        Use a direct message to keep the key secret."""

        await self.conf.apikey.set(key)
        await ctx.send('API key set.')

    @blizzard.command(name="noteformat", pass_context=True)
    @checks.is_owner()
    async def _noteformat_blizzard(self, ctx, form: str):
        """Set the format of the patch notes posted in chat.
        paged: post a single message with navigation menu
        full: post full notes in multiple messages
        embed: post a summary with link to full notes"""

        accept = ['paged', 'full', 'embed']
        if form in accept:
            await self.conf.notes_format.set(form)
            await ctx.send("Patch notes format set to `{}`.".format(form))
        else:
            await ctx.send("`{}` is not a valid format. Please choose "
                           "`{}`, `{}`, or `{}`.".format(form, accept[0],
                                                         accept[1], accept[2]))

    @blizzard.command(name="notetimeout", pass_context=True)
    @checks.is_owner()
    async def _notetimeout_blizzard(self, ctx, timeout: int):
        """Set the timeout period (sec) of the patch notes reaction menus.
        Only relevant for 'paged' or 'embed' mode."""

        min_max = (5, 3600)
        if min_max[0] <= timeout <= min_max[1]:
            await self.conf.notes_timeout.set(timeout)
            await ctx.send("Timeout period set to `{} sec`.".format(timeout))
        else:
            await ctx.send("Please choose a duration between "
                           "{} and {} seconds.".format(min_max[0], min_max[1]))

    @commands.group(name="battletag", pass_context=True)
    async def battletag(self, ctx):
        """Change your battletag settings."""
        pass

    @battletag.command(name="set", pass_context=True)
    async def _set_battletag(self, ctx, tag: str):
        """Set your battletag"""

        pattern = re.compile(r'.#\d{4,5}\Z')
        if pattern.search(tag) is None:
            await ctx.send("That doesn't look like a valid battletag.")
            return
        user = ctx.author
        await self.conf.user(user).battletag.set(tag)
        await ctx.send("Your battletag has been set.")

    @battletag.command(name="clear", pass_context=True)
    async def _clear_battletag(self, ctx):
        """Remove your battletag"""

        user = ctx.author
        tag = await self.conf.user(user).battletag()
        if tag is not None:
            await self.conf.user(user).battletag.set(None)
            await ctx.send("Your battletag has been removed.")
        else:
            await ctx.send("I had no battletag stored for you.")

    @commands.group(name="hearthstone", pass_context=True)
    async def hearthstone(self, ctx):
        """Hearthstone utilities"""
        pass

    @hearthstone.command(name="notes", pass_context=True)
    async def _notes_hearthstone(self, ctx):
        """Latest Hearthstone patch notes"""
        await self.format_patch_notes(ctx, 'hearthstone')

    @commands.group(name="overwatch", pass_context=True)
    async def overwatch(self, ctx):
        """Overwatch utilities"""
        pass

    @overwatch.command(name="stats", pass_context=True)
    async def _stats_overwatch(self, ctx, tag: str=None, region: str=None):
        """Overwatch stats for your battletag (case sensitive and PC only!).
        If battletag is ommitted, bot will use your battletag if stored.
        Region is optional and will autodetect with this priority: kr>eu>us

        Example: [p]overwatch stats CoolDude#1234 kr
        """

        user = ctx.author
        # Little hack to detect if region was entered, but not battletag
        if (tag in ['kr', 'eu', 'us']) and (region is None):
            region = tag
            tag = None

        if tag is None:
            tag = await self.conf.user(user).battletag()
            if tag is None:
                await ctx.send('You did not provide a battletag '
                               'and I do not have one stored for you.')
                return

        tag = tag.replace("#", "-")
        url = 'https://owapi.net/api/v3/u/' + tag + '/stats'
        async with self.session.get(url, headers=self.header) as response:
            stats = await response.json()

        if 'error' in stats:
            await ctx.send('Could not fetch your statistics. '
                           'Battletags are case sensitive '
                           'and require a 4 or 5-digit identifier '
                           '(e.g. CoolDude#1234)'
                           'Or, you may have an invalid tag '
                           'on file.')
            return

        if region is None:
            if stats['kr']:
                region = 'kr'
            elif stats['eu']:
                region = 'eu'
            elif stats['us']:
                region = 'us'
            else:
                await ctx.send('That battletag has no stats in any region.')
                return

        region_full = self.ow_full_region(region)

        if region not in stats.keys() or stats[region] is None:
            await ctx.send('That battletag exists, but I could not '
                           'find stats for the region specified. '
                           'Try a different region '
                           '<us/eu/kr> or leave that field blank '
                           'so I can autodetect the region.')
            return

        url = 'https://playoverwatch.com/en-us/career/pc/' + region + '/' + tag
        tag = tag.replace("-", "#")

        qplay = stats[region]['stats']['quickplay']
        if qplay is None:
            qplay_stats = "*No matches played*"
            thumb_url = self.thumbs['overwatch']
        else:
            thumb_url = qplay['overall_stats']['avatar']
            qplay_stats = ''.join(['**Wins:** ', self.dictgrab(qplay, 'game_stats', 'games_won'),
                                   '\n**Avg Elim:** ', self.dictgrab(qplay, 'average_stats', 'eliminations_avg'),
                                   '\n**Avg Death:** ', self.dictgrab(qplay, 'average_stats', 'deaths_avg'),
                                   '\n**Avg Heal:** ', self.dictgrab(qplay, 'average_stats', 'healing_done_avg')])

        comp = stats[region]['stats']['competitive']
        footer = None
        if comp is None:
            comp_stats = "*No matches played*"
            tier = None
        elif comp['overall_stats']['comprank'] is None:
            comp_stats = "*Not ranked*"
            tier = None
        else:
            tier = comp['overall_stats']['tier']
            footer = 'SR: ' + str(comp['overall_stats']['comprank'])
            comp_stats = ''.join(['**Wins:** ', self.dictgrab(comp, 'game_stats', 'games_won'),
                                  '\n**Avg Elim:** ', self.dictgrab(comp, 'average_stats', 'eliminations_avg'),
                                  '\n**Avg Death:** ', self.dictgrab(comp, 'average_stats', 'deaths_avg'),
                                  '\n**Avg Heal:** ', self.dictgrab(comp, 'average_stats', 'healing_done_avg')])

        icon_url = self.ow_tier_icon(tier)

        # Images not working in embed?
        embed = discord.Embed(title='Overwatch Stats (PC-' + region_full + ')', color=0xFAA02E)
        embed.set_author(name=tag, url=url, icon_url=icon_url)
        embed.set_thumbnail(url=thumb_url)
        embed.add_field(name='__Competitive__', value=comp_stats, inline=True)
        embed.add_field(name='__Quick Play__', value=qplay_stats, inline=True)
        if footer is not None:
            embed.set_footer(text=footer)
        await ctx.send(embed=embed)

    def ow_tier_icon(self, tier: str):
        return {
            'bronze': 'https://i.imgur.com/B4IR72H.png',
            'silver': 'https://i.imgur.com/1mOpjRc.png',
            'gold': 'https://i.imgur.com/lCTsNwo.png',
            'platinum': 'https://i.imgur.com/nDVHAbp.png',
            'diamond': 'https://i.imgur.com/fLmIC70.png',
            'master': 'https://i.imgur.com/wjf0lEc.png',
            'grandmaster': 'https://i.imgur.com/5ApGiZs.png',
        }.get(tier, self.thumbs['overwatch'])

    def ow_full_region(self, region: str):
        return {
            'kr': 'Asia',
            'eu': 'Europe',
            'us': 'US',
        }.get(region, ' ')

    @overwatch.command(name="notes", pass_context=True)
    async def _notes_overwatch(self, ctx):
        """Latest Overwatch patch notes"""
        await self.format_patch_notes(ctx, 'overwatch')

    @commands.group(name="starcraft2", pass_context=True)
    async def starcraft2(self, ctx):
        """Starcraft2 utilities"""
        pass

    @starcraft2.command(name="notes", pass_context=True)
    async def _notes_starcraft2(self, ctx):
        """Latest Starcraft2 patch notes"""
        await self.format_patch_notes(ctx, 'starcraft2')

    @commands.group(name="warcraft", pass_context=True)
    async def warcraft(self, ctx):
        """World of Warcraft utilities"""
        pass

    @warcraft.command(name="notes", pass_context=True)
    async def _notes_warcraft(self, ctx):
        """Latest World of Warcraft patch notes"""
        await self.format_patch_notes(ctx, 'warcraft')

    @warcraft.command(name="token", pass_context=True)
    async def _token_warcraft(self, ctx, realm: str='na'):
        """WoW Token Prices"""

        url = self.wowtoken_url

        if realm.lower() not in ['us', 'eu', 'cn', 'tw', 'kr']:
            await ctx.send("'" + realm + "' is not a valid realm.")
            return

        await self.print_token(ctx, url, self.wow_full_region(realm))

    def wow_full_region(self, region: str):
        # Works only with wowtokenprices.com
        return {
            'kr': 'korea',
            'eu': 'eu',
            'us': 'us',
            'cn': 'china',
            'tw': 'taiwan'
        }.get(region, ' ')

    @commands.group(name="diablo3", pass_context=True)
    async def diablo3(self, ctx):
        """Diablo3 utilities"""
        pass

    @diablo3.command(name="notes", pass_context=True)
    async def _notes_diablo3(self, ctx):
        """Latest Diablo3 patch notes"""
        await self.format_patch_notes(ctx, 'diablo3')

    @diablo3.command(name="stats", pass_context=True)
    async def _stats_diablo3(self, ctx, tag: str=None, region: str=None):
        """Diablo3 stats for your battletag.
        If battletag is ommitted, bot will use your battletag if stored.

        Example: [p]diablo3 stats CoolDude#1234
        """

        user = ctx.author

        # Little hack to detect if region was entered, but not battletag
        if tag is not None and tag.lower() in ['kr', 'eu', 'us', 'tw']\
                and region is None:
            region = tag
            tag = None

        if tag is None:
            tag = await self.conf.user(user).battletag()
            if tag is None:
                await ctx.send('You did not provide a battletag '
                               'and I do not have one stored for you.')
                return
        key = await self.conf.apikey()
        if key is None:
            await ctx.send('The bot owner has not provided a '
                           'battle.net API key, which is '
                           'required for Diablo 3 stats.')
            return

        if region is not None:
            region = region.lower()
        if region == 'us':
            locale = 'en_US'
        elif region == 'eu':
            locale = 'en_GB'
        elif region == 'kr':
            locale = 'ko_KR'
        elif region == 'tw':
            locale = 'zh_TW'
        else:
            locale = 'en_US'
            region = 'us'

        tag = tag.replace("#", "-")
        url = 'https://' + region + '.api.battle.net/d3/profile/'\
              + tag + '/?locale=' + locale + '&apikey=' + key
        
        async with self.session.get(url, headers=self.header) as response:
            stats = await response.json()

        if 'code' in stats:
            await ctx.send("I coulnd't find Diablo 3 stats for that battletag.")
            return

        tag = tag.replace("-", "#") + ' (' + region.upper() + ')'
        thumb_url = self.thumbs['diablo3']

        paragon = ''.join([':leaves:Seasonal: ', str(stats['paragonLevelSeason']),
                           '\n:leaves:Seasonal Hardcore: ', str(stats['paragonLevelSeasonHardcore']),
                           '\nNon-Seasonal: ', str(stats['paragonLevel']),
                           '\nNon-Seasonal Hardcore: ', str(stats['paragonLevelHardcore'])])

        hero_txt = ''
        for hero in stats['heroes']:
            hero_txt += ''.join([':leaves:' if hero['seasonal'] else '', hero['name'],
                                 ' - lvl ', str(hero['level']), ' ', hero['class'],
                                 ' - hardcore' if hero['hardcore'] else '',
                                 ' (RIP)\n' if hero['dead'] else '\n'])

        if not hero_txt:
            await ctx.send("You don't have any Diablo 3 heroes.")
            return

        kills = "Lifetime monster kills: " + str(stats['kills']['monsters'])

        embed = discord.Embed(title='Diablo 3 Stats', color=0xCC2200)
        embed.set_author(name=tag)
        embed.set_thumbnail(url=thumb_url)
        embed.add_field(name='__Paragon__', value=paragon, inline=False)
        embed.add_field(name='__Heroes__', value=hero_txt, inline=False)
        embed.set_footer(text=kills)
        await ctx.send(embed=embed)

    @commands.group(name="hots", pass_context=True)
    async def hots(self, ctx):
        """Heroes of the Storm utilities"""
        pass

    @hots.command(name="notes", pass_context=True)
    async def _notes_hots(self, ctx):
        """Latest Heroes of the Storm patch notes"""
        await self.format_patch_notes(ctx, 'hots')

    async def format_patch_notes(self, ctx, game: str=None):
        url = ''.join([self.base_url,
                       self.abbr[game],
                       self.product_url,
                       self.abbr[game]])
        tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'div']
        attr = {'div': 'class'}
        async with self.session.get(url, headers=self.patch_header) as response:
            dirty = await response.text()
        clean = bleach.clean(dirty, tags=tags, attributes=attr, strip=True)
        soup = BeautifulSoup(clean, "html.parser")
        # Preserving this list structure, in case we ever want to switch to
        # scraping the actual game websites for multiple notes
        notes = soup.find_all('div', class_="patch-notes-interior")
        note_list = []
        for note in notes:
            # Format each patch note into an array of messages using Paginator
            pager = formatter.Paginator(prefix='```markdown', suffix='```', max_size=1000)
            # Custom headers for sucky patch notes that have none
            if game == "starcraft2":
                text = "STARCRAFT 2 PATCH NOTES"
                pager.add_line(text + '\n' + '='*len(text))
            elif game == "warcraft":
                text = "WORLD OF WARCRAFT PATCH NOTES"
                pager.add_line(text + '\n' + '='*len(text))
            elif game == "hearthstone":
                # Convert first paragraph to h1
                note.p.name = 'h1'
            elif game == "overwatch":
                pass
            elif game == "diablo3":
                text = "DIABLO 3 PATCH NOTES"
                pager.add_line(text + '\n' + '='*len(text))
            elif game == "hots":
                text = "HEROES OF THE STORM PATCH NOTES"
                pager.add_line(text + '\n' + '='*len(text))

            for child in note.children:
                if child.name == 'h1':
                    # This is a patch notes title, with date.
                    text = child.get_text()
                    pager.add_line(text + '\n' + '='*len(text))
                elif str(child.name).startswith('h'):
                    # Thid is a patch notes section heading.
                    text = child.get_text()
                    pager.add_line('\n' + text + '\n' + '-'*len(text))
                elif child.name == 'p':
                    # This is a plain paragraph of patch notes.
                    text = child.get_text()
                    if text.strip():
                        text = '> ' + text if len(text) < 80 else text
                        pager.add_line('\n' + text)
                elif child.name == 'li':
                    # A list is about to follow.
                    pager.add_line('')
                    self.walk_list(child, pager, -1)
                else:
                    # Space reserved for future cases of "something else"
                    pass
            note_list.append(pager.pages)

        notes_format = await self.conf.notes_format()
        timeout = await self.conf.notes_timeout()
        if notes_format == 'paged':
            result = await self._info_menu(ctx, note_list[0], timeout=timeout)
            if result[0] == "no":
                await result[1].delete()
            else:
                await result[1].edit(embed=self.expired_embed)
        elif notes_format == 'full':
            await self.say_full_notes(ctx, note_list[0])
        else:
            # Extract title and body, remove markdown formatting line between
            split = note_list[0][0].split('\n', 3)
            title = split[1]
            # Remove \n```
            body = split[3][:-4]
            embed = discord.Embed(title=title, url=self.patch_urls[game], color=0x00B4FF)
            embed.set_thumbnail(url=self.thumbs[game])
            embed.add_field(name='Summary', value=body, inline=False)
            await ctx.send(embed=embed)

    def walk_list(self, child, pager, count):
        try:
            for grandchild in child.contents:
                self.walk_list(grandchild, pager, count + 1)
        except AttributeError:
            if child.string.strip():
                pager.add_line('  '*count + '*' + ' ' + child.string.strip())

    async def say_full_notes(self, ctx, pages):
        for page in pages:
            await ctx.send(page)
            await asyncio.sleep(1)

    async def print_token(self, ctx, url, realm):

        thumb_url = 'http://wowtokenprices.com/assets/wowtokeninterlaced.png'

        try:
            async with self.session.get(url, headers=self.header) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")

            data = soup.find('div', class_=realm + '-region-div')
            desc = data.div.a.h3.text
            buy_price = data.div.find('p', class_='money-text').text
            trend = data.div.find('span', class_='money-text-small').text
            # Update time broken, returns --:-- -- when requested by bot
            #updated = data.div.find('p', id=realm + '-datetime').text

            embed = discord.Embed(title='WoW Token Info', description=desc, colour=0xFFD966)
            embed.set_thumbnail(url=thumb_url)
            embed.add_field(name='Buy Price', value=buy_price, inline=False)
            embed.add_field(name='Change', value=trend, inline=False)
            #embed.set_footer(text='Updated: ' + updated)

            await ctx.send(embed=embed)

        except:
            await ctx.send("Error finding WoW token prices.")
