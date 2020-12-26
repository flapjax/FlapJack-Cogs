import copy
import discord
from redbot.core import Config, commands, checks
from redbot.core.utils.chat_formatting import pagify


class SmartReact(commands.Cog):
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

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    @checks.mod_or_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.guild_only()
    @commands.command(name="addreact")
    async def addreact(self, ctx, word, emoji):
        """Add an auto reaction to a word"""
        guild = ctx.message.guild
        message = ctx.message
        emoji = self.fix_custom_emoji(emoji)
        await self.create_smart_reaction(guild, word, emoji, message)

    @checks.mod_or_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.guild_only()
    @commands.command(name="delreact")
    async def delreact(self, ctx, word, emoji):
        """Delete an auto reaction to a word"""
        guild = ctx.message.guild
        message = ctx.message
        emoji = self.fix_custom_emoji(emoji)
        await self.remove_smart_reaction(guild, word, emoji, message)

    def fix_custom_emoji(self, emoji):
        if emoji[:2] not in ["<:", "<a"]:
            return emoji
        e = self.bot.get_emoji(int(emoji.split(':')[2][:-1]))
        if e:
            return e
        return None

    @checks.mod_or_permissions(administrator=True)
    @commands.guild_only()
    @commands.command(name="listreact")
    async def listreact(self, ctx):
        """List reactions for this server"""
        emojis = await self.conf.guild(ctx.guild).reactions()
        emojis_copy = copy.deepcopy(emojis)
        msg = f"Smart Reactions for {ctx.guild.name}:\n"
        for emoji, words in emojis_copy.items():
            e = self.fix_custom_emoji(emoji)
            if (not e) or (len(words) == 0):
                del emojis[emoji]
                continue
            for command in words:
                msg += f"{emoji}: {command}\n"
        await self.conf.guild(ctx.guild).reactions.set(emojis)
        if len(emojis) == 0:
            msg += "None."
        for page in pagify(msg, delims=["\n"]):
            await ctx.send(page)

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
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
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
                if not emoji:
                    return
                try:
                    await message.add_reaction(emoji)
                except (discord.errors.Forbidden, discord.errors.InvalidArgument, discord.errors.NotFound):
                    pass
                except discord.errors.HTTPException:
                    reactions = await self.conf.guild(guild).reactions()
                    if emoji in reactions:
                        del reactions[emoji]
                        await self.conf.guild(guild).reactions.set(reactions)
