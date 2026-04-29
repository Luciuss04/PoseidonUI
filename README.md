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

## ¿Qué hace el bot? (Guía funcional completa)

PoseidonUI es un bot modular (por cogs) que une **moderación**, **minijuegos**, **economía** e **integraciones**, con dos pilares extra: **configuración por servidor** (persistente) y **dashboard web** para administración remota. La lista exacta de comandos puede variar según el plan de licencia: **/ayuda** muestra solo los comandos disponibles para tu servidor.

### ✅ Puesta en marcha (checklist rápido para Admin)

1. Configura el canal de logs: `/config logcanal #tu-canal`
2. Configura rol/es de staff: `/config staffrol @RolStaff`
3. (Opcional) Configura canal de alertas: `/config alertas #alertas`
4. Ajusta alertas de salud (opcional): `/config salud ...`
5. Abre el dashboard (si lo usas) y revisa:
   - `license_plan` del servidor
   - canales de cada módulo (confesiones, logs de moderación, etc.)

### 🔐 Permisos recomendados del bot (por canal)

- Básicos: `View Channel`, `Send Messages`, `Embed Links`, `Read Message History`
- Si el bot fija mensajes (pines): `Pin Messages`
- Para moderación (según módulos): permisos típicos de moderación (mute/kick/ban, timeout, manage messages)

Si algo falla por permisos: usa `/diagnostico_permisos` (admin-only) para ver exactamente qué falta por canal.

### 🧩 Módulos (cogs) y qué aportan

| Área | Carpeta | Qué incluye (resumen) |
|---|---|---|
| Moderación | `/bot/cogs/moderacion` | antispam, automod, guardian, herramientas de staff y logs |
| Comunidad | `/bot/cogs/comunidad` | confesiones, oráculo, streaming, encuestas, matrimonios, clanes, niveles y utilidades |
| Economía | `/bot/cogs/economia` | monedas, tienda, casino, ofertas y sorteos |
| Juegos | `/bot/cogs/juegos` | trivia, ahorcado, rpg y mascotas/coliseo |
| Integraciones | `/bot/cogs/integraciones` | RSS, LoL/gaming, sentimiento/analytics y servidor web del dashboard |
| Info | `/bot/cogs/info` | about, ayuda y editor de temas |
| Diagnóstico | `/bot/cogs/diagnostico` | salud/alertas, herramientas de diagnóstico y hot-reload seguro de cogs |

### 🧭 “Top comandos” por uso

- **Ayuda**: `/ayuda`
- **Config (Admin)**: `/config ver`, `/config logcanal`, `/config staffrol`, `/config alertas`, `/config salud`
- **Diagnóstico**: `/diagnostico`, `/comandos`, `/diagnostico_permisos`
- **Hot-reload (Admin)**: `/cog list`, `/cog reload modulo:<...> sync:guild|global`
- **Confesiones**: `/set_confesiones #canal` + comandos de confesión (según servidor/configuración)
- **Minijuegos**: `/trivia`, `/ahorcado` (y otros según cogs activos)

### 🔔 Salud y alertas de degradación

- El bot monitoriza métricas básicas (latencia, CPU, RAM y pico de errores recientes).
- Cuando detecta degradación/estado crítico, avisa en `alert_channel_id` (si está configurado) y aplica cooldown para no spamear.
- Personaliza umbrales por servidor con `/config salud`:
  - `latencia_warn/crit` (ms), `cpu_warn/crit` (%), `mem_warn/crit` (%), `errores_warn/crit` (conteo últimos 5 min)

### 🔒 Licencias (modo hard)

- El bot puede bloquear comandos por servidor según `license_plan` (y también oculta comandos no disponibles en **/ayuda**).
- Planes válidos: `basic`, `pro`, `elite`, `custom`.
- Dónde se configura: dashboard (recomendado) o `guild_config.json` (clave `license_plan`).

---

## 🌐 Dashboard Web y API

El bot expone un servidor web (AioHTTP) para el dashboard y la API.

### Flujo de uso del dashboard (resumen)

1. Levanta el bot (el servidor web se inicia junto al bot).
2. Entra en `docs/admin.html` (GitHub Pages o local) y haz login.
3. Selecciona tu servidor y ajusta configuración (canales/roles/tema/licencia).
4. Verifica que los cambios impactan en el bot (comandos, logs, alertas).

### Dashboard desde GitHub Pages (muy importante)

Cuando abres el panel desde GitHub Pages, el frontend necesita saber la URL del bot (tu servidor local/VPS) para llamar a la API.

- El panel te pedirá una URL y la guardará en el navegador como `poseidon_bot_url`.
- Ejemplos de URL:
  - `http://127.0.0.1:8080`
  - `http://TU-IP:8080`
  - `https://tu-dominio.com` (si pones proxy/SSL delante)

### Endpoints públicos

- `GET /api/stats`: estado básico (online, versión, latencia, uptime, conteos).
- `GET /api/health`: salud del bot (latencia, CPU, RAM, errores últimos 5 min) y estado `ok/degraded/critical`.

Ejemplo rápido:

```bash
curl http://127.0.0.1:8080/api/stats
curl http://127.0.0.1:8080/api/health
```

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

Notas:

- La escritura de JSON se realiza de forma atómica para evitar corrupción (guardado seguro).
- El archivo de configuración por servidor incluye migraciones internas para mantener compatibilidad cuando cambian claves/formatos.

---

## 💎 Planes y Licencias

| Plan | Incluye | Ideal para |
| :--- | :--- | :--- |
| **Básico** | Moderación, Música, Minijuegos, Guardian | Servidores pequeños |
| **Pro** | Todo Básico + Niveles, Economía, Oráculo, Confesiones | Comunidades activas |
| **Élite** | Todo Pro + Mascotas v4.2, Dashboard Web, IA Atenea | Gaming / eSports |
| **Custom** | Todo Élite + marca blanca + funciones a medida | Proyectos a medida |

### Reglas reales (qué se bloquea por plan)

Por defecto, todo módulo no listado es `basic`. Los módulos que requieren `pro` (mínimo) son:

| Módulo (Python) | Plan mínimo |
|---|---|
| `bot.cogs.comunidad.musica` | `pro` |
| `bot.cogs.comunidad.streaming` | `pro` |
| `bot.cogs.comunidad.oraculo` | `pro` |
| `bot.cogs.economia.casino` | `pro` |
| `bot.cogs.economia.sorteos` | `pro` |
| `bot.cogs.economia.ofertas` | `pro` |
| `bot.cogs.juegos.rpg` | `pro` |
| `bot.cogs.juegos.mascotas` | `pro` |
| `bot.cogs.integraciones.lol` | `pro` |

Prioridad de plan:

1. Si el servidor tiene `license_plan` en `guild_config.json`, manda para ese servidor.
2. Si no, se usa el plan global instalado en el host (según tu licencia/entorno).

---

## ⚙️ Instalación y Configuración

### Requisitos
- Python 3.11+
- FFmpeg (Instalado en el PATH)
- Un puerto abierto para el Dashboard Web (Configurable en .env)

### Variables de entorno (.env)

Estas variables se cargan desde `.env` (ver `.env.example`) y controlan qué integraciones se activan.

| Variable | Obligatoria | Para qué sirve |
|---|---:|---|
| `DISCORD_TOKEN` | Sí | Token del bot de Discord |
| `SERVER_PORT` | No | Puerto del dashboard/API (por defecto `8080`) |
| `LICENSE_KEY` | No | Clave/ID de licencia instalada en el host |
| `LICENSES_URL` | No | URL remota de licencias (si aplica en tu flujo) |
| `LICENSE_SIGNING_SECRET` | Recomendado | Firma/verificación de licencias (evita manipulación) |
| `ALLOW_PLAIN_LICENSES` | No | Permite licencias sin firma (`1`) si lo necesitas temporalmente |
| `RIOT_API_KEY` | No | Habilita el cog de LoL (si no está, se omite) |
| `GENIUS_ACCESS_TOKEN` | No | Letras de canciones (si el módulo lo usa) |
| `CANAL_OFERTAS_ID` | No | Canal para ofertas (si el módulo lo usa) |
| `ORACULO_MAX_PARTICIPANTS` | No | Límite de participantes en oráculo |
| `ENABLED_COGS_ONLY` | No | Lista blanca de cogs a cargar (override) |
| `DISABLED_COGS` | No | Lista negra de cogs a NO cargar |
| `LOG_MIN_LEVEL` | No | Nivel mínimo de log: `debug|info|warn|error` |
| `LOG_INCLUDE` | No | Filtro por tipo de log (CSV), si se usa en tu setup |
| `LOG_EXCLUDE` | No | Exclusión por tipo de log (CSV), si se usa en tu setup |
| `LOG_DEBOUNCE_SECS` | No | Anti-spam de logs (segundos, por defecto `15`) |
| `POSEIDON_SKIP_DOTENV` | No | Si es `1`, no carga `.env` (útil en algunos hostings) |

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

## 🧯 Solución de problemas (lo típico)

### El dashboard “no muestra nada”

- Verifica que el bot está levantado y el puerto responde:
  - `http://127.0.0.1:8080/api/stats`
- Si abres el dashboard desde GitHub Pages, asegúrate de que has configurado la URL correcta del bot (se guarda en `poseidon_bot_url`).
- Si estás en una red distinta (móvil/otra WiFi), la URL `127.0.0.1` no sirve: usa la IP/DOMINIO del servidor donde corre el bot.

### “Unauthorized” en endpoints `/api/*`

- Solo `/api/stats` y `/api/health` son públicos.
- El resto exige login para obtener `token` y enviarlo en `Authorization`.

### Música no suena / FFmpeg

- Asegura que `ffmpeg` está instalado y en el `PATH`.
- Usa `/diagnostico` para confirmar si FFmpeg/Opus están OK en el host.

### Un comando “no existe” o “no está disponible”

- Mira `/ayuda`: si no aparece, o el cog no está cargado, o tu plan (`license_plan`) lo bloquea.
- Si acabas de tocar cogs en caliente, puedes usar `/cog reload` y luego sincronizar (`sync:guild`).

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
