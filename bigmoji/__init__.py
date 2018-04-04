from .bigmoji import Bigmoji


def setup(bot):
    bot.add_cog(Bigmoji(bot))
