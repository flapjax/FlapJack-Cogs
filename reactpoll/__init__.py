from .reactpoll import ReactPoll


def setup(bot):
    bot.add_cog(ReactPoll(bot))
