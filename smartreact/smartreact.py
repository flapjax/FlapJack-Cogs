import copy
import os

import discord
from discord.ext import commands
from discord.ext.commands import converter

from core.utils import helpers


class SmartReact:

    """Create automatic reactions when trigger words are typed in chat"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = helpers.JsonGuildDB("cogs/smartreact/data/settings.json")

    @commands.command(name="addreact", no_pm=True)
    async def addreact(self, ctx, word, emoji):
        """Add an auto reaction to a word"""
        guild = ctx.message.guild
        message = ctx.message
        emoji = self.fix_custom_emoji(emoji)
        await self.create_smart_reaction(guild, word, emoji, message)

    @commands.command(name="delreact", no_pm=True, pass_context=True)
    async def delreact(self, ctx, word, emoji):
        """Delete an auto reaction to a word"""
        guild = ctx.message.guild
        message = ctx.message
        emoji = self.fix_custom_emoji(emoji)
        await self.remove_smart_reaction(guild, word, emoji, message)

    def fix_custom_emoji(self, emoji):
        if emoji[:2] != "<:":
            return emoji
        # Need to address IndexError for invalid emojis
        return [r for guild in self.bot.guilds for r in guild.emojis if str(r.id) == emoji.split(':')[2][:-1]][0]

    async def create_smart_reaction(self, guild, word, emoji, message):
        try:
            # Use the reaction to see if it's valid
            await message.add_reaction(emoji)
            emoji = str(emoji)
            entry = self.settings.get(guild, emoji)
            if entry:
                if word.lower() in entry:
                    await message.channel.send("This smart reaction already exists.")
                    return
                print(entry)
                entry.append(word.lower())
                await self.settings.set(guild, emoji, entry)
            else:
                await self.settings.set(guild, emoji, [word.lower()])

            await message.channel.send("Successfully added this reaction.")

        except discord.errors.HTTPException:
            await message.channel.send("That's not an emoji I recognize. "
                                       "(might be custom!)")

    async def remove_smart_reaction(self, guild, word, emoji, message):
        try:
            # Use the reaction to see if it's valid
            await message.add_reaction(emoji)
            emoji = str(emoji)
            entry = self.settings.get(guild, emoji)
            if entry:
                if word.lower() in entry:
                    await self.settings.set(guild, emoji, entry.remove(word.lower()))
                    await message.channel.send("Removed this smart reaction.")
                else:
                    await message.channel.send("That emoji is not used as a reaction "
                                               "for that word.")
            else:
                await message.channel.send("There are no smart reactions which use "
                                           "this emoji.")

        except discord.errors.HTTPException:
            await self.bot.say("That's not an emoji I recognize. "
                               "(might be custom!)")

    # Special thanks to irdumb#1229 on discord for helping me make this method
    # "more Pythonic"
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        guild = message.guild
        reacts = copy.deepcopy(self.settings.get_all(guild))
        if reacts is None:
            return
        words = message.content.lower().split()
        for emoji in reacts:
            if set(w.lower() for w in reacts[emoji]).intersection(words):
                emoji = self.fix_custom_emoji(emoji)
                await message.add_reaction(emoji)
