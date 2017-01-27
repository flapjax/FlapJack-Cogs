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

base_url = 'https://us.battle.net/connect/en/app/'
product_url = '/patch-notes?productType='
hearthstone_abbr = 'wtcg'
overwatch_abbr = 'Pro'
starcraft2_abbr = 'sc2'
warcraft_abbr = 'WoW'
diablo_abbr = 'd3'
hots_abbr = 'heroes'
headers = {'User-Agent': 'Battle.net/1.0.8.4217'}

class BlizzPatchNotes:

	"""Blizzard Game Patch Notes"""

	def __init__(self, bot):
		self.bot = bot

	@commands.command(name="hearthstone", pass_context=True)
	async def hearthstone(self, ctx):
		"""Prints latest Hearthstone patch notes"""

		url = ''.join([base_url,
						hearthstone_abbr,
						product_url,
						hearthstone_abbr])

		await self.print_patch_notes(url)

	@commands.command(name="overwatch", pass_context=True)
	async def overwatch(self, ctx):
		"""Prints latest Overwatch patch notes"""

		url = ''.join([base_url,
						overwatch_abbr,
						product_url,
						overwatch_abbr])

		await self.print_patch_notes(url)

	@commands.command(name="starcraft2", pass_context=True)
	async def starcraft2(self, ctx):
		"""Prints latest Starcraft2 patch notes"""

		url = ''.join([base_url,
						starcraft2_abbr,
						product_url,
						starcraft2_abbr])

		await self.print_patch_notes(url)

	@commands.command(name="warcraft", pass_context=True)
	async def warcraft(self, ctx):
		"""Prints latest World of Warcraft patch notes"""

		url = ''.join([base_url,
						warcraft_abbr,
						product_url,
						warcraft_abbr])

		await self.print_patch_notes(url)

	@commands.command(name="diablo3", pass_context=True)
	async def diablo3(self, ctx):
		"""Prints latest Diablo3 patch notes"""

		url = ''.join([base_url,
						diablo_abbr,
						product_url,
						diablo_abbr])

		await self.print_patch_notes(url)

	@commands.command(name="hots", pass_context=True)
	async def hots(self, ctx):
		"""Prints latest Overwatch patch notes"""

		url = ''.join([base_url,
						hots_abbr,
						product_url,
						hots_abbr])

		await self.print_patch_notes(url)


	async def print_patch_notes(self, url):
		try:
			async with aiohttp.get(url, headers=headers) as response:
				soup = BeautifulSoup(await response.text(), "html.parser")

			html_notes = soup.find('div', {"class": "patch-notes-interior"})
			text_notes = pypandoc.convert_text(html_notes, 'plain', format='html', extra_args=['--wrap=none'])
			text_notes = text_notes.replace('&nbsp;', ' ')
			text_notes = text_notes.replace('&apos;', "'")
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
