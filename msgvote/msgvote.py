import asyncio
from datetime import datetime

import discord
from discord.ext import commands

#from __main__ import send_cmd_help
from core import checks
from core.utils import helpers


# Credit to JennJenn#6857 for thinking up this cog.
# It started as a joke, and people actualy use it! Who knew?


class MsgVote:

    """Turn Discord channels into Reddit-like threads"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = helpers.JsonDB("data/settings.json")
        # Not a huge fan of this, just experimenting
        if not self.settings.all():
            bot.loop.create_task(self._set_defaults())

    async def _set_defaults(self):
        default_settings = {"channels_enabled": [],
                            "bot": False,
                            "duration": 300,
                            "threshold": 3,
                            "up_emoji": "\ud83d\udc4d",
                            "dn_emoji": "\ud83d\udc4e"}
        for key, val in default_settings.items():
            await self.settings.set(key, val)

    @commands.group(name="msgvote", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def msgvote(self, ctx):
        """Msgvote cog settings"""

        #if ctx.invoked_subcommand is None:
        #    await send_cmd_help(ctx)

    @msgvote.command(name="on", pass_context=True, no_pm=True)
    async def _msgvote_on(self, ctx):
        """Turn on msgvote mode in the current channel"""

        channel_id = str(ctx.message.channel.id)
        entry = self.settings.get("channels_enabled", [])
        if channel_id in entry:
            await ctx.send("Msgvote mode is already on in this channel.")
        else:
            entry.append(channel_id)
            await self.settings.set("channels_enabled", entry)
            await ctx.send("Msgvote mode is now on in this channel.")

    @msgvote.command(name="off", pass_context=True, no_pm=True)
    async def _msgvote_off(self, ctx):
        """Turn off msgvote mode in the current channel"""

        channel_id = str(ctx.message.channel.id)
        entry = self.settings.get("channels_enabled", [])
        if channel_id not in entry:
            await ctx.send("Msgvote mode is already off in this channel.")
        else:
            entry.remove(channel_id)
            await self.settings.set("channels_enabled", entry)
            await ctx.send("Msgvote mode is now off in this channel.")

    @msgvote.command(name="bot", pass_context=True, no_pm=True)
    async def _msgvote_bot(self, ctx):
        """Turn on/off reactions to bot's own messages"""

        if self.settings.get("bot"):
            await self.settings.set("bot", False)
            await ctx.send("Reactions to bot messages turned OFF.")
        else:
            await self.settings.set("bot", True)
            await ctx.send("Reactions to bot messages turned ON.")

    @msgvote.command(name="upemoji", pass_context=True, no_pm=True)
    async def _msgvote_upemoji(self, ctx, emoji):
        """Set the upvote emoji"""

        emoji = self.fix_custom_emoji(emoji)
        if emoji is None:
            await ctx.send("That's not a valid emoji.")
            return
        await self.settings.set("up_emoji", str(emoji))
        await ctx.send("Upvote emoji set to: " + str(emoji))

    @msgvote.command(name="downemoji", pass_context=True, no_pm=True)
    async def _msgvote_downemoji(self, ctx, emoji):
        """Set the downvote emoji"""

        emoji = self.fix_custom_emoji(emoji)
        if emoji is None:
            await ctx.send("That's not a valid emoji.")
            return
        await self.settings.set("dn_emoji", str(emoji))
        await ctx.send("Downvote emoji set to: " + str(emoji))

    @msgvote.command(name="duration", pass_context=True, no_pm=True)
    async def _msgvote_duration(self, ctx, duration: int):
        """Set the duration in seconds for which votes will be monitored
        on each message."""

        if duration > 0:
            await self.settings.set("duration", duration)
            await ctx.send("I will monitor each message's votes until it "
                           "is {} seconds old.".format(duration))
        else:
            await ctx.send("Invalid duration. Must be a positive integer.")

    @msgvote.command(name="threshold", pass_context=True, no_pm=True)
    async def _msgvote_threshold(self, ctx, threshold: int):
        """Set the threshold of [downvotes - upvotes] for msg deletion.
        Must be a positive integer. Or, set to 0 to disable deletion."""

        if threshold < 0:
            await ctx.send("Invalid threshold. Must be a positive "
                           "integer, or 0 to disable.")
        elif threshold == 0:
            await self.settings.set("threshold", threshold)
            await ctx.send("Message deletion disabled.")
        else:
            await self.settings.set("threshold", threshold)
            await ctx.send("Messages will be deleted if [downvotes - "
                           "upvotes] reaches {}.".format(threshold))

    def fix_custom_emoji(self, emoji):
        if emoji[:2] != "<:":
            return emoji
        for guild in self.bot.guilds:
            for e in guild.emojis:
                if str(e.id) == emoji.split(':')[2][:-1]:
                    return e
        return None

    async def on_message(self, message):
        if str(message.channel.id) not in self.settings.get("channels_enabled", []):
            return
        if message.author.id == self.bot.user.id and not self.settings.get("bot", False):
            return
        # Still need to fix error (discord.errors.NotFound) on first run of cog
        # must be due to the way the emoji is stored in settings/json
        try:
            up_emoji = self.fix_custom_emoji(self.settings.get("up_emoji"))
            dn_emoji = self.fix_custom_emoji(self.settings.get("dn_emoji"))
            await message.add_reaction(up_emoji)
            await asyncio.sleep(0.5)
            await message.add_reaction(dn_emoji)
        except discord.errors.HTTPException:
            # Implement a non-spammy way to alert users in future
            pass

    async def on_reaction_add(self, reaction, user):
        if user.id == self.bot.user.id:
            return
        await self.count_votes(reaction)

    async def on_reaction_remove(self, reaction, user):
        if user.id == self.bot.user.id:
            return
        await self.count_votes(reaction)

    async def count_votes(self, reaction):
        message = reaction.message
        if not reaction.me:
            return
        if self.settings.get("threshold", 3) == 0:
            return
        if str(message.channel.id) not in self.settings.get("channels_enabled", []):
            return
        up_emoji = self.fix_custom_emoji(self.settings.get("up_emoji"))
        dn_emoji = self.fix_custom_emoji(self.settings.get("dn_emoji"))
        if reaction.emoji not in (up_emoji, dn_emoji):
            return
        age = (datetime.utcnow() - message.created_at).total_seconds()
        print('age was {}'.format(str(age)))
        if age > self.settings.get("duration", 300):
            return
        # We have a valid vote so we can count the votes now
        upvotes = 0
        dnvotes = 0
        for react in message.reactions:
            if react.emoji == up_emoji:
                upvotes = react.count
            elif react.emoji == dn_emoji:
                dnvotes = react.count
        if (dnvotes - upvotes) >= self.settings.get("threshold", 3):
            try:
                await message.delete()
            except discord.errors.Forbidden:
                await message.channel.send("I require the 'Manage "
                                           "Messages' permission to delete "
                                           "downvoted messages!")
