# 🔱 PoseidonUI — Gestión Avanzada para Comunidades de Discord

[![CI](https://github.com/Luciuss04/PoseidonUI/actions/workflows/ci.yml/badge.svg)](https://github.com/Luciuss04/PoseidonUI/actions/workflows/ci.yml)
[![Website](https://img.shields.io/badge/Website-PoseidonUI-0077be)](https://luciuss04.github.io/PoseidonUI/)
[![Discord](https://img.shields.io/discord/443479189597716480?color=5865F2&label=Soporte)](https://discord.gg/Kaf728xRFA)

![Banner](banner.png)

**PoseidonUI** es la solución definitiva para servidores de Discord que buscan profesionalismo, entretenimiento y gestión automatizada. Desde sistemas de economía complejos hasta batallas de mascotas estratégicas, todo bajo una interfaz moderna y temática mitológica.

🔗 **[Ver Documentación y Planes Web](https://luciuss04.github.io/PoseidonUI/)**

---

## 🚀 Características Principales

### 🐾 Sistema de Mascotas v2.1 (Batallas Estratégicas)
- **Colección:** 10 tipos de mascotas (Dragón, Fénix, Alien, Dinosaurio, etc.) con evoluciones visuales.
- **Combate:** Sistema de batalla por turnos con interfaz gráfica (BattleView).
- **Estrategia:** Tabla de elementos (Fuego > Agua > Eléctrico > Tierra > Fuego) y habilidades especiales.
- **Exploración:** Eventos aleatorios (tesoros, peligros, encuentros) para ganar XP y objetos.

### 💰 Economía Global v5.0
- **Bolsa de Valores:** Mercado dinámico de acciones que fluctúa en tiempo real.
- **Trabajos Progresivos:** Sistema de experiencia laboral con ascensos y mejores salarios.
- **Casino:** Ruleta, Slots y Blackjack para apostar monedas.
- **Tienda:** Compra de objetos, mejoras para mascotas y roles.

### 🛡️ Moderación y Seguridad (AutoMod)
- **Guardian:** Sistema de verificación con captcha/botón y roles temporales.
- **Auto-Moderación:** Filtros configurables para malas palabras, mayúsculas excesivas y spam.
- **Logs Avanzados:** Registro detallado de acciones en canales configurables.
- **Comandos:** `/clear`, `/mute`, `/warn`, `/lock`, `/slowmode`.

### 🎵 Música Pro
- **Calidad de Estudio:** Soporte para filtros de audio (Bassboost, Nightcore, 8D, Vaporwave).
- **Fuentes:** YouTube, SoundCloud, Spotify (via yt-dlp).
- **Lyrics:** Integración con Genius para mostrar letras en tiempo real.
- **Estabilidad:** Optimizado para evitar microcortes en hosting Linux (Teramont).

### 🏛️ Comunidad y Social
- **Clanes (Olimpos):** Crea tu propio clan, banco compartido y guerras de clanes.
- **Matrimonios:** Sistema de bodas con anillos, hijos y árbol genealógico.
- **Confesiones:** Sistema de confesiones anónimas con moderación previa.
- **Juegos:** Trivia competitiva, Ahorcado visual, Conecta 4.
- **Oráculo:** Sistema de tickets/soporte con transcripciones automáticas.

---

## 💎 Planes y Licencias

El bot funciona con un sistema de licencias validado criptográficamente.

| Plan | Precio | Incluye | Ideal para |
| :--- | :--- | :--- | :--- |
| **Básico** | 19€ | Moderación, Música, Minijuegos, Guardian | Servidores pequeños |
| **Pro** | 39€ | Todo Básico + Niveles, Economía, Oráculo, Confesiones | Comunidades activas |
| **Élite** | 69€ | Todo Pro + Mascotas v2, Clanes, Bolsa, Integraciones | Gaming / eSports |
| **Custom** | 99€+ | Marca Blanca (Tu Bot), Funciones a medida, Soporte 24/7 | Marcas y Empresas |

> ℹ️ **Nota:** Consulta los detalles completos en nuestra [página web](https://luciuss04.github.io/PoseidonUI/).

---

## 🛠️ Instalación y Despliegue

### Requisitos Previos
- Python 3.11 o superior.
- FFmpeg (para música).
- Clave de licencia válida (archivo `licenses_plans.txt` o variable de entorno).

### Despliegue Local / VPS
1. **Clonar repositorio:**
   ```bash
   git clone https://github.com/Luciuss04/PoseidonUI.git
   cd PoseidonUI/BotDiscord4.0
   ```

2. **Configurar entorno:**
   Copia `.env.example` a `.env` y rellena las variables:
   ```ini
   DISCORD_TOKEN=tu_token_aqui
   LICENSE_KEY=tu_clave_de_licencia
   # ... otras variables
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Iniciar:**
   ```bash
   python main.py
   # O usa start.bat en Windows
   ```

### Despliegue en Teramont (Pterodactyl)
1. Subir el contenido de la carpeta `BotDiscord4.0` a la raíz del servidor.
2. Configurar el **Punto de Entrada** (Startup File) como `app.py`.
3. Subir el archivo `.env` manualmente o configurar las variables en el panel.
4. Asegurarse de que `ffmpeg` está disponible o configurado en el bot.

---

## 📂 Estructura del Proyecto

```text
PoseidonUI/
├── BotDiscord4.0/          # Núcleo del Bot
│   ├── bot/
│   │   ├── cogs/           # Módulos (Comandos)
│   │   │   ├── comunidad/  # Clanes, Oráculo, Social
│   │   │   ├── economia/   # Bolsa, Tienda, Trabajos
│   │   │   ├── info/       # Ayuda, Ping, Planes
│   │   │   ├── mascotas/   # Sistema de Batallas y Mascotas
│   │   │   ├── moderacion/ # AutoMod, Guardian
│   │   │   ├── musica/     # Reproductor y Filtros
│   │   │   └── util/       # Utilidades varias
│   │   └── ...
│   ├── data/               # Persistencia (JSONs, ignorados en git)
│   ├── app.py              # Entrypoint para Hosting
│   └── main.py             # Entrypoint Local
└── docs/                   # Website / Documentación (GitHub Pages)
```

---

## 🤝 Soporte y Contacto

¿Necesitas ayuda o quieres adquirir una licencia?

- **Discord:** [Únete a nuestro servidor](https://discord.gg/Kaf728xRFA)
- **Web:** [luciuss04.github.io/PoseidonUI](https://luciuss04.github.io/PoseidonUI/)
- **Email:** luciuss0444@gmail.com

---

© 2026 PoseidonUI. Todos los derechos reservados.
