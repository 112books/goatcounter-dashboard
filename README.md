# GoatCounter Dashboard

Dashboard d'estadístiques elegant per a webs estàtics (Hugo, Jekyll, Eleventy…) amb [GoatCounter](https://www.goatcounter.com).

Actualització automàtica cada hora via **GitHub Actions**. Cap base de dades, cap servidor PHP, cap cookie. Funciona amb qualsevol hosting estàtic.

---

## Característiques

- **Gràfic temporal** interactiu (7d / 30d / 3m / 1a · dia / setmana / mes)
- **Seccions i pàgines** més visitades
- **Idiomes** dels visitants (barra visual)
- **Referrers** — d'on vénen les visites
- **Localització** per país
- **Dispositius** — mòbil / tauleta / escriptori
- **Navegadors i sistemes operatius**
- **Insights automàtics** en llenguatge natural
- **Accés protegit** amb contrasenya (SHA-256, sense servidor)
- **Disseny net** — IBM Plex Mono, tema clar, responsive

---

## Instal·lació ràpida

### 1. Crea un compte a GoatCounter (gratuït)

1. Ves a [goatcounter.com](https://www.goatcounter.com) → **Sign up**
2. Tria un nom de compte (ex: `el-meu-web`) → quedarà a `el-meu-web.goatcounter.com`
3. Afegeix el codi de seguiment al `<head>` del teu web:

```html
<script data-goatcounter="https://el-meu-web.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
```

Per a Hugo, posa'l al partial del `<head>` o a `baseof.html`.

### 2. Genera un token d'API

1. GoatCounter → **Settings → API tokens → New token**
2. Nom: `dashboard` | Permís: **Read stats** ✓
3. Copia el token — el necessitaràs al pas 4

### 3. Clona i configura

```bash
git clone https://github.com/112books/goatcounter-dashboard
cd goatcounter-dashboard
bash scripts/setup.sh
```

El wizard et demanarà:
- Nom del lloc web
- Nom del compte GoatCounter (sense `.goatcounter.com`)
- Contrasenya per al dashboard
- Seccions principals (opcional, per a noms més llegibles)

### 4. Afegeix el secret a GitHub

Al teu repo GitHub:
**Settings → Secrets and variables → Actions → New repository secret**

| Nom | Valor |
|-----|-------|
| `GOATCOUNTER_TOKEN` | el token del pas 2 |

### 5. Copia els fitxers al teu projecte

```bash
# Ajusta els paths al teu projecte
cp -r admin/   /el-teu-projecte-hugo/static/admin/
cp -r scripts/ /el-teu-projecte-hugo/scripts/
cp .github/workflows/fetch-analytics.yml /el-teu-projecte-hugo/.github/workflows/
```

**Si el teu Hugo publica a `docs/`** (GitHub Pages), afegeix al pas "Commit analytics" del workflow:

```yaml
- name: Commit analytics
  run: |
    cp static/admin/analytics.json docs/admin/analytics.json
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add static/admin/analytics.json docs/admin/analytics.json
    git diff --staged --quiet || git commit -m "chore: update analytics [skip ci]"
    git pull --rebase
    git push
```

### 6. Activa el primer workflow

**GitHub → Actions → Fetch GoatCounter Analytics → Run workflow**

En 1-2 minuts el dashboard estarà disponible a `https://el-teu-domini.com/admin/`

---

## Estructura de fitxers

```
el-teu-projecte/
├── static/
│   └── admin/
│       ├── index.html        ← dashboard (configurat per setup.sh)
│       └── analytics.json    ← generat automàticament cada hora
├── scripts/
│   ├── build-analytics-json.py
│   └── process-analytics.py
└── .github/
    └── workflows/
        └── fetch-analytics.yml
```

---

## Canviar la contrasenya

```bash
echo -n "nova_contrasenya" | sha256sum
# Copia el hash i substitueix PW_HASH a static/admin/index.html
```

---

## Estructura de `analytics.json`

```json
{
  "generated":    "2026-05-08T14:00:00Z",
  "period":       { "start": "2025-05-08", "end": "2026-05-08" },
  "total":        1234,
  "total_unique": 890,
  "hits_by_day":  [{ "date": "2026-05-07", "count": 42 }],
  "hits":         [{ "path": "/ca/inici/", "count": 300 }],
  "by_lang":      { "ca": 800, "en": 300, "es": 134 },
  "by_section":   { "inici": 400, "contacte": 200 },
  "browsers":     [{ "name": "Chrome", "id": "Chrome", "count": 700 }],
  "systems":      [{ "name": "Android", "id": "Android", "count": 500 }],
  "sizes":        [{ "name": "phone", "id": "phone", "count": 600 }],
  "locations":    [{ "name": "Spain", "id": "ES", "count": 1000 }],
  "refs":         [{ "name": "google.com", "id": "google.com", "count": 150 }]
}
```

---

## Llicència

MIT — lliure d'usar, modificar i distribuir.

Fet per [pocallum / LinuxBCN](https://linuxbcn.com) ♥
