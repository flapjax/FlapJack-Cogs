from .smartreact import SmartReact


def setup(bot):
    bot.add_cog(SmartReact(bot))
