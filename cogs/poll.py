import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import json
import os
import datetime

VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"
POLL_FILE = "polls.json"

class PollView(View):
    def __init__(self, poll_id, question, options, creator_id):
        super().__init__(timeout=None)  # Persistent view
        self.poll_id = poll_id
        self.question = question
        self.options = options
        self.creator_id = creator_id
        self.votes = {}
        
    async def handle_vote(self, interaction: discord.Interaction, option_index: int):
        user_id = str(interaction.user.id)
        
        # Remove previous vote if exists
        if user_id in self.votes:
            old_option = self.votes[user_id]
            self.options[old_option]["votes"] -= 1
        
        # Add new vote
        self.votes[user_id] = option_index
        self.options[option_index]["votes"] += 1
        
        # Update message
        await self.update_poll_message(interaction)
        
        # Save poll data
        await self.save_poll_data(interaction.guild.id)
        
        await interaction.response.send_message(
            f"✅ Du hast für **{self.options[option_index]['text']}** gestimmt!",
            ephemeral=True
        )
    
    async def update_poll_message(self, interaction: discord.Interaction):
        # Calculate total votes
        total_votes = sum(option["votes"] for option in self.options)
        
        # Create updated embed
        embed = discord.Embed(
            title=f"📊 {self.question}",
            color=VANTAX_COLOR
        )
        
        embed.add_field(
            name="🗳️ Optionen",
            value="\n".join([
                f"**{chr(65+i)}.** {option['text']} - **{option['votes']}** Stimmen ({option['votes']/total_votes*100:.1f}%)" 
                if total_votes > 0 else f"**{chr(65+i)}.** {option['text']} - **0** Stimmen"
                for i, option in enumerate(self.options)
            ]),
            inline=False
        )
        
        embed.add_field(
            name="📈 Statistik",
            value=f"**{total_votes}** Gesamtstimmen",
            inline=True
        )
        
        embed.set_footer(text=f"Erstellt von {interaction.guild.get_member(self.creator_id).display_name if interaction.guild.get_member(self.creator_id) else 'Unknown'} • {VANTAX_FOOTER}")
        
        # Update the original message
        try:
            await interaction.message.edit(embed=embed, view=self)
        except discord.Forbidden:
            pass
    
    async def save_poll_data(self, guild_id):
        polls = load_polls()
        guild_id = str(guild_id)
        
        if guild_id not in polls:
            polls[guild_id] = {}
        
        polls[guild_id][self.poll_id] = {
            "question": self.question,
            "options": self.options,
            "creator_id": self.creator_id,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        save_polls(polls)

def load_polls():
    if os.path.exists(POLL_FILE):
        with open(POLL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_polls(polls):
    with open(POLL_FILE, 'w', encoding='utf-8') as f:
        json.dump(polls, f, indent=4, ensure_ascii=False)

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_views = {}  # Store active poll views
        
    @app_commands.command(name="poll", description="Erstelle eine Umfrage mit Multiple-Choice Optionen.")
    @app_commands.describe(
        question="Die Frage der Umfrage",
        option1="Option 1",
        option2="Option 2", 
        option3="Option 3 (optional)",
        option4="Option 4 (optional)",
        option5="Option 5 (optional)"
    )
    async def create_poll(
        self, 
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str = None,
        option4: str = None,
        option5: str = None
    ):
        # Validate options
        options = [opt for opt in [option1, option2, option3, option4, option5] if opt]
        
        if len(options) < 2:
            await interaction.response.send_message(
                "❌ Du musst mindestens 2 Optionen angeben!",
                ephemeral=True
            )
            return
        
        if len(options) > 5:
            await interaction.response.send_message(
                "❌ Du kannst maximal 5 Optionen angeben!",
                ephemeral=True
            )
            return
        
        # Create poll data
        poll_id = f"{interaction.guild.id}_{datetime.datetime.now().timestamp()}"
        poll_options = [{"text": opt, "votes": 0} for opt in options]
        
        # Create view with buttons
        view = PollView(poll_id, question, poll_options, interaction.user.id)
        
        # Create initial embed
        embed = discord.Embed(
            title=f"📊 {question}",
            color=VANTAX_COLOR
        )
        
        embed.add_field(
            name="🗳️ Optionen",
            value="\n".join([
                f"**{chr(65+i)}.** {option['text']} - **0** Stimmen"
                for i, option in enumerate(poll_options)
            ]),
            inline=False
        )
        
        embed.add_field(
            name="📈 Statistik",
            value="**0** Gesamtstimmen",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ Info",
            value="Klicke auf die Buttons unten, um abzustimmen!",
            inline=False
        )
        
        embed.set_footer(text=f"Erstellt von {interaction.user.display_name} • {VANTAX_FOOTER}")
        
        # Send poll message
        await interaction.response.send_message(embed=embed, view=view)
        
        # Store view for persistence
        self.active_views[poll_id] = view
        
        # Save initial poll data
        await view.save_poll_data(interaction.guild.id)
    
    @app_commands.command(name="endpoll", description="Beendet eine Umfrage und zeigt die Endergebnisse an.")
    @app_commands.describe(
        poll_id="Die ID der Umfrage (verwende /listpolls um IDs zu sehen)"
    )
    async def end_poll(self, interaction: discord.Interaction, poll_id: str = None):
        polls = load_polls()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in polls or not polls[guild_id]:
            await interaction.response.send_message(
                "❌ Keine aktiven Umfragen gefunden!",
                ephemeral=True
            )
            return
        
        # If no poll_id provided, show list
        if not poll_id:
            embed = discord.Embed(
                title="📋 Aktive Umfragen",
                color=VANTAX_COLOR
            )
            
            for pid, poll_data in polls[guild_id].items():
                creator = interaction.guild.get_member(poll_data["creator_id"])
                creator_name = creator.display_name if creator else "Unknown"
                
                total_votes = sum(opt["votes"] for opt in poll_data["options"])
                
                embed.add_field(
                    name=f"📊 {poll_data['question'][:50]}{'...' if len(poll_data['question']) > 50 else ''}",
                    value=f"**ID:** `{pid}`\n**Ersteller:** {creator_name}\n**Stimmen:** {total_votes}",
                    inline=False
                )
            
            embed.set_footer(text="Verwende /endpoll [ID] um eine bestimmte Umfrage zu beenden")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # End specific poll
        if poll_id not in polls[guild_id]:
            await interaction.response.send_message(
                "❌ Umfrage mit dieser ID nicht gefunden!",
                ephemeral=True
            )
            return
        
        poll_data = polls[guild_id][poll_id]
        
        # Check if user is poll creator or has admin permissions
        if (poll_data["creator_id"] != interaction.user.id and 
            not interaction.user.guild_permissions.manage_messages):
            await interaction.response.send_message(
                "❌ Du kannst nur deine eigenen Umfragen beenden!",
                ephemeral=True
            )
            return
        
        # Create results embed
        total_votes = sum(opt["votes"] for opt in poll_data["options"])
        
        embed = discord.Embed(
            title=f"🏁 Umfrage beendet: {poll_data['question']}",
            color=discord.Color.gold()
        )
        
        # Sort options by votes
        sorted_options = sorted(poll_data["options"], key=lambda x: x["votes"], reverse=True)
        
        results_text = "\n".join([
            f"**{i+1}. Platz:** {option['text']} - **{option['votes']}** Stimmen ({option['votes']/total_votes*100:.1f}%)" 
            if total_votes > 0 else f"**{i+1}. Platz:** {option['text']} - **0** Stimmen"
            for i, option in enumerate(sorted_options)
        ])
        
        embed.add_field(name="🏆 Endergebnisse", value=results_text, inline=False)
        embed.add_field(name="📈 Statistik", value=f"**{total_votes}** Gesamtstimmen", inline=True)
        
        creator = interaction.guild.get_member(poll_data["creator_id"])
        embed.set_footer(
            text=f"Erstellt von {creator.display_name if creator else 'Unknown'} • Beendet von {interaction.user.display_name} • {VANTAX_FOOTER}"
        )
        
        # Remove poll from active polls
        del polls[guild_id][poll_id]
        save_polls(polls)
        
        # Remove view if exists
        if poll_id in self.active_views:
            del self.active_views[poll_id]
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Poll(bot))
