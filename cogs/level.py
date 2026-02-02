import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime
import random

LEVEL_FILE = "leveldata.json"
VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

# XP rewards for different activities
XP_REWARDS = {
    "message": random.randint(15, 25),  # Random XP per message
    "image_attachment": 10,  # Bonus XP for images
    "long_message": 5,  # Bonus XP for messages > 100 chars
    "voice_minute": 1  # XP per minute in voice
}

# Level requirements (exponential growth)
def get_xp_for_level(level):
    return int(100 * (level ** 1.5))

def get_level_from_xp(xp):
    level = 1
    while xp >= get_xp_for_level(level + 1):
        level += 1
    return level

# Hilfsfunktionen

def load_data():
    if not os.path.isfile(LEVEL_FILE):
        with open(LEVEL_FILE, "w") as f:
            json.dump({}, f)
    with open(LEVEL_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(LEVEL_FILE, "w") as f:
        json.dump(data, f)

class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
            
        uid = str(message.author.id)
        gid = str(message.guild.id)
        
        # Initialize user data if not exists
        if gid not in self.data:
            self.data[gid] = {}
        if uid not in self.data[gid]:
            self.data[gid][uid] = {
                "xp": 0, 
                "level": 1, 
                "messages": 0,
                "last_message": None,
                "streak": 0
            }
        
        # Cooldown check (prevent spam)
        now = datetime.datetime.now()
        last_msg = self.data[gid][uid].get("last_message")
        if last_msg and (now - datetime.datetime.fromisoformat(last_msg)).seconds < 30:
            return  # Skip if last message was less than 30 seconds ago
        
        # Calculate XP reward
        xp_reward = XP_REWARDS["message"]
        
        # Bonus XP for attachments
        if message.attachments:
            xp_reward += XP_REWARDS["image_attachment"]
        
        # Bonus XP for long messages
        if len(message.content) > 100:
            xp_reward += XP_REWARDS["long_message"]
        
        # Update user data
        self.data[gid][uid]["xp"] += xp_reward
        self.data[gid][uid]["messages"] += 1
        self.data[gid][uid]["last_message"] = now.isoformat()
        
        # Check for level up
        current_level = self.data[gid][uid]["level"]
        new_level = get_level_from_xp(self.data[gid][uid]["xp"])
        
        if new_level > current_level:
            self.data[gid][uid]["level"] = new_level
            
            # Create level up embed
            embed = discord.Embed(
                title="🎉 LEVEL UP! 🎉",
                description=f"**{message.author.mention} ist jetzt Level {new_level}!**",
                color=discord.Color.gold()
            )
            
            # Add level up rewards/info
            embed.add_field(name="🎯 Neues Level", value=f"Level {new_level}", inline=True)
            embed.add_field(name="⭐ Gesamt XP", value=f"{self.data[gid][uid]['xp']} XP", inline=True)
            embed.add_field(name="📈 XP für nächstes Level", value=f"{get_xp_for_level(new_level + 1)} XP", inline=True)
            
            # Special rewards for milestone levels
            milestone_rewards = {
                5: "🏅 Bronze Mitglied",
                10: "🥈 Silber Mitglied", 
                25: "🥇 Gold Mitglied",
                50: "💎 Diamant Mitglied",
                100: "👑 Legendär Mitglied"
            }
            
            if new_level in milestone_rewards:
                embed.add_field(
                    name="🎁 Meilenstein-Belohnung",
                    value=f"**{milestone_rewards[new_level]}**",
                    inline=False
                )
            
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_footer(text=VANTAX_FOOTER)
            
            await message.channel.send(embed=embed)
            
            # Try to give role reward if configured
            await self.give_level_role(message.guild, message.author, new_level)
        
        save_data(self.data)

    async def give_level_role(self, guild, member, level):
        """Give role rewards based on level (if configured)"""
        level_roles = {
            5: "Level 5",
            10: "Level 10", 
            25: "Level 25",
            50: "Level 50"
        }
        
        if level in level_roles:
            role = discord.utils.get(guild.roles, name=level_roles[level])
            if role:
                try:
                    await member.add_roles(role)
                    await member.send(f"🎉 Du hast die Rolle **{role.name}** für Level {level} erhalten!")
                except discord.Forbidden:
                    pass  # No permission to add role or send DM

    @app_commands.command(name="level", description="Zeigt dein Level und XP an.")
    async def level_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        user = member or interaction.user
        uid = str(user.id)
        gid = str(interaction.guild.id)
        
        user_data = self.data.get(gid, {}).get(uid, {"xp": 0, "level": 1, "messages": 0})
        
        # Calculate progress to next level
        current_level = user_data["level"]
        current_xp = user_data["xp"]
        xp_needed = get_xp_for_level(current_level + 1)
        xp_for_current = get_xp_for_level(current_level)
        progress = min(100, ((current_xp - xp_for_current) / (xp_needed - xp_for_current)) * 100) if xp_needed > xp_for_current else 100
        
        # Create progress bar
        progress_bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))
        
        embed = discord.Embed(
            title=f"📊 Level von {user.display_name}", 
            color=VANTAX_COLOR
        )
        
        embed.add_field(name="🏆 Level", value=f"**{current_level}**", inline=True)
        embed.add_field(name="⭐ Gesamt XP", value=f"**{current_xp}**", inline=True)
        embed.add_field(name="📝 Nachrichten", value=f"**{user_data.get('messages', 0)}**", inline=True)
        
        embed.add_field(
            name="📈 Fortschritt zum nächsten Level", 
            value=f"{progress_bar} {progress:.1f}%\n{current_xp - xp_for_current} / {xp_needed - xp_for_current} XP",
            inline=False
        )
        
        # Show rank on server
        all_users = self.data.get(gid, {})
        sorted_users = sorted(all_users.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
        rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == str(user.id)), len(sorted_users))
        
        embed.add_field(name="🥇 Rang auf Server", value=f"#{rank} von {len(sorted_users)}", inline=True)
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=VANTAX_FOOTER)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Zeigt die Top 10 XP.")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        gid = str(interaction.guild.id)
        users = self.data.get(gid, {})
        
        # Sort users by XP and get top 10
        sorted_users = sorted(users.items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]
        
        if not sorted_users:
            embed = discord.Embed(
                title="🏆 VANTAX Leaderboard",
                description="Noch keine Daten!",
                color=VANTAX_COLOR
            )
        else:
            # Create leaderboard with medals
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            
            description = "\n".join([
                f"**{i+1}.** {medals[i]} <@{uid}> - **Level {udata.get('level', 1)}** ({udata.get('xp', 0)} XP)"
                for i, (uid, udata) in enumerate(sorted_users)
            ])
            
            embed = discord.Embed(
                title="🏆 VANTAX Leaderboard",
                description=description,
                color=discord.Color.gold()
            )
            
            # Add server stats
            total_xp = sum(udata.get("xp", 0) for udata in users.values())
            total_messages = sum(udata.get("messages", 0) for udata in users.values())
            
            embed.add_field(name="📊 Server Statistiken", value=f"👥 **{len(users)}** Nutzer\n💬 **{total_messages}** Nachrichten\n⭐ **{total_xp}** Gesamt XP", inline=False)
        
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.set_footer(text=VANTAX_FOOTER)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Level(bot))
