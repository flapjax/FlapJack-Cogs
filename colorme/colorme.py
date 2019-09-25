import asyncio
import re

import discord
from redbot.core import Config, checks, commands


class ColorMe(commands.Cog):

    """Manage the color of your own name."""

    default_guild_settings = {
        "protected_roles": []
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=879271957)
        self.conf.register_guild(
            **self.default_guild_settings
        )
        self.suffix = ":color"

    def _is_sharing_role(self, ctx: commands.Context, role):
        guild = ctx.message.guild
        for member in guild.members:
            if (role in member.roles) and (member.id != ctx.message.author.id):
                return True
        return False

    def _could_be_colorme(self, role):
        pattern = re.compile(r'#\d{4}\Z')
        if pattern.search(role.name) is not None:
            # Possible role created by old version
            return True
        elif role.name.endswith(self.suffix):
            return True
        return False

    def _elim_valid_roles(self, roles):
        for role in roles:
            if len(role.members) > 0:
                roles.remove(role)
        return roles

    def _already_has_colorme(self, ctx, rolename):
        guild = ctx.message.guild
        return discord.utils.get(guild.roles, name=rolename)

    @commands.guild_only()
    @commands.group(name="colorme")
    async def colorme(self, ctx):
        """Change the color of your name via custom roles."""
        pass

    @colorme.command(name="change")
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def _change_colorme(self, ctx: commands.Context, newcolor: discord.Colour):
        """Change the color of your name.

        New color must be a valid hexidecimal color value.
        """
        guild = ctx.message.guild
        member = ctx.message.author
        name = member.name
        disc = member.discriminator
        top_role = member.top_role
        protected_roles = await self.conf.guild(guild).protected_roles()

        role_to_change = None
        for role in member.roles:
            if role.id in protected_roles:
                return await ctx.send("You have a role that is protected from color changes.")
            if self._could_be_colorme(role):
                if role_to_change is not None:
                    return await ctx.send("It looks like you have more than "
                                          "one role that can be used for "
                                          "ColorMe, so I'm not sure which one "
                                          "to edit. Talk to your server admin "
                                          "about fixing this!")
                role_to_change = role

        if role_to_change is None:
            rolename = f"{name}#{disc}{self.suffix}"
            if self._already_has_colorme(ctx, rolename):
                await ctx.send("It looks like the server already has "
                               "a ColorMe role for you, but it's not "
                               "applied to you. To be safe, I'm not "
                               "going to make a new one. Please talk "
                               "to your server admin about fixing this!")
                return
            # Make a new cosmetic role for this person
            try:
                new_role = await guild.create_role(reason='Custom ColorMe Role',
                                                   name=rolename,
                                                   colour=newcolor,
                                                   hoist=False,
                                                   permissions=discord.Permissions.none())
            except discord.Forbidden:
                await ctx.send("Failed to create new role. (permissions)")
                return
            except discord.HTTPException:
                await ctx.send("Failed to create new role. (request failed)")
                return

            try:
                await member.add_roles(new_role, reason='Custom ColorMe Role')
            except discord.Forbidden:
                await ctx.send("Failed to apply new role. (permissions)")
                return
            except discord.HTTPException:
                await ctx.send("Failed to apply new role. (request failed)")
                return
            # Change to reply?
            await ctx.send("Your new color is set.")
        else:
            # Member appears to have an existing ColorMe role
            # Need to make sure they are not sharing with someone else
            if not self._is_sharing_role(ctx, role_to_change):
                try:
                    await role_to_change.edit(colour=newcolor, reason='ColorMe Change')
                except discord.Forbidden:
                    return await ctx.send("Failed to edit role. (permissions)")
                except discord.HTTPException:
                    return await ctx.send("Failed to edit role. (request failed)")
                # Change to reply?
                await ctx.send("Your new color is set.")
            else:
                # Change to reply?
                await ctx.send("This is odd. It looks like you have a "
                               "valid ColorMe role, but you're sharing "
                               "it with one or more members. To be "
                               "safe, I'm not going to edit it.")
                return

    @colorme.command(name="clean")
    @checks.admin_or_permissions(manage_guild=True)
    async def _clean_colorme(self, ctx: commands.Context):
        """Clean colorme roles by removing all permissions."""
        user = ctx.message.author
        guild = ctx.message.guild
        dirty_roles = []
        emoji = ('\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}')
        for role in guild.roles:
            if self._could_be_colorme(role):
                if role.permissions != discord.Permissions.none():
                    dirty_roles.append(role)
        if not dirty_roles:
            await ctx.send("I couldn't find any ColorMe roles "
                           "that need to be cleaned.")
            return
        msg_txt = ("I have scanned the list of roles on this server. "
                   "I have detected the following roles which were "
                   "**possibly** created by ColorMe, but still have "
                   "permissions attached to them. Would you like me to "
                   "remove all permissions from these roles? If you are "
                   "unsure, **please** cancel and manually verify the roles. "
                   "These roles could have been created by another person or "
                   "bot, and this action is not reversible.\n\n"
                   "{} **to confirm**\n"
                   "{} **to cancel**\n```".format(emoji[0], emoji[1]))
        msg_txt += '\n'.join([role.name for role in dirty_roles]) + '```'
        msg = await ctx.send(msg_txt)
        await msg.add_reaction(emoji[0])
        await asyncio.sleep(0.5)
        await msg.add_reaction(emoji[1])

        def check(r, u):
            return r.message.id == msg.id and u == user

        try:
            (r, u) = await self.bot.wait_for('reaction_add', check=check, timeout=600)
        except asyncio.TimeoutError:
            r = None

        if r is None or r.emoji == emoji[1]:
            await msg.clear_reactions()
            return

        if r.emoji == emoji[0]:
            await msg.clear_reactions()
            await ctx.send("Cleaning roles...")
            for role in dirty_roles:
                await asyncio.sleep(1)
                try:
                    await role.edit(permissions=discord.Permissions.none(),
                                    reason='ColorMe permission wipe')
                except discord.Forbidden:
                    await ctx.send(f"Failed to edit role: {role.name} (permissions)")
                except discord.HTTPException:
                    await ctx.send(f"Failed to edit role: {role.name} (request failed)")

            await ctx.send("Finished cleaning roles!")

    @colorme.command(name="purge")
    @checks.admin_or_permissions(manage_guild=True)
    async def _purge_colorme(self, ctx: commands.Context):
        """Purge the server of roles that may have been created
        by ColorMe, but are no longer in use."""
        user = ctx.message.author
        guild = ctx.message.guild
        dead_roles = []
        emoji = ('\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}')

        for role in guild.roles:
            if self._could_be_colorme(role):
                dead_roles.append(role)
        dead_roles = self._elim_valid_roles(dead_roles)
        if not dead_roles:
            return await ctx.send("I couldn't find any roles to purge.")
        msg_txt = ("I have scanned the list of roles on this server. "
                   "I have detected the following roles which were "
                   "**possibly** created by ColorMe, but are not any "
                   "member's top_role, and are useless for setting color. "
                   "Would you like me to delete these roles? If you are "
                   "unsure, **please** cancel and manually verify the roles. "
                   "These roles could have been created by another person or "
                   "bot, and this action is not reversible.\n\n"
                   "{} **to confirm**\n"
                   "{} **to cancel**\n```".format(emoji[0], emoji[1]))
        msg_txt += '\n'.join([role.name for role in dead_roles]) + '```'
        msg = await ctx.send(msg_txt)
        await msg.add_reaction(emoji[0])
        await asyncio.sleep(0.5)
        await msg.add_reaction(emoji[1])

        def check(r, u):
            return r.message.id == msg.id and u == user

        try:
            (r, u) = await self.bot.wait_for('reaction_add', check=check, timeout=600)
        except asyncio.TimeoutError:
            r = None

        if r is None or r.emoji == emoji[1]:
            return await msg.clear_reactions()

        if r.emoji == emoji[0]:
            await msg.clear_reactions()
            await ctx.send("Deleting roles...")
            for role in dead_roles:
                await asyncio.sleep(1)
                try:
                    await role.delete(reason='ColorMe role purge')
                except discord.Forbidden:
                    await ctx.send(f"Failed to delete role: {role.name} (permissions)")
                except discord.HTTPException:
                    await ctx.send(f"Failed to delete role: {role.name} (request failed)")

            await ctx.send("Finished deleting roles!")

    @colorme.command(name="protect")
    @checks.admin_or_permissions(manage_guild=True)
    async def _protect_colorme(self, ctx, role: str):
        """Add a role to the list of protected roles.

        Members with this role as top role will not be allowed to change color.
        Example: [p]colorme protect admin
        """
        guild = ctx.message.guild
        protect_role = discord.utils.get(guild.roles, name=role)
        if protect_role is None:
            return await ctx.send("No roles match that name.")
        protected_roles = await self.conf.guild(guild).protected_roles()
        if protect_role.id in protected_roles:
            await ctx.send("That role is already protected.")
        else:
            protected_roles.append(protect_role.id)
            await self.conf.guild(guild).protected_roles.set(protected_roles)
            await ctx.send(f"Users with top role '{role}' are protected from color changes.")

    @colorme.command(name="unprotect")
    @checks.admin_or_permissions(manage_guild=True)
    async def _unprotect_colorme(self, ctx, role: str):
        """Remove a role from the list of protected roles.

        Example: [p]colorme unprotect admin
        """
        guild = ctx.message.guild
        protect_role = discord.utils.get(guild.roles, name=role)
        if protect_role is None:
            return await ctx.send("No roles match that name.")
        protected_roles = await self.conf.guild(guild).protected_roles()
        if protect_role.id not in protected_roles:
            await ctx.send("That role is not currently protected.")
        else:
            protected_roles.remove(protect_role.id)
            await self.conf.guild(guild).protected_roles.set(protected_roles)
            await ctx.send(f"Users with top role '{role}' are no longer protected from color changes.")

    @colorme.command(name="listprotect")
    async def _listprotect_colorme(self, ctx):
        """Lists roles that are protected from color changes."""
        guild = ctx.message.guild
        protected_roles = await self.conf.guild(guild).protected_roles()
        msg_text = "Protected role(s): "
        if len(protected_roles) == 0:
            msg_text += "None "
        for role in protected_roles:
            protected_role = discord.utils.get(guild.roles, id=role)
            if protected_role is not None:
                msg_text += " '" + protected_role.name + "',"
        msg_text = msg_text[:-1] + "."
        await ctx.send(msg_text)
