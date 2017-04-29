from .defcon import Defcon


def setup(bot):
    bot.add_cog(Defcon(bot))
