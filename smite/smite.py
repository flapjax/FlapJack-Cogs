import hashlib
from datetime import datetime
from json import JSONDecodeError

import aiohttp
import discord
from redbot.core import checks, Config, commands

# Special thanks to Kunkulada for suggesting this cog and
# contributing to the design of the embeds.


class Smite(commands.Cog):

    """Smite Game Utilities"""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=254906529)
        self.session = aiohttp.ClientSession()
        self.url_pc = 'http://api.smitegame.com/smiteapi.svc'
        self.header = {"User-Agent": "flapjackcogs/1.0"}

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.group(name="smite", pass_context=True)
    async def smite(self, ctx):
        """Smite cog commands."""
        pass

    @smite.command(name="auth", pass_context=True)
    @checks.is_owner()
    async def _auth_smite(self, ctx, devid: str, key: str):
        """Set the cog's Smite API authorization credentials, required for statistics.
        (get them at https://fs12.formsite.com/HiRez/form48/secure_index.html)
        Use a direct message to keep the credentials secret."""

        await self.conf.devid.set(devid)
        await self.conf.authkey.set(key)
        await ctx.send('API access credentials set.')

    @smite.command(name="ping", pass_context=True)
    @checks.is_owner()
    async def _ping_smite(self, ctx):
        """Ping the Smite API"""

        await self.ping(ctx)

    @smite.command(name="nameset", pass_context=True)
    async def _nameset_smite(self, ctx, name: str):
        """Set your Smite name"""

        user = ctx.author
        await self.conf.user(user).smitename.set(name)
        await ctx.send("Your Smite name has been set.")

    @smite.command(name="nameclear", pass_context=True)
    async def _nameclear_smite(self, ctx):
        """Remove your Smite name"""

        user = ctx.author
        name = await self.conf.user(user).smitename()
        if name is not None:
            await self.conf.user(user).smitename.set(None)
            await ctx.send("Your Smite name has been removed.")
        else:
            await ctx.send("I had no Smite name stored for you.")

    @smite.command(name="stats", pass_context=True)
    async def _stats_smite(self, ctx, name: str=None):
        """Smite stats for your in game name.
        If name is ommitted, bot will use your name if stored.

        Example: [p]smite stats Kunkulada
        """

        dev_id = await self.conf.devid()
        key = await self.conf.authkey()
        if dev_id is None or key is None:
            await ctx.send("I am missing Smite API credentials.")
            return

        user = ctx.message.author
        if name is None:
            name = await self.conf.user(user).smitename()
            if name is None:
                await ctx.send('You did not provide a name '
                               'and I do not have one stored for you.')
                return

        if not await self.test_session():
            if not await self.create_session():
                await ctx.send("I could not establish a connection "
                               "to the Smite API. Has my owner input "
                               "valid credentials?")
                return

        session = await self.conf.session_id()
        time = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        m = hashlib.md5()
        m.update(dev_id.encode('utf-8'))
        m.update('getplayer'.encode('utf-8'))
        m.update(key.encode('utf-8'))
        m.update(time.encode('utf-8'))
        str_hash = m.hexdigest()

        url = '/'.join([self.url_pc, 'getplayerJson', dev_id, str_hash, session, time, name])

        async with self.session.get(url, headers=self.header) as response:
            re = await response.json()

        if not re:
            await ctx.send("That profile is hidden or was not found.")
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
        await ctx.send(embed=embed)

    @smite.command(name="status", pass_context=True)
    async def _status_smite(self, ctx, name: str=None):
        """Smite player status.
        If name is ommitted, bot will use your name if stored.

        Example: [p]smite status Kunkulada
        """

        dev_id = await self.conf.devid()
        key = await self.conf.authkey()
        if dev_id is None or key is None:
            await ctx.send("I am missing Smite API credentials.")
            return

        user = ctx.message.author
        if name is None:
            name = await self.conf.user(user).smitename()
            if name is None:
                await ctx.send('You did not provide a name '
                               'and I do not have one stored for you.')
                return

        if not await self.test_session():
            if not await self.create_session():
                await ctx.send("I could not establish a connection "
                               "to the Smite API. Has my owner input "
                               "valid credentials?")
                return

        session = await self.conf.session_id()
        time = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        m = hashlib.md5()
        m.update(dev_id.encode('utf-8'))
        m.update('getplayerstatus'.encode('utf-8'))
        m.update(key.encode('utf-8'))
        m.update(time.encode('utf-8'))
        str_hash = m.hexdigest()

        url = '/'.join([self.url_pc, 'getplayerstatusJson', dev_id, str_hash, session, time, name])

        async with self.session.get(url, headers=self.header) as response:
            re = await response.json()

        # Smite - Icon by J1mB091 on DeviantArt (http://j1mb091.deviantart.com/art/Smite-Icon-314198305)
        icon_url = 'http://orig09.deviantart.net/6fc3/f/2013/095/9/a/smite___icon_by_j1mb091-d572cyp.png'

        if re[0]['status'] == 0:
            name = 'Offline'
        elif re[0]['status'] == 1:
            name = 'In Lobby'
        elif re[0]['status'] == 2:
            name = 'God Selection'
        elif re[0]['status'] == 3:
            name = 'In Game'
        elif re[0]['status'] == 4:
            name = 'Online - No Data'
        else:
            await ctx.send("I could not find information on this player.")
            return

        embed = discord.Embed(color=0x4E66A3)
        embed.set_author(name=name, icon_url=icon_url)
        if re[0]['status'] != 3:
            await ctx.send(embed=embed)
            return

        # If we reach here, player is in a game, and we can show live data
        mid = str(re[0]['Match'])
        session = await self.conf.session_id()
        time = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        m = hashlib.md5()
        m.update(dev_id.encode('utf-8'))
        m.update('getmatchplayerdetails'.encode('utf-8'))
        m.update(key.encode('utf-8'))
        m.update(time.encode('utf-8'))
        str_hash = m.hexdigest()

        url = '/'.join([self.url_pc, 'getmatchplayerdetailsJson', dev_id, str_hash, session, time, mid])

        async with self.session.get(url, headers=self.header) as response:
            re = await response.json()

        teams = ['', '']

        for player in re:
            team = player['taskForce']-1
            teams[team] += '\n'.join(['**' + player['playerName'] + '**',
                                      'God: ' + player['GodName'],
                                      'Tier: ' + self.league_tier(player['Tier']),
                                      '\n'])

        name += ' - ' + self.queue_type(re[0]['Queue'])
        embed.set_author(name=name, icon_url=icon_url)
        embed.add_field(name='__Team 1__', value=teams[0], inline=True)
        embed.add_field(name='__Team 2__', value=teams[1], inline=True)
        await ctx.send(embed=embed)

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

    def queue_type(self, queue: str):
        return {
            '423': 'Conquest 5v5',
            '424': 'Novice Queue',
            '426': 'Conquest',
            '427': 'Practice',
            '429': 'Conquest Challenge',
            '430': 'Conquest Ranked',
            '433': 'Domination',
            '434': 'MOTD',
            '435': 'Arena',
            '438': 'Arena Challenge',
            '439': 'Domination Challenge',
            '440': 'Joust League',
            '441': 'Joust Challenge',
            '445': 'Assault',
            '446': 'Assault Challenge',
            '448': 'Joust 3v3',
            '451': 'Conquest League',
            '452': 'Arena League',
            '465': 'MOTD'
        }.get(queue, 'Unknown')

    async def ping(self, ctx):

        url = self.url_pc + '/pingjson'
        async with self.session.get(url, headers=self.header) as response:
            await ctx.send(await response.text())
        return

    async def create_session(self):

        dev_id = await self.conf.devid()
        key = await self.conf.authkey()
        if dev_id is None or key is None:
            return False
        time = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        m = hashlib.md5()
        m.update(dev_id.encode('utf-8'))
        m.update('createsession'.encode('utf-8'))
        m.update(key.encode('utf-8'))
        m.update(time.encode('utf-8'))
        str_hash = m.hexdigest()

        url = '/'.join([self.url_pc, 'createsessionJson', dev_id, str_hash, time])

        async with self.session.get(url, headers=self.header) as response:
            try:
                re = await response.json()
            except JSONDecodeError:
                # Response was not JSON. Could be bad/missing credentials.
                return False

        if re['ret_msg'] == "Approved":
            await self.conf.session_id.set(re['session_id'])
            return True
        # Response received, but request rejected. Could be bad credentials.
        return False

    async def test_session(self):

        dev_id = await self.conf.devid()
        key = await self.conf.authkey()
        session = await self.conf.session_id()
        if dev_id is None or key is None or session is None:
            return False
        time = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        m = hashlib.md5()
        m.update(dev_id.encode('utf-8'))
        m.update('testsession'.encode('utf-8'))
        m.update(key.encode('utf-8'))
        m.update(time.encode('utf-8'))
        str_hash = m.hexdigest()

        url = '/'.join([self.url_pc, 'testsessionJson', dev_id, str_hash, session, time])
        async with self.session.get(url, headers=self.header) as response:
            text = await response.text()

        if text.startswith('"Invalid'):
            return False
        elif text.startswith('"This'):
            return True
        # Response was something unexpected. Could be bad credentials,
        # or the Smite API has changed.
        return False
