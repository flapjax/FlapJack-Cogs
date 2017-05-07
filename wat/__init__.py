from .wat import Wat


def setup(bot):
    bot.add_cog(Wat(bot))
