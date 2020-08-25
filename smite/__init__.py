from .smite import Smite

__red_end_user_data_statement__ = "This cog does store discord IDs as needed for operation."


def setup(bot):
    bot.add_cog(Smite(bot))
