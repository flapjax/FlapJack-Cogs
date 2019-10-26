import aiohttp
import asyncio
import discord
import functools
from io import BytesIO
import numpy as np
import os
from PIL import Image

from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.data_manager import cog_data_path
from wordcloud import WordCloud as WCloud
from wordcloud import ImageColorGenerator

# Special thanks to co-author aikaterna for pressing onward
# with this cog when I had lost motivation!


class WordClouds(commands.Cog):

    """Word Clouds"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.conf = Config.get_conf(self, identifier=3271169074)
        default_guild_settings = {
            "bg_color": "black",
            "maxwords": 200,
            "excluded": [],
            "mask": None,
            "colormask": False,
        }
        self.conf.register_guild(**default_guild_settings)
        self.mask_folder = str(cog_data_path(raw_name="WordClouds")) + "/masks"

        if not os.path.exists(self.mask_folder):
            os.mkdir(self.mask_folder)

        # Clouds can really just be stored in memory at some point

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def _list_masks(self, ctx):
        masks = sorted(os.listdir(self.mask_folder))

        if len(masks) == 0:
            return await ctx.send(
                "No masks found. Place masks in the bot's data folder for WordClouds or add one with `{}wcset maskfile`.".format(
                    ctx.prefix
                )
            )

        msg = "Here are the image masks you have installed:\n"
        for mask in masks:
            msg += f"{mask}\n"

        for page in pagify(msg, delims=["\n"]):
            await ctx.send(box(page, lang="ini"))

    @commands.guild_only()
    @commands.command(name="wordcloud", aliases=["wc"])
    @commands.cooldown(1, 15, commands.BucketType.guild)
    async def wordcloud(self, ctx, *argv):
        """Generate a wordcloud. Optional arguments are channel, user, and
        message limit (capped at 10,000)."""

        author = ctx.author
        channel = ctx.channel
        user = None
        limit = 10000

        # a bit clunky, see if Red has already implemented converters
        channel_converter = commands.TextChannelConverter()
        member_converter = commands.MemberConverter()

        for arg in argv:
            try:
                channel = await channel_converter.convert(ctx, arg)
                continue
            except discord.ext.commands.BadArgument:
                pass

            try:
                user = await member_converter.convert(ctx, arg)
                continue
            except discord.ext.commands.BadArgument:
                pass

            if arg.isdecimal() and int(arg) <= 10000:
                limit = int(arg)

        guild = channel.guild

        # Verify that wordcloud requester is not being a sneaky snek
        if not channel.permissions_for(author).read_messages or guild != ctx.guild:
            await ctx.send("\N{SMIRKING FACE} Nice try.")
            return

        # Default settings
        mask = None
        coloring = None
        width = 800
        height = 600
        mode = "RGB"
        bg_color = await self.conf.guild(guild).bgcolor()
        if bg_color == "clear":
            mode += "A"
            bg_color = None
        max_words = await self.conf.guild(guild).maxwords()
        if max_words == 0:
            max_words = 200
        excluded = await self.conf.guild(guild).excluded()
        if not excluded:
            excluded = None

        mask_name = await self.conf.guild(guild).mask()
        if mask_name is not None:
            mask_file = f"{self.mask_folder}/{mask_name}"
            try:
                mask = np.array(Image.open(mask_file))
            except FileNotFoundError:
                await ctx.send(
                    "I could not load your mask file. It may "
                    "have been deleted. `{}wcset clearmask` "
                    "may resolve this.".format(ctx.prefix)
                )
                return
            if await self.conf.guild(guild).colormask():
                coloring = ImageColorGenerator(mask)

        kwargs = {
            "mask": mask,
            "color_func": coloring,
            "mode": mode,
            "background_color": bg_color,
            "max_words": max_words,
            "stopwords": excluded,
            "width": width,
            "height": height,
        }

        msg = "Generating wordcloud for **" + guild.name + "/" + channel.name
        if user is not None:
            msg += "/" + user.display_name
        msg += "** using the last {} messages. (this might take a while)".format(limit)

        await ctx.send(msg)

        text = ""
        try:
            async for message in channel.history(limit=limit):
                if not message.author.bot:
                    if user is None or user == message.author:
                        text += message.clean_content + " "
        except discord.errors.Forbidden:
            await ctx.send("Wordcloud creation failed. I can't see that channel!")
            return

        if not text or text.isspace():
            await ctx.send(
                "Wordcloud creation failed. I couldn't find "
                "any words. You may have entered a very small "
                "message limit, or I may not have permission "
                "to view message history in that channel."
            )
            return

        task = functools.partial(self.generate, text, **kwargs)
        task = self.bot.loop.run_in_executor(None, task)
        try:
            image = await asyncio.wait_for(task, timeout=45)
        except asyncio.TimeoutError:
            await ctx.send("Wordcloud creation timed out.")
            return
        await ctx.send(file=discord.File(image))

    @staticmethod
    def generate(text, **kwargs):
        # Designed to be run in executor to avoid blocking
        wc = WCloud(**kwargs)
        wc.generate(text)
        file = BytesIO()
        file.name = "wordcloud.png"
        wc.to_file(file)
        file.seek(0)
        return file

    @commands.guild_only()
    @commands.group(name="wcset")
    @checks.mod_or_permissions(administrator=True)
    async def wcset(self, ctx):
        """WordCloud image settings"""
        pass

    @wcset.command(name="listmask")
    async def _wcset_listmask(self, ctx):
        """List image files available for masking"""
        await self._list_masks(ctx)

    @wcset.command(name="maskfile")
    async def _wcset_maskfile(self, ctx, filename: str):
        """Set local image file for masking
        - place masks in the cog's data folder/masks/"""
        guild = ctx.guild
        mask_path = f"{self.mask_folder}/{filename}"
        if not os.path.isfile(mask_path):
            print(mask_path)
            await ctx.send("That's not a valid filename.")
            return await self._list_masks(ctx)
        await self.conf.guild(guild).mask.set(filename)
        await ctx.send("Mask set to {}.".format(filename))

    @wcset.command(name="upload")
    @checks.is_owner()
    async def _wcset_upload(self, ctx, url: str = None):
        """Upload an image mask through Discord"""
        user = ctx.author
        guild = ctx.guild
        attachments = ctx.message.attachments
        emoji = ("\N{WHITE HEAVY CHECK MARK}", "\N{CROSS MARK}")
        if len(attachments) > 1 or (attachments and url):
            await ctx.send("Please add one image at a time.")
            return

        if attachments:
            filename = attachments[0].filename
            filepath = f"{self.mask_folder}/{filename}"
            try:
                await attachments[0].save(filepath)
            except:
                ctx.send("Saving attachment failed.")
                return

        elif url:
            filename = url.split("/")[-1].replace("%20", "_")
            filepath = f"{self.mask_folder}/{filename}"
            async with self.session.get(url) as new_image:
                # Overwrite file if it exists
                f = open(str(filepath), "wb")
                f.write(await new_image.read())
                f.close()

        else:
            await ctx.send(
                "You must provide either a Discord attachment " "or a direct link to an image"
            )
            return

        msg = await ctx.send(
            "Mask {} added. Set as current mask for this server?".format(filename)
        )
        await msg.add_reaction(emoji[0])
        await asyncio.sleep(0.5)
        await msg.add_reaction(emoji[1])

        def check(r, u):
            return u == user and r.message.id == msg.id and r.emoji == emoji[0]

        try:
            await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            await self.conf.guild(guild).mask.set(filename)
            await ctx.send("Mask for this server set to uploaded file.")
        except asyncio.TimeoutError:
            # Can add an timeout message, but not really necessary
            # as clearing the reactions is sufficient feedback
            pass
        finally:
            await msg.clear_reactions()

    @wcset.command(name="clearmask")
    async def _wcset_clearmask(self, ctx):
        """Clear image file for masking"""
        guild = ctx.guild
        await self.conf.guild(guild).mask.set(None)
        await ctx.send("Mask set to None.")

    @wcset.command(name="colormask")
    async def _wcset_colormask(self, ctx, on_off: bool = None):
        """Turn color masking on/off"""
        guild = ctx.guild
        if await self.conf.guild(guild).colormask():
            await self.conf.guild(guild).colormask.set(False)
            await ctx.send("Color masking turned off.")
        else:
            await self.conf.guild(guild).colormask.set(True)
            await ctx.send("Color masking turned on.")

    @wcset.command(name="bgcolor")
    async def _wcset_bgcolor(self, ctx, color: str):
        """Set background color. Use 'clear' for transparent."""
        # No checks for bad colors yet
        guild = ctx.guild
        await self.conf.guild(guild).bgcolor.set(color)
        await ctx.send("Background color set to {}.".format(color))

    @wcset.command(name="maxwords")
    async def _wcset_maxwords(self, ctx, count: int):
        """Set maximum number of words to appear in the word cloud
        Set to 0 for default (4000)."""
        # No checks for bad values yet
        guild = ctx.guild
        await self.conf.guild(guild).maxwords.set(count)
        await ctx.send("Max words set to {}.".format(str(count)))

    @wcset.command(name="exclude")
    async def _wcset_exclude(self, ctx, word: str):
        """Add a word to the excluded list.
        This overrides the default excluded list!"""
        guild = ctx.guild
        excluded = await self.conf.guild(guild).excluded()
        excluded.append(word)
        await self.conf.guild(guild).excluded.set(excluded)
        await ctx.send("'{}' added to excluded words.".format(word))

    @wcset.command(name="clearwords")
    async def _wcset_clearwords(self, ctx):
        """Clear the excluded word list.
        Default excluded list will be used."""
        guild = ctx.guild
        await self.conf.guild(guild).excluded.set([])
        await ctx.send("Cleared the excluded word list.")
