import copy

import discord
from redbot.core import Config, commands

BaseCog = getattr(commands, "Cog", object)


class SmartReact(BaseCog):

    """Create automatic reactions when trigger words are typed in chat"""

    default_guild_settings = {
        "reactions": {}
    }

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=964952632)
        self.conf.register_guild(
            **self.default_guild_settings
        )

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
        for guild in self.bot.guilds:
            for e in guild.emojis:
                if str(e.id) == emoji.split(':')[2][:-1]:
                    return e
        return None

    async def create_smart_reaction(self, guild, word, emoji, message):
        try:
            # Use the reaction to see if it's valid
            await message.add_reaction(emoji)
            emoji = str(emoji)
            reactions = await self.conf.guild(guild).reactions()
            if emoji in reactions:
                if word.lower() in reactions[emoji]:
                    await message.channel.send("This smart reaction already exists.")
                    return
                reactions[emoji].append(word.lower())
            else:
                reactions[emoji] = [word.lower()]
            await self.conf.guild(guild).reactions.set(reactions)
            await message.channel.send("Successfully added this reaction.")

        except (discord.errors.HTTPException, discord.errors.InvalidArgument):
            await message.channel.send("That's not an emoji I recognize. "
                                       "(might be custom!)")

    async def remove_smart_reaction(self, guild, word, emoji, message):
        try:
            # Use the reaction to see if it's valid
            await message.add_reaction(emoji)
            emoji = str(emoji)
            reactions = await self.conf.guild(guild).reactions()
            if emoji in reactions:
                if word.lower() in reactions[emoji]:
                    reactions[emoji].remove(word.lower())
                    await self.conf.guild(guild).reactions.set(reactions)
                    await message.channel.send("Removed this smart reaction.")
                else:
                    await message.channel.send("That emoji is not used as a reaction "
                                               "for that word.")
            else:
                await message.channel.send("There are no smart reactions which use "
                                           "this emoji.")

        except (discord.errors.HTTPException, discord.errors.InvalidArgument):
            await message.channel.send("That's not an emoji I recognize. "
                               "(might be custom!)")

    # Thanks irdumb#1229 for the help making this "more Pythonic"
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        guild = message.guild
        reacts = copy.deepcopy(await self.conf.guild(guild).reactions())
        if reacts is None:
            return
        words = message.content.lower().split()
        for emoji in reacts:
            if set(w.lower() for w in reacts[emoji]).intersection(words):
                emoji = self.fix_custom_emoji(emoji)
                await message.add_reaction(emoji)
