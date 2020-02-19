import asyncio
import discord
import random
import string
import logging

from typing import Dict, Optional, List
from datetime import datetime, timedelta

from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_timedelta, pagify
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

log = logging.getLogger("red.flapjackcogs.reactpoll")


class Poll:
    """A new reaction poll"""

    def __init__(self, bot, **kwargs):
        self.duration: Optional[timedelta] = kwargs.get("duration")
        self.tally: Dict[str, List[int]] = kwargs.get("tally", {})
        # Thanks 26 remindme.py
        # Following are needed to reconstruct a poll
        self.author_id: int = kwargs.get("author_id")
        self.channel_id: int = kwargs.get("channel_id")
        self.message_id: Optional[int] = kwargs.get("message_id", None)
        self.question: str = kwargs.get("question")
        self.emojis: Dict[str, str] = kwargs.get("emojis", {})
        if not self.emojis:
            self.emojis = kwargs.get("emoji", {})
        self.options: List[str] = kwargs.get("options")
        self.end_time: Optional[datetime] = kwargs.get(
            "end_time", self.parse_duration(self.duration)
        )
        self.embed: bool = kwargs.get("embed", True)
        self.interactive: bool = kwargs.get("interactive", False)
        self.multiple_votes: bool = kwargs.get("multiple_votes", False)
        self._bot: Red = bot

    def as_dict(self):
        # for JSON serialization. This dict completely defines a poll.
        return {
            "author_id": self.author_id,
            "channel_id": self.channel_id,
            "message_id": self.message_id,
            "question": self.question,
            "options": self.options,
            "emojis": self.emojis,
            "end_time": self.end_time.timestamp() if self.end_time else None,
            "tally": self.tally,
            "embed": self.embed,
            "multiple_votes": self.multiple_votes
        }

    def parse_duration(self, duration: Optional[timedelta] = None) -> Optional[datetime]:
        # use remindme parsing for now
        if duration:
            return datetime.utcnow() + duration
        else:
            return None

    async def add_vote(self, user_id: int, emoji: str):
        # log.info("Adding vote")
        member = self.channel.guild.get_member(int(user_id))
        if emoji not in self.emojis:
            # attempt to remove emoji and DM use not to clutter the poll
            if self.channel.permissions_for(self.guild.me).manage_messages:
                old_msg = await self.get_message()
                try:
                    await old_msg.remove_reaction(emoji, member)
                except Exception:
                    pass
            if member:
                try:
                    await member.send("Don't clutter the poll.")
                except discord.errors.Forbidden:
                    pass
            return
        if not self.multiple_votes:
            for e in self.tally:
                if user_id in self.tally[e] and emoji != e:
                    # DM user telling them their vote has changed
                    if self.channel.permissions_for(self.guild.me).manage_messages:
                        old_msg = await self.get_message()
                        self.tally[e].remove(user_id)
                        try:
                            await old_msg.remove_reaction(e, member)
                        except Exception:
                            pass
                    if member:
                        try:
                            await member.send(
                                f"You've already voted on `{self.question}`, changing vote to {emoji}."
                            )
                        except discord.errors.Forbidden:
                            pass
            if user_id not in self.tally[emoji]:
                self.tally[emoji].append(user_id)

        else:
            if user_id not in self.tally[emoji]:
                self.tally[emoji].append(user_id)

    async def remove_vote(self, user_id: int, emoji: str):
        if user_id in self.tally[emoji]:
            self.tally[emoji].remove(user_id)

    @property
    def bot(self):
        return self._bot

    @property
    def channel(self):
        return self.bot.get_channel(self.channel_id)

    @property
    def guild(self):
        return self.channel.guild

    @property
    def author(self):
        return self.guild.get_member(self.author_id)

    async def get_message(self):
        channel = self.channel
        if not channel:
            return None
        try:
            message = await channel.fetch_message(self.message_id)
        except discord.errors.HTTPException:
            return None
        return message

    async def get_colour(self, channel: discord.TextChannel):
        try:
            if await self.bot.db.guild(channel.guild).use_bot_color():
                return channel.guild.me.colour
            else:
                return await self.bot.db.color()
        except AttributeError:
            return await self.bot.get_embed_colour(channel)

    async def build_poll(self):
        # Starting codepoint for keycap number emoji (\u0030... == 0)
        base_emoji = ReactionPredicate.NUMBER_EMOJIS + ReactionPredicate.ALPHABET_EMOJIS
        msg = "**POLL STARTED!**\n\n{}\n\n".format(self.question)
        option_num = 1
        option_msg = ""
        if not self.interactive:
            for option in self.options:
                emoji = base_emoji[option_num]
                self.emojis[emoji] = option
                option_msg += f"**{option_num}**. {option}\n"
                option_num += 1
        else:
            for emoji, option in self.emojis.items():
                option_msg += f"{emoji}. {option}\n"
        if not self.tally:
            self.tally = {e: [] for e in self.emojis}
        msg += option_msg
        msg += "\nSelect the number to vote!"
        if self.duration:
            msg += f"\nPoll closes in {humanize_timedelta(timedelta=self.duration)}"

        em = discord.Embed(colour=await self.get_colour(self.channel))
        em.title = "POLL STARTED!"
        first = True
        for page in pagify(f"{self.question}\n\n{option_msg}", page_length=1024):
            if first:
                em.description = page
                first = False
            else:
                em.add_field(name="Options continued", value=page)
        end = ""
        if self.duration:
            end = "| ends at"
        em.set_footer(
            text=f"{self.author} created a poll {end}", icon_url=str(self.author.avatar_url),
        )
        if self.end_time:
            em.timestamp = self.end_time
        return msg, em

    async def open_poll(self):
        msg, em = await self.build_poll()
        if not self.embed:
            for page in pagify(msg):
                message = await self.channel.send(page)
        else:
            message = await self.channel.send(embed=em)
        self.message_id = message.id
        self.end_time = self.parse_duration(self.duration)
        start_adding_reactions(message, self.emojis.keys())

    async def close_poll(self):

        msg = "**POLL ENDED!**\n\n"
        try:
            old_msg = await self.get_message()

            if old_msg:
                for reaction in old_msg.reactions:
                    async for user in reaction.users():
                        if user.bot:
                            continue
                        if str(reaction.emoji) not in self.emojis:
                            continue
                        if user.id not in self.tally[str(reaction.emoji)]:
                            self.tally[str(reaction.emoji)].append(user.id)
                await old_msg.clear_reactions()
        except (discord.errors.Forbidden, discord.errors.NotFound):
            log.error("Cannot find message")
            pass
        except Exception:
            log.error("error tallying results", exc_info=True)

        em = discord.Embed(colour=await self.get_colour(self.channel))
        em.title = "**POLL ENDED**"
        # This is handled with fuck-all efficiency, but it works for now -Ruined1
        if sum(len(v) for k, v in self.tally.items()) == 0:
            msg += "***NO ONE VOTED.***\n"
            try:
                if self.embed:
                    await self.channel.send(msg)
                else:
                    em.description = f"{self.question}\n\n***NO ONE VOTED.***\n"
                    await self.channel.send(embed=em)
            except (discord.errors.Forbidden, discord.errors.NotFound, AttributeError):
                pass
        votes_msg = f"{self.question}\n\n**Results**\n"
        for e, vote in sorted(self.tally.items(), key=lambda x: len(x[1]), reverse=True):
            votes_msg += f"{self.emojis[e]}: {len(vote)}\n"
        msg += votes_msg
        first = True
        for page in pagify(votes_msg, page_length=1024):
            if first:
                em.description = page
                first = False
            else:
                em.add_field(name="Results continued", value=page)
        try:
            if not self.embed:
                for page in pagify(msg):
                    await self.channel.send(page)
            else:
                await self.channel.send(embed=em)
        except (discord.errors.Forbidden, discord.errors.NotFound, AttributeError):
            pass
