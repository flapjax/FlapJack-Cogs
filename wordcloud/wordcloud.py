import os

import numpy as np
from discord.ext import commands
from PIL import Image

from wordcloud import WordCloud as WCloud
from wordcloud import ImageColorGenerator

from .utils.dataIO import dataIO


class WordCloud:

    """Word Clouds"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/wordcloud/settings.json"
        self.settings = dataIO.load_json(self.settings_path)

    @commands.command(pass_context=True, no_pm=True)
    async def wordcloud(self, ctx, channel=None):
        """Generate a wordcloud"""
        if channel is None:
            channel = ctx.message.channel
            server = ctx.message.server
        else:
            channel = self.bot.get_channel(channel)
            server = channel.server

        # Note this requires activitylogger, and there is no error handling yet
        # Also, logging anything except messages is going to affect your cloud
        filepath = "data/activitylogger/" + server.id + "/" + channel.id + ".log"
        text = ' '.join([line.split(':')[3].strip() for line in open(filepath, mode="r")])

        mask = np.array(Image.open("data/wordcloud/red3.png"))
        coloring = ImageColorGenerator(mask)

        wc = WCloud(mask=mask, color_func=coloring, max_words=300)
        wc.generate(text)

        tempfile = "data/wordcloud/wordcloud.png"
        wc.to_file(tempfile)

        msg = "Today's Word Cloud for **" + server.name + '/' + channel.name + "**:"
        await self.bot.send_file(ctx.message.channel, tempfile, content=msg)


def check_folders():
    folder = "data/wordcloud"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {}
    if not dataIO.is_valid_json("data/wordcloud/settings.json"):
        print("Creating default wordcloud settings.json...")
        dataIO.save_json("data/wordcloud/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(WordCloud(bot))
