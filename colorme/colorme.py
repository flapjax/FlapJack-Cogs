import os
import re
import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help

# NOTE: This cog creates/edits roles to let users set custom name colors.
# Since only top_role determines the name color, things can get a bit wonky.
# (this is a Discord 'feature').
# Your bot must have permission to edit roles AND be placed above other roles
# in order to edit them (another Discord 'feature')
# Use [p]colorme protect <role> to protect certrain roles from color changes.
# For example, administrator roles, or roles for 'punished' users.


class ColorMe:

    """Manage the color of your own name."""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/colorme/settings.json"
        self.settings = dataIO.load_json(self.settings_path)

    @commands.group(name="colorme", pass_context=True)
    async def colorme(self, ctx):
        """Change the color of your name via custom roles."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @colorme.command(name="change", pass_context=True)
    async def _change_colorme(self, ctx, newcolor: str):
        """Change the color of your name.

        New color must be a valid 6 digit hexidecimal color value.
        Example: [p]colorme change 0099FF
        """

        server = ctx.message.server
        member = ctx.message.author
        name = member.name
        disc = member.discriminator
        top_role = member.top_role
        custom_role = discord.utils.get(server.roles, name=name+'#'+disc)

        self.load_settings(server.id)
        protected_roles = self.settings[server.id]["Roles"]["Protected"]

        # Check for valid color (thanks to Paddo for regexp)
        if not re.search(r'^(?:[0-9a-fA-F]{3}){1,2}$', newcolor):
            await self.bot.reply("Invalid color choice. Must be a valid "
                                 "hexidecimal color value.")
            return

        if top_role.id in protected_roles:
            await self.bot.reply("Color changes are not permitted for your role.")
            return

        # Convert color input to integer
        intcolor = int(newcolor, 16)

        if (custom_role is None) or (top_role.id != custom_role.id):
            # Make a new role for this person, using top role as template
            new_role = await self.bot.create_role(server, name=name+'#'+disc,
                                        permissions=top_role.permissions,
                                        colour=discord.Colour(intcolor),
                                        hoist=False,
                                        mentionable=top_role.mentionable)
            await self.bot.move_role(server, new_role, top_role.position)
            await self.bot.add_roles(member, new_role)
            await self.bot.reply("Your new color is set.")
        else:
            # Member's top role is already a custom role for their name
            await self.bot.edit_role(server, top_role,
                                     colour=discord.Colour(intcolor))
            await self.bot.reply("Your new color is set.")

    @colorme.command(name="protect", pass_context=True)
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

    @colorme.command(name="unprotect", pass_context=True)
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

    @colorme.command(name="defaultrole", pass_context=True)
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
        self.settings[server.id]["Roles"]["Default"] = default_role.id
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Role '{}' will be applied to each user who "
                           "joins the server.".format(role))

    @colorme.command(name="listprotect", pass_context=True)
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
                                 id=self.settings[member.server.id]
                                 ["Roles"].get("Default"))
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
