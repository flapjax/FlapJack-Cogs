import discord
from discord.ext import commands
import os
import textwrap

try:
    from PIL import Image, ImageDraw, ImageFont
    pillowAvailable = True
except:
    pillowAvailable = False


class Spoiler:

    """Hide spoilers using animated GIFs"""

    def __init__(self, bot):
        self.bot = bot
        self.temp_filepath = "data/spoiler/spoiler.gif"
        self.line_length = 40
        self.base_height = 18
        self.width = 300
        self.margin = (9, 9)
        self.font = "data/spoiler/UbuntuMono-Regular.ttf"
        self.font_size = 14
        self.font_color = 150
        self.bg_color = 20

    @commands.command(pass_context=True, no_pm=True)
    async def spoiler(self, ctx, *text: str):
        """Use an animated gif to hide spoiler text"""

        message = ctx.message
        author = message.author.display_name

        try:
            await self.bot.delete_message(message)
        except discord.errors.Forbidden:
            await self.bot.say("I require the 'manage messages' permission "
                               "to hide spoilers!")

        try:
            fnt = ImageFont.truetype(self.font, self.font_size)
        except OSError:
            await self.bot.say("I couldn't load the font file. Try "
                               "reinstalling via the downloader cog, or "
                               "manually place `UbuntuMono-Regular.ttf` "
                               "in `/data/spoiler/`")
            return

        text = textwrap.wrap(" ".join(text), width=self.line_length)
        height = self.base_height * (len(text) + 1)
        width = self.width
        spoil_text = ["Mouseover to reveal spoiler",
                      "\n".join(text)]
        spoil_img = [Image.new("L", (width, height), self.bg_color),
                     Image.new("L", (width, height), self.bg_color)]

        for i in range(0, 2):
            ImageDraw.Draw(spoil_img[i]).text(self.margin, spoil_text[i],
                                              font=fnt, fill=self.font_color)

        spoil_img[0].save(self.temp_filepath, format="GIF", save_all=True,
                          append_images=[spoil_img[1]],
                          duration=[0, 0xFFFF], loop=0)
        content = "**" + author + "** posted this spoiler:"
        await self.bot.send_file(ctx.message.channel, self.temp_filepath,
                                 content=content)
        os.remove(self.temp_filepath)


def check_folders():
    folder = "data/spoiler"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def setup(bot):
    check_folders()
    if pillowAvailable:
        bot.add_cog(Spoiler(bot))
    else:
        raise RuntimeError("You need to run `pip3 install pillow`")
