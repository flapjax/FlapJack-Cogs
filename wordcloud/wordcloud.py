import asyncio
import functools
import os

import aiohttp
import discord
import numpy as np
from __main__ import send_cmd_help
from cogs.utils import checks
from discord.ext import commands
from discord.ext.commands import converter, errors, formatter
from PIL import Image
from wordcloud import WordCloud as WCloud
from wordcloud import ImageColorGenerator

from .utils.dataIO import dataIO

# Special thanks to co-author aikaterna for pressing onward
# with this cog when I had lost motivation!


class WordCloud:

    """Word Clouds"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/wordcloud/settings.json"
        self.mask_folder = "data/wordcloud/masks/"
        self.settings = dataIO.load_json(self.settings_path)
        self.session = aiohttp.ClientSession()
        
    def __unload(self):
        self.session.close()

    async def _list_masks(self, ctx):

        channel = ctx.message.channel
        masks = sorted(os.listdir(self.mask_folder))

        if len(masks) == 0:
            await self.bot.send_message(channel, "No masks found. (place "
                                        "masks in /data/wordcloud/masks/) "
                                        "or add one with `{}wcset maskfile`.".format(ctx.prefix))
            return

        pager = formatter.Paginator(prefix='```', suffix='```', max_size=2000)
        pager.add_line('Here are the image masks you have installed:')
        for mask in masks:
            pager.add_line(mask)
        for page in pager.pages:
            await self.bot.send_message(channel, page)
            asyncio.sleep(1)

    @commands.command(name='wordcloud', pass_context=True, no_pm=True, aliases=['wc'])
    @commands.cooldown(1, 10, commands.BucketType.server)
    async def wordcloud(self, ctx, *argv):
        """Generate a wordcloud. Optional arguments are channel, user, and
        message limit (capped at 10,000)."""

        author = ctx.message.author
        channel = ctx.message.channel
        user = None
        limit = 4000

        for arg in argv:
            try:
                channel = converter.ChannelConverter(ctx, arg).convert()
                if channel.type != discord.ChannelType.text:
                    channel = ctx.message.channel
                continue

            except errors.BadArgument:
                pass

            try:
                user = converter.MemberConverter(ctx, arg).convert()
                continue
            except errors.BadArgument:
                pass

            if arg.isdigit() and int(arg) <= 10000:
                limit = int(arg)

        server = channel.server

        # Verify that wordcloud requester is not being a sneaky snek
        if not channel.permissions_for(author).read_messages or \
                server != ctx.message.server:
            await self.bot.say('\N{SMIRKING FACE} Nice try.')
            return

        # Default settings
        mask = None
        coloring = None
        width = 800
        height = 600
        mode = 'RGB'
        bg_color = self.settings.get(server.id, {}).get('bgcolor', 'black')
        if bg_color == 'clear':
            mode += 'A'
            bg_color = None
        max_words = self.settings.get(server.id, {}).get('maxwords', 200)
        if max_words == 0:
            max_words = 200
        excluded = self.settings.get(server.id, {}).get('excluded', [])
        if not excluded:
            excluded = None

        mask_file = self.settings.get(server.id, {}).get('mask', None)
        if mask_file is not None:
            try:
                mask = np.array(Image.open(mask_file))
            except FileNotFoundError:
                await self.bot.say('I could not load your mask file. It may '
                                   'have been deleted. `{}wcset clearmask` '
                                   'may resolve this.'.format(ctx.prefix))
                return
            if self.settings.get(server.id, {}).get('colormask', False):
                coloring = ImageColorGenerator(mask)

        kwargs = {'mask': mask, 'color_func': coloring, 'mode': mode,
                  'background_color': bg_color, 'max_words': max_words,
                  'stopwords': excluded, 'width': width, 'height': height}
        filepath = 'data/wordcloud/clouds/' + channel.id + '.png'

        msg = "Generating wordcloud for **" + server.name + '/' + channel.name
        if user is not None:
            msg += "/" + user.display_name
        msg += "** using the last {} messages. (this might take a while)".format(limit)

        await self.bot.say(msg)

        text = ''
        try:
            async for message in self.bot.logs_from(channel, limit=limit):
                if not message.author.bot:
                    if user is None or user == message.author:
                        text += message.clean_content + ' '
        except discord.errors.Forbidden:
            await self.bot.say("Wordcloud creation failed. I can't see that channel!")
            return

        if not text or text.isspace():
            await self.bot.say("Wordcloud creation failed. I couldn't find "
                               "any words. You may have entered a very small "
                               "message limit, or I may not have permission "
                               "to view message history in that channel.")
            return

        task = functools.partial(WordCloud.generate, filepath, text,
                                 **kwargs)
        task = self.bot.loop.run_in_executor(None, task)
        try:
            await asyncio.wait_for(task, timeout=45)
        except asyncio.TimeoutError:
            await self.bot.say('Wordcloud creation timed out.')
            return

        await self.bot.send_file(ctx.message.channel, filepath)

    @staticmethod
    def generate(filepath, text, **kwargs):
        # Designed to be run in executor to avoid blocking
        wc = WCloud(**kwargs)
        wc.generate(text)
        wc.to_file(filepath)

    @commands.group(name='wcset', pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def wcset(self, ctx):
        """WordCloud image settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @wcset.command(name='listmask', pass_context=True, no_pm=True)
    async def _wcset_listmask(self, ctx):
        """List image files available for masking"""
        await self._list_masks(ctx)

    @wcset.command(name='maskfile', pass_context=True, no_pm=True)
    async def _wcset_maskfile(self, ctx, filename: str):
        """Set local image file for masking
        - place masks in /data/wordcloud/masks/"""
        server = ctx.message.server
        if not os.path.isfile(self.mask_folder + filename):
            await self.bot.say("That's not a valid filename.")
            await self._list_masks(ctx)
            return
        self.settings.setdefault(server.id, {})['mask'] = self.mask_folder + filename
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('Mask set to {}.'.format(filename))

    @wcset.command(name='upload', pass_context = True, no_pm=True)
    @checks.is_owner()
    async def _wcset_upload(self, ctx, link: str=None):
        """Upload an image mask through Discord"""
        user = ctx.message.author
        server = ctx.message.server
        attach = ctx.message.attachments
        emoji = ('\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}')
        if len(attach) > 1 or (attach and link):
            await self.bot.say("Please add one image at a time.")
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
            await self.bot.say("You must provide either a Discord attachment "
                               "or a direct link to an image")
            return

        filepath = os.path.join(self.mask_folder, filename)

        async with self.session.get(url) as new_image:
            # Overwrite file if it exists
            f = open(filepath, "wb")
            f.write(await new_image.read())
            f.close()

        msg = await self.bot.say("Mask {} added. Set as current mask for this server?".format(os.path.splitext(filename)[0]))
        await self.bot.add_reaction(msg, emoji[0])
        await asyncio.sleep(0.5)
        await self.bot.add_reaction(msg, emoji[1])
        response = await self.bot.wait_for_reaction(emoji, user=user,
                                                    timeout=600, message=msg)

        if response is None or response.reaction.emoji == emoji[1]:
            await self.bot.clear_reactions(msg)
        elif response.reaction.emoji == emoji[0]:
            await self.bot.clear_reactions(msg)
            self.settings.setdefault(server.id, {})['mask'] = filepath
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say('Mask for this server set to uploaded file.')

    @wcset.command(name='clearmask', pass_context=True, no_pm=True)
    async def _wcset_clearmask(self, ctx):
        """Clear image file for masking"""
        server = ctx.message.server
        self.settings.setdefault(server.id, {})['mask'] = None
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('Mask set to None.')

    @wcset.command(name='colormask', pass_context=True, no_pm=True)
    async def _wcset_colormask(self, ctx, on_off: bool=None):
        """Turn color masking on/off"""
        server = ctx.message.server
        if self.settings.setdefault(server.id, {}).setdefault('colormask', False):
            if not on_off:  # This also catches None case
                self.settings[server.id]['colormask'] = False
                await self.bot.say('Color masking turned off.')
            else:
                await self.bot.say('Color masking is already on.')
        else:
            if on_off or on_off is None:
                self.settings[server.id]['colormask'] = True
                await self.bot.say('Color masking turned on.')
            else:
                await self.bot.say('Color masking is already off.')
        dataIO.save_json(self.settings_path, self.settings)

    @wcset.command(name='bgcolor', pass_context=True, no_pm=True)
    async def _wcset_bgcolor(self, ctx, color: str):
        """Set background color. Use 'clear' for transparent."""
        # No checks for bad colors yet
        server = ctx.message.server
        self.settings.setdefault(server.id, {})['bgcolor'] = color
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('Background color set to {}.'.format(color))

    @wcset.command(name='maxwords', pass_context=True, no_pm=True)
    async def _wcset_maxwords(self, ctx, count: int):
        """Set maximum number of words to appear in the word cloud
        Set to 0 for default (4000)."""
        # No checks for bad values yet
        server = ctx.message.server
        self.settings.setdefault(server.id, {})['maxwords'] = count
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say('Max words set to {}.'.format(str(count)))

    @wcset.command(name='exclude', pass_context=True, no_pm=True)
    async def _wcset_exclude(self, ctx, word: str):
        """Add a word to the excluded list.
        This overrides the default excluded list!"""
        server = ctx.message.server
        self.settings.setdefault(server.id, {}).setdefault('excluded', []).append(word)
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("'{}' added to excluded words.".format(word))

    @wcset.command(name='clearwords', pass_context=True, no_pm=True)
    async def _wcset_clearwords(self, ctx):
        """Clear the excluded word list.
        Default excluded list will be used."""
        server = ctx.message.server
        self.settings.setdefault(server.id, {})['excluded'] = []
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
