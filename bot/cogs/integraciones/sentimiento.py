# -*- coding: utf-8 -*-

import discord
from discord.ext import commands

from bot.config import LOG_CHANNEL_ID, get_guild_setting


class SentimentAI(commands.Cog):
    """Motor de Análisis de Sentimiento y Toxicidad de PoseidonUI (v4.2)"""

    def __init__(self, bot):
        self.bot = bot

        # Diccionarios de palabras clave para análisis de sentimiento
        self.KEYWORDS_POSITIVE = [
            "gracias",
            "genial",
            "increíble",
            "buen",
            "mejor",
            "feliz",
            "contento",
            "ayuda",
            "solucionado",
            "perfecto",
            "excelente",
            "amo",
            "adoro",
            "bien",
            "fantástico",
            "maravilla",
            "recomiendo",
        ]

        self.KEYWORDS_NEGATIVE = [
            "mal",
            "peor",
            "asco",
            "horrible",
            "error",
            "fallo",
            "malo",
            "odio",
            "enfadado",
            "triste",
            "pésimo",
            "basura",
            "inútil",
            "no funciona",
            "decepción",
            "estafa",
            "robo",
            "lento",
        ]

        self.KEYWORDS_TOXIC = [
            "idiota",
            "estúpido",
            "imbécil",
            "tonto",
            "mierda",
            "joder",
            "puto",
            "puta",
            "cabrón",
            "muérete",
            "basura",
            "rata",
            "manco",
            "lárgate",
            "inservible",
            "estupidez",
        ]

    def analyze_sentiment(self, text: str):
        """Analiza un texto y devuelve una puntuación de sentimiento (-1 a 1) y nivel de toxicidad (0 a 1)"""
        if not text:
            return {"score": 0, "label": "Neutral", "toxicity": 0}

        text = text.lower()
        score = 0
        toxicity = 0

        # 1. Calcular Sentimiento
        for word in self.KEYWORDS_POSITIVE:
            if word in text:
                score += 1

        for word in self.KEYWORDS_NEGATIVE:
            if word in text:
                score -= 1

        # 2. Calcular Toxicidad
        toxic_count = 0
        for word in self.KEYWORDS_TOXIC:
            if word in text:
                toxic_count += 1
                toxicity += 0.2

        # Normalización básica
        score = max(-1, min(1, score / 5)) if score != 0 else 0
        toxicity = min(1, toxicity)

        # Etiquetado
        label = "Neutral"
        if score > 0.2:
            label = "Positivo"
        elif score < -0.2:
            label = "Negativo"
        if toxicity > 0.5:
            label = "Tóxico"

        return {
            "score": score,
            "label": label,
            "toxicity": toxicity,
            "emoji": (
                "😊"
                if label == "Positivo"
                else ("😠" if label == "Tóxico" else ("😟" if label == "Negativo" else "😐"))
            ),
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # Solo analizar mensajes con cierta longitud para evitar falsos positivos
        if len(message.content) < 5:
            return

        analysis = self.analyze_sentiment(message.content)

        # Alerta de toxicidad alta
        if analysis["toxicity"] >= 0.7:
            # Aquí podríamos enviar un log al canal de logs del servidor
            try:
                log_cid = get_guild_setting(message.guild.id, "log_channel_id", LOG_CHANNEL_ID)
                log_ch = message.guild.get_channel(int(log_cid))

                if log_ch:
                    embed = discord.Embed(
                        title="⚠️ Alerta de Toxicidad Detectada",
                        description=f"Se ha detectado un mensaje con alta toxicidad en {message.channel.mention}.",
                        color=discord.Color.red(),
                    )
                    embed.add_field(name="Usuario", value=f"{message.author} ({message.author.id})")
                    embed.add_field(name="Mensaje", value=message.content[:1024])
                    embed.add_field(
                        name="Nivel de Toxicidad", value=f"{int(analysis['toxicity'] * 100)}%"
                    )
                    await log_ch.send(embed=embed)
            except Exception as e:
                print(f"Error enviando alerta de toxicidad: {e}")


async def setup(bot):
    await bot.add_cog(SentimentAI(bot))
