import asyncio
import os
from datetime import datetime

import discord
from discord.ext import commands

from __main__ import send_cmd_help
from cogs.utils import checks

from .utils.dataIO import dataIO

# Credit to JennJenn#6857 for thinking up this cog.
# It started as a joke, and people actualy use it! Who knew?


class Msgvote:

    """Turn Discord channels into Reddit-like threads"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/msgvote/settings.json"
        self.settings = dataIO.load_json(self.settings_path)

    @commands.group(name="msgvote", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def msgvote(self, ctx):
        """Msgvote cog settings"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @msgvote.command(name="on", pass_context=True, no_pm=True)
    async def _msgvote_on(self, ctx):
        """Turn on msgvote mode in the current channel"""

        channel = ctx.message.channel
        if channel.id in self.settings["channels_enabled"]:
            await self.bot.say("Msgvote mode is already on in this channel.")
        else:
            self.settings["channels_enabled"].append(channel.id)
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Msgvote mode is now on in this channel.")

    @msgvote.command(name="off", pass_context=True, no_pm=True)
    async def _msgvote_off(self, ctx):
        """Turn off msgvote mode in the current channel"""

        channel = ctx.message.channel
        if channel.id not in self.settings["channels_enabled"]:
            await self.bot.say("Msgvote mode is already off in this channel.")
        else:
            self.settings["channels_enabled"].remove(channel.id)
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Msgvote mode is now off in this channel.")

    @msgvote.command(name="bot", pass_context=True, no_pm=True)
    async def _msgvote_bot(self, ctx):
        """Turn on/off reactions to bot's own messages"""

        if self.settings.get("bot", False):
            self.settings["bot"] = False
            await self.bot.say("Reactions to bot messages turned OFF.")
        else:
            self.settings["bot"] = True
            await self.bot.say("Reactions to bot messages turned ON.")
        dataIO.save_json(self.settings_path, self.settings)

    @msgvote.command(name="upemoji", pass_context=True, no_pm=True)
    async def _msgvote_upemoji(self, ctx, emoji):
        """Set the upvote emoji"""

        emoji = str(self.fix_custom_emoji(ctx.message.server, emoji))
        self.settings["up_emoji"] = emoji
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Upvote emoji set to: " + emoji)

    @msgvote.command(name="downemoji", pass_context=True, no_pm=True)
    async def _msgvote_downemoji(self, ctx, emoji):
        """Set the downvote emoji"""

        emoji = str(self.fix_custom_emoji(ctx.message.server, emoji))
        self.settings["dn_emoji"] = emoji
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Downvote emoji set to: " + emoji)

    @msgvote.command(name="duration", pass_context=True, no_pm=True)
    async def _msgvote_duration(self, ctx, duration: int):
        """Set the duration in seconds for which votes will be monitored
        on each message."""

        if duration > 0:
            self.settings["duration"] = duration
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("I will monitor each message's votes until it "
                               "is {} seconds old.".format(duration))
        else:
            await self.bot.say("Invalid duration. Must be a positive integer.")

    @msgvote.command(name="threshold", pass_context=True, no_pm=True)
    async def _msgvote_threshold(self, ctx, threshold: int):
        """Set the threshold of [downvotes - upvotes] for msg deletion.
        Must be a positive integer. Or, set to 0 to disable deletion."""

        if threshold < 0:
            await self.bot.say("Invalid threshold. Must be a positive "
                               "integer, or 0 to disable.")
        elif threshold == 0:
            self.settings["threshold"] = threshold
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Message deletion disabled.")
        else:
            self.settings["threshold"] = threshold
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Messages will be deleted if [downvotes - "
                               "upvotes] reaches {}.".format(threshold))

    def fix_custom_emoji(self, server, emoji):
        if emoji[:2] != "<:":
            return emoji
        return [r for r in server.emojis if r.name == emoji.split(':')[1]][0]

    # From Twentysix26's trigger.py cog
    def is_command(self, msg):
        if callable(self.bot.command_prefix):
            prefixes = self.bot.command_prefix(self.bot, msg)
        else:
            prefixes = self.bot.command_prefix
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False

    async def on_message(self, message):
        if message.channel.id not in self.settings["channels_enabled"]:
            return
        if message.author == self.bot.user and not self.settings.get("bot", False):
            return
        if self.is_command(message):
            return
        try:
            up_emoji = self.fix_custom_emoji(message.server,
                                             self.settings["up_emoji"])
            dn_emoji = self.fix_custom_emoji(message.server,
                                             self.settings["dn_emoji"])
            await self.bot.add_reaction(message, up_emoji)
            await asyncio.sleep(0.5)
            await self.bot.add_reaction(message, dn_emoji)
        except discord.errors.HTTPException:
            # Implement a non-spammy way to alert users in future
            pass

    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user:
            return
        await self.count_votes(reaction)

    async def on_reaction_remove(self, reaction, user):
        if user == self.bot.user:
            return
        await self.count_votes(reaction)

    async def count_votes(self, reaction):
        message = reaction.message
        if self.settings["threshold"] == 0:
            return
        if message.channel.id not in self.settings["channels_enabled"]:
            return
        up_emoji = self.fix_custom_emoji(message.server,
                                         self.settings["up_emoji"])
        dn_emoji = self.fix_custom_emoji(message.server,
                                         self.settings["dn_emoji"])
        if reaction.emoji not in (up_emoji, dn_emoji):
            return
        age = (datetime.utcnow() - message.timestamp).total_seconds()
        if age > self.settings["duration"]:
            return
        # We have a valid vote so we can count the votes now
        for react in message.reactions:
            if react.emoji == up_emoji:
                upvotes = react.count
            elif react.emoji == dn_emoji:
                dnvotes = react.count
        if (dnvotes - upvotes) >= self.settings["threshold"]:
            try:
                await self.bot.delete_message(message)
            except discord.errors.Forbidden:
                await self.bot.send_message(channel, "I require the 'Manage "
                                            "Messages' permission to delete "
                                            "downvoted messages!")


def check_folders():
    folder = "data/msgvote"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {"channels_enabled": [], "duration": 300, "threshold": 3,
               "up_emoji": "\ud83d\udc4d",
               "dn_emoji": "\ud83d\udc4e"}
    if not dataIO.is_valid_json("data/msgvote/settings.json"):
        print("Creating default msgvote settings.json...")
        dataIO.save_json("data/msgvote/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Msgvote(bot))
