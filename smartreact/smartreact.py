import os
import discord
import copy
from discord.ext import commands
from .utils.dataIO import dataIO


class SmartReact:

    """Create automatic reactions when trigger words are typed in chat"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/smartreact/settings.json"
        self.settings = dataIO.load_json(self.settings_path)
        self.NONWORDS = set(" ~!@#$%^?&*()_=+`'\"/.,;:\\|[]\{\}<>")

    @commands.command(name="addreact", no_pm=True, pass_context=True)
    async def addreact(self, ctx, *command):
        """Add an auto reaction to a word"""
        server = ctx.message.server
        message = ctx.message
        self.load_settings(server.id)

        trigger, emoji = parse_command(command)
        emoji = self.fix_custom_emoji(emoji)
        await self.create_smart_reaction(server, trigger, emoji, message)

    @commands.command(name="delreact", no_pm=True, pass_context=True)
    async def delreact(self, ctx, *command):
        """Delete an auto reaction to a word"""
        server = ctx.message.server
        message = ctx.message
        self.load_settings(server.id)

        trigger, emoji = parse_command(command)
        emoji = self.fix_custom_emoji(emoji)
        await self.remove_smart_reaction(server, trigger, emoji, message)

    def load_settings(self, server_id):
        self.settings = dataIO.load_json(self.settings_path)
        if server_id not in self.settings.keys():
            self.add_default_settings(server_id)

    def add_default_settings(self, server_id):
        self.settings[server_id] = {}
        dataIO.save_json(self.settings_path, self.settings)

    def fix_custom_emoji(self, emoji):
        try:
            if emoji[:2] != "<:":
                return emoji
            return [r for server in self.bot.servers for r in server.emojis if r.id == emoji.split(':')[2][:-1]][0]
        except IndexError:
            return None

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

    async def create_smart_reaction(self, server, word, emoji, message):
        try:
            # Use the reaction to see if it's valid
            await self.bot.add_reaction(message, emoji)
            if str(emoji) in self.settings[server.id]:
                if word.lower() in self.settings[server.id][str(emoji)]:
                    await self.bot.say("This smart reaction already exists.")
                    return
                self.settings[server.id][str(emoji)].append(word.lower())
            else:
                self.settings[server.id][str(emoji)] = [word.lower()]

            await self.bot.say("Successfully added this reaction.")
            dataIO.save_json(self.settings_path, self.settings)

        except (discord.errors.HTTPException, discord.errors.InvalidArgument):
            await self.bot.say("That's not an emoji I recognize.")

    async def remove_smart_reaction(self, server, word, emoji, message):
        try:
            # Use the reaction to see if it's valid
            await self.bot.add_reaction(message, emoji)
            if str(emoji) in self.settings[server.id]:
                if word.lower() in self.settings[server.id][str(emoji)]:
                    self.settings[server.id][str(emoji)].remove(word.lower())
                    await self.bot.say("Removed this smart reaction.")
                else:
                    await self.bot.say("That emoji is not used as a reaction "
                                       "for that word.")
            else:
                await self.bot.say("There are no smart reactions which use "
                                   "this emoji.")

            dataIO.save_json(self.settings_path, self.settings)

        except (discord.errors.HTTPException, discord.errors.InvalidArgument):
            await self.bot.say("That's not an emoji I recognize.")

    # Special thanks to irdumb#1229 on discord for helping me make this method
    # "more Pythonic"
    async def msg_listener(self, message):
        if message.author == self.bot.user:
            return
        if self.is_command(message):
            return
        server = message.server
        if server is None:
            return
        if server.id not in self.settings:
            return
        react_dict = copy.deepcopy(self.settings[server.id])
        msg_lower = message.content.lower()
        for emoji in react_dict:
            triggers = react_dict[emoji]
            # check each trigger, in order to avoid '"trigger"' not being recognized
            for trigger in triggers:
                if self.is_word_boundary(msg_lower, trigger):
                    fixed_emoji = self.fix_custom_emoji(emoji)
                    if fixed_emoji is not None:
                        await self.bot.add_reaction(message, fixed_emoji)

    # makes sure that the trigger is surrounded by word boundaries
    # such as $, ^, a non-alphanumeric, etc
    def is_word_boundary(self, string, trigger):
        i = string.find(trigger)
        if i == -1:
            return False
        if 0 < i:
            c = string[i-1]
            if c not in self.NONWORDS:
                return False
        # find character after trigger
        i += len(trigger)
        if i < len(string) - 1:
            c = string[i]
            if c not in self.NONWORDS:
                return False
        return True

def parse_command(command):
    trigger = " ".join(command[0:-1])
    emoji = command[-1]
    return trigger, emoji

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
