// LUNES — componente de código de Framer (página geronimogentili.com/lunes)
//
// Fuente de verdad del componente "Lunes" en Framer. Para actualizar la web:
//   Framer → Assets → Code → Lunes → reemplazar todo el contenido con este archivo → Publish.
//
// Datos: lunes-newsletter.vercel.app/api/editions (lee archive/*.json del repo).
//   - Por defecto devuelve las últimas 6; con ?all=1 devuelve todas.
//   - Solo la edición más reciente lleva acento naranja; el resto barra neutra.

import * as React from "react"

const C = {
    crema: "#F7F3ED",
    naranja: "#FF4D12",
    tinta: "#211B17",
    gris: "#5C534C",
    bg: "rgba(33,27,23,0.055)",
    border: "rgba(33,27,23,0.11)",
    accentRest: "rgba(33,27,23,0.14)",
}

const MONO = "'Geist Mono', ui-monospace, 'Courier New', monospace"
const DISPLAY = "'Fractul', 'Space Grotesk', system-ui, sans-serif"

const API = "https://lunes-newsletter.vercel.app/api"
const SUBSCRIBE_URL = `${API}/subscribe`
const EDITIONS_URL = `${API}/editions`
const EDITION_URL = `${API}/edition`

const DEFAULT_VISIBLE = 6

const SECTIONS = [
    { tag: ":: TL;DR", desc: "Lo más importante de la semana" },
    { tag: ":: Lo de la semana", desc: "Un proyecto o pieza que vale la pena ver" },
    { tag: ":: Radar", desc: "Tendencias y recursos frescos" },
    { tag: ":: IA Aplicada", desc: "IA útil para diseñadores, sin hype" },
    { tag: ":: Para probar", desc: "Una cosa concreta para hacer hoy" },
]

type Edition = {
    num: string
    date: string
    slug: string
    accent?: string
    title: string
    sub: string
    tags: string[]
}

type EditionsResponse = {
    editions: Edition[]
    total?: number
    has_more?: boolean
}

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;600;700&display=swap');

/* Hero entrance animations */
@keyframes lFadeUp {
  from { opacity:0; transform:translateY(22px); }
  to   { opacity:1; transform:translateY(0); }
}
@media (prefers-reduced-motion: no-preference) {
  .la  { animation:lFadeUp 0.6s cubic-bezier(0.22,1,0.36,1) both; }
  .la1 { animation-delay:0.00s; }
  .la2 { animation-delay:0.09s; }
  .la3 { animation-delay:0.18s; }
  .la4 { animation-delay:0.27s; }
}

/* Card scroll animation via IntersectionObserver */
@keyframes lCardIn {
  from { opacity:0; transform:translateY(16px); }
  to   { opacity:1; transform:translateY(0); }
}
.lc-hidden { opacity:0 !important; transform:translateY(16px) !important; }
@media (prefers-reduced-motion: no-preference) {
  .lcard.lc-animate { animation:lCardIn 0.55s cubic-bezier(0.22,1,0.36,1) both; }
}

/* Card skeleton pulse */
@keyframes lPulse {
  0%,100% { opacity:0.5; }
  50%      { opacity:1; }
}
.lskeleton { animation:lPulse 1.4s ease-in-out infinite; }

/* Input */
.li {
  flex:1; min-width:0;
  font-family:'Geist Mono',ui-monospace,monospace;
  font-size:14px; color:#211B17;
  background:rgba(255,255,255,0.85);
  border:1px solid rgba(33,27,23,0.14);
  border-radius:12px; padding:14px 16px;
  outline:none; transition:border-color 0.2s,box-shadow 0.2s;
  -webkit-appearance:none;
}
.li::placeholder { color:rgba(92,83,76,0.4); }
.li:focus { border-color:#FF4D12; box-shadow:0 0 0 3px rgba(255,77,18,0.11); }
.li:disabled { opacity:0.5; cursor:not-allowed; }

/* Submit button */
.lb {
  font-family:'Geist Mono',ui-monospace,monospace;
  font-size:13px; font-weight:700; letter-spacing:0.01em;
  background:#FF4D12; color:#F7F3ED;
  border:none; border-radius:12px; padding:14px 24px;
  cursor:pointer; white-space:nowrap;
  transition:background 0.15s,transform 0.1s;
  -webkit-font-smoothing:antialiased;
}
.lb:hover:not(:disabled)  { background:#e03d08; }
.lb:active:not(:disabled) { transform:scale(0.96); }
.lb:disabled { background:#5C534C; cursor:not-allowed; opacity:0.6; }

/* Section tag chip */
.ltag {
  display:inline-flex;
  background:rgba(33,27,23,0.055);
  border:1px solid rgba(33,27,23,0.11);
  border-radius:6px; padding:4px 9px; cursor:default;
}

/* Edition card */
.lcard {
  background:rgba(255,255,255,0.68);
  border:1px solid rgba(33,27,23,0.09);
  border-radius:14px; overflow:hidden;
  display:flex; flex-direction:column;
  cursor:pointer;
  transition:box-shadow 0.2s,transform 0.2s,border-color 0.2s;
}
.lcard:hover { box-shadow:0 10px 28px rgba(33,27,23,0.13); transform:translateY(-3px); border-color:rgba(33,27,23,0.18); }
.lcard:focus-visible { outline:2px solid #FF4D12; outline-offset:2px; }

/* Ver edición link inside card */
.lcard-cta {
  font-family:'Geist Mono',ui-monospace,monospace;
  font-size:10px; font-weight:700; letter-spacing:0.04em;
  color:rgba(255,77,18,0.0);
  transition:color 0.2s;
}
.lcard:hover .lcard-cta { color:#FF4D12; }

/* "Ver todas las ediciones" */
.lmore {
  display:inline-flex; align-items:center; gap:8px;
  font-family:'Geist Mono',ui-monospace,monospace;
  font-size:12px; font-weight:700; letter-spacing:0.02em;
  color:#211B17;
  background:rgba(255,255,255,0.68);
  border:1px solid rgba(33,27,23,0.14);
  border-radius:12px; padding:12px 20px;
  cursor:pointer;
  transition:border-color 0.2s,box-shadow 0.2s,transform 0.2s,color 0.2s;
}
.lmore:hover:not(:disabled) { color:#FF4D12; border-color:rgba(255,77,18,0.4); box-shadow:0 8px 22px rgba(33,27,23,0.10); transform:translateY(-2px); }
.lmore:active:not(:disabled) { transform:scale(0.97); }
.lmore:disabled { opacity:0.55; cursor:wait; }
.lmore:focus-visible { outline:2px solid #FF4D12; outline-offset:2px; }

/* Section item */
.lsec {
  background:rgba(33,27,23,0.055);
  border:1px solid rgba(33,27,23,0.11);
  border-radius:10px; padding:12px 14px;
}

/* Nav back button */
.lback { background:none; border:none; padding:0; cursor:pointer; transition:color 0.15s; }
.lback:hover { color:#211B17 !important; }

/* ── Responsive ── */
@media (max-width: 640px) {
  .lnav, .lfooter { padding-left:20px !important; padding-right:20px !important; }
  .lhero           { padding-top:56px !important; padding-bottom:40px !important;
                     padding-left:20px !important; padding-right:20px !important; }
  .lsub-section    { padding-left:20px !important; padding-right:20px !important; }
  .lform-row       { flex-direction:column !important; }
  .lcards          { grid-template-columns:1fr !important; }
  .lsections       { grid-template-columns:1fr 1fr !important; }
}
`

const isValidEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)

export default function Lunes() {
    const [email, setEmail] = React.useState("")
    const [status, setStatus] = React.useState<"idle" | "loading" | "success" | "error">("idle")
    const [error, setError] = React.useState("")

    const [editions, setEditions] = React.useState<Edition[]>([])
    const [total, setTotal] = React.useState(0)
    const [loading, setLoading] = React.useState(true)

    // "Ver todas": se piden una sola vez y se cachean en allEditions
    const [showAll, setShowAll] = React.useState(false)
    const [allEditions, setAllEditions] = React.useState<Edition[] | null>(null)
    const [loadingAll, setLoadingAll] = React.useState(false)

    const cardRefs = React.useRef<(HTMLDivElement | null)[]>([])

    React.useEffect(() => {
        fetch(EDITIONS_URL)
            .then((r) => r.json())
            .then((d: EditionsResponse) => {
                if (Array.isArray(d.editions)) {
                    setEditions(d.editions)
                    setTotal(typeof d.total === "number" ? d.total : d.editions.length)
                }
            })
            .catch(() => {})
            .finally(() => setLoading(false))
    }, [])

    const visible = showAll && allEditions ? allEditions : editions
    const hasMore = !showAll && total > visible.length

    async function toggleAll() {
        if (showAll) {
            setShowAll(false)
            return
        }
        if (allEditions) {
            setShowAll(true)
            return
        }
        setLoadingAll(true)
        try {
            const d: EditionsResponse = await (await fetch(`${EDITIONS_URL}?all=1`)).json()
            if (Array.isArray(d.editions) && d.editions.length > 0) {
                setAllEditions(d.editions)
                setTotal(typeof d.total === "number" ? d.total : d.editions.length)
                setShowAll(true)
            }
        } catch {
            // dejamos las 6 visibles; el botón queda disponible para reintentar
        } finally {
            setLoadingAll(false)
        }
    }

    // Scroll-in de las cards. Solo anima las que todavía no se animaron,
    // así al expandir "Ver todas" las primeras 6 no parpadean.
    React.useLayoutEffect(() => {
        if (typeof window === "undefined") return
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

        const pending = cardRefs.current.filter(
            (el): el is HTMLDivElement => !!el && !el.classList.contains("lc-animate")
        )
        if (pending.length === 0) return

        pending.forEach((el) => el.classList.add("lc-hidden"))
        const io = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) return
                    const el = entry.target as HTMLDivElement
                    el.style.animationDelay = el.dataset.animDelay ?? "0s"
                    el.classList.remove("lc-hidden")
                    el.classList.add("lc-animate")
                    io.unobserve(el)
                })
            },
            { threshold: 0.12 }
        )
        pending.forEach((el) => io.observe(el))
        return () => io.disconnect()
    }, [visible])

    async function handleSubmit(ev: React.FormEvent) {
        ev.preventDefault()
        if (!isValidEmail(email)) {
            setError("Ingresá un email válido.")
            return
        }
        setStatus("loading")
        setError("")
        try {
            const r = await (
                await fetch(SUBSCRIBE_URL, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email }),
                })
            ).json()
            if (r.ok) {
                setStatus("success")
            } else {
                setStatus("error")
                setError(r.error ?? "Algo salió mal. Intentá de nuevo.")
            }
        } catch {
            setStatus("error")
            setError("Error de red. Intentá de nuevo.")
        }
    }

    const openEdition = (slug: string) => window.open(`${EDITION_URL}?slug=${slug}`, "_blank")

    return (
        <>
            <style>{CSS}</style>
            <div
                style={{
                    width: "100%",
                    minHeight: "100vh",
                    background: C.crema,
                    display: "flex",
                    flexDirection: "column",
                    boxSizing: "border-box",
                }}
            >
                {/* ── Nav ── */}
                <nav
                    className="lnav"
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "18px 40px",
                        borderBottom: `1px solid ${C.border}`,
                        position: "sticky",
                        top: 0,
                        zIndex: 50,
                        background: C.crema,
                    }}
                >
                    <button
                        className="lback"
                        onClick={() => window.open("https://geronimogentili.com", "_self")}
                        style={{
                            fontFamily: MONO,
                            fontSize: 12,
                            fontWeight: 600,
                            color: C.gris,
                            letterSpacing: "0.02em",
                        }}
                    >
                        ← geronimogentili.com
                    </button>
                    <span
                        style={{
                            fontFamily: DISPLAY,
                            fontSize: 19,
                            fontWeight: 800,
                            color: C.tinta,
                            letterSpacing: "-0.04em",
                        }}
                    >
                        LUNES
                    </span>
                </nav>

                {/* ── Hero ── */}
                <section
                    className="lhero"
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        padding: "80px 40px 64px",
                        maxWidth: 620,
                        margin: "0 auto",
                        width: "100%",
                        boxSizing: "border-box",
                    }}
                >
                    <div
                        className="la la1"
                        style={{
                            display: "inline-flex",
                            alignItems: "center",
                            background: C.bg,
                            border: `1px solid ${C.border}`,
                            borderRadius: 8,
                            padding: "6px 14px",
                            marginBottom: 32,
                        }}
                    >
                        <span
                            style={{
                                fontFamily: MONO,
                                fontSize: 11,
                                fontWeight: 700,
                                color: C.gris,
                                letterSpacing: "0.08em",
                                textTransform: "uppercase",
                            }}
                        >
                            :: newsletter de diseño
                        </span>
                    </div>

                    <h1
                        className="la la2"
                        style={{
                            fontFamily: DISPLAY,
                            fontSize: "clamp(48px,10vw,78px)",
                            fontWeight: 800,
                            color: C.tinta,
                            letterSpacing: "-0.05em",
                            lineHeight: 0.93,
                            textAlign: "center",
                            margin: "0 0 22px 0",
                        }}
                    >
                        Diseño.
                        <br />
                        IA.
                        <br />
                        Cada lunes.
                    </h1>

                    <p
                        className="la la3"
                        style={{
                            fontFamily: MONO,
                            fontSize: 14,
                            color: C.gris,
                            lineHeight: 1.75,
                            letterSpacing: "-0.01em",
                            textAlign: "center",
                            margin: "0 0 44px 0",
                            maxWidth: "40ch",
                        }}
                    >
                        Una newsletter curada de diseño, tipografía y cultura visual. Sin
                        algoritmos. Sin ruido.
                    </p>

                    <div className="la la4" style={{ width: "100%", maxWidth: 480 }}>
                        {status === "success" ? (
                            <div
                                style={{
                                    background: "rgba(255,77,18,0.07)",
                                    border: "1px solid rgba(255,77,18,0.26)",
                                    borderRadius: 14,
                                    padding: "24px 28px",
                                    textAlign: "center",
                                }}
                            >
                                <p
                                    style={{
                                        fontFamily: MONO,
                                        fontSize: 14,
                                        fontWeight: 700,
                                        color: C.naranja,
                                        margin: 0,
                                        lineHeight: 1.5,
                                    }}
                                >
                                    Revisá tu mail y confirmá la suscripción.
                                </p>
                                <p
                                    style={{
                                        fontFamily: MONO,
                                        fontSize: 12,
                                        color: C.gris,
                                        margin: "10px 0 0",
                                        lineHeight: 1.65,
                                    }}
                                >
                                    Te enviamos un link de confirmación. Si no llega, revisá spam.
                                </p>
                            </div>
                        ) : (
                            <form
                                onSubmit={handleSubmit}
                                style={{ display: "flex", flexDirection: "column", gap: 6 }}
                            >
                                <label
                                    htmlFor="lunes-email"
                                    style={{
                                        fontFamily: MONO,
                                        fontSize: 11,
                                        fontWeight: 700,
                                        color: C.gris,
                                        letterSpacing: "0.06em",
                                        textTransform: "uppercase",
                                        marginBottom: 2,
                                    }}
                                >
                                    Tu email
                                </label>
                                <div className="lform-row" style={{ display: "flex", gap: 8 }}>
                                    <input
                                        id="lunes-email"
                                        className="li"
                                        type="email"
                                        placeholder="tu@email.com"
                                        value={email}
                                        onChange={(e) => {
                                            setEmail(e.target.value)
                                            setError("")
                                        }}
                                        disabled={status === "loading"}
                                        aria-describedby="lunes-hint"
                                        autoComplete="email"
                                    />
                                    <button className="lb" type="submit" disabled={status === "loading"}>
                                        {status === "loading" ? "Enviando…" : "Suscribirme →"}
                                    </button>
                                </div>
                                {error ? (
                                    <p
                                        id="lunes-hint"
                                        role="alert"
                                        style={{
                                            fontFamily: MONO,
                                            fontSize: 12,
                                            color: C.naranja,
                                            margin: "2px 0 0",
                                            letterSpacing: "-0.01em",
                                        }}
                                    >
                                        {error}
                                    </p>
                                ) : (
                                    <p
                                        id="lunes-hint"
                                        style={{
                                            fontFamily: MONO,
                                            fontSize: 11,
                                            color: "rgba(92,83,76,0.48)",
                                            margin: "4px 0 0",
                                            letterSpacing: "0.01em",
                                        }}
                                    >
                                        Confirmás por mail · Sin spam · Baja en un click
                                    </p>
                                )}
                            </form>
                        )}
                    </div>
                </section>

                {/* ── Qué trae cada edición ── */}
                <section
                    className="lsub-section"
                    style={{
                        maxWidth: 620,
                        margin: "0 auto",
                        width: "100%",
                        padding: "0 40px 56px",
                        boxSizing: "border-box",
                    }}
                >
                    <p
                        style={{
                            fontFamily: MONO,
                            fontSize: 11,
                            fontWeight: 700,
                            color: "rgba(92,83,76,0.45)",
                            letterSpacing: "0.12em",
                            textTransform: "uppercase",
                            margin: "0 0 14px",
                        }}
                    >
                        Qué trae cada edición
                    </p>
                    <div
                        className="lsections"
                        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}
                    >
                        {SECTIONS.map(({ tag, desc }) => (
                            <div className="lsec" key={tag}>
                                <span
                                    style={{
                                        fontFamily: MONO,
                                        fontSize: 12,
                                        fontWeight: 700,
                                        color: C.tinta,
                                        display: "block",
                                        marginBottom: 4,
                                    }}
                                >
                                    {tag}
                                </span>
                                <span
                                    style={{
                                        fontFamily: MONO,
                                        fontSize: 11,
                                        color: C.gris,
                                        lineHeight: 1.55,
                                    }}
                                >
                                    {desc}
                                </span>
                            </div>
                        ))}
                    </div>
                </section>

                {/* ── Ediciones ── */}
                {(loading || visible.length > 0) && (
                    <section
                        className="lsub-section"
                        style={{
                            maxWidth: 620,
                            margin: "0 auto",
                            width: "100%",
                            padding: "0 40px 80px",
                            boxSizing: "border-box",
                        }}
                    >
                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 14,
                                marginBottom: 20,
                            }}
                        >
                            <div style={{ flex: 1, height: 1, background: C.border }} />
                            <span
                                style={{
                                    fontFamily: MONO,
                                    fontSize: 10,
                                    fontWeight: 700,
                                    color: "rgba(92,83,76,0.4)",
                                    letterSpacing: "0.12em",
                                    textTransform: "uppercase",
                                    whiteSpace: "nowrap",
                                }}
                            >
                                Ediciones
                            </span>
                            <div style={{ flex: 1, height: 1, background: C.border }} />
                        </div>

                        <div
                            className="lcards"
                            style={{
                                display: "grid",
                                gridTemplateColumns: "repeat(3, 1fr)",
                                gap: 10,
                            }}
                        >
                            {loading
                                ? [0, 1, 2].map((i) => (
                                      <div
                                          key={i}
                                          className="lcard lskeleton"
                                          style={{ minHeight: 160, background: C.bg }}
                                      />
                                  ))
                                : visible.map((ed, i) => {
                                      // Solo la más reciente en naranja, pase lo que pase con la API
                                      const accent = i === 0 ? C.naranja : C.accentRest
                                      return (
                                          <div
                                              key={ed.num}
                                              ref={(el) => {
                                                  cardRefs.current[i] = el
                                              }}
                                              data-anim-delay={`${(i % DEFAULT_VISIBLE) * 0.07}s`}
                                              className="lcard"
                                              role="link"
                                              tabIndex={0}
                                              onClick={() => openEdition(ed.slug)}
                                              onKeyDown={(e) => {
                                                  if (e.key === "Enter" || e.key === " ")
                                                      openEdition(ed.slug)
                                              }}
                                          >
                                              <div style={{ height: 3, background: accent, flexShrink: 0 }} />
                                              <div
                                                  style={{
                                                      padding: "14px 14px 16px",
                                                      display: "flex",
                                                      flexDirection: "column",
                                                      gap: 10,
                                                      flex: 1,
                                                  }}
                                              >
                                                  <div
                                                      style={{
                                                          display: "flex",
                                                          justifyContent: "space-between",
                                                          alignItems: "center",
                                                      }}
                                                  >
                                                      <span
                                                          style={{
                                                              fontFamily: MONO,
                                                              fontSize: 10,
                                                              fontWeight: 700,
                                                              color: i === 0 ? C.naranja : C.gris,
                                                              letterSpacing: "0.05em",
                                                              textTransform: "uppercase",
                                                          }}
                                                      >
                                                          LUNES {ed.num}
                                                      </span>
                                                      <span
                                                          style={{
                                                              fontFamily: MONO,
                                                              fontSize: 10,
                                                              color: "rgba(92,83,76,0.45)",
                                                          }}
                                                      >
                                                          {ed.date}
                                                      </span>
                                                  </div>
                                                  <div style={{ height: 1, background: C.border }} />
                                                  <div>
                                                      <p
                                                          style={{
                                                              fontFamily: DISPLAY,
                                                              fontSize: 13,
                                                              fontWeight: 800,
                                                              color: C.tinta,
                                                              letterSpacing: "-0.03em",
                                                              lineHeight: 1.2,
                                                              margin: "0 0 6px",
                                                          }}
                                                      >
                                                          {ed.title}
                                                      </p>
                                                      <p
                                                          style={{
                                                              fontFamily: MONO,
                                                              fontSize: 11,
                                                              color: C.gris,
                                                              lineHeight: 1.55,
                                                              margin: 0,
                                                          }}
                                                      >
                                                          {ed.sub}
                                                      </p>
                                                  </div>
                                                  <div
                                                      style={{
                                                          display: "flex",
                                                          justifyContent: "space-between",
                                                          alignItems: "flex-end",
                                                          marginTop: "auto",
                                                      }}
                                                  >
                                                      {ed.tags.length > 0 && (
                                                          <div
                                                              style={{
                                                                  display: "flex",
                                                                  flexWrap: "wrap",
                                                                  gap: 4,
                                                              }}
                                                          >
                                                              {ed.tags.map((t) => (
                                                                  <span className="ltag" key={t}>
                                                                      <span
                                                                          style={{
                                                                              fontFamily: MONO,
                                                                              fontSize: 10,
                                                                              fontWeight: 600,
                                                                              color: C.tinta,
                                                                          }}
                                                                      >
                                                                          {t}
                                                                      </span>
                                                                  </span>
                                                              ))}
                                                          </div>
                                                      )}
                                                      <span
                                                          className="lcard-cta"
                                                          style={{
                                                              marginLeft: "auto",
                                                              paddingLeft: 6,
                                                              flexShrink: 0,
                                                          }}
                                                      >
                                                          Ver →
                                                      </span>
                                                  </div>
                                              </div>
                                          </div>
                                      )
                                  })}
                        </div>

                        {/* Ver todas / Ver menos */}
                        {!loading && (hasMore || showAll) && (
                            <div
                                style={{
                                    display: "flex",
                                    justifyContent: "center",
                                    marginTop: 24,
                                }}
                            >
                                <button
                                    className="lmore"
                                    type="button"
                                    onClick={toggleAll}
                                    disabled={loadingAll}
                                    aria-expanded={showAll}
                                >
                                    {loadingAll
                                        ? "Cargando…"
                                        : showAll
                                          ? "Ver menos ↑"
                                          : `Ver todas las ediciones (${total}) →`}
                                </button>
                            </div>
                        )}
                    </section>
                )}

                {/* ── Footer ── */}
                <footer
                    className="lfooter"
                    style={{
                        borderTop: `1px solid ${C.border}`,
                        padding: "18px 40px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginTop: "auto",
                    }}
                >
                    <span
                        style={{
                            fontFamily: MONO,
                            fontSize: 11,
                            color: "rgba(92,83,76,0.45)",
                            letterSpacing: "0.03em",
                        }}
                    >
                        Hecho por Gerónimo Gentili · Buenos Aires
                    </span>
                    <span
                        style={{
                            fontFamily: MONO,
                            fontSize: 11,
                            fontWeight: 700,
                            color: "rgba(92,83,76,0.32)",
                            letterSpacing: "0.14em",
                            textTransform: "uppercase",
                        }}
                    >
                        LUNES
                    </span>
                </footer>
            </div>
        </>
    )
}
