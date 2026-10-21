# Distribució del dashboard GoatCounter a tots els projectes

> **Estat:** pendent d'executar · **Data:** 2026-10-21 · **Àmbit:** 16 projectes consumidors
>
> Aquest document recull la investigació feta i el pla per portar el **filtre de període** (dia / setmana / mes / trimestre / any / tot) i els **gràfics circulars** (dispositius, navegadors, sistemes operatius) a tots els webs que fan servir aquest dashboard, i per deixar de mantenir 16 còpies del mateix codi.

---

## 0. Què ja està fet al repo plantilla

Commit `978b254` a `112books/goatcounter-dashboard`:

- `scripts/process-analytics.py` i `scripts/fetch_goatcounter_analytics.py` generen `pages_daily` i `sections_daily` (mapes `pàgina/secció → {data: visites}`).
- `admin/index.html`: selector `dia / setm. / mes / trim. / any / tot` a la pestanya Pàgines, que filtra seccions, pàgines i l'insight. Si el JSON no té els camps diaris, els botons es desactiven i es mostra un avís (fallback segur).
- `admin/index.html`: formatges per dispositius, navegadors i sistemes operatius (top 5 + «Altres», llegenda amb compte i percentatge).
- Tests: `tests/scripts/test_process_analytics.py` i `test_fetch_analytics.py` (27 tests passen).
- README actualitzat amb els camps nous.

**Important:** cap dels 16 projectes consumidors té encara aquests canvis. Els seus `analytics.json` en línia no tenen `pages_daily` (verificat el 2026-10-21).

---

## 1. Inventari de projectes (verificat 2026-10-21)

S'han identificat 16 repos de `112books` que contenen el dashboard o el mateix pipeline. `goatcounter-wp` és un plugin de WordPress a part i **no** forma part d'aquest abast.

### Grup A — plantilla estàndard o gairebé

| Projecte | Repo | Dashboard | Dades | Generació | Estat en línia | Dificultat |
|---|---|---|---|---|---|---|
| ressona.eu | `112books/ressona.eu` | `/admin/` | `static/admin/analytics.json` | Python + GHA | 200 · dades fresques | Baixa-mitjana |
| terraifoc.cat | `112books/terraifoc.cat` | `/admin/` | `static/admin/analytics.json` | Python + GHA | 200 · dades velles (deploy) | Baixa |
| awpcp.org | `112books/awpcp.org` | `/admin/` | `static/admin/analytics.json` | Python + GHA | 200 · dades velles (deploy) | Baixa |
| 112revelats | `112books/112revelats` | `https://112revelats.112books.eu/admin/` | `static/admin/analytics.json` | Python + GHA | 200 · dades velles (deploy) | Baixa |
| cuinetes | `112books/cuinetes` | `https://cuinetes.linuxbcn.com/admin/` | `static/admin/analytics.json` | Python + GHA | 200 · dades velles · **sense bloc de seccions** | Baixa |
| about-pocallum | `112books/about-pocallum` | `https://about.pocallum.cat/admin/` | `admin/analytics.json` | Python + GHA | 200 · fresc · **lloc estàtic, no Hugo** | Baixa |
| blog.pocallum.cat | `112books/blog.pocallum.cat` | `https://blog.pocallum.cat/stats/` | `static/stats/analytics.json` | Python + GHA | 200 · fresc | Mitjana |
| guiesbarcelona | `112books/guiesbarcelona-elglobusvermell` | `static/admin/stats/` (URL per confirmar) | `static/admin/stats/analytics.json` | `build-stats.py` + GHA | no verificat (404 a la URL provada) | Mitjana |
| 9bi | `112books/9bi` | `static/stats/` (URL per confirmar) | `static/stats/analytics.json` | `fetch_9bi_analytics.py` · **sense workflow** | no verificat | Mitjana |

### Grup B — personalitzats (cal merge a mida)

| Projecte | Repo | Dashboard | Dades | Generació | Notes |
|---|---|---|---|---|---|
| pocallum.cat | `112books/pocallum.cat` | `/stats/` | `static/stats/analytics.json` | Python + GHA | Moltes seccions pròpies (blog, festivals, serveis, conversió, wizard, missatges) |
| llumatics.com | `112books/llumatics-web` | `/admin/` | `static/admin/analytics-cache.json` | **PHP** `fetch-analytics.php` | Tallers, campanyes, tendències, dies de la setmana |
| linuxbcn.com | `112books/linuxbcn` | `/admin/` (401) | `static/admin/analytics-cache.json` | **PHP** + `admin.js` | JS externalitzat; projectes, tendències, dies |
| machiroku.com | `112books/machiroku-web` | `/admin/` | `static/admin/analytics.json` + `docs/admin/analytics.json` | Python + GHA (copia a `docs/`) | Versió antiga de la plantilla (`var`, `renderBars` diferent) |

### Grup C — dashboards Hugo propis (mateix pipeline, un altre frontend)

| Projecte | Repo | Dashboard | Dades | Notes |
|---|---|---|---|---|
| barcelonabigbluesband.com | `112books/barcelonabigbluesband.com` | `/admin/` | `static/data/analytics.json` | `layouts/admin` + `static/js/admin-dashboard.js`; ja porta `pieChart` propi; el seu `analytics.json` **no** té `hits_by_day` |
| bratiamusic.com | `112books/bratiamusic` | `/admin/` | `static/data/analytics.json` | Idem |
| ivankovacevic.com | `112books/ivankovacevic.com` | `/admin/` | `static/data/analytics.json` | Idem |

### Frescor de les dades en línia (21/10/2026)

| Web | `generated` en línia | `pages_daily` |
|---|---|---|
| pocallum.cat | 2026-10-21 | ❌ |
| blog.pocallum.cat | 2026-10-20 | ❌ |
| about.pocallum.cat | 2026-10-21 | ❌ |
| ressona.eu | 2026-10-21 | ❌ |
| llumatics.com | 2026-10-13 | ❌ |
| 112revelats | 2026-10-03 | ❌ |
| machiroku.com | 2026-09-19 | ❌ |
| terraifoc.cat | 2026-09-09 | ❌ |
| awpcp.org | 2026-09-09 | ❌ |
| cuinetes | 2026-09-09 | ❌ |

> `terraifoc`, `awpcp` i `112revelats` tenen el JSON **fresc al repo** però el web serveix dades velles: el deploy no s'executa (vegeu §2.1).
>
> No verificat: `guiesbarcelona`, `9bi` i els 3 del Grup C (aquests fan servir un altre esquema de dades i el seu JSON no té `hits_by_day`).

---

## 2. Problemes coneguts que cal resoldre durant el desplegament

### 2.1 Deploy encallat per `[skip ci]`

El workflow de fetch fa commit amb `chore: update analytics [skip ci]`. GitHub interpreta `[skip ci]` i **salta tots els workflows d'aquell push**, inclòs el de deploy (`on: push: branches: [main]`). Resultat: el JSON del repo s'actualitza, però el web no es reconstrueix.

Afectats (repo fresc, web vell): `terraifoc.cat`, `awpcp.org`, `112revelats`. A `terraifoc` s'ha confirmat que el commit porta `[skip ci]`; cal revisar els altres dos.

Opcions de correcció:

1. **Recomanada:** generar l'analytics **durant el build** (l'acció de fetch s'executa abans de `hugo`) i no committejar-lo. Elimina el problema i els commits horaris.
2. Treure `[skip ci]` del commit i afegir un filtre de paths al deploy perquè només es desplegui quan calgui.
3. Mantenir el commit i disparar el deploy amb `workflow_run` o `gh workflow run deploy.yml` després del fetch.

### 2.2 Backends duplicats

- Python: còpies de `process-analytics.py` / `fetch_goatcounter_analytics.py` amb divergències.
- PHP: `llumatics-web` i `linuxbcn` generen el JSON amb `fetch-analytics.php`. Cal afegir-hi `pages_daily` i `sections_daily` en paral·lel.
- Scripts propis: `guiesbarcelona/scripts/build-stats.py`, `9bi/scripts/fetch_9bi_analytics.py`.

### 2.3 Variants del frontend

- `machiroku-web` és una versió antiga (no comparteix els anchors actuals).
- `linuxbcn` té la lògica a `static/admin/admin.js`.
- `llumatics-web` té funcions pròpies (tallers, campanyes, tendències).
- `pocallum.cat` té moltes seccions pròpies.
- `about-pocallum` no és Hugo.
- Els 3 del Grup C ja tenen layout Hugo propi.

### 2.4 Seguretat

- El login és **client-side** (SHA-256); el hash és públic i les dades `analytics.json` també. No és autenticació real. `linuxbcn` ja està protegit amb 401.
- El remote local d'aquest repo té un PAT incrustat a la URL. Convé rotar-lo i fer servir SSH o un credential helper.

---

## 3. Arquitectura objectiu: mòdul de Hugo + acció de fetch

Hugo **no té plugins**; l'equivalent són els **mòduls** (Go modules) o *theme components*. Combinats amb una **acció composta** de GitHub per a les dades, donen un sol origen de codi i actualitzacions versionades.

### 3.1 Estructura del mòdul

```
goatcounter-dashboard/
├── go.mod                                  # module github.com/112books/goatcounter-dashboard
├── assets/
│   └── goatcounter-dashboard/
│       ├── app.js                          # JS del dashboard (extret de index.html)
│       └── app.css                         # CSS del dashboard
├── layouts/
│   └── _default/
│       └── goatcounter-dashboard.html      # pàgina standalone completa
├── .github/
│   └── actions/fetch/action.yml            # fetch + process + escriptura del JSON
├── scripts/                                # pipeline Python
└── tests/
```

### 3.2 Integració a cada web

`hugo.toml`:

```toml
[[module.imports]]
path = "github.com/112books/goatcounter-dashboard"

[params.goatcounter]
siteName     = "ressona.eu"
account      = "ressona"
passwordHash = "<sha256>"
dataUrl      = "/admin/analytics.json"
sectionNames = { inici = "Inici", tallers = "Tallers" }
```

Un fitxer de contingut mínim (la ruta decideix la URL del dashboard):

```md
<!-- content/admin/_index.md -->
---
title: Stats
layout: goatcounter-dashboard
---
```

Si el web ja té Sveltia CMS a `/admin/`, es fa servir `content/stats/_index.md` i `url = /stats/` (com `pocallum` i `blog.pocallum`).

### 3.3 Dades: acció composta (recomanada)

Al workflow de deploy, **abans de `hugo`**:

```yaml
- uses: 112books/goatcounter-dashboard/.github/actions/fetch@v1
  with:
    site: ressona
    output: static/admin/analytics.json
    days: 365
  env:
    GC_TOKEN: ${{ secrets.GOATCOUNTER_TOKEN }}
```

- Genera el JSON amb el codi versionat del mòdul (no cal copiar `scripts/`).
- El deploy s'executa amb dades fresques; no cal commit ni `[skip ci]`.
- Per als webs amb GitHub Pages des de branca (sense workflow de build), es pot mantenir el commit, però **sense** `[skip ci]`.

Alternativa equivalent: `workflow_call` reutilitzable (`uses: .../.github/workflows/fetch.yml@v1`) amb `secrets: inherit`.

### 3.4 Versionat i actualització

- Tags semver al repo plantilla (`v1.0.0`, `v1.1.0`…). Els webs fixen `@v1` o una versió exacta.
- Actualització: `hugo mod get -u github.com/112books/goatcounter-dashboard` + canviar `@v1` si cal.
- Renovate/Dependabot pot obrir PRs automàtics per `go.mod` i per les referències `@v1`.
- Requisit: `actions/setup-go` al CI dels webs que facin servir el mòdul.

### 3.5 Límit: personalitzacions

El mòdul genèric cobreix els Grups A. Per als Grups B i C cal una de dues:

1. **Hooks d'extensió** al mòdul (partial opcional + esdeveniment `gc:data` perquè cada web afegeixi els seus widgets). És la solució neta a mitjà termini.
2. Mantenir aquells webs a mida i actualitzar-los amb el pedaç actual (més ràpid, més duplicació).

No migrar al mòdul sense decidir això: `pocallum`, `llumatics`, `linuxbcn` i `machiroku` perdrien funcionalitats.

---

## 4. Pla d'execució

> Ordre pensat per validar primer amb poc risc i deixar els casos difícils per al final.

### Fase 0 — Canari: `ressona.eu`

Per què: és la combinació de plantilla propera (similitud HTML 0,631; proc 0,893), deploy sa (dades fresques) i tràfic baix (1.513 visites/any).

- [ ] Crear branca `feat/filtre-periode-i-formatges`.
- [ ] Aplicar el pedaç de `admin/index.html` (selector, filtres, formatges) conservant el bloc `CFG` del web.
- [ ] Aplicar el pedaç de `scripts/process-analytics.py` (`pages_daily`, `sections_daily`).
- [ ] Proves locals: `node --check`, `pytest`, render amb dades sintètiques.
- [ ] Obrir PR i revisar el diff (sobretot el `CFG`).
- [ ] Merge + verificar deploy.
- [ ] Executar el workflow de fetch (o esperar) i comprovar `pages_daily` al JSON.
- [ ] Provar a producció: filtres, formatges, consola neta, mòbil.
- [ ] Anotar resultats i temps al final d'aquest document.

### Fase 1 — Extreure el mòdul v1

- [ ] Crear `go.mod` i l'estructura de §3.1 a partir del codi validat al canari.
- [ ] Extreure JS i CSS de `admin/index.html` a `assets/` (sense canviar comportament).
- [ ] Crear `layouts/_default/goatcounter-dashboard.html` amb paràmetres de `params.goatcounter`.
- [ ] Crear `.github/actions/fetch/action.yml` (o `workflow_call`).
- [ ] Afegir tests del mòdul i un lloc de demostració.
- [ ] Tag `v1.0.0` i notes de release.

### Fase 2 — Migrar els estàndard (un a un)

Ordre suggerit (de més fàcil a més complex):

1. `terraifoc.cat` — **primer corregir el deploy** (§2.1) o usar-lo per validar la generació al build.
2. `guiesbarcelona` — confirmar URL i workflow.
3. `9bi` — confirmar URL; decidir si es crea workflow o es manté manual.
4. `awpcp.org`
5. `112revelats`
6. `cuinetes` — afegir el bloc de seccions (ara no en té).
7. `about-pocallum` — no Hugo: muntar el widget JS o mantenir còpia estàtica.
8. `blog.pocallum.cat`
9. `ressona.eu` — migrar el canari al mòdul (o deixar-lo com a referència).

Per a cada web, vegeu el checklist de §5.

### Fase 3 — Personalitzats

- [ ] `pocallum.cat` — decidir hooks vs. pedaç a mida; conservar totes les seccions pròpies.
- [ ] `llumatics.com` — afegir `pages_daily`/`sections_daily` a `fetch-analytics.php` i el selector/formatges a l'HTML.
- [ ] `linuxbcn.com` — ídem a `fetch-analytics.php` + `admin.js`; recordar l'accés 401.
- [ ] `machiroku.com` — versió antiga; pedaç a mida o migració completa.

### Fase 4 — Dashboards Hugo propis (opcional)

- [ ] `barcelonabigbluesband.com`, `bratiamusic.com`, `ivankovacevic.com`.

Ja tenen layout Hugo i `pieChart` propi; el seu `process-analytics.py` ni tan sols genera `hits_by_day`. Cal decidir si s'unifiquen al mòdul o es mantenen.

---

## 5. Checklist de verificació per a cada web

### Abans

- [ ] Desar una còpia de l'HTML i el JSON en línia actuals (`curl`).
- [ ] Confirmar el nom del secret de GoatCounter al repo (no és uniforme: `GOATCOUNTER_TOKEN`, `GC_TOKEN`, `GC_API_KEY`…).
- [ ] Confirmar la ruta del dashboard i del `analytics.json` (taula de §1).

### Després del merge

- [ ] `curl -s -o /dev/null -w '%{http_code}' https://web/admin/` → 200.
- [ ] `curl -s https://web/admin/ | grep -c 'pg-btn'` → > 0.
- [ ] `curl -s https://web/admin/analytics.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('pages_daily' in d, 'sections_daily' in d)"` → `True True`. (La ruta pot ser `/stats/analytics.json`; vegeu la taula de §1.)
- [ ] Els botons de període estan actius (no desactivats) i el text del rang de dates és correcte.
- [ ] Els 3 canvases `pie-devices`, `pie-browsers`, `pie-systems` existeixen.
- [ ] Prova amb Chrome headless: sense errors de consola i amb dades als gràfics (`--dump-dom` + diagnòstic).
- [ ] Comprovar mòbil (amplada < 860 px): els formatges passen a una columna.
- [ ] Rollback: `git revert <sha>` al repo del web i redeploy.

> El frontend nou **tolera** un `analytics.json` antic (botons desactivats), així que es pot desplegar primer l'HTML i després el backend/dades sense deixar el web trencat.

### Ordre de desplegament segur per web

1. Frontend (filtres + formatges) → els formatges ja funcionen amb les dades agregades actuals.
2. Backend (`pages_daily`/`sections_daily`) + regenerar el JSON.
3. Verificar filtres amb dades reals.

---

## 6. Decisions obertes

- [ ] **Mòdul Hugo vs. paquet JS/CDN vs. dashboard central únic** (`stats.112books.eu` amb selector de lloc). El mòdul és el més natural per a 15 webs Hugo; el paquet JS és l'únic que encaixa amb `about-pocallum`.
- [ ] **Hooks d'extensió** per als webs personalitzats o mantenir-los a mida.
- [ ] **Generar el JSON al build** (recomanat) vs. mantenir el commit horari.
- [ ] Què fem amb els 3 dashboards Hugo propis.
- [ ] Ruta definitiva per a `guiesbarcelona` i `9bi` (URLs i pipeline).

---

## 7. Referència ràpida

### Comandes útils

```bash
# Tests de la plantilla
.venv/bin/python -m pytest -q

# Comprovar sintaxi del dashboard
python3 - <<'PY'
import re, pathlib
html = pathlib.Path('admin/index.html').read_text()
blocks = re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', html, re.S)
pathlib.Path('/tmp/dashboard-main.js').write_text(blocks[-1])
PY
node --check /tmp/dashboard-main.js

# Estat dels workflows d'un web
gh run list -R 112books/<repo> --limit 5

# Disparar el fetch manualment
gh workflow run fetch-analytics.yml -R 112books/<repo>

# Veure si el JSON en línia té els camps nous
curl -s https://<web>/admin/analytics.json | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('generated'), 'pages_daily' in d)"
```

### Secrets

El nom varia per repo. Cal mirar el workflow de cadascun abans de tocar-lo. No committejar mai el token.

### Enllaços

- Plantilla: https://github.com/112books/goatcounter-dashboard
- GoatCounter API: https://www.goatcounter.com/help/api

---

## 8. Registre d'execució

| Data | Web | Què s'ha fet | Resultat | Notes |
|---|---|---|---|---|
| — | — | — | — | — |
