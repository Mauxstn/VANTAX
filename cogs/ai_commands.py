import discord
import aiohttp
import json
import asyncio
import random
from discord.ext import commands
import os

class AICommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.google_translate_key = os.getenv("GOOGLE_TRANSLATE_KEY", "")
        
    @commands.command(name="chatgpt")
    async def chatgpt(self, ctx, *, prompt: str):
        """OpenAI GPT-4 Integration"""
        if not self.openai_key:
            await ctx.send("OpenAI API Key nicht konfiguriert!")
            return
            
        async with ctx.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": "Du bist ein hilfreicher Discord Bot Assistent."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            reply = result['choices'][0]['message']['content']
                            
                            embed = discord.Embed(
                                title="🤖 ChatGPT Antwort",
                                description=reply,
                                color=discord.Color.blue()
                            )
                            embed.add_field(name="💬 Deine Frage", value=prompt, inline=False)
                            embed.set_footer(text=f"Powered by GPT-4 | Requested by {ctx.author.name}")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"Fehler: {response.status}")
                            
            except Exception as e:
                await ctx.send(f"Fehler bei der Anfrage: {e}")

    @commands.command(name="image_gen")
    async def image_gen(self, ctx, *, prompt: str):
        """DALL-E 3 Bildgenerierung"""
        if not self.openai_key:
            await ctx.send("OpenAI API Key nicht konfiguriert!")
            return
            
        async with ctx.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "quality": "standard"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/images/generations",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            image_url = result['data'][0]['url']
                            
                            embed = discord.Embed(
                                title="🎨 AI Bildgenerierung",
                                description=f"**Prompt:** {prompt}",
                                color=discord.Color.purple()
                            )
                            embed.set_image(url=image_url)
                            embed.set_footer(text="Powered by DALL-E 3 | Requested by {ctx.author.name}")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"Fehler: {response.status}")
                            
            except Exception as e:
                await ctx.send(f"Fehler bei der Bildgenerierung: {e}")

    @commands.command(name="translate")
    async def translate(self, ctx, target_lang: str, *, text: str):
        """Google Translate API"""
        if not self.google_translate_key:
            # Fallback zu kostenlosem Service
            await ctx.send("Google Translate API nicht konfiguriert. Nutze kostenlosen Service...")
            
            # MyMemory API (kostenlos, limitiert)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.mymemory.translated.net/get?q={text}&langpair=auto|{target_lang}"
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            translated = result['responseData']['translatedText']
                            
                            embed = discord.Embed(
                                title="🌐 Übersetzung",
                                color=discord.Color.green()
                            )
                            embed.add_field(name="📝 Original", value=text, inline=False)
                            embed.add_field(name="🔄 Übersetzt", value=translated, inline=False)
                            embed.add_field(name="🌍 Ziel-Sprache", value=target_lang.upper())
                            embed.set_footer(text="Powered by MyMemory API")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send("Übersetzung fehlgeschlagen!")
            except Exception as e:
                await ctx.send(f"Fehler bei der Übersetzung: {e}")
            return
            
        # Mit Google Translate API
        async with ctx.typing():
            try:
                url = f"https://translation.googleapis.com/language/translate/v2?key={self.google_translate_key}"
                data = {
                    "q": text,
                    "target": target_lang,
                    "source": "auto"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            translated = result['data']['translations'][0]['translatedText']
                            source_lang = result['data']['translations'][0]['detectedSourceLanguage']
                            
                            embed = discord.Embed(
                                title="🌐 Google Übersetzung",
                                color=discord.Color.blue()
                            )
                            embed.add_field(name="📝 Original", value=f"{text} ({source_lang.upper()})", inline=False)
                            embed.add_field(name="🔄 Übersetzt", value=f"{translated} ({target_lang.upper()})", inline=False)
                            embed.set_footer(text="Powered by Google Translate")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send("Übersetzung fehlgeschlagen!")
                            
            except Exception as e:
                await ctx.send(f"Fehler bei der Übersetzung: {e}")

    @commands.command(name="summarize")
    async def summarize(self, ctx, *, text: str):
        """Text Zusammenfassung"""
        if not self.openai_key:
            await ctx.send("OpenAI API Key nicht konfiguriert!")
            return
            
        async with ctx.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Fasse den folgenden Text präzise zusammen."},
                        {"role": "user", "content": text}
                    ],
                    "max_tokens": 200,
                    "temperature": 0.3
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            summary = result['choices'][0]['message']['content']
                            
                            embed = discord.Embed(
                                title="📝 Text Zusammenfassung",
                                description=summary,
                                color=discord.Color.orange()
                            )
                            embed.add_field(name="📄 Original Länge", value=f"{len(text)} Zeichen")
                            embed.add_field(name="📊 Zusammenfassung Länge", value=f"{len(summary)} Zeichen")
                            embed.set_footer(text="Powered by GPT-3.5 | Requested by {ctx.author.name}")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"Fehler: {response.status}")
                            
            except Exception as e:
                await ctx.send(f"Fehler bei der Zusammenfassung: {e}")

    @commands.command(name="sentiment")
    async def sentiment(self, ctx, *, text: str):
        """Gefühlsanalyse"""
        if not self.openai_key:
            await ctx.send("OpenAI API Key nicht konfiguriert!")
            return
            
        async with ctx.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Analysiere die Gefühle in diesem Text und gib eine kurze Bewertung mit Emojis."},
                        {"role": "user", "content": text}
                    ],
                    "max_tokens": 100,
                    "temperature": 0.3
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            analysis = result['choices'][0]['message']['content']
                            
                            # Sentiment emojis
                            if "positiv" in analysis.lower() or "glücklich" in analysis.lower():
                                color = discord.Color.green()
                                emoji = "😊"
                            elif "negativ" in analysis.lower() or "traurig" in analysis.lower():
                                color = discord.Color.red()
                                emoji = "😢"
                            else:
                                color = discord.Color.yellow()
                                emoji = "😐"
                            
                            embed = discord.Embed(
                                title=f"{emoji} Gefühlsanalyse",
                                description=analysis,
                                color=color
                            )
                            embed.add_field(name="📝 Analysierter Text", value=text, inline=False)
                            embed.set_footer(text="Powered by GPT-3.5 | Requested by {ctx.author.name}")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"Fehler: {response.status}")
                            
            except Exception as e:
                await ctx.send(f"Fehler bei der Gefühlsanalyse: {e}")

    @commands.command(name="code_helper")
    async def code_helper(self, ctx, *, problem: str):
        """Code Completion & Debugging"""
        if not self.openai_key:
            await ctx.send("OpenAI API Key nicht konfiguriert!")
            return
            
        async with ctx.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": "Du bist ein erfahrener Programmierer. Hilf bei Code-Problemen und gib Lösungen mit Code-Beispielen."},
                        {"role": "user", "content": problem}
                    ],
                    "max_tokens": 800,
                    "temperature": 0.2
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            solution = result['choices'][0]['message']['content']
                            
                            embed = discord.Embed(
                                title="💻 Code Hilfe",
                                description=solution,
                                color=discord.Color.blue()
                            )
                            embed.add_field(name="🐛 Problem", value=problem, inline=False)
                            embed.set_footer(text="Powered by GPT-4 | Requested by {ctx.author.name}")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"Fehler: {response.status}")
                            
            except Exception as e:
                await ctx.send(f"Fehler bei der Code-Hilfe: {e}")

    @commands.command(name="story_generator")
    async def story_generator(self, ctx, *, prompt: str):
        """KI Story Generator"""
        if not self.openai_key:
            await ctx.send("OpenAI API Key nicht konfiguriert!")
            return
            
        async with ctx.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Schreibe eine kurze, kreative Geschichte basierend auf der Eingabe."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 400,
                    "temperature": 0.8
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            story = result['choices'][0]['message']['content']
                            
                            embed = discord.Embed(
                                title="📖 KI Story",
                                description=story,
                                color=discord.Color.purple()
                            )
                            embed.add_field(name="✍️ Prompt", value=prompt, inline=False)
                            embed.set_footer(text="Powered by GPT-3.5 | Requested by {ctx.author.name}")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"Fehler: {response.status}")
                            
            except Exception as e:
                await ctx.send(f"Fehler bei der Story-Generierung: {e}")

    @commands.command(name="poem")
    async def poem(self, ctx, *, topic: str):
        """AI Gedichte"""
        if not self.openai_key:
            await ctx.send("OpenAI API Key nicht konfiguriert!")
            return
            
        async with ctx.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Schreibe ein kurzes, kreatives Gedicht über das gegebene Thema."},
                        {"role": "user", "content": topic}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            poem = result['choices'][0]['message']['content']
                            
                            embed = discord.Embed(
                                title="🎭 AI Gedicht",
                                description=poem,
                                color=discord.Color.pink()
                            )
                            embed.add_field(name="✍️ Thema", value=topic, inline=False)
                            embed.set_footer(text="Powered by GPT-3.5 | Requested by {ctx.author.name}")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"Fehler: {response.status}")
                            
            except Exception as e:
                await ctx.send(f"Fehler bei der Gedicht-Generierung: {e}")

    @commands.command(name="joke")
    async def joke(self, ctx, category: str = "general"):
        """AI Witze"""
        if not self.openai_key:
            # Fallback zu预设 Witzen
            jokes = {
                "general": [
                    "Warum können Geister so schlecht lügen? Weil man durch sie hindurchsehen kann!",
                    "Was ist grün und rennt durch den Garten? Ein Rasen-Stier!",
                    "Wie nennt man einen Bären ohne Zähne? Einen Gummibären!"
                ],
                "tech": [
                    "Warum programmieren Programmierer im Dunkeln? Weil sie Licht scheuen!",
                    "Es gibt 10 Arten von Menschen: Die, die Binär verstehen, und die, die es nicht tun."
                ],
                "dad": [
                    "Ich habe einen Witz über NaN... aber er macht keinen Sinn.",
                    "Ich habe einen Witz über Zeitreisen... aber den erzähle ich dir später."
                ]
            }
            
            joke_list = jokes.get(category.lower(), jokes["general"])
            joke = random.choice(joke_list)
            
            embed = discord.Embed(
                title="😄 Witz des Tages",
                description=joke,
                color=discord.Color.yellow()
            )
            embed.add_field(name="📂 Kategorie", value=category.capitalize())
            embed.set_footer(text="Classic Jokes | Requested by {ctx.author.name}")
            return await ctx.send(embed)
            
        async with ctx.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": f"Erzähle einen lustigen Witz aus der Kategorie: {category}"},
                        {"role": "user", "content": "Erzähl mir einen Witz"}
                    ],
                    "max_tokens": 200,
                    "temperature": 0.8
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            joke = result['choices'][0]['message']['content']
                            
                            embed = discord.Embed(
                                title="😄 AI Witz",
                                description=joke,
                                color=discord.Color.yellow()
                            )
                            embed.add_field(name="📂 Kategorie", value=category.capitalize())
                            embed.set_footer(text="Powered by GPT-3.5 | Requested by {ctx.author.name}")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"Fehler: {response.status}")
                            
            except Exception as e:
                await ctx.send(f"Fehler beim Witz: {e}")

    @commands.command(name="advice")
    async def advice(self, ctx, *, topic: str = None):
        """AI Ratschläge"""
        if not self.openai_key:
            await ctx.send("OpenAI API Key nicht konfiguriert!")
            return
            
        async with ctx.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                
                prompt = f"Gib einen hilfreichen Ratschlag zum Thema: {topic}" if topic else "Gib einen allgemeinen Lebensrat"
                
                data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Du bist ein weiser Berater. Gib nützliche, durchdachte Ratschläge."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.5
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            advice = result['choices'][0]['message']['content']
                            
                            embed = discord.Embed(
                                title="💡 AI Ratschlag",
                                description=advice,
                                color=discord.Color.teal()
                            )
                            if topic:
                                embed.add_field(name="🎯 Thema", value=topic, inline=False)
                            embed.set_footer(text="Powered by GPT-3.5 | Requested by {ctx.author.name}")
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"Fehler: {response.status}")
                            
            except Exception as e:
                await ctx.send(f"Fehler beim Ratschlag: {e}")

async def setup(bot):
    await bot.add_cog(AICommands(bot))
