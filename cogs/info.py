import discord
from discord.ext import commands
import platform
from datetime import datetime

VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def serverinfo(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title='Serverinfo', description=guild.name)
        embed.add_field(name='Mitglieder', value=guild.member_count)
        embed.add_field(name='Owner', value=guild.owner)
        await ctx.send(embed=embed)

    @commands.command()
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        
        # Calculate time differences
        now = datetime.now()
        joined_days = (now - member.joined_at.replace(tzinfo=None)).days
        created_days = (now - member.created_at.replace(tzinfo=None)).days
        
        # Format dates
        joined_date = member.joined_at.strftime("%m/%d/%Y %H:%M")
        created_date = member.created_at.strftime("%m/%d/%Y %H:%M")
        
        # Calculate time ago strings
        def time_ago(days):
            years = days // 365
            months = (days % 365) // 30
            remaining_days = days % 30
            
            parts = []
            if years > 0:
                parts.append(f"{years} year{'s' if years != 1 else ''}")
            if months > 0:
                parts.append(f"{months} month{'s' if months != 1 else ''}")
            if remaining_days > 0 or not parts:
                parts.append(f"{remaining_days} day{'s' if remaining_days != 1 else ''}")
            
            return " and ".join(parts) + " ago"
        
        # Get roles (limit to 10)
        roles = [role.name for role in member.roles[1:]]  # Skip @everyone
        roles_display = roles[:10] if roles else ["No roles"]
        roles_text = "\n".join(f"• {role}" for role in roles_display)
        if len(roles) > 10:
            roles_text += f"\n... and {len(roles) - 10} more"
        
        # Get permissions
        if member.guild_permissions.administrator:
            permissions = "👑 Administrator (all permissions)"
        else:
            perm_list = []
            for perm, value in member.guild_permissions:
                if value and perm not in ['administrator']:
                    perm_list.append(perm.replace('_', ' ').title())
            permissions = ", ".join(perm_list[:5]) if perm_list else "No special permissions"
            if len(perm_list) > 5:
                permissions += f" (+{len(perm_list) - 5} more)"
        
        # Create embed
        embed = discord.Embed(
            title=":busts_in_silhouette: USER INFORMATION :busts_in_silhouette:",
            color=VANTAX_COLOR
        )
        
        embed.add_field(name="Username", value=f"**{member.name}**", inline=False)
        embed.add_field(name="User ID", value=f"`{member.id}`", inline=False)
        embed.add_field(name=f"Roles [{len(roles)}] (shows up to 10 roles)", value=roles_text, inline=False)
        embed.add_field(name="Nickname", value=member.nick or "No nickname", inline=False)
        embed.add_field(name="Is boosting", value="Yes" if member.premium_since else "No", inline=False)
        embed.add_field(name="Global permissions", value=permissions, inline=False)
        embed.add_field(name="Joined this server on (MM/DD/YYYY)", value=f"{joined_date} ({time_ago(joined_days)})", inline=False)
        embed.add_field(name="Account created on (MM/DD/YYYY)", value=f"{created_date} ({time_ago(created_days)})", inline=False)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=VANTAX_FOOTER)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def botinfo(self, ctx):
        embed = discord.Embed(title='Botinfo')
        embed.add_field(name='Python', value=platform.python_version())
        embed.add_field(name='discord.py', value=discord.__version__)
        embed.add_field(name='Ping', value=f'{round(self.bot.latency * 1000)}ms')
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Info(bot))
