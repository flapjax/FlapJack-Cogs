import os

import discord
from redbot.core import Config, checks, commands


class Defcon(commands.Cog):

    """Server DEFCON Levels"""

    default_global_settings = {
        # Yes this is weird, but lower defcon == higher threat
        "max_defcon": 1,
        "min_defcon": 5
    }

    default_guild_settings = {
        "defcon": 5,
        "authority": "none",
        "channel": None
    }

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=440374611)
        self.conf.register_global(
            **self.default_global_settings
        )
        self.conf.register_guild(
            **self.default_guild_settings
        )

    @commands.command(name="defcon", no_pm=True, pass_context=True)
    async def defcon(self, ctx):
        """Reports the server DEFCON level."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        await self._post_defcon(ctx, guild, channel)

    @commands.command(name="defcon+", no_pm=True, pass_context=True)
    async def defconplus(self, ctx):
        """Elevates the server DEFCON level."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        member = ctx.message.author
        level = await self.conf.guild(guild).defcon()
        if level == await self.conf.max_defcon():
            await ctx.send("We are already maximum DEFCON! Oh no!")
            return
        else:
            await self.conf.guild(guild).defcon.set(level - 1)
        await self.conf.guild(guild).authority.set(member.display_name)
        await self._post_defcon(ctx, guild, channel)

    @commands.command(name="defcon-", no_pm=True, pass_context=True)
    async def defconminus(self, ctx):
        """Lowers the server DEFCON level."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        member = ctx.message.author
        level = await self.conf.guild(guild).defcon()
        if level == await self.conf.min_defcon():
            await ctx.send("We are already at minimum DEFCON! Relax!")
            return
        else:
            await self.conf.guild(guild).defcon.set(level + 1)
        await self.conf.guild(guild).authority.set(member.display_name)
        await self._post_defcon(ctx, guild, channel)

    @commands.command(name="setdefcon", no_pm=True, pass_context=True)
    async def setdefcon(self, ctx, level: int):
        """Manually set the server DEFCON level in case of emergency."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        member = ctx.message.author
        if await self.conf.max_defcon() <= level <= await self.conf.min_defcon():
            await self.conf.guild(guild).defcon.set(level)
            await self.conf.guild(guild).authority.set(member.display_name)
            await self._post_defcon(ctx, guild, channel)
        else:
            await ctx.send("Not a valid DEFCON level. Haven't "
                           "you seen War Games?")

    @commands.command(name="defconchan", no_pm=True, pass_context=True)
    @checks.mod()
    async def defconchan(self, ctx, channel: discord.TextChannel=None):
        """Constrain defcon alerts to a specific channel.
        Omit the channel argument to clear the setting."""
        me = ctx.me
        author = ctx.author
        guild = ctx.guild
        if channel is None:
            await self.conf.guild(guild).channel.set(None)
            await ctx.send("DEFCON channel setting cleared.")
            return

        if not channel.permissions_for(author).send_messages:
            await ctx.send("You're not allowed to send messages in that channel.")
            return
        elif not channel.permissions_for(me).send_messages:
            await ctx.send("I'm not allowed to send messaages in that channel.")
            return

        await self.conf.guild(guild).channel.set(channel.id)
        await ctx.send("Defcon channel set to **{}**.".format(channel.name))

    async def _post_defcon(self, ctx, guild, channel):

        level = await self.conf.guild(guild).defcon()
        nick = await self.conf.guild(guild).authority()

        icon_url = 'https://i.imgur.com/MfDcOEU.gif'

        if level == 5:
            color = 0x0080ff
            thumbnail_url = 'https://i.imgur.com/ynitQlf.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = ("No known threats to your self esteem "
                        "exist at this time.")
            instructions = ("- Partipaction in online games is encouraged\n"
                            "- Remain vigilant of insider threats\n"
                            "- Report all suspicious activity")
        elif level == 4:
            color = 0x00ff00
            thumbnail_url = 'https://i.imgur.com/sRhQekI.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Trace amounts of sodium have been detected.'
            instructions = ("- Inhale deeply through your nose and "
                            "count to 5\n"
                            "- Take short breaks between games\n"
                            "- Do not encourage trolls")
        elif level == 3:
            color = 0xffff00
            thumbnail_url = 'https://i.imgur.com/xY9SkkA.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Sodium levels may exceed OSHA exposure limits.'
            instructions = ("- Use extreme caution when playing ranked games\n"
                            "- Log off non-essential communication channels\n"
                            "- Put on your big boy pants")
        elif level == 2:
            color = 0xff0000
            thumbnail_url = 'https://i.imgur.com/cSzezRE.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Sodium levels are approaching critical mass'
            instructions = ("- Avoid ranked game modes at all costs\n"
                            "- Mute all hostile voice channels\n"
                            "- Queue up some relaxing jazz music")
        elif level == 1:
            color = 0xffffff
            thumbnail_url = 'https://i.imgur.com/NVB1AFA.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Total destruction is IMMINENT.'
            instructions = ("- Do not participate in any online games\n"
                            "- Log off all social media immediately\n"
                            "- Take shelter outdoors until the "
                            "all-clear is given")
        else:
            # Better error handling?
            return

        embed = discord.Embed(title="\u2063", color=color)
        embed.set_author(name=author, icon_url=icon_url)
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(name=subtitle, value=instructions, inline=False)
        embed.set_footer(text="Authority: {}".format(nick))

        set_channel = self.bot.get_channel(await self.conf.guild(guild).channel())
        if set_channel is None:
            await channel.send(embed=embed)
        else:
            if channel != set_channel:
                await ctx.send("Done.")
            await set_channel.send(embed=embed)
