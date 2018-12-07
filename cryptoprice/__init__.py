from .cryptoprice import CryptoPrice


def setup(bot):
    bot.add_cog(CryptoPrice(bot))
