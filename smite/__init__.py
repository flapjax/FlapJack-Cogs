from .smite import Smite

__red_end_user_data_statement__ = "This cog stores discord IDs as needed for operation."


def setup(bot):
    bot.add_cog(Smite(bot))
