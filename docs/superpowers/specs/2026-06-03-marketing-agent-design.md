# Marketing Agent — Design Spec
**Data:** 2026-06-03  
**Estat:** Aprovat, pendent d'implementació  
**Repo d'implementació:** `112books/goatcounter-dashboard`  
**Sites objectiu (per fases):** pocallum.cat → linuxbcn.cat → llumatics.com

---

## Visió

Agent de màrqueting i vendes autònom que opera de forma **desassistida**. No és un dashboard passiu: analitza les dades, pren decisions i crea tasques accionables automàticament. L'objectiu és captar visites i convertir-les en feines reals, com si hi hagués un cap de màrqueting i vendes treballant en segon pla.

---

## Arquitectura

### Capa de dades

```
GoatCounter API ──────────→ analytics.json (cada hora, existent)
                                  │
Google Search Console API ────────┤──→ weekly-agent.py
                                  │         (cada dilluns 8h)
Historical snapshots ─────────────┘
(snapshots/YYYY-WW.json)
```

### Capa de tasques (output principal)

L'agent **crea GitHub Issues automàticament** al repo del site. Cada Issue inclou:
- Evidència (dades reals, no suposicions)
- Acció concreta i específica
- Esforç estimat (XS/S/M/L)
- Impacte esperat (alt/mig/baix)
- Label automàtic: `marketing-agent`, `seo`, `content`, `social`, `conversion`

### Capa de notificació

Telegram: resum setmanal de 5-10 punts, amb link als Issues creats.

---

## Estructura de fitxers

```
goatcounter-dashboard/
├── agents/
│   ├── intelligence.py      # Fase 1: analytics + GSC → Issues
│   ├── competitor.py        # Fase 2: fetch competitors → gap analysis
│   ├── social.py            # Fase 3: Instagram proposals
│   └── conversion.py        # Fase 4: funnel analysis
├── tasks/
│   └── github_issues.py     # Crea/actualitza Issues via GitHub API
├── scripts/                 # Existent: fetch-analytics, process-analytics
└── .github/workflows/
    ├── fetch-analytics.yml  # Existent: cada hora
    ├── weekly-agent.yml     # NOU: dilluns 8h — corre tots els agents actius
    └── hourly-alerts.yml    # NOU: pics de tràfic, anomalies
```

### Config per site (`agent-config.yaml` a cada repo)

```yaml
site: pocallum.cat
goatcounter_site: pocallum
gsc_property: https://pocallum.cat/
telegram_chat_id: xxx
github_repo: joan-linux/pocallum.cat
competitors:
  - https://www.jordiplay.com
  - https://www.marcbusquets.com
instagram_account: pocallum
instagram_handle: "@pocallum"
services:
  - books actors/actrius
  - fotografia concerts jazz
  - fotografia festivals
```

---

## Fases d'implementació

### Fase 1 — Intelligence Pipeline *(prioritat immediata)*

**Inputs:** analytics.json + Google Search Console API + snapshot anterior

**Tasques que genera automàticament:**

| Detecció | Condició | Issue generat |
|----------|----------|---------------|
| URL morta amb tràfic | path → 404, count > 0 | "Redirigir /serveis-fotografics-2/books-per-actors-i-actrices → /serveis/" |
| Keyword oportunitat | impressions > 100, CTR < 5%, posició 8-20 | "Millorar meta+títol de /festivals/calella-harmonica/ — 200 impr, 3% CTR, pos 14" |
| Blog sense link al site | post del blog sense link a pàgina relacionada | "Afegir link a /festivals/vijazz/ des de 9 posts del blog" |
| Secció en caiguda | -30% visites vs setmana anterior | "Investigar caiguda a /galeria/ (-35% vs setmana passada)" |
| Conversió baixa | wizard-sent / total_visits < 0.5% | "Revisar funnel contacte: conversion rate al 0.3%" |

**Secrets requerits al repo del site:**
- `GOATCOUNTER_TOKEN` (existent a pocallum.cat)
- `GOOGLE_SERVICE_ACCOUNT_JSON` (nou)
- `TELEGRAM_BOT_TOKEN` (nou)
- `TELEGRAM_CHAT_ID` (nou)
- `GH_TOKEN` (per crear Issues via API — necessita permís `issues: write`)

**Output:**
- `admin/insights/YYYY-WW.md` — informe complet al repo
- `admin/snapshots/YYYY-WW.json` — còpia setmanal per trending
- GitHub Issues: 3-8 issues per setmana
- Telegram: missatge resum amb links als issues

---

### Fase 2 — Content & Competitor Agent

**Inputs:** GSC data + fetch de 3-5 competitors (HTML públic)

**Tasques que genera:**
- "Competitors cobreixen Festival Primavera Sound — tu no tens pàgina"
- "Keyword 'fotografia jazz barcelona' — tu posició 18, competitor posició 4"
- "Gap: competitors tenen pàgina de servei 'fotografia corporativa' — considera si és rellevant"
- "10 paraules amb creixement de cerques aquest mes sense contingut al site"

---

### Fase 3 — Social & GEO Agent

**Inputs:** analytics.json + galeria de fotos + GSC + monitoring AI search

**Tasques que genera:**
- Instagram: detecta foto de galeria amb més visites → genera caption + hashtags → Issue "Proposta post Instagram — foto X, caption adjuntat, aprovar per publicar"
- GEO: monitora si "pocallum" apareix a ChatGPT/Perplexity/Gemini per "fotògrafs jazz barcelona" → Issue si no apareix
- Directoris: detecta llocs de referència del sector on el perfil manca

---

### Fase 4 — Conversion Agent

**Inputs:** funnel data + analytics sectorial + correlació contingut→contacte

**Tasques que genera:**
- Correlació: quins continguts acaben en contacte (wizard-sent)
- Recomanació d'optimització del wizard
- A/B test proposals per CTAs

---

## Invocació com a skill de Claude Code

El sistema és invocable manualment des de qualsevol projecte web via skill de Claude Code:

```
/marketing-agent analyze    # anàlisi a demanda del analytics.json actual
/marketing-agent issues     # llista Issues oberts generats per l'agent
/marketing-agent seo        # focus en oportunitats SEO del moment
/marketing-agent content    # recomanacions de contingut basades en dades
/marketing-agent instagram  # proposta de posts Instagram per aquesta setmana
```

La skill llegeix `static/admin/analytics.json` del projecte actual + crida l'API de GSC configurada i genera conclusions interactives en el moment.

---

## Criteris d'èxit

- **Fase 1:** Setmana 1 post-deploy → primer informe automàtic amb almenys 3 Issues accionables
- **Fase 2:** Mes 1 → gap analysis amb competitors identificat
- **Fase 3:** Mes 2 → primer post Instagram semi-automatitzat publicat
- **Fase 4:** Mes 3 → taxa de conversió del wizard incrementada i mesurada

---

## Notes d'implementació

- **Disseny sense servidor:** tot corre com GitHub Actions; zero VPS, zero costs d'infraestructura
- **Privacy-first:** GoatCounter ja és sense cookies; GSC data és privada al repo
- **Incremental:** cada fase és independent, es pot activar/desactivar per site
- **Reutilitzable:** afegir un site nou = afegir `agent-config.yaml` + 4 secrets
