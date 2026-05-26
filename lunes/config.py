import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY")
RESEND_API_KEY     = os.getenv("RESEND_API_KEY")
RESEND_AUDIENCE_ID = os.getenv("RESEND_AUDIENCE_ID")
FROM_EMAIL         = os.getenv("FROM_EMAIL")
TEST_EMAIL         = os.getenv("TEST_EMAIL")
HMAC_SECRET        = os.getenv("HMAC_SECRET")

# TODO verificar el model ID vigente en docs.anthropic.com/api antes de cada uso
ANTHROPIC_MODEL = "claude-sonnet-4-6"

WINDOW_DAYS = 7   # artículos de los últimos N días

# ---------------------------------------------------------------------------
# Fuentes con RSS verificado (URLs testeadas 2026-05-26)
# ---------------------------------------------------------------------------
FEEDS = {
    "diseño": [
        {
            "name": "It's Nice That",
            "url":  "https://www.itsnicethat.com/articles.rss",
        },
        {
            "name": "AIGA Eye on Design",
            "url":  "https://eyeondesign.aiga.org/feed/",
        },
        {
            # Feed del sitio raíz; filtrar por URL prefix para solo Brand New
            "name": "Brand New",
            "url":  "https://www.underconsideration.com/feed/",
            "filter_url_prefix": "https://www.underconsideration.com/brandnew/",
        },
        {
            # Sirve RSS con Content-Type: text/html — feedparser lo maneja igual
            "name": "Typewolf",
            "url":  "https://www.typewolf.com/feed",
        },
        {
            "name": "Creative Review",
            "url":  "https://www.creativereview.co.uk/feed/",
        },
        {
            # /feed devuelve 404; /rss.xml es el path correcto
            "name": "Abduzeedo",
            "url":  "https://abduzeedo.com/rss.xml",
        },
        {
            # /feed/ devuelve 404; /rss es el path correcto
            "name": "Mindsparkle Mag",
            "url":  "https://mindsparklemag.com/rss",
        },
        {
            "name": "The Dieline",
            "url":  "https://thedieline.com/feed/",
        },
        {
            "name": "Dezeen",
            "url":  "https://www.dezeen.com/feed/",
        },
        {
            # Antes bloqueaba (403); verificado 200 + RSS válido en 2026-05-26
            "name": "Design Week",
            "url":  "https://www.designweek.co.uk/feed/",
        },
    ],
    "ia": [
        {
            "name": "TLDR AI",
            "url":  "https://tldr.tech/rss/ai",
        },
        {
            # bensbites.beehiiv.com bloquea (403); bensbites.com/feed verificado 200
            "name": "Ben's Bites",
            "url":  "https://www.bensbites.com/feed",
        },
        {
            "name": "Hugging Face Blog",
            "url":  "https://huggingface.co/blog/feed.xml",
        },
        {
            "name": "OpenAI News",
            "url":  "https://openai.com/news/rss.xml",
        },
    ],
    "awwwards": [
        {
            # "Sites of the day" — sección propia, no mezclar con diseño general
            "name": "Awwwards SOTD",
            "url":  "https://www.awwwards.com/feed/",
        },
    ],
}

# ---------------------------------------------------------------------------
# Fuentes SIN RSS accesible — alternativas pendientes
# ---------------------------------------------------------------------------
# Creative Boom (creativeboom.com)    → /feed/ devuelve 404.
# Fonts In Use (fontsinuse.com)       → /feed devuelve 500 (error de servidor).
# FOROALFA (foroalfa.org)             → /feed y /rss devuelven 404.
# Anthropic News (anthropic.com/news) → sin RSS; SPA Next.js, sin endpoint accesible.
# ---------------------------------------------------------------------------

CURATION_PROMPT = """\
ROL: Editor de LUNES, newsletter semanal para diseñadores freelance hispanohablantes.
Curador con criterio, no agregador. Cada edición vale los 3-5 min que pide. Semana
floja = poco y bueno, nunca rellenás.
LECTOR: diseñador que cobra por su trabajo (gráfico, identidad, web). Poco tiempo.
Quiere las pocas cosas que le sirven esta semana y sentirse más afilado, no saturado.
VALIOSO (en orden): 1) utilidad práctica 2) relevancia para quien VIVE del diseño
3) actualidad real 4) señal sobre ruido.
PRINCIPIOS: OPINIÓN, no neutralidad (en radar cada nota lleva tu "take" en 1 frase).
Mezclá inspiración con utilidad. "Lo de la semana" es el imán visual: la pieza más
fuerte, no la más "noticia".
SELECCIÓN: puntuá 1-5 en utilidad/relevancia/"¿se lo mandaría a un colega?". Ante la
duda, afuera. Mejor menos y bueno.
DESCARTÁ: PR sin sustancia, listicles, sponsored, refritos, hype de IA sin nada
accionable, inspiración vacía sin un porqué.
MEZCLA: no repitas tema; variá entre identidad, tipografía, herramientas, oficio,
negocio e IA aplicada.
RESÚMENES: máx 2 frases, la 1ª dice POR QUÉ importa. Concreto, voz seca. Sin signos de
admiración, sin emojis. Si no podés decir por qué importa en 1 frase, no va.
TL;DR: 4 bullets, cada uno un takeaway completo, legible en 20 segundos.
ASUNTO: específico + curiosidad, sin clickbait, sin emojis, nada de "Newsletter #12".
AWWWARDS: tomá los Site of the Day de awwwards.com/feed/ de los últimos 7 días. 1 como
"featured" (el más fuerte) con imagen; los otros 6 en "more" (nombre + link). No opines,
es vitrina. Atribuí "vía Awwwards".
INPUT: artículos de la última semana (título, fuente, fecha, resumen, url, imagen).
OUTPUT: SOLO JSON válido, sin markdown. Las rotativas sin material van en null:
{"subject":"",
 "tldr":["","","",""],
 "lead":{"title":"","kind":"sitio|identidad|proyecto","source":"","mins":N,"summary":"","url":"","image":"","credit":""},
 "radar":[{"source":"","mins":N,"title":"","take":"opinión en 1 frase","summary":"","url":"","image":"url|null","credit":""}],
 "type_pick":{"name":"","note":"","url":"","image":"url|null"},
 "ai":[{"source":"","mins":N,"title":"","summary":"","url":"","image":"url|null","credit":""}],
 "craft":{"title":"","summary":"","url":""},
 "try_this":{"title":"","summary":"","url":"","image":"url|null","credit":""},
 "opportunity":{"title":"","org":"","deadline":"","url":""},
 "spotted":[{"title":"","url":""}],
 "awwwards":{"featured":{"name":"","author":"","url":"","image":""},"more":[{"name":"","url":""}]}}
"""
