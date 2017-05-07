import asyncio
import copy
import glob
import os
import os.path
import random
from typing import List

import aiohttp
import discord
from discord import FFmpegPCMAudio
from discord.ext import commands

import audioop
from core import checks
from core.utils import chat_formatting as cf
from core.utils import helpers

try:
    from gtts import gTTS
    gTTS_avail = True
except:
    gTTS_avail = False


class MuxedSource(discord.AudioSource):

    def __init__(self, source):
        self.sources = [source]

    def read(self):
        frames = []
        for source in self.sources:
            frame = source.read()
            if frame:
                frames.append(frame)

        if not frames:
            return None
        elif len(frames) == 1:
            return frames[0]
        elif len(frames) == 2:
            return audioop.add(frames[0], frames[1], 2)
        else:
            mux = audioop.add(frames[0], frames[1], 2)
            for frame in frames[2:]:
                mux = audioop.add(mux, frame, 2)
            return mux

    def mux(self, source):
        self.sources.append(source)


class Sfx:

    """Inject sound effects into a voice channel"""

    def __init__(self, bot):
        self.bot = bot
        self.json = helpers.JsonDB("data/settings.json")
        self.audio_players = {}
        self.sound_base = "cogs/sfx/data/sfx"
        self.temp_filepath = self.sound_base + "/temp/"
        self.language = "en"
        self.default_volume = 75
        self.tts_volume = 100
        self.master_queue = asyncio.Queue()
        # Combine slave_queues and slave_tasks into a single dict, maybe
        self.slave_queues = {}
        self.slave_tasks = {}
        self.queue_task = bot.loop.create_task(self._queue_manager())

    # Other cogs may use the following two functions as an easy API for sfx.
    # The function definitions probably violate every possible style guide,
    # But I like it :)
    def enqueue_tts(self, vchan: discord.VoiceChannel,
                           text: str,
                            vol: int=None,
                       priority: int=5,
                          tchan: discord.TextChannel=None,
                       language: str=None):
        if vol is None:
            vol = self.tts_volume
        if language is None:
            language = self.language
        tts = gTTS(text=text, lang=language)
        path = self.temp_filepath + ''.join(random.choice(
                   '0123456789ABCDEF') for i in range(12)) + ".mp3"
        tts.save(path)

        try:
            item = {'cid': vchan.id, 'path': path, 'vol': vol,
                    'priority': priority, 'delete': False, 'tchan': tchan}
            self.master_queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            return False

    def enqueue_sfx(self, vchan: discord.VoiceChannel,
                           path: str,
                            vol: int=None,
                       priority: int=5,
                         delete: bool=False,
                          tchan: discord.TextChannel=None):
        if vol is None:
            vol = self.default_volume
        try:
            item = {'cid': vchan.id, 'path': path, 'vol': vol,
                    'priority': priority, 'delete': delete, 'tchan': tchan}
            self.master_queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            return False

    async def _check_guild_settings(self, guild):
        if str(guild.id) not in self.json:
            await self.json.set(str(guild.id), {})

    def _list_sounds(self, server_id: str) -> List[str]:
        return sorted(
            [os.path.splitext(s)[0] for s in os.listdir(os.path.join(
                self.sound_base, server_id))],
            key=lambda s: s.lower())

    async def _slave_queue_manager(self, queue, g_id):
        guild = self.bot.get_guild(g_id)
        vc = None
        timeout_counter = 0
        while True:
            await asyncio.sleep(0.1)
            try:
                next_sound = queue.get_nowait()
                timeout_counter = 0
            except asyncio.QueueEmpty:
                if vc is not None and vc.is_playing():
                    timeout_counter = 0
                    continue
                timeout_counter += 1
                if timeout_counter > 3000 and vc is not None:
                    await vc.disconnect()
                    return
                continue

            c_id = next_sound['cid']
            channel = self.bot.get_channel(c_id)
            tchannel = next_sound['tchan']
            path = next_sound['path']
            vol = next_sound['vol']
            delete = next_sound['delete']
            vc = guild.voice_client

            if vc is None:
                # Voice not in use, we can connect to a voice channel
                try:
                    vc = await channel.connect()
                except asyncio.TimeoutError:
                    print("Could not join channel '{}'".format(channel.name))
                    if delete:
                        os.remove(path)
                    continue

                vc.play(MuxedSource(FFmpegPCMAudio(path)))

            elif not vc.is_playing():
                # Have voice client but it is not playing
                vc.play(MuxedSource(FFmpegPCMAudio(path)))
            else:
                # Have voice client and it is playing
                if not isinstance(vc.source, MuxedSource):
                    vc.source = MuxedSource(vc.source)
                vc.source.mux(FFmpegPCMAudio(path))

            # lol this won't work anymore, need to fix
            if delete:
                os.remove(path)

    @commands.command(pass_context=True, no_pm=True, aliases=['gtts'])
    async def tts(self, ctx, *text: str):
        """Play a TTS clip in your current channel"""

        if not gTTS_avail:
            await ctx.send("You do not have gTTS installed.")
            return
        vchan = ctx.author.voice.channel
        tchan = ctx.message.channel
        if vchan is None:
            await ctx.send("You are not connected to a voice channel.")
            return

        self.enqueue_tts(vchan, " ".join(text), tchan=tchan)

    @commands.command(no_pm=True, pass_context=True, aliases=['playsound'])
    async def sfx(self, ctx, soundname: str):
        """Plays the specified sound."""

        guild = ctx.message.guild
        vchan = ctx.author.voice.channel
        tchan = ctx.message.channel

        if vchan is None:
            await ctx.send("You are not connected to a voice channel.")
            return

        if str(guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(guild.id)))

        await self._check_guild_settings(guild)

        f = glob.glob(os.path.join(
            self.sound_base, str(guild.id), soundname + ".*"))

        if len(f) < 1:
            # No exact match, but try for a partial match
            f = glob.glob(os.path.join(self.sound_base, str(guild.id), soundname + "*"))

            if len(f) < 1:
                # There are still 0 possible sound matches
                await ctx.send(cf.error(
                    "Sound file not found. Try `{}allsfx` for a list.".format(
                        ctx.prefix)))
                return
            else:
                # There are one or more partial matches, pick one at random
                f[0] = random.choice(f)

        elif len(f) > 1:
            # There are identical file names, so this is still a valid error
            await ctx.send(cf.error(
                "There are {} sound files with the same name, but different"
                " extensions, and I can't deal with it. Please make filenames"
                " (excluding extensions) unique.".format(len(f))))
            return

        soundname = os.path.splitext(os.path.basename(f[0]))[0]
        if soundname in self.json[str(guild.id)]:
            if "volume" in self.json[str(guild.id)][soundname]:
                vol = self.json[str(guild.id)][soundname]["volume"]
            else:
                vol = self.default_volume
                self.json[str(guild.id)][soundname]["volume"] = vol
                await self.json.save()
        else:
            vol = self.default_volume
            self.json[str(guild.id)][soundname] = {"volume": vol}
            await self.json.save()

        self.enqueue_sfx(vchan, f[0], vol=vol, tchan=tchan)

    @commands.command(pass_context=True, aliases=['allsounds'])
    async def allsfx(self, ctx):
        """Sends a list of every sound in a PM."""

        guild = ctx.message.guild

        if str(guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(guild.id)))

        await self._check_guild_settings(guild)

        strbuffer = self._list_sounds(str(guild.id))

        if len(strbuffer) == 0:
            await ctx.send(cf.warning(
                "No sounds found. Use `{}addsfx` to add one.".format(
                    ctx.prefix)))
            return

        mess = "```"
        for line in strbuffer:
            if len(mess) + len(line) + 4 < 2000:
                mess += "\n" + line
            else:
                mess += "```"
                await ctx.message.author.dm_channel.send(mess)
                mess = "```" + line
        if mess != "":
            mess += "```"
            await ctx.message.author.dm_channel.send(mess)

        await ctx.send("Check your PMs!")

    @commands.command(no_pm=True, pass_context=True, aliases=['addsound'])
    @checks.is_owner()
    async def addsfx(self, ctx, link: str=None):
        """Adds a new sound.

        Either upload the file as a Discord attachment and make your comment
        "[p]addsfx", or use "[p]addsfx direct-URL-to-file".
        """

        guild = ctx.message.guild

        if str(guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(guild.id)))

        await self._check_guild_settings(guild)

        attach = ctx.message.attachments
        if len(attach) > 1 or (attach and link):
            await ctx.send(
                cf.error("Please only add one sound at a time."))
            return

        url = ""
        filename = ""
        if attach:
            a = attach[0]
            url = a["url"]
            filename = a["filename"]
        elif link:
            url = "".join(link)
            filename = os.path.basename(
                "_".join(url.split()).replace("%20", "_"))
        else:
            await ctx.send(
                cf.error("You must provide either a Discord attachment or a"
                         " direct link to a sound."))
            return

        filepath = os.path.join(self.sound_base, str(guild.id), filename)

        if os.path.splitext(filename)[0] in self._list_sounds(str(guild.id)):
            await ctx.send(
                cf.error("A sound with that filename already exists."
                         " Please change the filename and try again."))
            return

        async with aiohttp.request("GET", url) as new_sound:
            f = open(filepath, "wb")
            f.write(await new_sound.read())
            f.close()

        self.json[str(guild.id)][
            os.path.splitext(filename)[0]] = {"volume": self.default_volume}
        await self.json.save()

        await ctx.send(
            cf.info("Sound {} added.".format(os.path.splitext(filename)[0])))

    @commands.command(no_pm=True, pass_context=True, aliases=['soundvol'])
    @checks.is_owner()
    async def sfxvol(self, ctx, soundname: str, percent: int=None):
        """Sets the volume for the specified sound.

        If no value is given, the current volume for the sound is printed.
        """

        guild = ctx.message.guild

        if str(guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(guild.id)))

        await self._check_guild_settings(guild)

        f = glob.glob(os.path.join(self.sound_base, str(guild.id),
                                   soundname + ".*"))
        if len(f) < 1:
            await ctx.send(cf.error(
                "Sound file not found. Try `{}allsfx` for a list.".format(
                    ctx.prefix)))
            return
        elif len(f) > 1:
            await ctx.send(cf.error(
                "There are {} sound files with the same name, but different"
                " extensions, and I can't deal with it. Please make filenames"
                " (excluding extensions) unique.".format(len(f))))
            return

        if soundname not in self.json[str(guild.id)]:
            self.json[str(guild.id)][soundname] = {"volume": self.default_volume}
            await self.json.save()

        if percent is None:
            await ctx.send("Volume for {} is {}.".format(
                soundname, self.json[str(guild.id)][soundname]["volume"]))
            return

        self.json[str(guild.id)][soundname]["volume"] = percent
        await self.json.save()

        await ctx.send("Volume for {} set to {}.".format(soundname,
                                                         percent))

    @commands.command(no_pm=True, pass_context=True, aliases=['delsound'])
    @checks.is_owner()
    async def delsfx(self, ctx, soundname: str):
        """Deletes an existing sound."""

        guild = ctx.message.guild

        if str(guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(guild.id)))

        f = glob.glob(os.path.join(self.sound_base, str(guild.id),
                                   soundname + ".*"))
        if len(f) < 1:
            await ctx.send(cf.error(
                "Sound file not found. Try `{}allsfx` for a list.".format(
                    ctx.prefix)))
            return
        elif len(f) > 1:
            await ctx.send(cf.error(
                "There are {} sound files with the same name, but different"
                " extensions, and I can't deal with it. Please make filenames"
                " (excluding extensions) unique.".format(len(f))))
            return

        os.remove(f[0])

        if soundname in self.json[str(guild.id)]:
            del self.json[str(guild.id)][soundname]
            await self.json.save()

        await ctx.send(cf.info("Sound {} deleted.".format(soundname)))

    @commands.command(no_pm=True, pass_context=True, aliases=['getsound'])
    async def getsfx(self, ctx, soundname: str):
        """Gets the given sound."""

        guild = ctx.message.guild

        if str(guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(guild.id)))

        f = glob.glob(os.path.join(self.sound_base, str(guild.id),
                                   soundname + ".*"))

        if len(f) < 1:
            await ctx.send(cf.error(
                "Sound file not found. Try `{}allsfx` for a list.".format(
                    ctx.prefix)))
            return
        elif len(f) > 1:
            await ctx.send(cf.error(
                "There are {} sound files with the same name, but different"
                " extensions, and I can't deal with it. Please make filenames"
                " (excluding extensions) unique.".format(len(f))))
            return

        await ctx.send(file=discord.File(f[0]))

    async def _queue_manager(self):
        await self.bot.wait_until_ready()
        while True:
            await asyncio.sleep(0.1)
            # First check for empty queues
            for slave in self.slave_tasks:
                if (self.slave_tasks[slave] is not None and
                        self.slave_tasks[slave].done()):
                    # Task is not completed until:
                    # Slave queue is empty, and timeout is reached /
                    # vc disconnected / someone else stole vc
                    self.slave_tasks[slave] = None
                    self.slave_queues[slave] = None

            # Next we can check for new items
            item = None
            try:
                item = self.master_queue.get_nowait()
            except asyncio.QueueEmpty:
                continue
            # This does not really check to make sure the queued item
            # is valid. Should probably check that with the enqueue function.
            channel = self.bot.get_channel(item['cid'])
            guild = channel.guild
            g_id = str(guild.id)
            priority = item['priority']

            if self.slave_tasks.get(g_id) is None:
                # Create slave queue
                queue = asyncio.Queue(maxsize=20)
                self.slave_queues[g_id] = queue
                self.slave_tasks[g_id] = self.bot.loop.create_task(
                                            self._slave_queue_manager(queue,
                                                                      guild.id))
            try:
                self.slave_queues[g_id].put_nowait(item)
            except asyncio.QueueFull:
                # It's possible to add a way to handle full queue situation.
                pass
        # Need to add cancelled task exception handler?

    def __unload(self):
        self.queue_task.cancel()
        for slave in self.slave_tasks:
            if self.slave_tasks[slave] is not None:
                self.slave_tasks[slave].cancel()
