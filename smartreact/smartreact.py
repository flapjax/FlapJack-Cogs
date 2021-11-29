import asyncio
import copy
import discord
import re

from redbot.core import Config, commands, checks
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate


EMOJI_RE = re.compile("(<a?)?:\\w+:(\\d{18}>)?")
EMOJI_ID_RE = re.compile("\\d{18}")


class SmartReact(commands.Cog):
    """Create automatic reactions when trigger words are typed in chat."""

    default_guild_settings = {"reactions": {}}

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=964952632)
        self.conf.register_guild(**self.default_guild_settings)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    @checks.mod_or_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.guild_only()
    @commands.command()
    async def addreact(self, ctx, word, emoji):
        """
        Add an auto reaction to a word.

        The `emoji` can be either the emoji itself, or in the case of a custom emoji, the ID.
        """
        emoji = self.fix_custom_emoji(emoji)
        await self.create_smart_reaction(ctx.guild, word, emoji, ctx.message)

    @checks.mod_or_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.guild_only()
    @commands.command()
    async def delreact(self, ctx, word, emoji):
        """
        Delete an auto reaction to a word.

        The `emoji` can be either the emoji itself, or in the case of a custom emoji, the ID.
        """
        emoji = self.fix_custom_emoji(emoji)
        await self.remove_smart_reaction(ctx.guild, word, emoji, ctx.message)

    @checks.mod_or_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.guild_only()
    @commands.command()
    async def delallreact(self, ctx):
        """Delete ALL smart reactions in the server."""
        msg = await ctx.send("Are you sure you want to clear **ALL** smart reactions in this guild?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await ctx.bot.wait_for("reaction_add", check=pred, timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("Response timed out. Please run this command again if you wish to try again.")

        if pred.result is True:
            await self.conf.guild(ctx.guild).clear()
            return await ctx.send("Done. All reactions for this server have been cleared.")
        else:
            return await ctx.send("Alright, I'm not clearing all reactions in this server.")

    def fix_custom_emoji(self, emoji):
        # custom emoji id
        if re.match(EMOJI_ID_RE, emoji):
            e = self.bot.get_emoji(int(emoji))
            if e:
                return e

        # default emoji
        custom_emoji_match = EMOJI_RE.search(emoji)
        if not custom_emoji_match:
            return emoji

        # animated or static custom emoji
        e = emoji.split(":")[2][:-1].strip()
        try:
            e = self.bot.get_emoji(int(e))
        except ValueError:
            return None
        if e:
            return e

        # or, nothing matched
        return None

    @checks.mod_or_permissions(administrator=True)
    @commands.guild_only()
    @commands.command(name="listreact")
    async def listreact(self, ctx):
        """List smart reactions for this server."""
        emojis = await self.conf.guild(ctx.guild).reactions()
        emojis_copy = copy.deepcopy(emojis)
        emojis_copy = {k: v for k, v in sorted(emojis_copy.items(), key=lambda item: item[1])}
        msg = f"Smart Reactions for {ctx.guild.name}:\n"
        for emoji, words in emojis_copy.items():
            e = self.fix_custom_emoji(emoji)
            if (not e) or (len(words) == 0):
                del emojis[emoji]
                continue
            for command in words:
                custom_emoji_match = EMOJI_RE.search(emoji)
                if custom_emoji_match:
                    custom_emoji_id = custom_emoji_match.group(2).rstrip(">")
                    msg += f"{emoji} `{custom_emoji_id}`: {command}\n"
                else:
                    msg += f"{emoji} `Default emoji`: {command}\n"
        await self.conf.guild(ctx.guild).reactions.set(emojis)
        if len(emojis) == 0:
            msg += "None."
        for page in pagify(msg, delims=["\n"]):
            await ctx.send(page, allowed_mentions=discord.AllowedMentions(users=False, everyone=False, roles=False))

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
            await message.channel.send("That's not an emoji I recognize. " "(might be custom!)")

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
                    await message.channel.send("That emoji is not used as a reaction for that word.")
            else:
                await message.channel.send("There are no smart reactions which use this emoji.")
        except (discord.errors.HTTPException, discord.errors.InvalidArgument):
            await message.channel.send("That's not an emoji I recognize. (might be custom!)")

    # Thanks irdumb#1229 for the help making this "more Pythonic"
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if not message.channel.permissions_for(message.guild.me).add_reactions:
            return
        if message.author.id == self.bot.user.id:
            return
        reacts = copy.deepcopy(await self.conf.guild(message.guild).reactions())
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
                    if emoji in reacts:
                        del reacts[emoji]
                        await self.conf.guild(message.guild).reactions.set(reacts)
