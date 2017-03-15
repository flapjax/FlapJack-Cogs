import discord
from discord.ext import commands
from cogs.utils import checks
from __main__ import send_cmd_help
from .utils.dataIO import dataIO
import asyncio
import os

# Credit to JennJenn#6857 for jokingly suggesting this cancer cog!
# I accept no responsibility for this.


class Msgvote:

    """Turn Discord into Reddit (not recommended)"""

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
            await self.bot.say("Msgvote mode in on in this channel.")

    @msgvote.command(name="off", pass_context=True, no_pm=True)
    async def _msgvote_off(self, ctx):
        """Turn off msgvote mode in the current channel"""

        channel = ctx.message.channel
        if channel.id not in self.settings["channels_enabled"]:
            await self.bot.say("Msgvote mode is already off in this channel.")
        else:
            self.settings["channels_enabled"].remove(channel.id)
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Msgvote mode is off in this channel.")

    @msgvote.command(name="upemoji", pass_context=True, no_pm=True)
    async def _msgvote_upemoji(self, ctx, emoji):
        """Set the upvote emoji"""

        emoji = str(self.fix_custom_emoji(emoji))
        self.settings["up_emoji"] = emoji
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Upvote emoji set to: " + emoji)

    @msgvote.command(name="downemoji", pass_context=True, no_pm=True)
    async def _msgvote_downemoji(self, ctx, emoji):
        """Set the downvote emoji"""

        emoji = str(self.fix_custom_emoji(emoji))
        self.settings["dn_emoji"] = emoji
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Downvote emoji set to: " + emoji)

    @msgvote.command(name="duration", pass_context=True, no_pm=True)
    async def _msgvote_duration(self, ctx, duration: int):
        """Set the duration in seconds for which votes will be monitored
        on each message. Must be an integer between 60-3600. For best results,
        make your duration divisible by the interval."""

        if 60 <= duration <= 3600:
            self.settings["duration"] = duration
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Duration set to: " + str(duration))
        else:
            await self.bot.say("Invalid duration. Must be an integer "
                               "between 60-3600.")

    @msgvote.command(name="interval", pass_context=True, no_pm=True)
    async def _msgvote_interval(self, ctx, interval: int):
        """Set the interval in seconds between checks for message votes
        on each message. Must be an integer between 1-60. For best results,
        make your duration divisible by the interval."""

        if 1 <= interval <= 60:
            self.settings["interval"] = interval
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Interval set to: " + str(interval))
        else:
            await self.bot.say("Invalid interval. Must be an integer "
                               "between 1-60.")

    @msgvote.command(name="threshold", pass_context=True, no_pm=True)
    async def _msgvote_threshold(self, ctx, threshold: int):
        """Set the threshold of [downvotes - upvotes] that must be
        reached for a message to be deleted. Must be a positive integer.
        Or, set to 0 to disable message deletion."""

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
                               "upvotes] exceeds {}.".format(threshold))

    def fix_custom_emoji(self, emoji):
        if emoji[:2] != "<:":
            return emoji
        return [r for server in self.bot.servers for r in server.emojis if r.id == emoji.split(':')[2][:-1]][0]

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

    # For high activity servers, it is probably better to accomplish this
    # through an on_reaction listener. I will change this soon.
    # I just wanted to experiment with tasks at the moment :)
    async def count_votes(self, channel, msg_id: str):
        timer = 0
        up_emoji = self.fix_custom_emoji(self.settings["up_emoji"])
        dn_emoji = self.fix_custom_emoji(self.settings["dn_emoji"])
        while timer < self.settings["duration"]:
            await asyncio.sleep(self.settings["interval"])
            timer += self.settings["interval"]
            # Count current votes
            msg = await self.bot.get_message(channel, msg_id)
            for reaction in msg.reactions:
                if reaction.emoji == up_emoji:
                    upvotes = reaction.count
                elif reaction.emoji == dn_emoji:
                    dnvotes = reaction.count

            if self.settings["threshold"] == 0:
                pass
            elif (dnvotes - upvotes) >= self.settings["threshold"]:
                try:
                    await self.bot.delete_message(msg)
                except discord.errors.Forbidden:
                    await self.bot.say("I require the 'manage messages' permission "
                                       "to delete downvoted messages!")
                return

    async def msg_listener(self, message):
        if message.channel.id not in self.settings["channels_enabled"]:
            return
        if message.author == self.bot.user:
            return
        if self.is_command(message):
            return
        try:
            await self.bot.add_reaction(message, self.fix_custom_emoji(self.settings["up_emoji"]))
            await self.bot.add_reaction(message, self.fix_custom_emoji(self.settings["dn_emoji"]))
            self.bot.loop.create_task(self.count_votes(message.channel, message.id))
        except discord.errors.HTTPException:
            # Implement a non-spammy way to alert users in future
            pass


def check_folders():
    folder = "data/msgvote"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {"channels_enabled": [], "duration": 300, "threshold": 3,
               "interval": 5, "up_emoji": "\u2b06", "dn_emoji": "\u2b07"}
    if not dataIO.is_valid_json("data/msgvote/settings.json"):
        print("Creating default msgvote settings.json...")
        dataIO.save_json("data/msgvote/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    n = Msgvote(bot)
    bot.add_cog(n)
    bot.add_listener(n.msg_listener, "on_message")
