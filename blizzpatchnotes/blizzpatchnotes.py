import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
import aiohttp

try: # check if BeautifulSoup4 is installed
	from bs4 import BeautifulSoup
	soup_available = True
except:
	soup_available = False

try: # check if pypandoc is installed
	import pypandoc
	pypandoc_available = True
except:
	pypandoc_available = False

# Special thanks to judge2020 for telling me about pandoc, and offering their
# code as a reference: https://github.com/judge2020/BattleNetUpdateChecker

# This cog requires:
# BeautifulSoup4 :: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
# pypandoc :: https://pypi.python.org/pypi/pypandoc
# Pandoc :: http://pandoc.org/

class BlizzPatchNotes:

	"""Blizzard Game Patch Notes"""

	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def overwatch(self):
		"""Prints latest Overwatch patch notes"""

		url = "https://playoverwatch.com/en-us/game/patch-notes/pc/"
		try:
			async with aiohttp.get(url) as response:
				soup = BeautifulSoup(await response.text(), "html.parser")

			html_notes = soup.find('div', {"class": "patch-notes-body"})
			text_notes = pypandoc.convert_text(html_notes, 'plain', format='html', extra_args=['--wrap=none'])
			msg_list = pagify(text_notes, delims=["\n"])
			for msg in msg_list:
				await self.bot.say(msg)

		except:
			await self.bot.say("I couldn't find any patch notes. ¯\_(ツ)_/¯")

def setup(bot):
	if soup_available and pypandoc_available:
		bot.add_cog(BlizzPatchNotes(bot))
	else:
		if not soup_available:
			error_text += "You need to run `pip install beautifulsoup4`\n"
		if not pypandoc_available:
			error_text += "You need to run `pip install pypandoc`\n"
		# No need to raise an error for missing Pandoc, pypandoc will alert user
		raise RuntimeError(error_text)
