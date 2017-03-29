import os
import discord
from discord.ext import commands
from cogs.utils import checks
from .utils.dataIO import dataIO
from __main__ import send_cmd_help
from datetime import datetime
from json import JSONDecodeError
import hashlib
import aiohttp

# Special thanks to Kunkulada for suggesting this cog and
# contributing to the design of the embeds.


class Smite:

    """Smite Game Utilities"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/smite/settings.json"
        self.settings = dataIO.load_json(self.settings_path)
        self.url_pc = 'http://api.smitegame.com/smiteapi.svc'
        self.header = {"User-Agent": "flapjackcogs/1.0"}

    @commands.group(name="smite", pass_context=True)
    async def smite(self, ctx):
        """Smite cog commands."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @smite.command(name="auth", pass_context=True)
    @checks.is_owner()
    async def _auth_smite(self, ctx, devid: str, key: str):
        """Set the cog's Smite API authorization credentials, required for statistics.
        (get them at https://fs12.formsite.com/HiRez/form48/secure_index.html)
        Use a direct message to keep the credentials secret."""

        self.settings['devid'] = devid
        self.settings['authkey'] = key
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('API access credentials set.')

    @smite.command(name="ping", pass_context=True)
    @checks.is_owner()
    async def _ping_smite(self, ctx):
        """Ping the Smite API"""

        await self.ping()

    @smite.command(name="nameset", pass_context=True)
    async def _nameset_smite(self, ctx, name: str):
        """Set your Smite name"""

        uid = ctx.message.author.id
        self.settings['smitenames'][uid] = name
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Your Smite name has been set.")

    @smite.command(name="nameclear", pass_context=True)
    async def _nameclear_smite(self, ctx):
        """Remove your Smite name"""

        uid = ctx.message.author.id
        if self.settings['smitenames'].pop(uid, None) is not None:
            await self.bot.say("Your Smite name has been removed.")
        else:
            await self.bot.say("I had no Smite name stored for you.")
        dataIO.save_json(self.settings_path, self.settings)

    @smite.command(name="stats", pass_context=True)
    async def _stats_smite(self, ctx, name: str=None):
        """Smite stats for your in game name.
        If name is ommitted, bot will use your name if stored.

        Example: [p]smite stats Kunkulada
        """

        if not await self.test_session():
            if not await self.create_session():
                await self.bot.say("I could not establish a connection "
                                   "to the Smite API. Has my owner input "
                                   "valid credentials?")
                return

        uid = ctx.message.author.id
        if name is None:
            if uid in self.settings['smitenames']:
                name = self.settings['smitenames'][uid]
            else:
                await self.bot.say('You did not provide a name '
                                   'and I do not have one stored for you.')
                return

        dev_id = self.settings['devid']
        key = self.settings['authkey']
        session = self.settings['session_id']
        time = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        m = hashlib.md5()
        m.update(dev_id.encode('utf-8'))
        m.update('getplayer'.encode('utf-8'))
        m.update(key.encode('utf-8'))
        m.update(time.encode('utf-8'))
        str_hash = m.hexdigest()

        url = '/'.join([self.url_pc, 'getplayerJson', dev_id, str_hash, session, time, name])

        async with aiohttp.ClientSession(headers=self.header) as session:
            async with session.get(url) as resp:
                re = await resp.json()

        if not re:
            await self.bot.say("That profile is hidden or was not found.")
            return

        # Smite - Icon by J1mB091 on DeviantArt (http://j1mb091.deviantart.com/art/Smite-Icon-314198305)
        icon_url = 'http://orig09.deviantart.net/6fc3/f/2013/095/9/a/smite___icon_by_j1mb091-d572cyp.png'
        url = 'https://www.smitegame.com/player-stats/?set_platform_preference=pc&player-name=' + name

        # Fixes for empty string as team name or avatar url
        if not re[0]['Team_Name']:
            re[0]['Team_Name'] = "*none*"

        if not re[0]['Avatar_URL']:
            re[0]['Avatar_URL'] = "https://i.gyazo.com/af5f81163d9ee64586c0a3c19a9da769.png"

        embed = discord.Embed(color=0x4E66A3)
        embed.set_author(name=re[0]['Name'], url=url, icon_url=icon_url)
        embed.set_thumbnail(url=re[0]['Avatar_URL'])
        embed.add_field(name='Team', value=re[0]['Team_Name'], inline=False)
        embed.add_field(name='Wins', value=str(re[0]['Wins']), inline=False)
        embed.add_field(name='Losses', value=str(re[0]['Losses']), inline=True)
        embed.add_field(name='Ranked Conquest', value=self.league_tier(re[0]['RankedConquest']['Tier']), inline=True)
        embed.add_field(name='Leaves', value=str(re[0]['Leaves']), inline=True)
        embed.add_field(name='Ranked Joust', value=self.league_tier(re[0]['RankedJoust']['Tier']), inline=True)
        embed.add_field(name='Mastery', value=str(re[0]['MasteryLevel']), inline=True)
        embed.add_field(name='Ranked Duel', value=self.league_tier(re[0]['RankedDuel']['Tier']), inline=True)
        await self.bot.say(embed=embed)

    def league_tier(self, tier: int):
        return {
            1: 'Bronze V',
            2: 'Bronze IV',
            3: 'Bronze III',
            4: 'Bronze II',
            5: 'Bronze I',
            6: 'Silver V',
            7: 'Silver IV',
            8: 'Silver III',
            9: 'Silver II',
            10: 'Silver I',
            11: 'Gold V',
            12: 'Gold IV',
            13: 'Gold III',
            14: 'Gold II',
            15: 'Gold I',
            16: 'Platinum V',
            17: 'Platinum IV',
            18: 'Platinum III',
            19: 'Platinum II',
            20: 'Platinum I',
            21: 'Diamond V',
            22: 'Diamond IV',
            23: 'Diamond III',
            24: 'Diamond II',
            25: 'Diamond I',
            26: 'Masters I'
        }.get(tier, 'None')

    async def ping(self):

        url = self.url_pc + '/pingjson'
        async with aiohttp.ClientSession(headers=self.header) as session:
            async with session.get(url) as resp:
                await self.bot.say(await resp.text())

        return

    async def create_session(self):

        dev_id = self.settings['devid']
        key = self.settings['authkey']
        time = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        m = hashlib.md5()
        m.update(dev_id.encode('utf-8'))
        m.update('createsession'.encode('utf-8'))
        m.update(key.encode('utf-8'))
        m.update(time.encode('utf-8'))
        str_hash = m.hexdigest()

        url = '/'.join([self.url_pc, 'createsessionJson', dev_id, str_hash, time])

        async with aiohttp.ClientSession(headers=self.header) as session:
            async with session.get(url) as resp:
                try:
                    re = await resp.json()
                except JSONDecodeError:
                    # Response was not JSON. Could be bad/missing credentials.
                    return False

        if re['ret_msg'] == "Approved":
            self.settings['session_id'] = re['session_id']
            dataIO.save_json(self.settings_path, self.settings)
            return True
        # Response received, but request rejected. Could be bad credentials.
        return False

    async def test_session(self):

        dev_id = self.settings['devid']
        key = self.settings['authkey']
        session = self.settings['session_id']
        time = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        m = hashlib.md5()
        m.update(dev_id.encode('utf-8'))
        m.update('testsession'.encode('utf-8'))
        m.update(key.encode('utf-8'))
        m.update(time.encode('utf-8'))
        str_hash = m.hexdigest()

        url = '/'.join([self.url_pc, 'testsessionJson', dev_id, str_hash, session, time])
        async with aiohttp.ClientSession(headers=self.header) as session:
            async with session.get(url) as resp:
                text = await resp.text()

        if text.startswith('"Invalid'):
            return False
        elif text.startswith('"This'):
            return True
        # Response was something unexpected. Could be bad credentials,
        # or the Smite API has changed.
        return False


def check_folders():
    folder = "data/smite"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {'smitenames': {}, 'devid': '', 'authkey': '', 'session_id': ''}
    if not dataIO.is_valid_json("data/smite/settings.json"):
        print("Creating default Smite settings.json...")
        dataIO.save_json("data/smite/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    n = Smite(bot)
    bot.add_cog(n)
