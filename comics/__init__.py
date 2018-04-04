from .comics import Comics


def setup(bot):
    bot.add_cog(Comics(bot))
