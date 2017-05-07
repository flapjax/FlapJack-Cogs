from .spoiler import Spoiler
import os

try:
    from PIL import Image, ImageDraw, ImageFont
    pillowAvailable = True
except:
    pillowAvailable = False


def check_folders():
    folder = "cogs/spoiler/data"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def setup(bot):
    check_folders()
    if pillowAvailable:
        bot.add_cog(Spoiler(bot))
    else:
        error_text = ("Make sure Pillow is intalled."
                      "\n`pip install Pillow`")
        raise RuntimeError(error_text)
