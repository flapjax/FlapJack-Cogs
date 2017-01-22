import discord
from discord.ext import commands
#import asyncio

# React if message includes one of these phrases
words_that_are_bees = 'bee'
# But not these prhases
words_that_are_not_bees = ['beef',
							'been',
							'beep',
							'beer',
							'beet',
							'beech',
							'beedi',
							'beest',
							'frisbee']

# Unicode character of emoji to react with
react_emoji = '\U0001F41D'

class Bees:

	"""Automatic bee reactions!"""

	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def bees(self):
		"""bees?"""

		await self.bot.say("bees.")

async def check_messages(message):
	if message.author.id != bee_manager.bot.user.id: # Don't react to self
		if words_that_are_bees in message.content.lower():
			bees_detected = True # Bee detection flag
		else:
			bees_detected = False

		if bees_detected:
			for phrase in words_that_are_not_bees:
				if phrase in message.content.lower():
					bees_detected = False # False alarm!
					# Yeah, false negatives are possible with multiple bee references in message
					# I will fix this soon!
					break

		if bees_detected:
			try:
				await bee_manager.bot.add_reaction(message, react_emoji)
			except:
				await asyncio.sleep(0.5)
				await bee_manager.bot.add_reaction(message, react_emoji)
			return True


def setup(bot):
	global bee_manager
	bee_manager = Bees(bot)
	bot.add_cog(bee_manager)
	bot.add_listener(check_messages, "on_message")
