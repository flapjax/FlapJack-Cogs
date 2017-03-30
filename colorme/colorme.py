import asyncio
import copy
import os
import re

import discord
from discord.ext import commands
from discord.ext.commands import converter

from __main__ import send_cmd_help

from .utils import checks
from .utils.dataIO import dataIO


# This cog creates/edits roles to let users set custom name colors.
# Since only top_role determines the name color, things are a bit tricky.
# Your bot must have permission to edit roles AND be placed above other roles
# in order to edit them.
# The bot should also have permissions that are equal to, or greather than,
# those of the roles it is trying to edit.


class ColorMe:

    """Manage the color of your own name."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_path = "data/colorme/settings.json"
        self.settings = dataIO.load_json(self.settings_path)
        self.suffix = ":color"

    def _is_sharing_role(self, ctx: commands.Context, role):
        server = ctx.message.server
        for member in server.members:
            if (role in member.roles) and (member != ctx.message.author):
                return True
        return False

    def _could_be_colorme(self, ctx: commands.Context, role):
        pattern = re.compile(r'#\d{4}\Z')
        if pattern.search(role.name) is not None:
            # Possible role created by old version
            return True
        elif role.name.endswith(self.suffix):
            return True
        return False

    def _elim_valid_roles(self, ctx: commands.Context, roles):
        # HOW is role.members NOT a thing?
        server = ctx.message.server
        role_copy = copy.deepcopy(roles)
        for role in role_copy:
            for member in server.members:
                if role == member.top_role:
                    roles.remove(role)
                    break
        return roles

    @commands.group(name="colorme", pass_context=True)
    async def colorme(self, ctx):
        """Change the color of your name via custom roles."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @colorme.command(name="change", pass_context=True, no_pm=True)
    @commands.cooldown(2, 60, commands.BucketType.user)
    async def _change_colorme(self, ctx: commands.Context, newcolor: str):
        """Change the color of your name.

        New color must be a valid hexidecimal color value.
        """
        server = ctx.message.server
        member = ctx.message.author
        name = member.name
        disc = member.discriminator
        top_role = member.top_role

        self.load_settings(server.id)
        protected_roles = self.settings[server.id]["Roles"]["Protected"]

        try:
            newcolor = converter.ColourConverter(ctx, newcolor).convert()
        except commands.BadArgument:
            await self.bot.say("Color must be a valid hexidecimal value.")
            return

        if top_role.id in protected_roles:
            await self.bot.reply("Color changes are not permitted for your role.")
            return

        if not self._could_be_colorme(ctx, top_role):
            # Make a new role for this person, using top role as template
            rolename = "{}#{}{}".format(name, disc, self.suffix)
            try:
                new_role = await self.bot.create_role(server, name=rolename,
                                        permissions=top_role.permissions,
                                        colour=newcolor,
                                        hoist=False,
                                        mentionable=top_role.mentionable)
            except discord.Forbidden:
                await self.bot.say("Failed to create new role. (permissions)")
                return
            except discord.HTTPException:
                await self.bot.say("Failed to create new role. (request failed)")
                return

            try:
                await self.bot.move_role(server, new_role, top_role.position)
            except discord.Forbidden:
                await self.bot.say("Failed to move new role. (permissions)")
                return
            except discord.HTTPException:
                await self.bot.say("Failed to move new role. (request failed)")
                return
            except discord.InvalidArgument:
                await self.bot.say("Failed to move new role. (invalid position)")
                return

            try:
                await self.bot.add_roles(member, new_role)
            except discord.Forbidden:
                await self.bot.say("Failed to apply new role. (permissions)")
                return
            except discord.HTTPException:
                await self.bot.say("Failed to apply new role. (request failed)")
                return

            await self.bot.reply("Your new color is set.")
        else:
            # Member's top role could already be a custom role for their name
            # Need to make sure they are not sharing with someone else
            if not self._is_sharing_role(ctx, top_role):
                try:
                    await self.bot.edit_role(server, top_role, colour=newcolor)
                except discord.Forbidden:
                    await self.bot.say("Failed to edit role. (permissions)")
                    return
                except discord.HTTPException:
                    await self.bot.say("Failed to edit role. (request failed)")
                    return
                await self.bot.reply("Your new color is set.")
            else:
                await self.bot.reply("This is odd. It looks like you have a "
                                     "valid ColorMe role, but you're sharing "
                                     "it with one or more members. To be ",
                                     "safe, I'm not going to edit it.")
                return

    @colorme.command(name="purge", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _purge_colorme(self, ctx: commands.Context):
        """Purge the server of roles that may have been created
        by ColorMe, but are no longer in use."""
        user = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        dead_roles = []
        emoji = ('\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}')

        for role in server.role_hierarchy:
            if self._could_be_colorme(ctx, role):
                dead_roles.append(role)
        dead_roles = self._elim_valid_roles(ctx, dead_roles)
        if not dead_roles:
            await self.bot.say("I couldn't find any roles to purge.")
            return
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
        msg = await self.bot.send_message(channel, msg_txt)
        await self.bot.add_reaction(msg, emoji[0])
        await asyncio.sleep(0.5)
        await self.bot.add_reaction(msg, emoji[1])
        response = await self.bot.wait_for_reaction(emoji, user=user,
                                              timeout=600, message=msg)

        if response is None or response.reaction.emoji == emoji[1]:
            await self.bot.clear_reactions(msg)
            return

        if response.reaction.emoji == emoji[0]:
            await self.bot.clear_reactions(msg)
            await self.bot.say("Deleting roles...")
            for role in dead_roles:
                await asyncio.sleep(1)
                try:
                    await self.bot.delete_role(server, role)
                except discord.Forbidden:
                    await self.bot.say("Failed to delete role: "
                                       "{} (permissions)".format(role.name))
                except discord.HTTPException:
                    await self.bot.say("Failed to delete role: "
                                       "{} (request failed)".format(role.name))

            await self.bot.say("Finished deleting roles!")

    @colorme.command(name="protect", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _protect_colorme(self, ctx, role: str):
        """Add a role to the list of protected roles.

        Members with this role as top role will not be allowed to change color.
        Example: [p]colorme protect admin
        """
        server = ctx.message.server
        protect_role = discord.utils.get(server.roles, name=role)
        if protect_role is None:
            await self.bot.say("No roles match that name.")
            return
        self.load_settings(server.id)
        if protect_role.id in self.settings[server.id]["Roles"]["Protected"]:
            await self.bot.say("That role is already protected.")
        else:
            self.settings[server.id]["Roles"]["Protected"].append(protect_role.id)
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Users with top role '{}' are protected from "
                               "color changes.".format(role))

    @colorme.command(name="unprotect", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _unprotect_colorme(self, ctx, role: str):
        """Remove a role from the list of protected roles.

        Example: [p]colorme unprotect admin
        """
        server = ctx.message.server
        protect_role = discord.utils.get(server.roles, name=role)
        if protect_role is None:
            await self.bot.say("No roles match that name.")
            return
        self.load_settings(server.id)
        if protect_role.id not in self.settings[server.id]["Roles"]["Protected"]:
            await self.bot.say("That role is not currently protected.")
        else:
            self.settings[server.id]["Roles"]["Protected"].remove(protect_role.id)
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Users with top role '{}' are no longer protected "
                               "from color changes.".format(role))

    @colorme.command(name="defaultrole", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _defaultrole_colorme(self, ctx, role: str):
        """Specify a role that will automatically be granted to new members
        when they join the server. Set to "@everyone" to disable this feature.
        ("@everyone" is the default setting)

        Example: [p]colorme defaultrole member
        """
        server = ctx.message.server
        default_role = discord.utils.get(server.roles, name=role)
        if default_role is None:
            await self.bot.say("No roles match that name.")
            return
        self.load_settings(server.id)
        self.settings[server.id]["Roles"]["Default"] = default_role.id
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Role '{}' will be applied to each user who "
                           "joins the server.".format(role))

    @colorme.command(name="listprotect", pass_context=True, no_pm=True)
    async def _listprotect_colorme(self, ctx):
        """Lists roles that are protected from color changes."""
        server = ctx.message.server
        self.load_settings(server.id)
        msg_text = "Protected role(s):"
        for role in self.settings[server.id]["Roles"]["Protected"]:
            role_name = discord.utils.get(server.roles, id=role).name
            msg_text += " '" + role_name + "',"
        msg_text = msg_text[:-1] + "."
        await self.bot.say(msg_text)

    def load_settings(self, server_id):
        self.settings = dataIO.load_json(self.settings_path)
        if server_id not in self.settings.keys():
            self.add_default_settings(server_id)

    def add_default_settings(self, server_id):
        self.settings[server_id] = {"Roles": {"Protected": [],
                                    "Default": "@everyone"}}
        dataIO.save_json(self.settings_path, self.settings)

    async def member_join_listener(self, member):
        # Backwards compatibility
        role = discord.utils.get(member.server.roles,
                                 id=self.settings.get(member.server.id, {})
                                 .get("Roles", {}).get("Default"))
        if role is not None and not role.is_everyone:
            await self.bot.add_roles(member, role)


def check_folders():
    folder = "data/colorme"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {}
    if not dataIO.is_valid_json("data/colorme/settings.json"):
        print("Creating default colorme settings.json...")
        dataIO.save_json("data/colorme/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    n = ColorMe(bot)
    bot.add_cog(n)
    bot.add_listener(n.member_join_listener, "on_member_join")
