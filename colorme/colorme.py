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

from webcolors import css3_names_to_hex

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
                if role in member.roles:
                    roles.remove(role)
                    break
        return roles

    def _already_has_colorme(self, ctx, rolename):
        server = ctx.message.server
        return discord.utils.get(server.roles, name=rolename)

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

        # Attempt to map newcolor to CSS3 color spec
        newcolor = str(css3_names_to_hex[str.lower(newcolor)]) if str.lower(newcolor) in css3_names_to_hex else newcolor

        try:
            newcolor = converter.ColourConverter(ctx, newcolor).convert()
        except commands.BadArgument:
            await self.bot.reply("Color must be a valid hexidecimal value.")
            return

        role_to_change = None
        for role in member.roles:
            if role.id in protected_roles:
                await self.bot.reply("You have a role that is protected from "
                                     "color changes.")
                return
            if self._could_be_colorme(ctx, role):
                if role_to_change is not None:
                    await self.bot.reply("It looks like you have more than "
                                         "one role that can be used for "
                                         "ColorMe, so I'm not sure which one "
                                         "to edit. Talk to your server admin "
                                         "about fixing this!")
                    return
                role_to_change = role

        if role_to_change is None:
            rolename = "{}#{}{}".format(name, disc, self.suffix)
            if self._already_has_colorme(ctx, rolename):
                await self.bot.say("It looks like the server already has "
                                   "a ColorMe role for you, but it's not "
                                   "applied to you. To be safe, I'm not "
                                   "going to make a new one. Please talk "
                                   "to your server admin about fixing this!")
                return
            # Make a new cosmetic role for this person
            try:
                new_role = await self.bot.create_role(server, name=rolename,
                                                      colour=newcolor,
                                                      hoist=False,
                                                      permissions=discord.Permissions.none())
            except discord.Forbidden:
                await self.bot.say("Failed to create new role. (permissions)")
                return
            except discord.HTTPException:
                await self.bot.say("Failed to create new role. (request failed)")
                return

            try:
                await self.bot.add_roles(member, new_role)
            except discord.Forbidden:
                await self.bot.say("Failed to apply new role. (permissions)")
                return
            except discord.HTTPException:
                await self.bot.say("Failed to apply new role. (request failed)")
                return

            try:
                await self.bot.move_role(server, new_role, 2)
            except discord.InvalidArgument:
                await self.bot.say("Failed to move new role. (position invalid)")
                return
            except discord.Forbidden:
                await self.bot.say("Failed to move new role. (permissions)")
                return
            except discord.HTTPException:
                await self.bot.say("Failed to move new role. (request failed)")
                return

            await self.bot.reply("Your new color is set.")
        else:
            # Member appears to have an existing ColorMe role
            # Need to make sure they are not sharing with someone else
            if not self._is_sharing_role(ctx, role_to_change):
                try:
                    await self.bot.edit_role(server, role_to_change, colour=newcolor)
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
                                     "it with one or more members. To be "
                                     "safe, I'm not going to edit it.")
                return

    @colorme.command(name="clean", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _clean_colorme(self, ctx: commands.Context):
        """Clean colorme roles by removing all permissions."""
        user = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        dirty_roles = []
        emoji = ('\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}')
        for role in server.role_hierarchy:
            if self._could_be_colorme(ctx, role):
                if role.permissions != discord.Permissions.none():
                    dirty_roles.append(role)
        if not dirty_roles:
            await self.bot.say("I couldn't find any ColorMe roles "
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
            await self.bot.say("Cleaning roles...")
            for role in dirty_roles:
                await asyncio.sleep(1)
                try:
                    await self.bot.edit_role(server, role,
                                        permissions=discord.Permissions.none())
                except discord.Forbidden:
                    await self.bot.say("Failed to edit role: "
                                       "{} (permissions)".format(role.name))
                except discord.HTTPException:
                    await self.bot.say("Failed to edit role: "
                                       "{} (request failed)".format(role.name))

            await self.bot.say("Finished cleaning roles!")

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

    @colorme.command(name="listprotect", pass_context=True, no_pm=True)
    async def _listprotect_colorme(self, ctx):
        """Lists roles that are protected from color changes."""
        server = ctx.message.server
        self.load_settings(server.id)
        msg_text = "Protected role(s): "
        for role in self.settings[server.id]["Roles"]["Protected"]:
            protected_role = discord.utils.get(server.roles, id=role)
            if protected_role is not None:
                msg_text += " '" + protected_role.name + "',"
        msg_text = msg_text[:-1] + "."
        await self.bot.say(msg_text)

    def load_settings(self, server_id):
        self.settings = dataIO.load_json(self.settings_path)
        if server_id not in self.settings.keys():
            self.add_default_settings(server_id)

    def add_default_settings(self, server_id):
        self.settings[server_id] = {"Roles": {"Protected": []}}
        dataIO.save_json(self.settings_path, self.settings)


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
    bot.add_cog(ColorMe(bot))
