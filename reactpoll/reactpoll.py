import asyncio
import random
import string
import time

from redbot.core import Config, checks, commands

BaseCog = getattr(commands, "Cog", object)


class NewPoll:
    """A new reaction poll"""

    def __init__(self, ctx, main, question: str, options: str, duration: str):
        self.duration = None
        self.main = main
        self.tally = []
        # Thanks 26 remindme.py
        self.units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800, "month": 2592000}
        # Following are needed to reconstruct a poll
        self.author_id = ctx.author.id
        self.channel_id = ctx.channel.id
        self.message_id = None
        self.question = question
        self.emoji = []
        self.options = self.parse_options(options)
        self.end_time = self.parse_duration(duration)
        self.id = self.generate_id()

    def as_dict(self):
        # for JSON serialization. This dict completely defines a poll.
        return {
            'author': self.author_id,
            'channel': self.channel_id,
            'message': self.message_id,
            'question': self.question,
            'options': self.options,
            'emoji': self.emoji,
            'end_time': self.end_time,
            'id': self.id
        }

    def generate_id(self):
        return ''.join(random.choice(
                       string.ascii_uppercase) for i in range(5))

    def parse_duration(self, text):
        # use remindme parsing for now
        text = text.replace(" ", "")

        idx = 0
        for char in text:
            if char.isdigit():
                idx += 1
            else:
                break

        value = int(text[:idx])
        unit = text[idx:].lower()

        if unit == "s":
            unit = "second"
        elif unit.endswith("s"):
            unit = unit[:-1]
        if unit not in self.units:
            return None
        if value < 1:
            return None

        self.duration = self.units[unit] * value
        return int(time.time() + self.duration)

    def parse_options(self, text):
        return [opt.strip() for opt in text.split(";")]

    @property
    async def message(self):
        message = await self.channel.get_message(self.message_id)
        return message

    @property
    def channel(self):
        return self.main.bot.get_channel(self.channel_id)

    @property
    def author(self):
        return self.main.bot.get_user(self.author_id)

    def is_valid(self):
        return False if self.end_time is None or not self.options else True

    async def open_poll(self):
        # Starting codepoint for keycap number emoji (\u0030... == 0)
        base_emoji = [ord('\u0030'), ord('\u20E3')]
        msg = "**POLL STARTED!**\n\n{}\n\n".format(self.question)
        option_num = 1
        for option in self.options:
            base_emoji[0] += 1
            self.emoji.append(chr(base_emoji[0]) + chr(base_emoji[1]))
            msg += f"**{option_num}**. {option}\n".format(option)
            option_num += 1

        msg += ("\nSelect the number to vote!"
                "\nPoll closes in {} seconds.".format(self.duration))
        message = await self.channel.send(msg)
        self.message_id = message.id
        for emoji in self.emoji:
            await message.add_reaction(emoji)
            await asyncio.sleep(0.5)

    async def close_poll(self):
        message = await self.message
        msg = "**POLL ENDED!**\n\n{}\n\n".format(self.question)
        for reaction in message.reactions:
            if reaction.emoji in self.emoji:
                self.tally.append(reaction.count - 1)
        await message.clear_reactions()
        winner_idx = self.tally.index(max(self.tally))

        #This is handled with fuck-all efficiency, but it works for now -Ruined1
        if self.tally[winner_idx] == 0:
            msg += "***NO ONE VOTED.***\n"
            await self.channel.send(msg)
            return

        for idx, option in enumerate(self.options):
            if idx == winner_idx:
                if self.tally.count(self.tally[idx]) > 1:
                    msg += "**TIE: \n{}** - {} votes\n".format(option, self.tally[idx])
                else:
                    msg += "**WINNER: \n{}** - {} votes\n".format(option, self.tally[idx])
            else:
                if self.tally.count(self.tally[idx]) > 1 and self.tally[idx] == self.tally[winner_idx]:
                    msg += "**TIE: \n{}** - {} votes\n".format(option, self.tally[idx])
                else:
                    msg += "{} - {} votes\n".format(option, self.tally[idx])
        await self.channel.send(msg)


class LoadedPoll(NewPoll):
    """A reaction poll loaded from disk"""

    def __init__(self, main, poll):
        self.main = main
        self.tally = []
        # Following are needed to reconstruct a poll
        self.author_id = poll['author']
        self.channel_id = poll['channel']
        self.message_id = poll['message']
        self.question = poll['question']
        self.options = poll['options']
        self.emoji = poll['emoji']
        self.end_time = poll['end_time']
        self.id = poll['id']


class ReactPoll(BaseCog):
    """Commands for Reaction Polls"""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=1148673908)
        default_global_settings = {
            'polls': []
        }
        self.conf.register_global(
            **default_global_settings
        )
        self.polls = []
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.load_polls())
        self.poll_task = self.loop.create_task(self.poll_closer())

    def __unload(self):     
        self.poll_task.cancel()

    async def poll_closer(self):
        while True:
            # consider making < 60 second polls not use config + this task
            await asyncio.sleep(1)
            now_time = time.time()
            for poll in self.polls:
                if poll.end_time <= now_time:
                    await poll.close_poll()
                    # probs a better way to do this
                    self.polls.remove(poll)
                    # also need to delete from config
                    await self.delete_poll(poll)

    async def delete_poll(self, poll: NewPoll):
        async with self.conf.polls() as polls:
            for existing_poll in polls:
                if poll.id == existing_poll['id']:
                    polls.remove(existing_poll)

    async def store_poll(self, poll: NewPoll):
        async with self.conf.polls() as polls:
            polls.append(poll.as_dict())

    async def load_polls(self):
        # unfortunately we have to deal with an issue where JSON
        # serialization fails if the config default list is used
        polls = await self.conf.polls()
        if not polls:
            await self.conf.polls.set([])
            return
        else:
            for poll in polls:
                load_poll = LoadedPoll(self, poll)
                if load_poll.is_valid():
                    self.polls.append(load_poll)

    @commands.guild_only()
    @commands.command(name='rpoll')
    async def rpoll(self, ctx: commands.Context, question: str,
                    options: str, duration: str='60s'):
        """Start a reaction poll
        Usage example (time argument is optional)
        [p]rpoll "Is this a poll?" "Yes;No;Maybe" "60s"
        """
        message = ctx.message
        channel = ctx.channel
        guild = ctx.guild

        if not channel.permissions_for(guild.me).manage_messages:
            return await ctx.send("I require the 'Manage Messages' "
                           "permission in this channel to conduct "
                           "a reaction poll.")
            
        option_count = options.split(";")
        if len(option_count) > 9:
            return await ctx.send("Use less options for the poll. Max options: 9.")

        poll = NewPoll(ctx, self, question, options, duration)

        if poll.is_valid():
            await poll.open_poll()
            self.polls.append(poll)
            await self.store_poll(poll)
        else:
            await ctx.send('Poll was not valid.')
