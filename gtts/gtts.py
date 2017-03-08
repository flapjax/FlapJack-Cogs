import discord
from discord.ext import commands
import os
import asyncio

try:
    from gtts import gTTS
    gTTSAvailable = True
except:
    gTTSAvailable = False


class GTTS:

    """Google TTS for Discord"""

    def __init__(self, bot):
        self.bot = bot
        self.audio_players = {}
        self.temp_filepath = "data/gtts/temp.mp3"

    # Using code from tmerc's playsound for proof of concept
    def voice_channel_full(self, voice_channel: discord.Channel) -> bool:
        return (voice_channel.user_limit != 0 and
                len(voice_channel.voice_members) >= voice_channel.user_limit)

    def voice_connected(self, server: discord.Server) -> bool:
        return self.bot.is_voice_connected(server)

    def voice_client(self, server: discord.Server) -> discord.VoiceClient:
        return self.bot.voice_client_in(server)

    async def _join_voice_channel(self, ctx: commands.Context):
        channel = ctx.message.author.voice_channel
        if channel:
            await self.bot.join_voice_channel(channel)

    async def _leave_voice_channel(self, server: discord.Server):
        if not self.voice_connected(server):
            return
        voice_client = self.voice_client(server)

        if server.id in self.audio_players:
            self.audio_players[server.id].stop()
        await voice_client.disconnect()

    async def wait_for_disconnect(self, server: discord.Server):
        while not self.audio_players[server.id].is_done():
            await asyncio.sleep(0.01)
        await self._leave_voice_channel(server)

    async def sound_init(self, ctx: commands.Context, path: str, vol: int):
        server = ctx.message.server
        options = "-filter \"volume=volume={}\"".format(str(vol/100))
        voice_client = self.voice_client(server)
        self.audio_players[server.id] = voice_client.create_ffmpeg_player(
            path, options=options)

    async def sound_play(self, ctx: commands.Context, p: str, vol: int):
        server = ctx.message.server
        if not ctx.message.author.voice_channel:
            await self.bot.reply(
                cf.warning("You need to join a voice channel first."))
            return

        if self.voice_channel_full(ctx.message.author.voice_channel):
            return

        if not ctx.message.channel.is_private:
            if self.voice_connected(server):
                if server.id not in self.audio_players:
                    await self.sound_init(ctx, p, vol)
                    self.audio_players[server.id].start()
                    await self.wait_for_disconnect(server)
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(ctx, p, vol)
                    self.audio_players[server.id].start()
                    await self.wait_for_disconnect(server)
            else:
                await self._join_voice_channel(ctx)
                if server.id not in self.audio_players:
                    await self.sound_init(ctx, p, vol)
                    self.audio_players[server.id].start()
                    await self.wait_for_disconnect(server)
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(ctx, p, vol)
                    self.audio_players[server.id].start()
                    await self.wait_for_disconnect(server)

    async def say_tts(self, ctx, text: str):
        tts = gTTS(text=text, lang='en')
        tts.save(self.temp_filepath)
        await self.sound_play(ctx, self.temp_filepath, 100)
        os.remove(self.temp_filepath)

    @commands.command(pass_context=True, no_pm=True)
    async def gtts(self, ctx, *text: str):
        """Play a TTS clip in your current channel"""

        await self.say_tts(ctx, " ".join(text))


def check_folders():
    folder = "data/gtts"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def setup(bot):
    check_folders()
    if gTTSAvailable:
        bot.add_cog(GTTS(bot))
    else:
        raise RuntimeError("You need to run `pip3 install gTTS`")
