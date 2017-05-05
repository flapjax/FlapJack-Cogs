from .msgvote import MsgVote


def setup(bot):
    bot.add_cog(MsgVote(bot))
