from .sfx import Sfx
import glob
import os
import os.path


def check_folders():
    folder = "cogs/sfx/data/sfx/temp"
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


def setup(bot):
    check_folders()
    bot.add_cog(Sfx(bot))
