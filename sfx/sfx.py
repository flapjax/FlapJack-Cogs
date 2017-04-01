import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks, chat_formatting as cf
from typing import List
import random
import os
import asyncio
import copy
import random
import os.path
import aiohttp
import glob

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


class SFX:

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
        self.queue = {}
        self.server_tasks = {}
        self.vc_buffers = {}
        self.master_queue = asyncio.Queue()
        # combine these 2
        self.slave_queues = {}
        self.slave_tasks = {}
        self.queue_task = bot.loop.create_task(self.queue_manager())

    def list_sounds(self, server_id: str) -> List[str]:
        return sorted(
            [os.path.splitext(s)[0] for s in os.listdir(os.path.join(
                self.sound_base, server_id))],
            key=lambda s: s.lower())

    async def change_and_resume(self, vc, channel: discord.Channel):
        await vc.move_to(channel)
        vc.audio_player.resume()

    async def enqueue_tts(self, vchan, text: str):

        server = vchan.server
        tts = gTTS(text=text, lang=self.language)

        path = self.temp_filepath + ''.join(random.choice('0123456789ABCDEF') for i in range(12)) + ".mp3"
        tts.save(path)

        try:
            item = {'cid': vchan.id, 'path': path, 'vol': self.tts_volume, 'priority': 1, 'delete': True}
            self.master_queue.put_nowait(item)
        except asyncio.QueueFull:
            print('queue was full')
            # put an error message here you lazy ass
            return

    async def enqueue_sfx(self, vchan, path, vol: int):

        server = vchan.server
        path = path

        if server.id not in self.queue:
            # Create an async queue!
            self.queue[server.id] = asyncio.PriorityQueue(maxsize=5)
        try:
            item = {'cid': vchan.id, 'path': path, 'vol': vol, 'priority': 1, 'delete': False}
            self.master_queue.put_nowait(item)
        except asyncio.QueueFull:
            print('queue was full')
            # put an error message here you lazy ass
            return

    def revive_audio(self, sid):
        server = self.bot.get_server(sid)
        vc_current = self.bot.voice_client_in(server)
        vc_current.audio_player = self.vc_buffers[sid].vc_ap
        vchan_old = self.vc_buffers[sid].vchan
        self.vc_buffers[sid] = None
        if vc_current.channel.id != vchan_old.id:
            self.bot.loop.create_task(self.change_and_resume(vc_current, vchan_old))
        else:
            vc_current.audio_player.resume()

    def suspend_audio(self, vc, cid):
        channel = self.bot.get_channel(cid)
        vc.audio_player.pause()
        self.vc_buffers[channel.server.id] = SuspendedPlayer(vc)

    async def play_next_sound(self, queue, sid):
        server = self.bot.get_server(sid)
        timeout_counter = 0
        while True:
            # Hopefully this is also enough delay to not miss the first queued item.
            #print('hi this is slave task reporting in')
            await asyncio.sleep(0.1)
            try:
                next_sound = queue.get_nowait()
                # New sound was found, restart the timer!
                timeout_counter = 0
                #next_sound = self.queue[sid][0]
                #print('ok this is slave I found a thing')
            except asyncio.QueueEmpty:
                #print('my slave queue was empty')
                # Start the wait for disconnect task here?
                #self.bot.loop.create_task(self.check_for_disconnect(server))
                # or, start a timer and take the place of check for disconnect
                timeout_counter += 1
                # give back control to any prior vcs
                if self.vc_buffers.get(sid) is not None:
                    self.revive_audio(sid)
                # Any way to check if this vc = our vc?
                vc = self.bot.voice_client_in(server)
                if vc is not None:
                    if hasattr(vc, 'audio_player') and vc.audio_player.is_playing():
                        # This should never happen unless some other cog has stolen vc
                        # so its safe to kill the task
                        return
                else:
                    # Something else has shit on our voice client, so its also safe
                    # to kill the task
                    return
                # If we're here, queue is still empty, a voice client exists
                # It's probably ours and we're responsible for disconnecting it
                # Assuming 0.1 second sleep -> 5 sec disconnect
                timeout_counter += 1
                if timeout_counter > 50:
                    # Do the disconnect thing
                    await vc.disconnect()
                    return
                # We made it here, its safe to start another iteration
                continue

            # item looks like: item = {'cid': vchan.id, 'path': path, 'vol': vol, 'delete': False}
            #print('slave here, about to get the attributes for the thing')
            # It's pretty much ok to block from here on out.
            cid = next_sound['cid']
            channel = self.bot.get_channel(cid)
            path = next_sound['path']
            vol = next_sound['vol']
            delete = next_sound['delete']
            #print('ok got all the attributes')
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
                    #return

                # TODO: ffmpeg options
                options = "-filter \"volume=volume={}\"".format(str(vol/100))
                self.audio_players[sid] = vc.create_ffmpeg_player(
                    path, options=options)
                self.audio_players[sid].start()

            else:
                # We already have a client, use it
                if hasattr(vc, 'audio_player') and vc.audio_player.is_playing():
                    self.suspend_audio(vc, cid)

                if vc.channel.id != cid:
                    # It looks like this does not raise an exception if bot
                    # fails to join channel. Need to add a manual check.
                    await vc.move_to(channel)

                options = "-filter \"volume=volume={}\"".format(str(vol/100))
                self.audio_players[sid] = vc.create_ffmpeg_player(
                    path, options=options)
                self.audio_players[sid].start()

            # Wait for current sound to finish playing
            while self.audio_players[sid].is_playing():
                await asyncio.sleep(0.1)

            if delete:
                os.remove(path)


    @commands.command(pass_context=True, no_pm=True, aliases=['gtts'])
    async def tts(self, ctx, *text: str):
        """Play a TTS clip in your current channel"""

        if not gTTS_avail:
            await self.bot.say("You do not have gTTS installed.")
            return
        vchan = ctx.message.author.voice_channel
        if vchan is None:
            await self.bot.say("You are not connected to a voice channel.")

        await self.enqueue_tts(vchan, " ".join(text))

    @commands.command(no_pm=True, pass_context=True, aliases=['playsound'])
    async def sfx(self, ctx, soundname: str):
        """Plays the specified sound."""

        server = ctx.message.server
        vchan = ctx.message.author.voice_channel

        if vchan is None:
            await self.bot.say("You are not connected to a voice channel.")

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

        await self.enqueue_sfx(vchan, f[0], vol)

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

        strbuffer = self.list_sounds(server.id)

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

        if os.path.splitext(filename)[0] in self.list_sounds(server.id):
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

    async def queue_manager(self):
        await self.bot.wait_until_ready()
        while True:
            # Experimental delay to reduce overhead
            await asyncio.sleep(0.1)
            #print('loop')
            # First check for empty queues to be destroyed
            for slave in self.slave_tasks:
                # Task is only done when slave queue is empty
                if self.slave_tasks[slave] is not None and self.slave_tasks[slave].done():
                    # Task is not completed until:
                    # Slave queue is empty, and timeout is reached / vc disconnected / someone else stole vc
                    self.slave_tasks[slave] = None
                    self.slave_queues[slave] = None

            # Next we can check for new items
            item = None
            try:
                item = self.master_queue.get_nowait()
                #print('something found in master queue')
            except asyncio.QueueEmpty:
                # If it's empty, we're done, move along
                #print('master queue was empty')
                continue
            #print(str(item))
            # Must have been an item in queue
            # Need to handle integrity checking of the item, probable in enqueue function
            # So assume this is a good item
            channel = self.bot.get_channel(item['cid'])
            #print(str(channel))
            server = channel.server
            #print(str(server))
            sid = server.id
            #print(sid)
            priority = item['priority']

            #print(str(priority))

            if self.slave_tasks.get(sid) is None:
                # Create slave. Find out if need loop
                #print('creating slave queue')
                queue = asyncio.Queue(maxsize=10)
                self.slave_queues[sid] = queue
                # Start the task to handle this queue
                # Play next sound should be renamed to some thing like slave queue task
                #print('slave queue was created')
                self.slave_tasks[sid] = self.bot.loop.create_task(self.play_next_sound(queue, sid))
                #print('slave task was launched')

            try:
                self.slave_queues[sid].put_nowait(item)
                #Sprint('put item in slave queue')
            except asyncio.QueueFull:
                print('queue was full')
                # await self.bot.send_message(channel, 'sfx queue is full! stop spamming! :c')
                # put a better error message here you lazy ass
                # will need to propogate this back to whoever tried to enqueue

        # Do we need an asyncio cancelled error exception handler? Dunno!

    def __unload(self):
        self.queue_task.cancel()
        for slave in self.slave_queues:
            if self.slave_queues[slave] is not None:
                self.slave_queues[slave].cancel()


def check_folders():
    folder = "data/sfx/temp"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    f = "data/sfx/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating data/playsound/settings.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(SFX(bot))
