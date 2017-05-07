from .blizzard import Blizzard

try:
    from bs4 import BeautifulSoup
    soup_available = True
except:
    soup_available = False

try:
    import bleach
    bleach_available = True
except:
    bleach_available = False


def setup(bot):
    if soup_available and bleach_available:
        bot.add_cog(Blizzard(bot))
    else:
        error_text = ("Make sure beautifulsoup4 and bleach are installed."
                      "\n`pip install beautifulsoup4`"
                      "\n`pip install bleach`")
        raise RuntimeError(error_text)
