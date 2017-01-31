import os
import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help

# NOTE: To use this cog properly, if you have roles with elevated permissions
# (i.e. admins, mods) these users will need special roles placed ABOVE their
# admin or mod roles, since only top_role determines the name color (this is a
# Discord limitation).
# Use [p]colorme protect <role> to protect these roles from color changes.
# Alternatively, you can remove admin and mod roles completely and just make
# sure each user's custom role has the right permissions.
# Your bot must have permission to edit roles AND be placed above other roles
# in order to edit them (another Discord limitation)
# The @everyone role is used as a template for creating the new custom roles,
# otherwise new users could access additional permissions by using the bot.


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
        Example: [p]colorme change #4286F4
        """

        server = ctx.message.server
        member = ctx.message.author
        nick = member.display_name

        self.load_settings(server.id)
        roles_to_ignore = self.settings[server.id]["Roles"]["Protected"]
        default_role = self.settings[server.id]["Roles"]["Default"]

        # Check for valid color
        if not self.is_color_valid(newcolor):
            await self.bot.reply("Invalid color choice. Must be a valid "
                                 "hexidecimal color value.")
            return

        # Convert color input to integer
        intcolor = int(newcolor, 16)

        if member.top_role.name in roles_to_ignore:
            # Member's top role is on the protected list
            await self.bot.reply("Your top role is protected from editing, "
                                 "sorry.")

        elif member.top_role.name == '@everyone':
            # Make a new role for this person, using default role as template
            role_to_copy = discord.utils.get(server.roles, name=default_role)
            new_role = await self.bot.create_role(server, name=nick,
                                        permissions=role_to_copy.permissions,
                                        colour=discord.Colour(intcolor),
                                        hoist=role_to_copy.hoist,
                                        mentionable=role_to_copy.mentionable)
            await self.bot.add_roles(member, new_role)
            await self.bot.reply("You didn't have a custom role yet, so I "
                                 "made you one.")

        else:
            # Member has a top role that can be edited.
            await self.bot.edit_role(server, member.top_role,
                                     colour=discord.Colour(intcolor))
            await self.bot.reply("Your new color is set.")

    @colorme.command(name="protect", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _protect_colorme(self, ctx, role: str):
        """Add a role to the list of protected roles.

        Example: [p]colorme protect admin
        """
        server = ctx.message.server
        self.load_settings(server.id)
        if role in self.settings[server.id]["Roles"]["Protected"]:
            await self.bot.say("That role is already protected.")
        else:
            self.settings[server.id]["Roles"]["Protected"].append(role)
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Role '{}' is now protected from color "
                               "changes.".format(role))

    @colorme.command(name="unprotect", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _unprotect_colorme(self, ctx, role: str):
        """Remove a role from the list of protected roles.

        Example: [p]colorme unprotect admin
        """
        server = ctx.message.server
        self.load_settings(server.id)
        if role not in self.settings[server.id]["Roles"]["Protected"]:
            await self.bot.say("That role is not currently protected.")
        else:
            self.settings[server.id]["Roles"]["Protected"].remove(role)
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Role '{}' is no longer protected from color "
                               "changes.".format(role))

    @colorme.command(name="listprotected", pass_context=True)
    async def _listprotected_colorme(self, ctx):
        """Lists roles that are protected from color changes."""
        server = ctx.message.server
        self.load_settings(server.id)
        msg_text = "Protected role(s):"
        for role in self.settings[server.id]["Roles"]["Protected"]:
            msg_text += " '" + role + "',"
        msg_text = msg_text[:-1] + "."
        await self.bot.say(msg_text)

    def load_settings(self, server_id):
        self.settings = dataIO.load_json(self.settings_path)
        if server_id not in self.settings.keys():
            self.add_default_settings(server_id)

    def add_default_settings(self, server_id):
        self.settings[server_id] = {"Roles": {"Protected": [], "Default":
                                    "@everyone"}}
        dataIO.save_json(self.settings_path, self.settings)

    def is_color_valid(self, newcolor):
        try:
            if len(newcolor) == 6:
                if 0 <= int(newcolor[0:1], 16) <= 255:
                    if 0 <= int(newcolor[2:3], 16) <= 255:
                        if 0 <= int(newcolor[4:5], 16) <= 255:
                            return True
                        else:
                            return False
                    else:
                        return False
                else:
                    return False
            else:
                return False
        except ValueError:
            return False


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
