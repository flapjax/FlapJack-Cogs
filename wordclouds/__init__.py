from .wordclouds import WordClouds


def setup(bot):
    bot.add_cog(WordClouds(bot))
