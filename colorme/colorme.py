import discord
from discord.ext import commands

from .utils.dataIO import dataIO

# NOTE: To use this cog properly, if you have roles with elevated permissions (i.e. admins, mods)
# these users will need special roles placed ABOVE their admin or mod roles, since only top_role
# determines the name color. Or, you can remove admin and mod roles completely
# and just make sure each user's custom role has the right permissions.

# If a member's top role matches one of these roles, the color will not be changed.
# Use this to protect roles that are not meant to be used for changing colors.
roles_to_ignore = ['admin', 'mod', 'bots']
# When creating a custom role for a new member, this is the role that will be copied.
# Recommended to use the @everyone role, otherwise new users could get access to
# additional permissions by using the bot.
default_role = '@everyone'

class ColorMe:

    """Manage the color of your own name."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True, pass_context=True)
    async def colorme(self, ctx, newcolor: str):
        """Change the color of your name.

        New color must be a valid 6 digit hexidecimal color value.
        Example: !colorme #4286F4
        """

        server = ctx.message.server
        member = ctx.message.author
        nick = member.nick
        # If message came from a private channel, member would actually be a user,
        # and we need name instead of nick
        if not nick:
            nick = member.name

        # Check for valid color
        if not is_color_valid(newcolor):
            await self.bot.reply("Invalid color choice. Must be a valid hexidecimal color value.")
            return

        # Convert color input to integer
        intcolor = int(newcolor, 16)

        if member.top_role.name in roles_to_ignore:
            # Member's top role is on the ignore list
            await self.bot.reply("Your top role cannot be edited, sorry.")

        elif member.top_role.name == '@everyone':
            # Make a new role for this person, using default role as template
            role_to_copy = discord.utils.get(server.roles, name=default_role)
            new_role = await self.bot.create_role(server, name=nick, permissions=role_to_copy.permissions,
                            colour=discord.Colour(intcolor), hoist=role_to_copy.hoist, mentionable=role_to_copy.mentionable)
            await self.bot.add_roles(member, new_role)
            await self.bot.reply("You didn't have a custom role yet, so I made you one.")

        else:
            #Member has a top role that can be edited.
            await self.bot.edit_role(server, member.top_role, colour = discord.Colour(intcolor))
            await self.bot.reply("Your new color is set.")

def is_color_valid(newcolor):

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



def setup(bot):

    bot.add_cog(ColorMe(bot))
