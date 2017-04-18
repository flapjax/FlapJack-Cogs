import asyncio
import copy
import glob
import os
import os.path
import random
from typing import List

import aiohttp
import discord
from discord.ext import commands

from .utils import chat_formatting as cf
from .utils import checks
from .utils.dataIO import dataIO

try:
    from gtts import gTTS
    gTTS_avail = True
except:
    gTTS_avail = False

# A very special thanks to two people:
# First, irdumb, for sharing his past work on sfx.
# Last, but certainly not least, tmerc. This would not exist without him.
# His sound effects cog was the thing that got me involved with Red,
# And the sound file management functions in this cog were written by him.
# Without the help of these people,
# I would be light years behind where I am now :)


class SuspendedPlayer:

    def __init__(self, voice_client):
        self.vchan = voice_client.channel
        self.vc_ap = voice_client.audio_player


class Sfx:

    """Inject sound effects into a voice channel"""

    def __init__(self, bot):
        self.bot = bot
        self.audio_players = {}
        self.sound_base = "data/sfx"
        self.temp_filepath = self.sound_base + "/temp/"
        self.settings_path = "data/sfx/settings.json"
        self.settings = dataIO.load_json(self.settings_path)
        self.language = "en"
        self.default_volume = 75
        self.tts_volume = 100
        self.vc_buffers = {}
        self.master_queue = asyncio.Queue()
        # Combine slave_queues and slave_tasks into a single dict, maybe
        self.slave_queues = {}
        self.slave_tasks = {}
        self.queue_task = bot.loop.create_task(self._queue_manager())

    # Other cogs may use the following two functions as an easy API for sfx.
    # The function definitions probably violate every possible style guide,
    # But I like it :)
    def enqueue_tts(self, vchan: discord.Channel,
                           text: str,
                            vol: int=None,
                       priority: int=5,
                          tchan: discord.Channel=None,
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
                    'priority': priority, 'delete': True, 'tchan': tchan}
            self.master_queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            return False

    def enqueue_sfx(self, vchan: discord.Channel,
                           path: str,
                            vol: int=None,
                       priority: int=5,
                         delete: bool=False,
                          tchan: discord.Channel=None):
        if vol is None:
            vol = self.default_volume
        try:
            item = {'cid': vchan.id, 'path': path, 'vol': vol,
                    'priority': priority, 'delete': delete, 'tchan': tchan}
            self.master_queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            return False

    def _list_sounds(self, server_id: str) -> List[str]:
        return sorted(
            [os.path.splitext(s)[0] for s in os.listdir(os.path.join(
                self.sound_base, server_id))],
            key=lambda s: s.lower())

    async def _change_and_resume(self, vc, channel: discord.Channel):
        await vc.move_to(channel)
        vc.audio_player.resume()

    def _revive_audio(self, sid):
        server = self.bot.get_server(sid)
        vc_current = self.bot.voice_client_in(server)
        vc_current.audio_player = self.vc_buffers[sid].vc_ap
        vchan_old = self.vc_buffers[sid].vchan
        self.vc_buffers[sid] = None
        if vc_current.channel.id != vchan_old.id:
            self.bot.loop.create_task(self._change_and_resume(vc_current,
                                                              vchan_old))
        else:
            vc_current.audio_player.resume()

    def _suspend_audio(self, vc, cid):
        channel = self.bot.get_channel(cid)
        vc.audio_player.pause()
        self.vc_buffers[channel.server.id] = SuspendedPlayer(vc)

    async def _slave_queue_manager(self, queue, sid):
        server = self.bot.get_server(sid)
        timeout_counter = 0
        audio_cog = self.bot.get_cog('Audio')
        while True:
            await asyncio.sleep(0.1)
            try:
                next_sound = queue.get_nowait()
                # New sound was found, restart the timer!
                timeout_counter = 0
            except asyncio.QueueEmpty:
                timeout_counter += 1
                # give back control to any prior voice clients
                if self.vc_buffers.get(sid) is not None:
                    self._revive_audio(sid)
                vc = self.bot.voice_client_in(server)
                if vc is not None:
                    if (hasattr(vc, 'audio_player') and
                            vc.audio_player.is_playing()):
                        # This should not happen unless some other cog has
                        # stolen voice client so its safe to kill the task
                        return
                else:
                    # Something else killed our voice client, 
                    # so its also safe to kill the task
                    return
                # If we're here, we still have control of the voice client,
                # So it's our job to wait for disconnect
                timeout_counter += 1
                if timeout_counter > 10:
                    await vc.disconnect()
                    return
                continue

            # This function can block itself from here on out. Our only job
            # is to play the sound and watch for Audio stealing back control
            cid = next_sound['cid']
            channel = self.bot.get_channel(cid)
            path = next_sound['path']
            vol = next_sound['vol']
            delete = next_sound['delete']
            vc = self.bot.voice_client_in(server)

            if vc is None:
                # Voice not in use, we can connect to a voice channel
                try:
                    vc = await self.bot.join_voice_channel(channel)
                except asyncio.TimeoutError:
                    print("Could not join channel '{}'".format(channel.name))
                    if delete:
                        os.remove(path)
                    continue

                options = "-filter \"volume=volume={}\"".format(str(vol/100))
                self.audio_players[sid] = vc.create_ffmpeg_player(
                    path, options=options)
                self.audio_players[sid].start()

            else:
                # We already have a client, use it
                if (hasattr(vc, 'audio_player') and
                        vc.audio_player.is_playing()):
                    self._suspend_audio(vc, cid)

                if vc.channel.id != cid:
                    # It looks like this does not raise an exception if bot
                    # fails to join channel. Need to add a manual check.
                    await vc.move_to(channel)

                options = "-filter \"volume=volume={}\"".format(str(vol/100))
                self.audio_players[sid] = vc.create_ffmpeg_player(
                    path, options=options)
                self.audio_players[sid].start()

            # Wait for current sound to finish playing
            # Watch for audio interrupts
            while self.audio_players[sid].is_playing():
                await asyncio.sleep(0.1)
                # if audio_cog is not None:
                audio_cog.voice_client(server)
                if vc is not None:
                    if (hasattr(vc, 'audio_player') and
                            vc.audio_player.is_playing()):
                        # We were interrupted, how rude :c
                        # Let's be polite and destroy our queue and go home.
                        self.audio_players[sid].stop()
                        return

            if delete:
                os.remove(path)

    @commands.command(pass_context=True, no_pm=True, aliases=['gtts'])
    @commands.cooldown(1, 1, commands.BucketType.server)
    async def tts(self, ctx, *text: str):
        """Play a TTS clip in your current channel"""

        if not gTTS_avail:
            await self.bot.say("You do not have gTTS installed.")
            return
        vchan = ctx.message.author.voice_channel
        if vchan is None:
            await self.bot.say("You are not connected to a voice channel.")
            return

        self.enqueue_tts(vchan, " ".join(text))

    @commands.command(no_pm=True, pass_context=True, aliases=['playsound'])
    @commands.cooldown(1, 1, commands.BucketType.server)
    async def sfx(self, ctx, soundname: str):
        """Plays the specified sound."""

        server = ctx.message.server
        vchan = ctx.message.author.voice_channel

        if vchan is None:
            await self.bot.say("You are not connected to a voice channel.")
            return

        if server.id not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, server.id))

        if server.id not in self.settings:
            self.settings[server.id] = {}
            dataIO.save_json(self.settings_path, self.settings)

        f = glob.glob(os.path.join(
            self.sound_base, server.id, soundname + ".*"))

        if len(f) < 1:
            # No exact match, but try for a partial match
            f = glob.glob(os.path.join(self.sound_base, server.id, soundname + "*"))

            if len(f) < 1:
                # There are still 0 possible sound matches
                await self.bot.say(cf.error(
                    "Sound file not found. Try `{}allsfx` for a list.".format(
                        ctx.prefix)))
                return
            else:
                # There are one or more partial matches, pick one at random
                f[0] = random.choice(f)

        elif len(f) > 1:
            # There are identical file names, so this is still a valid error
            await self.bot.say(cf.error(
                "There are {} sound files with the same name, but different"
                " extensions, and I can't deal with it. Please make filenames"
                " (excluding extensions) unique.".format(len(f))))
            return

        soundname = os.path.splitext(os.path.basename(f[0]))[0]
        if soundname in self.settings[server.id]:
            if "volume" in self.settings[server.id][soundname]:
                vol = self.settings[server.id][soundname]["volume"]
            else:
                vol = self.default_volume
                self.settings[server.id][soundname]["volume"] = vol
                dataIO.save_json(self.settings_path, self.settings)
        else:
            vol = self.default_volume
            self.settings[server.id][soundname] = {"volume": vol}
            dataIO.save_json(self.settings_path, self.settings)

        self.enqueue_sfx(vchan, f[0], vol=vol)

    @commands.command(pass_context=True, aliases=['allsounds'])
    async def allsfx(self, ctx):
        """Sends a list of every sound in a PM."""

        await self.bot.type()

        server = ctx.message.server

        if server.id not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, server.id))

        if server.id not in self.settings:
            self.settings[server.id] = {}
            dataIO.save_json(self.settings_path, self.settings)

        strbuffer = self._list_sounds(server.id)

        if len(strbuffer) == 0:
            await self.bot.say(cf.warning(
                "No sounds found. Use `{}addsfx` to add one.".format(
                    ctx.prefix)))
            return

        mess = "```"
        for line in strbuffer:
            if len(mess) + len(line) + 4 < 2000:
                mess += "\n" + line
            else:
                mess += "```"
                await self.bot.whisper(mess)
                mess = "```" + line
        if mess != "":
            mess += "```"
            await self.bot.whisper(mess)

        await self.bot.reply("Check your PMs!")

    @commands.command(no_pm=True, pass_context=True, aliases=['addsound'])
    @checks.mod_or_permissions(administrator=True)
    async def addsfx(self, ctx, link: str=None):
        """Adds a new sound.

        Either upload the file as a Discord attachment and make your comment
        "[p]addsfx", or use "[p]addsfx direct-URL-to-file".
        """

        await self.bot.type()

        server = ctx.message.server

        if server.id not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, server.id))

        if server.id not in self.settings:
            self.settings[server.id] = {}
            dataIO.save_json(self.settings_path, self.settings)

        attach = ctx.message.attachments
        if len(attach) > 1 or (attach and link):
            await self.bot.say(
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
            await self.bot.say(
                cf.error("You must provide either a Discord attachment or a"
                         " direct link to a sound."))
            return

        filepath = os.path.join(self.sound_base, server.id, filename)

        if os.path.splitext(filename)[0] in self._list_sounds(server.id):
            await self.bot.say(
                cf.error("A sound with that filename already exists."
                         " Please change the filename and try again."))
            return

        async with aiohttp.get(url) as new_sound:
            f = open(filepath, "wb")
            f.write(await new_sound.read())
            f.close()

        self.settings[server.id][
            os.path.splitext(filename)[0]] = {"volume": self.default_volume}
        dataIO.save_json(self.settings_path, self.settings)

        await self.bot.say(
            cf.info("Sound {} added.".format(os.path.splitext(filename)[0])))

    @commands.command(no_pm=True, pass_context=True, aliases=['soundvol'])
    @checks.mod_or_permissions(administrator=True)
    async def sfxvol(self, ctx, soundname: str, percent: int=None):
        """Sets the volume for the specified sound.

        If no value is given, the current volume for the sound is printed.
        """

        await self.bot.type()

        server = ctx.message.server

        if server.id not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, server.id))

        if server.id not in self.settings:
            self.settings[server.id] = {}
            dataIO.save_json(self.settings_path, self.settings)

        f = glob.glob(os.path.join(self.sound_base, server.id,
                                   soundname + ".*"))
        if len(f) < 1:
            await self.bot.say(cf.error(
                "Sound file not found. Try `{}allsfx` for a list.".format(
                    ctx.prefix)))
            return
        elif len(f) > 1:
            await self.bot.say(cf.error(
                "There are {} sound files with the same name, but different"
                " extensions, and I can't deal with it. Please make filenames"
                " (excluding extensions) unique.".format(len(f))))
            return

        if soundname not in self.settings[server.id]:
            self.settings[server.id][soundname] = {"volume": self.default_volume}
            dataIO.save_json(self.settings_path, self.settings)

        if percent is None:
            await self.bot.say("Volume for {} is {}.".format(
                soundname, self.settings[server.id][soundname]["volume"]))
            return

        self.settings[server.id][soundname]["volume"] = percent
        dataIO.save_json(self.settings_path, self.settings)

        await self.bot.say("Volume for {} set to {}.".format(soundname,
                                                               percent))

    @commands.command(no_pm=True, pass_context=True, aliases=['delsound'])
    @checks.mod_or_permissions(administrator=True)
    async def delsfx(self, ctx, soundname: str):
        """Deletes an existing sound."""

        await self.bot.type()

        server = ctx.message.server

        if server.id not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, server.id))

        f = glob.glob(os.path.join(self.sound_base, server.id,
                                   soundname + ".*"))
        if len(f) < 1:
            await self.bot.say(cf.error(
                "Sound file not found. Try `{}allsfx` for a list.".format(
                    ctx.prefix)))
            return
        elif len(f) > 1:
            await self.bot.say(cf.error(
                "There are {} sound files with the same name, but different"
                " extensions, and I can't deal with it. Please make filenames"
                " (excluding extensions) unique.".format(len(f))))
            return

        os.remove(f[0])

        if soundname in self.settings[server.id]:
            del self.settings[server.id][soundname]
            dataIO.save_json(self.settings_path, self.settings)

        await self.bot.say(cf.info("Sound {} deleted.".format(soundname)))

    @commands.command(no_pm=True, pass_context=True, aliases=['getsound'])
    async def getsfx(self, ctx, soundname: str):
        """Gets the given sound."""

        await self.bot.type()

        server = ctx.message.server

        if server.id not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, server.id))

        f = glob.glob(os.path.join(self.sound_base, server.id,
                                   soundname + ".*"))

        if len(f) < 1:
            await self.bot.say(cf.error(
                "Sound file not found. Try `{}allsfx` for a list.".format(
                    ctx.prefix)))
            return
        elif len(f) > 1:
            await self.bot.say(cf.error(
                "There are {} sound files with the same name, but different"
                " extensions, and I can't deal with it. Please make filenames"
                " (excluding extensions) unique.".format(len(f))))
            return

        await self.bot.upload(f[0])

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
            server = channel.server
            sid = server.id
            priority = item['priority']

            if self.slave_tasks.get(sid) is None:
                # Create slave queue
                queue = asyncio.Queue(maxsize=20)
                self.slave_queues[sid] = queue
                self.slave_tasks[sid] = self.bot.loop.create_task(
                                            self._slave_queue_manager(queue,
                                                                        sid))
            try:
                self.slave_queues[sid].put_nowait(item)
            except asyncio.QueueFull:
                # It's possible to add a way to handle full queue situation.
                pass
        # Need to add cancelled task exception handler?

    def __unload(self):
        self.queue_task.cancel()
        for slave in self.slave_tasks:
            if self.slave_tasks[slave] is not None:
                self.slave_tasks[slave].cancel()


def check_folders():
    folder = "data/sfx/temp"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)
    files = glob.glob(folder + '/*')
    for f in files:
        try:
            os.remove(f)
        except PermissionError:
            print("Could not delete file '{}'. "
                  "Check your file permissions.".format(f))


def check_files():
    f = "data/sfx/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating data/playsound/settings.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Sfx(bot))
