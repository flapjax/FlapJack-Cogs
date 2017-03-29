import os
import discord
from discord.ext import commands
from discord.ext.commands import formatter
from .utils import chat_formatting as cf
from cogs.utils import checks
from .utils.dataIO import dataIO
from __main__ import send_cmd_help
import re
import aiohttp
import asyncio
import bleach

try:
    from bs4 import BeautifulSoup
    soup_available = True
except:
    soup_available = False

# Special thanks to judge2020 for telling me about this message of getting
# patch notes: https://github.com/judge2020/BattleNetUpdateChecker
# Embed menus are modified version of the menu cog written by Awoonar Dust#7332
# https://github.com/Lunar-Dust/Dusty-Cogs/


class Forbidden():
    pass


class Blizzard:

    """Blizzard Game Utilities"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_path = "data/blizzard/settings.json"
        self.settings = dataIO.load_json(self.settings_path)
        self.timeout = 3600
        self.base_url = 'https://us.battle.net/connect/en/app/'
        self.wowtoken_url = 'https://wowtoken.info/'
        self.product_url = '/patch-notes?productType='
        self.hearthstone_abbr = 'wtcg'
        self.overwatch_abbr = 'Pro'
        self.starcraft2_abbr = 'sc2'
        self.warcraft_abbr = 'WoW'
        self.diablo_abbr = 'd3'
        self.hots_abbr = 'heroes'
        self.header = {"User-Agent": "flapjackcogs/1.0"}
        self.patch_header = {'User-Agent': 'Battle.net/1.0.8.4217'}
        self.patch_urls = {
            "overwatch": "https://playoverwatch.com/en-us/game/patch-notes/pc/"
        }
        self.emoji = {
            0: "0⃣",
            1: "1⃣",
            2: "2⃣",
            3: "3⃣",
            4: "4⃣",
            5: "5⃣",
            6: "6⃣",
            7: "7⃣",
            8: "8⃣",
            9: "9⃣",
            10: "🔟",
            "up": "⬆️",
            "down": "⬇️",
            "next": "➡",
            "back": "⬅",
            "yes": "✅",
            "no": "❌"
        }
        self.expired_embed = discord.Embed(title='This menu has exipred due to inactivity.')

    def perms(self, ctx):
        user = ctx.message.server.get_member(self.bot.user.id)
        return ctx.message.channel.permissions_for(user)

    async def _add_reactions(self, message, choices: list, page, emoji, loop=False):
        pages = [choices[x:x + 10] for x in range(0, len(choices), 10)]
        if page > len(pages):
            page = 0
        if page:
            await self.bot.add_reaction(message, str(emoji['back']))
        for idx, i in enumerate(pages[page], 1):
            await self.bot.add_reaction(message, str(emoji[idx]))

        is_last = (page < len(pages) - 1)
        if not is_last or (is_last and loop):
            await self.bot.add_reaction(message, str(emoji['next']))
        return

    async def menu(self, ctx, _type: int, messages, choices: int = 1, **kwargs):
        """Creates and manages a new menu
        Required arguments:
            Type:
                1- number menu
                2- confirmation menu
                3- info menu (basically menu pagination)
            Messages:
                Strings or embeds to use for the menu.
                Pass as a list for number menu
        Optional agruments:
            page (Defaults to 0):
                The message in messages that will be displayed
            timeout (Defaults to 15):
                The number of seconds until the menu automatically expires
            check (Defaults to default_check):
                The same check that wait_for_reaction takes
            is_open (Defaults to False):
                Whether or not the menu can take input from any user
            emoji (Decaults to self.emoji):
                A dictionary containing emoji to use for the menu.
                If you pass this, use the same naming scheme as self.emoji
            message (Defaults to None):
                The discord.Message to edit if present
            loop (Defaults to False):
                Whether or not the pages loop to the first page at the end"""
        result = None
        if _type == 1:
            result = await self._number_menu(ctx, messages, choices, **kwargs)
        if _type == 2:
            result = await self._confirm_menu(ctx, messages, **kwargs)
        if _type == 3:
            result = await self._info_menu(ctx, messages, **kwargs)

        return result

    async def show_menu(self,
                        ctx,
                        message,
                        messages,
                        page):
        if message:
            return await self.bot.edit_message(message, messages[page])
        else:
            # This must be the initial post
            return await self.bot.send_message(ctx.message.channel,
                                               messages[page])

    async def _number_menu(self, ctx, messages, choices, **kwargs):
        page = kwargs.get('page', 0)
        timeout = kwargs.get('timeout', 15)
        check = kwargs.get('check', default_check)
        is_open = kwargs.get('is_open', False)
        emoji = kwargs.get('emoji', self.emoji)
        message = kwargs.get('message', None)
        loop = kwargs.get('loop', False)

        await self.show_menu(ctx, message, messages)

        await self._add_reactions(message, choices, page, emoji, loop)

        r = await self.bot.wait_for_reaction(
            emoji=list(emoji.values()),
            message=message,
            user=ctx.message.author,
            check=check,
            timeout=timeout)
        if r is None:
            return None

        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.reaction.emoji]

        if react == "next":
            page += 1
        elif react == "back":
            page -= 1
        else:
            return react

        try:
            await self.bot.remove_reaction(message, emoji[react], r.user)
        except Forbidden:
            await self.bot.delete_message(message)
            message = None

        return await self._number_menu(
            ctx, message,
            choices, page=page,
            timeout=timeout,
            check=check, is_open=is_open,
            emoji=emoji, message=message,
            loop=loop)

    async def _confirm_menu(self, ctx, message, **kwargs):
        timeout = kwargs.get('timeout', 15)
        check = kwargs.get('check', default_check)
        emoji = kwargs.get('emoji', self.emoji)

        await self.bot.add_reaction(message, str(emoji['yes']))
        await self.bot.add_reaction(message, str(emoji['no']))

        r = await self.bot.wait_for_reaction(
            message=message,
            check=check,
            user=ctx.message.author,
            timeout=timeout)
        if r is None:
            return None

        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.reaction.emoji]

        if react == "no":
            return False
        else:
            return True

    async def _info_menu(self, ctx, messages, **kwargs):
        page = kwargs.get("page", 0)
        timeout = kwargs.get("timeout", 15)
        is_open = kwargs.get("is_open", False)
        check = kwargs.get("check", default_check)
        emoji = kwargs.get("emoji", self.emoji)
        message = kwargs.get("message", None)
        choices = len(messages)

        if message is None:
            reactions_needed = True
        else:
            reactions_needed = False

        message = await self.show_menu(ctx, message, messages, page)

        if reactions_needed:
            await self.bot.add_reaction(message, str(emoji['back']))
            await self.bot.add_reaction(message, str(emoji['no']))
            await self.bot.add_reaction(message, str(emoji['next']))

        r = await self.bot.wait_for_reaction(
            message=message,
            user=ctx.message.author,
            check=default_check,
            timeout=timeout)
        if r is None:
            return [None, message]

        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.reaction.emoji]

        if react == "next":
            page += 1
        if react == "back":
            page -= 1
        if react == "no":
            return ["no", message]

        if page < 0:
            page = choices - 1

        if page == choices:
            page = 0

        if self.perms(ctx).manage_messages:
            await self.bot.remove_reaction(message, emoji[react], r.user)
        else:
            await self.bot.delete_message(message)
            message = None

        return await self._info_menu(
            ctx, messages,
            page=page,
            timeout=timeout,
            check=check, is_open=is_open,
            emoji=emoji, message=message)

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

        pattern = re.compile(r'.#\d{4,5}\Z')
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
        url = ''.join([self.base_url,
                       self.hearthstone_abbr,
                       self.product_url,
                       self.hearthstone_abbr])

        notes = await self.format_patch_notes(url, 'wtcg')

        result = await self.menu(ctx, 3, notes, timeout=self.timeout)
        if result[0] == "no":
            await self.bot.delete_messages([result[1], ctx.message])
        else:
            await self.bot.edit_message(result[1], embed=self.expired_embed)

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
                await self.bot.say('You did not provide a battletag '
                                   'and I do not have one stored for you.')
                return

        tag = tag.replace("#", "-")
        url = 'https://owapi.net/api/v3/u/' + tag + '/stats'
        async with aiohttp.ClientSession(headers=self.header) as session:
            async with session.get(url) as resp:
                stats = await resp.json()

        if 'error' in stats:
            await self.bot.say('Could not fetch your statistics. '
                               'Battletags are case sensitive '
                               'and require a 4 or 5-digit identifier '
                               '(e.g. CoolDude#1234)'
                               'Or, you may have an invalid tag '
                               'on file.')
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
            await self.bot.say('That battletag exists, but I could not '
                               'find stats for the region specified. '
                               'Try a different region '
                               '<us/eu/kr> or leave that field blank '
                               'so I can autodetect the region.')
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
        url = ''.join([self.base_url,
                       self.overwatch_abbr,
                       self.product_url,
                       self.overwatch_abbr])

        notes = await self.format_patch_notes(url, 'ow')

        result = await self.menu(ctx, 3, notes, timeout=self.timeout)
        if result[0] == "no":
            await self.bot.delete_messages([result[1], ctx.message])
        else:
            await self.bot.edit_message(result[1], embed=self.expired_embed)

    @overwatch.command(name="notes2", pass_context=True)
    async def _notes2_overwatch(self, ctx):
        """Recent Overwatch patch notes"""
        url = self.patch_urls['overwatch']
        async with aiohttp.get(url, headers=self.header) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
        notes = soup.find_all("div", class_="patch-notes-body")
        embed_list = []
        icon_url = 'http://i.imgur.com/YZ4w2ey.png'
        footer = "Use the reaction controls to navigate through previous patch notes!"
        for n in notes:
            author = n.h1.string.upper()
            url = self.patch_urls['overwatch']
            embed=discord.Embed(url=url)
            embed.set_author(name=author, icon_url=icon_url)
            embed.set_footer(text=footer)
            embed_list.append(embed)

        result = await self.menu(ctx, 3, embed_list)
        if result[0] == "no":
            await self.bot.delete_messages([result[1], ctx.message])
        else:
            await self.bot.edit_message(result[1], embed=self.expired_embed)




    @commands.group(name="starcraft2", pass_context=True)
    async def starcraft2(self, ctx):
        """Starcraft2 utilities"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @starcraft2.command(name="notes", pass_context=True)
    async def _notes_starcraft2(self, ctx):
        """Latest Starcraft2 patch notes"""
        url = ''.join([self.base_url,
                       self.starcraft2_abbr,
                       self.product_url,
                       self.starcraft2_abbr])

        notes = await self.format_patch_notes(url, 'sc2')

        result = await self.menu(ctx, 3, notes, timeout=self.timeout)
        if result[0] == "no":
            await self.bot.delete_messages([result[1], ctx.message])
        else:
            await self.bot.edit_message(result[1], embed=self.expired_embed)

    @commands.group(name="warcraft", pass_context=True)
    async def warcraft(self, ctx):
        """World of Warcraft utilities"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @warcraft.command(name="notes", pass_context=True)
    async def _notes_warcraft(self, ctx):
        """Latest World of Warcraft patch notes"""

        url = ''.join([self.base_url,
                       self.warcraft_abbr,
                       self.product_url,
                       self.warcraft_abbr])

        notes = await self.format_patch_notes(url, 'WoW')

        result = await self.menu(ctx, 3, notes, timeout=self.timeout)
        if result[0] == "no":
            await self.bot.delete_messages([result[1], ctx.message])
        else:
            await self.bot.edit_message(result[1], embed=self.expired_embed)

    @warcraft.command(name="token", pass_context=True)
    async def _token_warcraft(self, ctx, realm: str='na'):
        """WoW Token Prices"""

        url = ''.join([self.wowtoken_url])

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
        url = ''.join([self.base_url,
                       self.diablo_abbr,
                       self.product_url,
                       self.diablo_abbr])

        notes = await self.format_patch_notes(url, 'd3')

        result = await self.menu(ctx, 3, notes, timeout=self.timeout)
        if result[0] == "no":
            await self.bot.delete_messages([result[1], ctx.message])
        else:
            await self.bot.edit_message(result[1], embed=self.expired_embed)

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
                await self.bot.say('You did not provide a battletag '
                                   'and I do not have one stored for you.')
                return

        if 'apikey' not in self.settings:
            await self.bot.say('The bot owner has not provided a '
                               'battle.net API key, which is '
                               'required for Diablo 3 stats.')
            return

        key = self.settings['apikey']
        tag = tag.replace("#", "-")
        url = 'https://us.api.battle.net/d3/profile/' + tag + '/?locale=en_US&apikey=' + key

        async with aiohttp.ClientSession(headers=self.header) as session:
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
            hero_txt += ''.join([':leaves:' if hero['seasonal'] else '', hero['name'],
                                 ' - lvl ', str(hero['level']), ' ', hero['class'],
                                 ' - hardcore' if hero['hardcore'] else '',
                                 ' (RIP)\n' if hero['dead'] else '\n'])

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
        url = ''.join([self.base_url,
                       self.hots_abbr,
                       self.product_url,
                       self.hots_abbr])

        notes = await self.format_patch_notes(url, 'hots')

        result = await self.menu(ctx, 3, notes, timeout=self.timeout)
        if result[0] == "no":
            await self.bot.delete_messages([result[1], ctx.message])
        else:
            await self.bot.edit_message(result[1], embed=self.expired_embed)

    async def format_patch_notes(self, url, game: str=None):
        tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'div']
        attr = {'div': 'class'}
        async with aiohttp.get(url, headers=self.patch_header) as response:
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
            # Custom headers for sucky patch notes that have None
            if game == "sc2":
                text = "STARCRAFT 2 PATCH NOTES"
                pager.add_line(text + '\n' + '='*len(text))
            elif game == "WoW":
                text = "WORLD OF WARCRAFT PATCH NOTES"
                pager.add_line(text + '\n' + '='*len(text))
            elif game == "wtcg":
                # Convert first paragraph to h1
                note.p.name = 'h1'
            elif game == "ow":
                pass
            elif game == "d3":
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
                    # It's something different, treat like a paragraph and hope.
                    #pager.add_line(child.get_text())
                    pass
            note_list.append(pager.pages)


        return note_list[0]
        # Can say full notes with:
        #await self.say_full_notes(note_list[0])

    def walk_list(self, child, pager, count):
        try:
            for grandchild in child.contents:
                self.walk_list(grandchild, pager, count + 1)
        except AttributeError:
            if child.string.strip():
                pager.add_line('  '*count + '*' + ' ' + child.string.strip())


    async def say_full_notes(self, pages):
        for page in pages:
            await self.bot.say(page)
            await asyncio.sleep(1)

    async def print_token(self, url, realm):

        thumb_url = 'http://wowtokenprices.com/assets/wowtokeninterlaced.png'

        try:
            async with aiohttp.get(url, headers=self.header) as response:
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

def default_check(reaction, user):
        if user.bot:
            return False
        else:
            return True


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
    if soup_available:
        check_folders()
        check_files()
        n = Blizzard(bot)
        bot.add_cog(n)
    else:
        error_text = "You need to run `pip install beautifulsoup4`"
        raise RuntimeError(error_text)
