from .reactpoll import ReactPoll

__red_end_user_data_statement__ = "This cog stores Discord IDs as needed for operation temporary during a poll which are automatically deleted when it ends."


def setup(bot):
    bot.add_cog(ReactPoll(bot))
