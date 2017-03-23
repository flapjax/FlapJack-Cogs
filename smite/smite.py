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
# Believe these are not needed. Check in next revision
import re
import asyncio


class Smite:

    """Smite Game Data"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/smite/settings.json"
        self.settings = dataIO.load_json(self.settings_path)
        self.url_pc = 'http://api.smitegame.com/smiteapi.svc'
        self.smite_abbr = 'xxxx'
        self.header = {"User-Agent": "Put User Agent Here/1.0"}

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

    @smite.command(name="open", pass_context=True)
    @checks.is_owner()
    async def _open_smite(self, ctx):
        """Open an API session. Troubleshooting only"""

        await self.bot.say("creating session...")

        if await self.create_session():
            await self.bot.say("successful!")
        else:
            await self.bot.say("unsuccessful!")

    @smite.command(name="stats", pass_context=True)
    @checks.is_owner()
    async def _stats_smite(self, ctx, name: str=None):
        """Smite stats for your in game name.
        If name is ommitted, bot will use your name if stored.

        Example: [p]smite stats CoolDude
        """

        uid = ctx.message.author.id

        if name is None:
            if uid in self.settings['smitenames']:
                name = self.settings['smitenames'][uid]
            else:
                await self.bot.say('You did not provide a name '
                                   'and I do not have one stored for you.')
                return

        await self.bot.say("testing session...")

        if await self.test_session():
            await self.bot.say("successful!")
        else:
            await self.bot.say("unsuccessful!")
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

        #msg = 'response:\n'
        #for key in re[0]:
        #    msg += "key: {}, value: {}\n".format(key, re[0][key])
        #await self.bot.say(msg)

        icon_url = 'https://hzweb.hi-rezgame.net/hirezstudios/wp-content/uploads/2015/12/smite-logo-hzcom1.png'
        url = 'https://www.smitegame.com/player-stats/?set_platform_preference=pc&player-name=' + name

        stats = ''.join(['**Wins:** ', str(re[0]['Wins']),
                         '\n**Losses:** ', str(re[0]['Losses']),
                         '\n**Leaves:** ', str(re[0]['Leaves']),
                         '\n**Mastery:** ', str(re[0]['MasteryLevel'])])

        embed = discord.Embed(title='Team: ' + re[0]['Team_Name'], color=0x4E66A3)
        embed.set_author(name=re[0]['Name'], url=url, icon_url=icon_url)
        embed.set_thumbnail(url=re[0]['Avatar_URL'])
        embed.add_field(name='Smite Stats', value=stats, inline=False)
        await self.bot.say(embed=embed)

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
                    await self.bot.say('No response from API. '
                                       'Did my owner input credentials?')
                    return False

        #msg = 'response:\n'
        #for key in re:
        #    msg += "key: {}, value: {}\n".format(key, re[key])
        #await self.bot.say(msg)

        if re['ret_msg'] == "Approved":
            self.settings['session_id'] = re['session_id']
            dataIO.save_json(self.settings_path, self.settings)

            return True

        await self.bot.say('API request rejected. '
                           'Did my owner input valid credentials?')

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
                #await self.bot.say(await resp.text())
                text = await resp.text()

        if text.startswith('"Invalid'):
            await self.bot.say("Session is no longer valid.")
            return False
        elif text.startswith('"This'):
            await self.bot.say("Session is still valid.")
            return True
        await self.bot.say('No response from API. '
                           'Did my owner input credentials?')
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
