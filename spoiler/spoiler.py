import discord
from redbot.core import commands


class Spoiler(commands.Cog):

    """Hide spoilers by delivering them via DM"""

    def __init__(self, bot):
        self.bot = bot
        self.emoji = "👀"
        self.spoilers = {}

    @commands.guild_only()
    @commands.command(name="spoiler")
    async def spoiler(self, ctx, title: str, spoiler: str=None):
        """Hide spoiler text and have it delivered via DM."""

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send("I require the 'manage messages' permission "
                           "to hide spoilers!")

        if spoiler is None:
            # User probably meant to omit title
            spoiler = title
            title = ""
        else:
            title = "(" + title + ")"

        content = "{} posted a spoiler {}:\nReact with {} to have it DMed to you.".format(ctx.author.mention, title, self.emoji)
        message = await ctx.send(content)
        await message.add_reaction(self.emoji)

        self.spoilers[message.id] = {
            'title': title,
            'spoiler': spoiler,
            'deliveries': []  # user ids to which the spoiler has been delivered
        }

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        msg_id = reaction.message.id
        if reaction.emoji == self.emoji and msg_id in self.spoilers and user.id != self.bot.user.id:
            if user.id not in self.spoilers[msg_id]['deliveries']:
                # reply with spoiler
                try:
                    await user.send("Spoiler {}: {}".format(self.spoilers[msg_id]['title'],
                                                                  self.spoilers[msg_id]['spoiler']))

                    self.spoilers[msg_id]['deliveries'].append(user.id)
                except (discord.Forbidden, discord.HTTPException) as err:
                    # It's alright to fail silently if we are unable to DM the user
                    pass
