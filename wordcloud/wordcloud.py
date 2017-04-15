import asyncio
import os

import numpy as np
from __main__ import send_cmd_help
from discord.ext import commands
from discord.ext.commands import formatter
from PIL import Image
from wordcloud import WordCloud as WCloud
from wordcloud import ImageColorGenerator

from .utils.dataIO import dataIO


class WordCloud:

    """Word Clouds"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/wordcloud/settings.json"
        self.log_folder = "data/wordcloud/logs/"
        self.mask_folder = "data/wordcloud/masks/"
        self.settings = dataIO.load_json(self.settings_path)

    async def _list_masks(self, channel):

        masks = sorted(os.listdir(self.mask_folder))

        if len(masks) == 0:
            await self.bot.send_message(channel, "No masks found. Use "
                                        "`{}wordmask add`to add one."
                                        .format(ctx.prefix))

        pager = formatter.Paginator(prefix='```', suffix='```', max_size=2000)
        pager.add_line('Here are the image masks you have installed:')
        for mask in masks:
            pager.add_line(mask)
        for page in pager.pages:
            await self.bot.send_message(channel, page)
            asyncio.sleep(1)

    @commands.command(name='wordcloud', pass_context=True, no_pm=True)
    async def wordcloud(self, ctx, channel=None):
        """Generate a wordcloud"""

        if channel is None:
            channel = ctx.message.channel
            server = ctx.message.server
        else:
            channel = self.bot.get_channel(channel)
            if channel is None:
                await self.bot.say("That's not a valid channel.")
                return
            server = channel.server

        fp = self.log_folder + channel.id + '.log'
        # Currently this just grabs the entire log's message content
        # Will need to add purging and selective word clouds later
        text = ''
        try:
            with open(fp, mode='r', encoding='utf-8') as f:
                for line in f:
                    text += line[22:]
        except FileNotFoundError:
            await self.bot.say("I couldn't find a log for this channel.")
            return

        mask = None
        coloring = None
        mask_file = self.settings.get('mask', None)
        if mask_file is not None:
            mask = np.array(Image.open(mask_file))
        if self.settings.get('colormask', False):
            coloring = ImageColorGenerator(mask)

        wc = WCloud(mask=mask, color_func=coloring)
        wc.generate(text)
        cloudfile = 'data/wordcloud/clouds/' + channel.id + '.png'
        wc.to_file(cloudfile)

        msg = "Word Cloud for **" + server.name + '/' + channel.name + "**:"
        await self.bot.send_file(ctx.message.channel, cloudfile, content=msg)

    @commands.group(name='wordlog', pass_context=True, no_pm=True)
    async def wordlog(self, ctx):
        """WordCloud logging settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @wordlog.command(name='server', pass_context=True, no_pm=True)
    async def _wordlog_server(self, ctx, on_off: bool=None):
        """Turn wordcloud logging on/off for an entire server"""
        server = ctx.message.server
        if server.id in self.settings.setdefault('servers', []):
            if not on_off:  # This also catches None case
                self.settings['servers'].remove(server.id)
                await self.bot.say("I will stop logging message content "
                                   "for word clouds on **{}**. However, "
                                   "I will still log channels specified by "
                                   "`{}wordcloud log channel`."
                                   .format(server.name, ctx.prefix))
            else:
                await self.bot.say("I am already logging this server.")
        else:
            if on_off or on_off is None:
                self.settings['servers'].append(server.id)
                await self.bot.say("I will begin logging message content "
                                   "for word clouds in all channels I can "
                                   "see on **{}**.".format(server.name))
            else:
                await self.bot.say("I was not logging this server.")
        dataIO.save_json(self.settings_path, self.settings)

    @wordlog.command(name='channel', pass_context=True, no_pm=True)
    async def _wordlog_channel(self, ctx, on_off: bool=None):
        """Turn wordcloud logging on/off for a specific channel"""
        channel = ctx.message.channel
        if channel.id in self.settings.setdefault('channels', []):
            if not on_off:  # This also catches None case
                self.settings['channels'].remove(channel.id)
                await self.bot.say("I will stop logging message content "
                                   "for word clouds in **{}**. However, "
                                   "I will still log this channel if the "
                                   "entire server is enabled via "
                                   "`{}wordcloud log server`."
                                   .format(channel.name, ctx.prefix))
            else:
                await self.bot.say("I am already logging this channel.")
        else:
            if on_off or on_off is None:
                self.settings['channels'].append(channel.id)
                await self.bot.say("I will begin logging message content "
                                   "for word clouds in **{}**."
                                   .format(channel.name))
            else:
                await self.bot.say("I am not logging this channel.")
        dataIO.save_json(self.settings_path, self.settings)

    @commands.group(name='wordmask', pass_context=True, no_pm=True)
    async def wordmask(self, ctx):
        """WordCloud masking settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @wordmask.command(name='list', pass_context=True, no_pm=True)
    async def _wordmask_list(self, ctx):
        """List image files available for masking"""

        await self._list_masks(ctx.message.channel)

    @wordmask.command(name='set', pass_context=True, no_pm=True)
    async def _wordmask_set(self, ctx, filename: str):
        """Set image file for masking"""

        if not os.path.isfile(self.mask_folder + filename):
            await self.bot.say("That's not a valid filename.")
            await self._list_masks(ctx.message.channel)
            return
        self.settings['mask'] = self.mask_folder + filename
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('Mask set to {}.'.format(filename))

    @wordmask.command(name='color', pass_context=True, no_pm=True)
    async def _wordmask_color(self, ctx, on_off: bool=None):
        """Turn color masking on/off"""

        if self.settings.setdefault('colormask', False):
            if not on_off:  # This also catches None case
                self.settings['colormask'] = False
                await self.bot.say('Color masking turned off.')
            else:
                await self.bot.say('Color masking is already on.')
        else:
            if on_off or on_off is None:
                self.settings['colormask'] = True
                await self.bot.say('Color masking turned on.')
            else:
                await self.bot.say('Color masking is already off.')
        dataIO.save_json(self.settings_path, self.settings)

    async def on_message(self, message):
        # For now, WordCloud will log its own message content, per server
        # channel. In the future, something like ActiviyLog or LogItAll
        # will be used
        if message.author.bot:
            return
        if self.is_command(message):
            return
        if message.server is None:
            return
        if message.server.id not in self.settings.setdefault('servers', []) and\
                message.channel.id not in self.settings.setdefault('channels', []):
            return

        fp = self.log_folder + message.channel.id + '.log'
        # [YYYY-MM-DD HH:MM:SS]:
        timestamp = message.timestamp.strftime('[%Y-%m-%d %H:%M:%S]: ')
        content = timestamp + message.clean_content + '\n'
        with open(fp, mode='a', encoding='utf-8') as f:
            f.write(content)

    # Credit to Twentysix26's trigger cog
    def is_command(self, msg):
        if callable(self.bot.command_prefix):
            prefixes = self.bot.command_prefix(self.bot, msg)
        else:
            prefixes = self.bot.command_prefix
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False


def check_folders():
    root_folder = "data/wordcloud/"
    folders = ['logs', 'masks', 'clouds']
    for folder in folders:
        if not os.path.exists(root_folder + folder):
            print("Creating {} folder...".format(root_folder + folder))
            os.makedirs(root_folder + folder)


def check_files():
    default = {}
    if not dataIO.is_valid_json("data/wordcloud/settings.json"):
        print("Creating default wordcloud settings.json...")
        dataIO.save_json("data/wordcloud/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(WordCloud(bot))
