# LUNES — Contexto del proyecto (leer en cada fase)

## Proyecto
Newsletter semanal "LUNES", sale los lunes, noticias curadas de diseño + IA relevante
para diseñadores freelance hispanohablantes. TL;DR arriba. Enviado por email con marca
propia. El email es liviano; la experiencia rica vive en la web (Fase 5).

## Stack
- Python 3.11+ (fetch RSS, curación, render).
- API de Claude para curar: modelo Sonnet actual — VERIFICÁ el string vigente en
  docs.anthropic.com/api antes de usarlo, no lo adivines. ANTHROPIC_API_KEY del entorno.
- Resend = lista + base de datos + envío (Audiences + Broadcasts). RESEND_API_KEY.
- GitHub Actions corre el cron semanal. Vercel hostea el alta con doble opt-in.
- Lógica en código testeable, NO en nodos de flujo.

## Marca (estricto)
Crema #F7F3ED, naranja #FF4D12, tinta #211B17, gris #5C534C, cards #FFFFFF.
Display: Fractul Bold. Body e info: Geist Mono. Esquinas muy redondeadas, pills/tags
monospace con prefijo "::" y bullets "•". Los templates base ya existen en
template/lunes.html, template/welcome.html y template/confirm.html con las fonts
embebidas. NO inventes diseño nuevo.

## Fuentes

### DISEÑO — RSS verificado (2026-05-26)
| Fuente           | URL RSS                                              | Notas                            |
|------------------|------------------------------------------------------|----------------------------------|
| It's Nice That   | itsnicethat.com/articles.rss                         |                                  |
| AIGA Eye on D.   | eyeondesign.aiga.org/feed/                           |                                  |
| Brand New        | underconsideration.com/feed/                         | filter_url_prefix /brandnew/     |
| Typewolf         | typewolf.com/feed                                    | Content-Type: text/html, ok igual|
| Creative Review  | creativereview.co.uk/feed/                           |                                  |
| Abduzeedo        | abduzeedo.com/rss.xml                                | /feed devuelve 404               |
| Mindsparkle Mag  | mindsparklemag.com/rss                               | /feed/ devuelve 404              |
| The Dieline      | thedieline.com/feed/                                 |                                  |
| Dezeen           | dezeen.com/feed/                                     |                                  |
| Design Week      | designweek.co.uk/feed/                               | antes bloqueaba, ahora 200       |

### DISEÑO — Sin RSS accesible
- Creative Boom (creativeboom.com) → /feed/ devuelve 404.
- Fonts In Use (fontsinuse.com)    → /feed devuelve 500 (error de servidor).
- FOROALFA (foroalfa.org)          → /feed y /rss devuelven 404.

### IA — RSS verificado (2026-05-26)
| Fuente           | URL RSS                                              | Notas                            |
|------------------|------------------------------------------------------|----------------------------------|
| TLDR AI          | tldr.tech/rss/ai                                     |                                  |
| Ben's Bites      | bensbites.com/feed                                   | beehiiv bloquea, sitio propio ok |
| Hugging Face     | huggingface.co/blog/feed.xml                         |                                  |
| OpenAI News      | openai.com/news/rss.xml                              |                                  |

### IA — Sin RSS accesible
- Anthropic News (anthropic.com/news) → sin RSS; SPA Next.js.

### AWWWARDS — RSS verificado (2026-05-26)
| Fuente           | URL RSS                                              | Notas                            |
|------------------|------------------------------------------------------|----------------------------------|
| Awwwards SOTD    | awwwards.com/feed/                                   | "Sites of the day"               |

## Settings
Ventana: últimos 7 días. Idioma: resúmenes y TL;DR en español; nombres propios,
herramientas y títulos en idioma original. Tono directo, seco, sin relleno, sin hype,
sin emojis. Objetivo de lectura: 3-5 min.

## Secciones
Core (siempre): TL;DR (4 bullets) · lead (Lo de la semana, 1 pieza con imagen) ·
radar (3-5 notas de diseño CON opinión) · ai (1-3, IA usable) · try_this (1 herramienta).
Rotativas (SOLO con material excelente, si no → null): type_pick · craft · opportunity ·
spotted · awwwards.
Lanzá con el core. Las rotativas se suman cuando haya material. Nunca rellenes.

## Imágenes
- Por nota: media:content/thumbnail/enclosure del RSS → og:image/twitter:image del artículo.
  Validá que cargue y tenga ancho ≥600px. Si no, image=null.
- NUNCA generés imágenes con AI para notas: la audiencia son diseñadores, se nota.
- Si image=null el render usa placeholder de marca, no rompe el layout. v1 = hotlink solamente.

## Prompt de curación (usar literal en curate.py)
```
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
```

## Fases
- Fase 1: fetch.py — parsear feeds, filtrar últimos 7 días, enrich images
- Fase 2: curate.py — llamar Claude API, parsear JSON nuevo schema
- Fase 3: render.py — Jinja2 sobre template/lunes.html, guardar output/
- Fase 4: send.py — envío con Resend (test → producción)
- Fase 5: web + suscripción — Vercel, doble opt-in, confirm.html, welcome.html
