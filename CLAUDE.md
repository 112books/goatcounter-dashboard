# CLAUDE.md — GoatCounter Dashboard

Guia operativa per a Claude Code en aquest projecte.

## El projecte

**Dashboard d'estadístiques elegant per a webs estàtics.** Integra dades de GoatCounter sense base de dades, servidor PHP ni cookies. Dissenyat per a webs estàtics (Hugo, Jekyll, Eleventy) allotjats a GitHub Pages, Netlify o Vercel.

- **Repositori:** GitHub (privat)
- **Instàncies actives:** pocallum.cat/admin · llumatics.com/admin

---

## Stack tècnic

| Capa | Tecnologia |
|------|-----------|
| Frontend | HTML5 + Vanilla JS + Chart.js |
| Scripts | Python 3.11 + Bash |
| APIs | GoatCounter v0, Google Search Console, GitHub API |
| CI/CD | GitHub Actions (fetch cada hora + agent setmanal dilluns 07:00 UTC) |
| Autenticació | SHA-256 client-side (sense servidor) |

**Dependències Python:** `requests`, `google-api-python-client`, `google-auth`, `PyYAML`

---

## Estructura principal

```
goatcounter-dashboard/
├── admin/
│   ├── index.html              # Dashboard interactiu (Login + Charts)
│   ├── analytics.json          # Dades generades automàticament
│   └── snapshots/{site}/       # Snapshots setmanals (JSON)
├── scripts/
│   ├── fetch_goatcounter_analytics.py
│   ├── process-analytics.py
│   └── run-weekly-agent.py     # Orquestrador agent setmanal
├── agents/intelligence.py      # Detectors: dead URLs, seasonality, spikes
├── config/                     # YAML per site (pocallum.cat, llumatics.com)
└── .github/workflows/          # fetch-analytics.yml + weekly-agent.yml
```

---

## Comandos habituals

```bash
# Setup inicial
bash scripts/setup.sh

# Fetch manual (debugging)
python3 scripts/fetch_goatcounter_analytics.py
python3 scripts/process-analytics.py /tmp/raw.json admin/analytics.json START END

# Agent setmanal (local)
export AGENT_CONFIG=config/pocallum.cat.yaml
export GOATCOUNTER_TOKEN=...
python3 scripts/run-weekly-agent.py

# Canviar contrasenya dashboard
echo -n "nova_contrasenya" | sha256sum   # copiar hash → PW_HASH a admin/index.html
```

---

## Secrets GitHub requerits

| Secret | Ús |
|--------|----|
| `GOATCOUNTER_TOKEN` | pocallum.cat |
| `GOATCOUNTER_TOKEN_LLUMATICS` | llumatics.com |
| `GSC_CLIENT_ID`, `GSC_CLIENT_SECRET`, `GSC_REFRESH_TOKEN` | Google Search Console |
| `GH_AGENT_TOKEN` | Crear issues automàtics |

---

## Regles operatives

- **Deploy:** completament automàtic via GitHub Actions (no manual)
- **Analytics JSON:** sempre versionat al repo (accessible via RAW GitHub URL per als webs clients)
- **GoatCounter API:** rate limit — no fer crides paral·leles (usar seqüencial)
- **Commits automàtics:** format `chore: update analytics [skip ci]`
- **Error handling:** fallback graciós si falla GoatCounter (arrays buits, no crash)

---

## Convencions

**Commits:** `chore:` (updates automàtics), `feat:` (funcionalitats), `fix:` (correccions)

**Branca única:** `main`

**Format dates:** ISO 8601 (`YYYY-MM-DD`)

---

## Control horari

Skill actiu: `gestor-hores` — registra automàticament el temps de treball per sessió.

- Logs a `.taques/goatcounter-dashboard/YYYY-MM-DD.md` (creat automàticament)
- Comandes: `/time-log [tasca] [hores]`, `/time-report [periode]`, `/time-config [hores] [tarifa]`
- No modificar manualment els fitxers `.taques/` — són append-only
