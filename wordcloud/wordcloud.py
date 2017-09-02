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
    async def wordcloud(self, ctx, channel=None, limit: int=1000):
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

        text = ''
        async for message in self.bot.logs_from(channel, limit=limit):
            if not mssage.author.bot:
                text += message.clean_content + ' '

        # Default settings
        mask = None
        coloring = None
        mode = 'RGB'
        bg_color = self.settings.get('bgcolor', 'black')
        if bg_color == 'clear':
            mode += 'A'
            bg_color = None
        max_words = self.settings.get('maxwords', 200)
        if max_words == 0:
            max_words = 200
        excluded = self.settings.get('excluded', [])
        if not excluded:
            excluded = None

        mask_file = self.settings.get('mask', None)
        if mask_file is not None:
            mask = np.array(Image.open(mask_file))
        if self.settings.get('colormask', False):
            coloring = ImageColorGenerator(mask)

        wc = WCloud(mask=mask, color_func=coloring, mode=mode,
                    background_color=bg_color, max_words=max_words,
                    stopwords=excluded)
        wc.generate(text)
        cloudfile = 'data/wordcloud/clouds/' + channel.id + '.png'
        wc.to_file(cloudfile)

        msg = "Word Cloud for **" + server.name + '/' + channel.name + "**:"
        await self.bot.send_file(ctx.message.channel, cloudfile, content=msg)

    @commands.group(name='wordset', pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def wordset(self, ctx):
        """WordCloud image settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @wordset.command(name='listmask', pass_context=True, no_pm=True)
    async def _wordset_listmask(self, ctx):
        """List image files available for masking"""

        await self._list_masks(ctx.message.channel)

    @wordset.command(name='setmask', pass_context=True, no_pm=True)
    async def _wordset_setmask(self, ctx, filename: str):
        """Set image file for masking"""

        if not os.path.isfile(self.mask_folder + filename):
            await self.bot.say("That's not a valid filename.")
            await self._list_masks(ctx.message.channel)
            return
        self.settings['mask'] = self.mask_folder + filename
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('Mask set to {}.'.format(filename))

    @wordset.command(name='clearmask', pass_context=True, no_pm=True)
    async def _wordset_clearmask(self, ctx):
        """Clear image file for masking"""
        self.settings['mask'] = None
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('Mask set to None.')

    @wordset.command(name='colormask', pass_context=True, no_pm=True)
    async def _wordset_colormask(self, ctx, on_off: bool=None):
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

    @wordset.command(name='bgcolor', pass_context=True, no_pm=True)
    async def _wordset_bgcolor(self, ctx, color: str):
        """Set background color. Use 'clear' for transparent."""
        # No checks for bad colors yet
        self.settings['bgcolor'] = color
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('Background color set to {}.'.format(color))

    @wordset.command(name='maxwords', pass_context=True, no_pm=True)
    async def _wordset_maxwords(self, ctx, count: int):
        """Set maximum number of words to appear in the word cloud (
        Set to 0 for default)."""
        # No checks for bad values yet
        self.settings['maxwords'] = count
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('Max words set to {}.'.format(str(count)))

    @wordset.command(name='exclude', pass_context=True, no_pm=True)
    async def _wordset_exclude(self, ctx, word: str):
        """Add a word to the excluded list.
        This overrides the default excluded list!"""

        self.settings.setdefault('excluded', [])
        self.settings['excluded'].append(word)
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("'{}' added to excluded words.".format(word))

    @wordset.command(name='clear', pass_context=True, no_pm=True)
    async def _wordset_clear(self, ctx):
        """Clear the excluded word list.
        Default excluded list will be used."""

        self.settings['excluded'] = []
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Cleared the excluded word list.")


def check_folders():
    root_folder = "data/wordcloud/"
    folders = ['masks', 'clouds']
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
