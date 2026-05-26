# LUNES

Newsletter semanal automatizado de diseño + IA para diseñadores freelance hispanohablantes.

## Setup

```bash
cp .env.example .env
# completar las keys en .env
# HMAC_SECRET: python3 -c "import secrets; print(secrets.token_hex(32))"

pip install -r requirements.txt
```

## Uso

```bash
# dry run: fetch + curate + render (sin enviar)
python main.py

# render + enviar preview a TEST_EMAIL
python main.py --send

# verbose logging
python main.py --debug
```

## Estructura

```
config.py          fuentes RSS, CURATION_PROMPT, configuración global
fetch.py           parsea feeds, filtra últimos 7 días, enrich images
curate.py          curación con Claude API → JSON estructurado
render.py          renderiza HTML con Jinja2
send.py            envío con Resend (test + producción)
main.py            orquestador CLI

template/
  lunes.html       template semanal (Jinja2, fonts embebidas)
  welcome.html     bienvenida al suscribirse (envío único)
  confirm.html     doble opt-in (envío único)

output/            HTMLs y JSONs generados (ignorados en git)
```

## Feeds verificados

| Sección   | Fuente           | RSS                                        |
|-----------|------------------|--------------------------------------------|
| diseño    | It's Nice That   | itsnicethat.com/articles.rss               |
| diseño    | AIGA Eye on D.   | eyeondesign.aiga.org/feed/                 |
| diseño    | Brand New        | underconsideration.com/feed/ (filtrado)    |
| diseño    | Typewolf         | typewolf.com/feed                          |
| diseño    | Creative Review  | creativereview.co.uk/feed/                 |
| diseño    | Abduzeedo        | abduzeedo.com/rss.xml                      |
| diseño    | Mindsparkle Mag  | mindsparklemag.com/rss                     |
| diseño    | The Dieline      | thedieline.com/feed/                       |
| diseño    | Dezeen           | dezeen.com/feed/                           |
| diseño    | Design Week      | designweek.co.uk/feed/                     |
| ia        | TLDR AI          | tldr.tech/rss/ai                           |
| ia        | Ben's Bites      | bensbites.com/feed                         |
| ia        | Hugging Face     | huggingface.co/blog/feed.xml               |
| ia        | OpenAI News      | openai.com/news/rss.xml                    |
| awwwards  | Awwwards SOTD    | awwwards.com/feed/                         |

Sin RSS: Creative Boom · Fonts In Use · FOROALFA · Anthropic News

## Fases

| Fase | Módulo          | Estado     |
|------|-----------------|------------|
| 1    | fetch           | completo   |
| 2    | curate          | actualizar schema |
| 3    | render          | actualizar template |
| 4    | send            | completo   |
| 5    | web + opt-in    | pendiente  |
