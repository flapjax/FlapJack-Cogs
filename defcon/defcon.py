import os

import discord
from discord.ext import commands

from core.utils import helpers


class Defcon:

    """Server DEFCON Levels"""

    def __init__(self, bot):
        self.bot = bot
        self.json = helpers.JsonGuildDB("cogs/defcon/data/settings.json",
                                        create_dirs=True)
        self.valid_defcons = ['1', '2', '3', '4', '5']

    async def _check_guild_settings(self, guild):
        if str(guild.id) not in self.json:
            await self.json.set(guild, "defcon", 5)
            await self.json.set(guild, "authority", "none")

    @commands.command(name="defcon", no_pm=True, pass_context=True)
    async def defcon(self, ctx):
        """Reports the server DEFCON level."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        await self._check_guild_settings(guild)
        await self._post_defcon(guild, channel)

    @commands.command(name="defcon+", no_pm=True, pass_context=True)
    async def defconplus(self, ctx):
        """Elevates the server DEFCON level."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        member = ctx.message.author
        await self._check_guild_settings(guild)
        level = self.json.get(guild, "defcon")
        if level == 1:
            await ctx.send("We are already at DEFCON 1! Oh no!")
            return
        else:
            await self.json.set(guild, "defcon", level - 1)
        await self.json.set(guild, "authority", member.display_name)
        await self._post_defcon(guild, channel)

    @commands.command(name="defcon-", no_pm=True, pass_context=True)
    async def defconminus(self, ctx):
        """Lowers the server DEFCON level."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        member = ctx.message.author
        await self._check_guild_settings(guild)
        level = self.json.get(guild, "defcon")
        if level == 5:
            await ctx.send("We are already at DEFCON 5! Relax!")
            return
        else:
            await self.json.set(guild, "defcon", level + 1)
        await self.json.set(guild, "authority", member.display_name)
        await self._post_defcon(guild, channel)

    @commands.command(name="setdefcon", no_pm=True, pass_context=True)
    async def setdefcon(self, ctx, level: str):
        """Manually set the server DEFCON level in case of emergency."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        member = ctx.message.author
        await self._check_guild_settings(guild)

        if level in self.valid_defcons:
            await self.json.set(guild, "defcon", int(level))
            await self.json.set(guild, "authority", member.display_name)
            await self._post_defcon(guild, channel)
        else:
            await ctx.send("Not a valid DEFCON level. Haven't "
                           "you seen War Games?")

    async def _post_defcon(self, guild, channel):

        level = str(self.json.get(guild, "defcon"))
        nick = self.json.get(guild, "authority")

        if level not in self.valid_defcons:
            return

        icon_url = 'https://i.imgur.com/MfDcOEU.gif'

        if level == '5':
            color = 0x0080ff
            thumbnail_url = 'https://i.imgur.com/uTPeW7N.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = ("No known threats to your self esteem "
                        "exist at this time.")
            instructions = ("- Partipaction in online games is encouraged\n"
                            "- Remain vigilant of insider threats\n"
                            "- Report all suspicious activity")
        elif level == '4':
            color = 0x00ff00
            thumbnail_url = 'https://i.imgur.com/siIWL5V.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Trace amounts of sodium have been detected.'
            instructions = ("- Inhale deeply through your nose and "
                            "count to 5\n"
                            "- Take short breaks between games\n"
                            "- Do not encourage trolls")
        elif level == '3':
            color = 0xffff00
            thumbnail_url = 'https://i.imgur.com/E71VSBE.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Sodium levels may exceed OSHA exposure limits.'
            instructions = ("- Use extreme caution when playing ranked games\n"
                            "- Log off non-essential communication channels\n"
                            "- Put on your big boy pants")
        elif level == '2':
            color = 0xff0000
            thumbnail_url = 'https://i.imgur.com/PxKhT7h.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Sodium levels are approaching critical mass'
            instructions = ("- Avoid ranked game modes at all costs\n"
                            "- Mute all hostile voice channels\n"
                            "- Queue up some relaxing jazz music")
        elif level == '1':
            color = 0xffffff
            thumbnail_url = 'https://i.imgur.com/wzXSNWi.gif'
            author = "This server is at DEFCON LEVEL {}.".format(level)
            subtitle = 'Total destruction is IMMINENT.'
            instructions = ("- Do not participate in any online games\n"
                            "- Log off all social media immediately\n"
                            "- Take shelter outdoors until the "
                            "all-clear is given")

        embed = discord.Embed(title="\u2063", color=color)
        embed.set_author(name=author, icon_url=icon_url)
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(name=subtitle, value=instructions, inline=False)
        embed.set_footer(text="Authority: {}".format(nick))
        await channel.send(embed=embed)
