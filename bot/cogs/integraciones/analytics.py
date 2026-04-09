# -*- coding: utf-8 -*-
import datetime

from discord.ext import commands, tasks

from bot.config import load_json_file, save_json_file_atomic

ANALYTICS_FILE = "analytics_data.json"


class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = self._load_data()
        self.save_task.start()

    def _load_data(self):
        data = load_json_file(ANALYTICS_FILE, {})
        return data if isinstance(data, dict) else {}

    def _save_data(self):
        try:
            save_json_file_atomic(ANALYTICS_FILE, self.data, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"🔥 [Analytics] Error al guardar: {e}")

    @tasks.loop(minutes=5)
    async def save_task(self):
        self._save_data()

    def _increment(self, guild_id, metric):
        if not guild_id:
            return
        gid = str(guild_id)
        date = datetime.date.today().isoformat()

        if gid not in self.data:
            self.data[gid] = {}
        if date not in self.data[gid]:
            self.data[gid][date] = {
                "messages": 0,
                "commands": 0,
                "joins": 0,
                "sentiment_sum": 0,
                "sentiment_count": 0,
            }

        self.data[gid][date][metric] = self.data[gid][date].get(metric, 0) + 1

    def _add_sentiment(self, guild_id, score):
        if not guild_id:
            return
        gid = str(guild_id)
        date = datetime.date.today().isoformat()

        if gid not in self.data:
            self.data[gid] = {}
        if date not in self.data[gid]:
            self.data[gid][date] = {
                "messages": 0,
                "commands": 0,
                "joins": 0,
                "sentiment_sum": 0,
                "sentiment_count": 0,
            }

        self.data[gid][date]["sentiment_sum"] += score
        self.data[gid][date]["sentiment_count"] += 1

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        self._increment(message.guild.id if message.guild else None, "messages")

        # Analizar sentimiento si el Cog está cargado
        sentiment_cog = self.bot.get_cog("SentimentAI")
        if sentiment_cog and len(message.content) > 10:
            analysis = sentiment_cog.analyze_sentiment(message.content)
            self._add_sentiment(message.guild.id if message.guild else None, analysis["score"])

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction, command):
        self._increment(interaction.guild_id, "commands")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self._increment(member.guild.id, "joins")

    def get_guild_analytics(self, guild_id, days=7):
        gid = str(guild_id)

        # Obtener los últimos N días
        history = []
        for i in range(days):
            date = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            day_data = {
                "messages": 0,
                "commands": 0,
                "joins": 0,
                "sentiment_sum": 0,
                "sentiment_count": 0,
            }
            if gid in self.data and date in self.data[gid]:
                day_data.update(self.data[gid][date])
            day_data["date"] = date
            history.append(day_data)

        return history[::-1]  # Retornar en orden cronológico


async def setup(bot):
    await bot.add_cog(Analytics(bot))
