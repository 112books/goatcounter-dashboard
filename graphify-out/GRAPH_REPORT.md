# Graph Report - .  (2026-05-27)

## Corpus Check
- Corpus is ~5,309 words - fits in a single context window. You may not need a graph.

## Summary
- 45 nodes · 53 edges · 7 communities (6 shown, 1 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.88)
- Token cost: 6,200 input · 1,850 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Analytics Data Schema|Analytics Data Schema]]
- [[_COMMUNITY_Data Processing Pipeline|Data Processing Pipeline]]
- [[_COMMUNITY_Data Ingestion & CI|Data Ingestion & CI]]
- [[_COMMUNITY_Dashboard & Auth Setup|Dashboard & Auth Setup]]
- [[_COMMUNITY_Dashboard Rendering|Dashboard Rendering]]
- [[_COMMUNITY_Time Period Filters|Time Period Filters]]
- [[_COMMUNITY_Setup Script|Setup Script]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 7 edges
2. `GoatCounter API v0 — external stats REST API` - 5 edges
3. `norm_items()` - 4 edges
4. `fetch-analytics.yml — GitHub Actions hourly workflow` - 4 edges
5. `period` - 3 edges
6. `extract_lang()` - 3 edges
7. `extract_section()` - 3 edges
8. `admin/index.html — Dashboard UI` - 3 edges
9. `loadData() — fetch analytics.json and trigger render` - 3 edges
10. `Serverless password auth via SHA-256 (no backend)` - 3 edges

## Surprising Connections (you probably didn't know these)
- `README — GoatCounter Dashboard documentation` --references--> `GoatCounter API v0 — external stats REST API`  [EXTRACTED]
  README.md → scripts/process-analytics.py
- `setup.sh — interactive wizard to configure dashboard` --references--> `admin/index.html — Dashboard UI`  [EXTRACTED]
  scripts/setup.sh → admin/index.html
- `fetch-analytics.yml — GitHub Actions hourly workflow` --references--> `GoatCounter API v0 — external stats REST API`  [EXTRACTED]
  .github/workflows/fetch-analytics.yml → scripts/process-analytics.py
- `admin/index.html — Dashboard UI` --implements--> `Static hosting compatibility — no DB, no PHP, no cookies`  [INFERRED]
  admin/index.html → README.md
- `Serverless password auth via SHA-256 (no backend)` --rationale_for--> `Static hosting compatibility — no DB, no PHP, no cookies`  [INFERRED]
  admin/index.html → README.md

## Hyperedges (group relationships)
- **Analytics Data Pipeline: Fetch → Build → Process → Serve** — github_workflows_fetch_analytics, scripts_build_analytics_json, scripts_process_analytics, admin_analytics_json, admin_index [INFERRED 0.95]
- **GoatCounter API v0 Consumers** — github_workflows_fetch_analytics, scripts_build_analytics_json, scripts_process_analytics, concept_goatcounter_api_v0 [EXTRACTED 1.00]
- **Serverless Static Dashboard Pattern (no DB, SHA-256 auth, JSON data)** — concept_serverless_auth, concept_static_hosting, admin_index, admin_analytics_json [INFERRED 0.85]

## Communities (7 total, 1 thin omitted)

### Community 0 - "Analytics Data Schema"
Cohesion: 0.15
Nodes (12): browsers, by_lang, by_section, generated, hits, hits_by_day, locations, refs (+4 more)

### Community 1 - "Data Processing Pipeline"
Cohesion: 0.33
Nodes (8): extract_lang(), extract_section(), main(), norm_items(), Detecta idioma del primer o segon segment si és ca/es/en/fr/de/it/pt., Retorna el primer segment significatiu de la ruta (secció principal)., Normalitza [{name,id,count}] des de resposta GoatCounter API v0 stats/{page}., safe_get()

### Community 2 - "Data Ingestion & CI"
Cohesion: 0.43
Nodes (4): GoatCounter API v0 — external stats REST API, /tmp/raw_all.json — intermediate aggregated raw data file, fetch-analytics.yml — GitHub Actions hourly workflow, load()

### Community 3 - "Dashboard & Auth Setup"
Cohesion: 0.40
Nodes (6): admin/index.html — Dashboard UI, sha256() — client-side SHA-256 password check, Serverless password auth via SHA-256 (no backend), Static hosting compatibility — no DB, no PHP, no cookies, README — GoatCounter Dashboard documentation, setup.sh — interactive wizard to configure dashboard

### Community 4 - "Dashboard Rendering"
Cohesion: 0.40
Nodes (5): groupHits() — group hits by day/week/month, loadData() — fetch analytics.json and trigger render, renderAll() — render all dashboard sections, renderChart() — Chart.js time-series line chart, showDashboard() — reveal dashboard after auth

### Community 5 - "Time Period Filters"
Cohesion: 0.67
Nodes (3): period, end, start

## Knowledge Gaps
- **19 isolated node(s):** `generated`, `start`, `end`, `total`, `total_unique` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Data Processing Pipeline` to `Analytics Data Schema`, `Data Ingestion & CI`?**
  _High betweenness centrality (0.263) - this node is a cross-community bridge._
- **Why does `fetch-analytics.yml — GitHub Actions hourly workflow` connect `Data Ingestion & CI` to `Analytics Data Schema`?**
  _High betweenness centrality (0.246) - this node is a cross-community bridge._
- **Why does `GoatCounter API v0 — external stats REST API` connect `Data Ingestion & CI` to `Data Processing Pipeline`, `Dashboard & Auth Setup`?**
  _High betweenness centrality (0.245) - this node is a cross-community bridge._
- **What connects `generated`, `start`, `end` to the rest of the system?**
  _22 weakly-connected nodes found - possible documentation gaps or missing edges._