from .blizzard import Blizzard


def setup(bot):
    bot.add_cog(Blizzard(bot))
