import os
import discord
from discord.ext import commands
from .utils.dataIO import dataIO

class SmartReact:

	"""Create automatic reactions when trigger words are typed in chat"""

	def __init__(self, bot):
		self.bot = bot
		self.settings_path = "data/smartreact/settings.json"
		self.settings = dataIO.load_json(self.settings_path)

	@commands.command(name="addreact", no_pm=True, pass_context=True)
	async def addreact(self, ctx, word, emoji):
		"""Add an auto reaction to a word"""
		server = ctx.message.server
		message = ctx.message
		self.load_settings(server.id)
		emoji = self.fix_custom_emoji(emoji)
		await self.create_smart_reaction(server, word, emoji, message)

	@commands.command(name="delreact", no_pm=True, pass_context=True)
	async def delreact(self, ctx, word, emoji):
		"""Delete an auto reaction to a word"""
		server = ctx.message.server
		message = ctx.message
		self.load_settings(server.id)
		emoji = self.fix_custom_emoji(emoji)
		await self.remove_smart_reaction(server, word, emoji, message)

	def load_settings(self, server_id):
		self.settings = dataIO.load_json(self.settings_path)
		if server_id not in self.settings.keys():
			self.add_default_settings(server_id)

	def add_default_settings(self, server_id):
		self.settings[server_id] = {}
		dataIO.save_json(self.settings_path, self.settings)

	def fix_custom_emoji(self, emoji):
		# Not very useful at the moment, perhaps later for custom emoji handling
		# For now, custom emojis will throw HTTPException and will be ignored
		if emoji[:2] == "<:":
			return ':' + emoji.split(':')[1] + ':'

		return emoji

	async def create_smart_reaction(self, server, word, emoji, message):
		try:
			# Use the reaction to see if it's valid
			await self.bot.add_reaction(message, emoji)
			if emoji in self.settings[server.id]:
				# Already some existing words for this reaction
				self.settings[server.id][emoji].append(word)
			else:
				self.settings[server.id][emoji] = [word]

			await self.bot.remove_reaction(message, emoji, server.me)
			await self.bot.say("Successfully added this reaction.")
			dataIO.save_json(self.settings_path, self.settings)

		except discord.errors.HTTPException:
			await self.bot.say("That's not an emoji I recognize. (might be custom!)")

	async def remove_smart_reaction(self, server, word, emoji, message):
		try:
			# Use the reaction to see if it's valid
			await self.bot.add_reaction(message, emoji)
			if emoji in self.settings[server.id]:
				if word in self.settings[server.id][emoji]:
					self.settings[server.id][emoji].remove(word)
					await self.bot.say("Removed this smart reaction.")
				else:
					await self.bot.say("That emoji is not used as a reaction for that word.")
			else:
				await self.bot.say("There are no smart reactions which use this emoji.")

			await self.bot.remove_reaction(message, emoji, server.me)
			dataIO.save_json(self.settings_path, self.settings)

		except discord.errors.HTTPException:
			await self.bot.say("That's not an emoji I recognize. (might be custom!)")

	async def msg_listener(self, message):
		if message.author.id != self.bot.user.id:
			server = message.server
			react_dict = self.settings[server.id]
			for emoji in react_dict:
				for word in react_dict[emoji]:
					if word.lower() in message.content.lower():
						try:
							await self.bot.add_reaction(message, emoji)
						except discord.errors.HTTPException:
							pass
							# Probably a custom emoji. Ignore

def check_folders():
    folder = "data/smartreact"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)

def check_files():
    default = {}
    if not dataIO.is_valid_json("data/smartreact/settings.json"):
        print("Creating default smartreact settings.json...")
        dataIO.save_json("data/smartreact/settings.json", default)

def setup(bot):
	check_folders()
	check_files()
	n = SmartReact(bot)
	bot.add_cog(n)
	bot.add_listener(n.msg_listener, "on_message")
