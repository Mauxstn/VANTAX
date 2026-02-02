import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import aiohttp

VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

class MemeView(View):
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.bot = bot

    @discord.ui.button(label="Neues Meme", style=discord.ButtonStyle.green)
    async def new_meme(self, interaction: discord.Interaction, button: Button):
        # Acknowledge the interaction first
        await interaction.response.defer()
        
        url = "https://meme-api.com/gimme"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await interaction.followup.send("Konnte kein Meme laden :(", ephemeral=True)
                    return
                data = await resp.json()
                embed = discord.Embed(title="Meme", color=VANTAX_COLOR)
                embed.set_image(url=data['url'])
                embed.set_footer(text=VANTAX_FOOTER)
                await interaction.followup.send(embed=embed, view=MemeView(self.bot))

class ZufallView(View):
    def __init__(self, min, max):
        super().__init__(timeout=30)
        self.min = min
        self.max = max

    @discord.ui.button(label="Neue Zahl", style=discord.ButtonStyle.blurple)
    async def new_number(self, interaction: discord.Interaction, button: Button):
        # Acknowledge the interaction first
        await interaction.response.defer()
        
        num = random.randint(self.min, self.max)
        embed = discord.Embed(title="Neue Zufallszahl", description=f"{num}", color=VANTAX_COLOR)
        embed.set_footer(text=VANTAX_FOOTER)
        await interaction.followup.send(embed=embed, ephemeral=True)

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="meme", description="Zeigt ein zufälliges deutsches Meme.")
    async def meme_slash(self, interaction: discord.Interaction):
        # German subreddits for memes
        subreddits = [
            'r/DeutscheMemes',
            'r/ich_iel',  # German version of me_irl
            'r/HandOfMemes',
            'r/maudadomememittwoch',
            'r/spacefrogs'
        ]
        
        # Try each subreddit until we get a valid response
        for subreddit in subreddits:
            url = f"https://meme-api.com/gimme/{subreddit}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if 'url' in data:
                                embed = discord.Embed(title=f"Meme aus r/{data.get('subreddit')}", color=VANTAX_COLOR)
                                embed.set_image(url=data['url'])
                                embed.set_footer(text=f"👍 {data.get('ups', 0)} | 💬 {data.get('num_comments', 0)} | {VANTAX_FOOTER}")
                                # Remove ephemeral=True to make it visible to everyone
                                await interaction.response.send_message(embed=embed, view=MemeView(self.bot))
                                return
            except Exception as e:
                print(f"Error fetching from {subreddit}: {e}")
                continue
        
        # If no meme was found in German subreddits, fall back to English
        try:
            url = "https://meme-api.com/gimme"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(title="Englisches Meme (kein deutsches gefunden)", color=VANTAX_COLOR)
                        embed.set_image(url=data['url'])
                        embed.set_footer(text=f"👍 {data.get('ups', 0)} | 💬 {data.get('num_comments', 0)} | {VANTAX_FOOTER}")
                        await interaction.response.send_message(embed=embed, view=MemeView(self.bot))
                        return
        except Exception as e:
            print(f"Error fetching fallback meme: {e}")
        
        await interaction.response.send_message("Entschuldigung, ich konnte leider kein Meme finden. Versuche es später noch einmal!", ephemeral=True)

    @app_commands.command(name="zufall", description="Zufallszahl zwischen min und max.")
    async def zufall_slash(self, interaction: discord.Interaction, min: int = 1, max: int = 100):
        num = random.randint(min, max)
        embed = discord.Embed(title="Deine Zufallszahl", description=f"{num}", color=VANTAX_COLOR)
        embed.set_footer(text=VANTAX_FOOTER)
        await interaction.response.send_message(embed=embed, view=ZufallView(min, max), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Fun(bot))
