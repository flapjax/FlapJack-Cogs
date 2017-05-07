from .smite import Smite


def setup(bot):
    bot.add_cog(Smite(bot))
