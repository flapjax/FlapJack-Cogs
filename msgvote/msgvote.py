import asyncio
from datetime import datetime

import discord
from redbot.core import Config, checks, commands

# Credit to JennJenn#6857 for thinking up this cog.
# It started as a joke, and people actualy use it! Who knew?


class MsgVote(commands.Cog):
    """Turn Discord channels into Reddit-like threads"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=494641511)

        default_guild = {
            "channels_enabled": [],
            "bot_react": False,
            "duration": 300,
            "threshold": 3,
            "up_emoji": "👍",
            "dn_emoji": "👎",
        }
        self.config.register_guild(**default_guild)

    @commands.group(autohelp=False)
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def msgvote(self, ctx):
        """Msgvote cog settings"""

        if ctx.invoked_subcommand is None:
            await ctx.send_help()

            guild_data = await self.config.guild(ctx.guild).all()
            bad_channels = []
            msg = "Active Channels:\n"
            if not guild_data["channels_enabled"]:
                msg += "None."
            else:
                channel_list = []
                for chan_id in guild_data["channels_enabled"]:
                    channel_obj = self.bot.get_channel(chan_id)
                    if hasattr(channel_obj, 'name'):
                        channel_list.append(channel_obj)
                    else:
                        bad_channels.append(chan_id)
                if not channel_list:
                    msg = "None."
                else:
                    msg += "\n".join(chan.name for chan in channel_list)

            msg += f"\nBot message reactions: {guild_data['bot_react']}\nListening duration: {guild_data['duration']}s\nVote threshold: {guild_data['threshold']} votes\nUp/down emojis: {guild_data['up_emoji']} / {guild_data['dn_emoji']}"

            embed = discord.Embed(colour=await ctx.embed_colour(), description=msg)
            await ctx.send(embed=embed)

            if bad_channels:
                new_channel_list = [x for x in guild_data["channels_enabled"] if x not in bad_channels]
                await self.config.guild(ctx.guild).channels_enabled.set(new_channel_list)

    @msgvote.command(name="on")
    async def _msgvote_on(self, ctx):
        """Turn on msgvote mode in the current channel"""

        channel_id = ctx.message.channel.id
        channels = await self.config.guild(ctx.guild).channels_enabled()
        if not channels:
            await self.config.guild(ctx.guild).channels_enabled.set([])

        if channel_id in channels:
            await ctx.send("Msgvote mode is already on in this channel.")
        else:
            channels.append(channel_id)
            await self.config.guild(ctx.guild).channels_enabled.set(channels)
            await ctx.send("Msgvote mode is now on in this channel.")

    @msgvote.command(name="off")
    async def _msgvote_off(self, ctx):
        """Turn off msgvote mode in the current channel"""

        channel_id = ctx.message.channel.id
        channels = await self.config.guild(ctx.guild).channels_enabled()
        if not channels:
            await self.config.guild(ctx.guild).channels_enabled.set([])
        if channel_id not in channels:
            await ctx.send("Msgvote mode is already off in this channel.")
        else:
            channels.remove(channel_id)
            await self.config.guild(ctx.guild).channels_enabled.set(channels)
            await ctx.send("Msgvote mode is now off in this channel.")

    @msgvote.command(name="bot")
    async def _msgvote_bot(self, ctx):
        """Turn on/off reactions to bot's own messages"""

        if await self.config.guild(ctx.guild).bot_react():
            await self.config.guild(ctx.guild).bot_react.set(False)
            await ctx.send("Reactions to bot messages turned OFF.")
        else:
            await self.config.guild(ctx.guild).bot_react.set(True)
            await ctx.send("Reactions to bot messages turned ON.")

    @msgvote.command(name="upemoji")
    async def _msgvote_upemoji(self, ctx, emoji):
        """Set the upvote emoji"""

        emoji = self.fix_custom_emoji(emoji)
        if emoji is None:
            await ctx.send("That's not a valid emoji.")
            return
        await self.config.guild(ctx.guild).up_emoji.set(str(emoji))
        await ctx.send("Upvote emoji set to: " + str(emoji))

    @msgvote.command(name="downemoji")
    async def _msgvote_downemoji(self, ctx, emoji):
        """Set the downvote emoji"""

        emoji = self.fix_custom_emoji(emoji)
        if emoji is None:
            await ctx.send("That's not a valid emoji.")
            return
        await self.config.guild(ctx.guild).dn_emoji.set(str(emoji))
        await ctx.send("Downvote emoji set to: " + str(emoji))

    @msgvote.command(name="duration")
    async def _msgvote_duration(self, ctx, duration: int):
        """Set the duration in seconds for which votes will be monitored
        on each message."""

        if duration > 0:
            await self.config.guild(ctx.guild).duration.set(duration)
            await ctx.send(
                "I will monitor each message's votes until it "
                "is {} seconds old.".format(duration)
            )
        else:
            await ctx.send("Invalid duration. Must be a positive integer.")

    @msgvote.command(name="threshold")
    async def _msgvote_threshold(self, ctx, threshold: int):
        """Set the threshold of [downvotes - upvotes] for msg deletion.
        Must be a positive integer. Or, set to 0 to disable deletion."""

        if threshold < 0:
            await ctx.send("Invalid threshold. Must be a positive integer, or 0 to disable.")
        elif threshold == 0:
            await self.config.guild(ctx.guild).threshold.set(threshold)
            await ctx.send("Message deletion disabled.")
        else:
            await self.config.guild(ctx.guild).threshold.set(threshold)
            await ctx.send(
                "Messages will be deleted if [downvotes - "
                "upvotes] reaches {}.".format(threshold)
            )

    def fix_custom_emoji(self, emoji):
        if emoji[:2] != "<:":
            return emoji
        for guild in self.bot.guilds:
            for e in guild.emojis:
                if str(e.id) == emoji.split(":")[2][:-1]:
                    return e
        return None

    @commands.Cog.listener()
    async def on_message(self, message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        guild_data = await self.config.guild(message.guild).all()
        try:
            test = guild_data["channels_enabled"]
        except KeyError:
            return
        if message.channel.id not in await self.config.guild(message.guild).channels_enabled():
            return
        if (
            message.author.id == self.bot.user.id
            and not await self.config.guild(message.guild).bot_react()
        ):
            return
        # Still need to fix error (discord.errors.NotFound) on first run of cog
        # must be due to the way the emoji is stored in settings/json
        try:
            up_emoji = self.fix_custom_emoji(await self.config.guild(message.guild).up_emoji())
            dn_emoji = self.fix_custom_emoji(await self.config.guild(message.guild).dn_emoji())
            await message.add_reaction(up_emoji)
            await asyncio.sleep(0.5)
            await message.add_reaction(dn_emoji)
        except discord.errors.HTTPException:
            # Implement a non-spammy way to alert users in future
            pass

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.id == self.bot.user.id:
            return
        await self.count_votes(reaction)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.id == self.bot.user.id:
            return
        await self.count_votes(reaction)

    async def count_votes(self, reaction):
        message = reaction.message
        if not message.guild:
            return
        if not reaction.me:
            return
        if await self.config.guild(message.guild).threshold() == 0:
            return
        if message.channel.id not in await self.config.guild(message.guild).channels_enabled():
            return
        up_emoji = self.fix_custom_emoji(await self.config.guild(message.guild).up_emoji())
        dn_emoji = self.fix_custom_emoji(await self.config.guild(message.guild).dn_emoji())
        if reaction.emoji not in (up_emoji, dn_emoji):
            return
        age = (datetime.utcnow() - message.created_at).total_seconds()
        if age > await self.config.guild(message.guild).duration():
            return
        # We have a valid vote so we can count the votes now
        upvotes = 0
        dnvotes = 0
        for react in message.reactions:
            if react.emoji == up_emoji:
                upvotes = react.count
            elif react.emoji == dn_emoji:
                dnvotes = react.count
        if (dnvotes - upvotes) >= await self.config.guild(message.guild).threshold():
            try:
                await message.delete()
            except discord.errors.Forbidden:
                await message.channel.send(
                    "I require the 'Manage Messages' permission to delete downvoted messages!"
                )
