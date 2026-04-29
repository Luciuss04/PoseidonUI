# 🔱 PoseidonUI — Gestión de Élite para Comunidades de Discord (v4.2)

[![CI](https://github.com/Luciuss04/PoseidonUI/actions/workflows/ci.yml/badge.svg)](https://github.com/Luciuss04/PoseidonUI/actions/workflows/ci.yml)
[![Website](https://img.shields.io/badge/Website-PoseidonUI-0077be)](https://luciuss04.github.io/PoseidonUI/)
[![Discord](https://img.shields.io/discord/443479189597716480?color=5865F2&label=Soporte)](https://discord.gg/Kaf728xRFA)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

![Banner](banner.png)

**PoseidonUI** es la solución definitiva para servidores de Discord en 2026. Combina una gestión profesional mediante un **Dashboard Web** exclusivo, inteligencia artificial avanzada (**IA de Atenea**) y entretenimiento de alto nivel con un sistema de **Mascotas y Coliseo** totalmente interactivo.

🔗 **[Explorar Panel de Control](https://luciuss04.github.io/PoseidonUI/admin.html)** | **[Documentación Oficial](https://luciuss04.github.io/PoseidonUI/)**

---

## 🚀 Novedades Destacadas (Actualización Marzo 2026)

### 🖥️ Dashboard Administrativo Web
- **Control Remoto:** Gestiona canales de logs, roles de staff y temas visuales desde tu navegador.
- **Estadísticas en Tiempo Real:** Monitoriza el ping, uptime y actividad de los servidores.
- **Visor de Logs:** Accede a los registros detallados de cada servidor de forma centralizada.
- **Seguridad SHA-256:** Sistema de autenticación robusto con protección contra ataques de fuerza bruta.

### 🦉 IA de Atenea (Tickets Inteligentes)
- **Análisis de Intenciones:** La IA analiza el contenido de los tickets para sugerir la categoría adecuada.
- **Auto-Urgencia:** Detección automática de palabras clave críticas para marcar tickets como prioritarios.
- **Respuestas Divinas:** Bienvenida inteligente y personalizada según el problema detectado.

### 🏟️ El Coliseo de Mascotas v4.2
- **Interfaz RPG:** Barras de vida dinámicas y diseño visual estilo Coliseo.
- **Habilidades Únicas:** Cada especie cuenta con ataques especiales (Ej: *Aliento de Fuego*, *Descarga Voltáica*).
- **Críticos Divinos:** Sistema de combate aleatorio con bonificadores por elementos y golpes críticos.

---

## 🛠️ Características Core

- **💰 Economía Pro:** Bolsa de valores dinámica, trabajos con niveles y casino completo.
- **🛡️ Seguridad Avanzada:** Sistema Guardian (Captcha), AutoMod inteligente y soporte para protocolo DAVE (Voice E2EE).
- **🎵 Música Studio:** Filtros de audio (8D, Bassboost, Nightcore) y búsqueda ultra-rápida.
- **🏛️ Social & Rol:** Sistema de Clanes (Olimpos), Matrimonios, Confesiones y Niveles con rangos mitológicos.

---

## ¿Qué hace el bot? (Guía funcional)

PoseidonUI es un bot modular (por cogs) que combina moderación, entretenimiento y administración remota. La lista exacta de comandos puede variar según el plan de licencia: el comando **/ayuda** muestra solo los comandos disponibles para tu servidor.

### 🧩 Módulos principales (por carpeta)

- **Moderación** (`/bot/cogs/moderacion`): antispam, automod, guardian, herramientas de staff y logs.
- **Comunidad** (`/bot/cogs/comunidad`): confesiones, oráculo, streaming, encuestas, matrimonios, clanes, niveles y utilidades sociales.
- **Economía** (`/bot/cogs/economia`): monedas, tienda, casino, ofertas y sorteos.
- **Juegos** (`/bot/cogs/juegos`): trivia, ahorcado, rpg y mascotas/coliseo.
- **Integraciones** (`/bot/cogs/integraciones`): RSS, LoL/gaming, sentimiento/analytics y servidor web del dashboard.
- **Info** (`/bot/cogs/info`): about, ayuda y editor de temas.
- **Diagnóstico** (`/bot/cogs/diagnostico`): salud/alertas, herramientas de diagnóstico y hot-reload seguro de cogs.

### 🧭 Comandos rápidos (los más usados)

- **Ayuda**: `/ayuda` (categorías y comandos disponibles por plan).
- **Configuración (Admin)**: `/config ver`, `/config logcanal`, `/config staffrol`, `/config alertas`, `/config salud`.
- **Diagnóstico**: `/diagnostico`, `/comandos`, `/diagnostico_permisos`.
- **Confesiones**: `/set_confesiones` y comandos de confesión (según configuración del canal).
- **Minijuegos**: `/trivia`, `/ahorcado` (y otros según cogs activos).

### 🔒 Licencias (modo hard)

- El bot puede bloquear comandos por servidor según `license_plan`.
- También filtra la interfaz de ayuda para ocultar comandos no disponibles.
- Planes válidos a nivel de configuración: `basic`, `pro`, `elite`, `custom`.

---

## 🌐 Dashboard Web y API

El bot expone un servidor web (AioHTTP) para el dashboard y la API.

### Endpoints públicos

- `GET /api/stats`: estado básico (online, versión, latencia, uptime, conteos).
- `GET /api/health`: salud del bot (latencia, CPU, RAM, errores últimos 5 min) y estado `ok/degraded/critical`.

### Endpoints privados (requieren login)

- `POST /api/login` → devuelve `token` (sesión).
- `GET /api/guilds` → lista de servidores + config.
- `GET /api/config/{guild_id}` → config del servidor + canales/roles.
- `POST /api/config/update` → actualiza claves permitidas del servidor (whitelist).
- `GET /api/logs/{guild_id}` → logs recientes del servidor.
- `GET /api/analytics/{guild_id}` → métricas/analytics.
- `GET/POST /api/streaming/*` → configuración de streaming.
- `GET/POST /api/custom_cmds/*` → comandos personalizados.
- `POST /api/theme/update` → tema.
- `POST /api/reboot` → reinicio controlado.

### Variables típicas

- `SERVER_PORT`: puerto del servidor web (dashboard/API).

---

## ⚙️ Configuración por servidor (guild_config.json)

La configuración se guarda por servidor y se puede editar desde el dashboard o con `/config ...`.

Claves habituales:

- `log_channel_id`: canal principal de logs.
- `alert_channel_id`: canal de alertas de salud/degradación.
- `staff_role_ids`: lista de roles staff (IDs).
- `theme`: tema visual (`default`, `ocean`, `fire`, `nature`).
- `license_plan`: plan por servidor (`basic|pro|elite|custom`).
- `confesiones_channel_id`: canal donde se publican confesiones.
- `moderacion_logs_channel_id`: canal específico para logs de moderación (si aplica).
- `health_thresholds`: umbrales personalizados de alertas (latencia/cpu/mem/errores).

---

## 💎 Planes y Licencias

| Plan | Incluye | Ideal para |
| :--- | :--- | :--- |
| **Básico** | Moderación, Música, Minijuegos, Guardian | Servidores pequeños |
| **Pro** | Todo Básico + Niveles, Economía, Oráculo, Confesiones | Comunidades activas |
| **Élite** | Todo Pro + Mascotas v4.2, Dashboard Web, IA Atenea | Gaming / eSports |
| **Custom** | Todo Élite + marca blanca + funciones a medida | Proyectos a medida |

---

## ⚙️ Instalación y Configuración

### Requisitos
- Python 3.11+
- FFmpeg (Instalado en el PATH)
- Un puerto abierto para el Dashboard Web (Configurable en .env)

### Guía Rápida
1. **Clonar y Entrar:**
   ```bash
   git clone https://github.com/Luciuss04/PoseidonUI.git
   cd PoseidonUI/BotDiscord4.0
   ```
2. **Entorno:**
   Configura el archivo `.env` basándote en `.env.example`.
3. **Dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Ejecutar:**
   ```bash
   python app.py
   ```

### Despliegue en Hosting (Pterodactyl/VPS)
1. Subir el contenido de la carpeta `BotDiscord4.0` a la raíz del servidor.
2. Configurar el **Punto de Entrada** (Startup File) como `app.py`.
3. Configurar las variables de entorno en el panel del servidor.

### 🔒 Seguridad Importante
- Asegúrate de configurar `LICENSE_SIGNING_SECRET` para proteger la integridad de tus licencias.
- El Dashboard requiere que el navegador permita "Contenido no seguro" si no se utiliza un certificado SSL en el host.

---

## 📂 Estructura de Carpetas

- `/bot/cogs`: Módulos de comandos organizados por categorías (Economía, Juegos, Moderación, etc.).
- `/docs`: Frontend del Dashboard y Landing Page (Servido por GitHub Pages).
- `app.py`: Punto de entrada principal optimizado para Teramont/Pterodactyl.
- `guild_config.json`: Persistencia de configuraciones personalizadas por servidor.

---

## 🤝 Soporte

- **Discord:** [Únete al Soporte](https://discord.gg/Kaf728xRFA)
- **Web:** [luciuss04.github.io/PoseidonUI](https://luciuss04.github.io/PoseidonUI/)
- **Email:** luciuss0444@gmail.com

© 2026 PoseidonUI. Todos los derechos reservados.
