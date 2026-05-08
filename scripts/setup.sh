#!/usr/bin/env bash
set -e

echo ""
echo "══════════════════════════════════════════════"
echo "  GoatCounter Dashboard — Setup"
echo "══════════════════════════════════════════════"
echo ""
echo "Configura el dashboard en 2 minuts."
echo "Pots trobar més informació a README.md"
echo ""

read -rp "Nom del lloc web (ex: Machiroku): " SITE_NAME
read -rp "Compte GoatCounter (ex: machiroku — sense .goatcounter.com): " GC_ACCOUNT
read -rsp "Contrasenya per al dashboard: " PW && echo ""

# Seccions: opcionals
echo ""
echo "Seccions principals del teu web (opcionals)."
echo "Format JSON: {\"inici\":\"Inici\",\"oferta\":\"Oferta\",\"contacte\":\"Contacte\"}"
echo "Deixa en blanc per usar els noms de ruta originals."
read -rp "Seccions: " SECTION_NAMES_JSON
if [[ -z "$SECTION_NAMES_JSON" ]]; then
  SECTION_NAMES_JSON="{}"
fi

# SHA-256 de la contrasenya (compatible macOS i Linux)
if command -v sha256sum &>/dev/null; then
  PW_HASH=$(echo -n "${PW}" | sha256sum | awk '{print $1}')
elif command -v shasum &>/dev/null; then
  PW_HASH=$(echo -n "${PW}" | shasum -a 256 | awk '{print $1}')
else
  echo "ERROR: no s'ha trobat sha256sum ni shasum. Instal·la coreutils." >&2
  exit 1
fi

echo ""
echo "Configurant fitxers..."

# admin/index.html
sed -i.bak \
  -e "s|{{SITE_NAME}}|${SITE_NAME}|g" \
  -e "s|{{GC_ACCOUNT}}|${GC_ACCOUNT}|g" \
  -e "s|{{PW_HASH}}|${PW_HASH}|g" \
  -e "s|{{SECTION_NAMES_JSON}}|${SECTION_NAMES_JSON}|g" \
  admin/index.html
rm -f admin/index.html.bak

# .github/workflows/fetch-analytics.yml
sed -i.bak \
  -e "s|{{GC_ACCOUNT}}|${GC_ACCOUNT}|g" \
  .github/workflows/fetch-analytics.yml
rm -f .github/workflows/fetch-analytics.yml.bak

echo ""
echo "✓ admin/index.html configurat"
echo "✓ .github/workflows/fetch-analytics.yml configurat"
echo ""
echo "═══════════════════════════════════════════════"
echo " Passos següents"
echo "═══════════════════════════════════════════════"
echo ""
echo "1. Afegeix el secret GOATCOUNTER_TOKEN al repo:"
echo "   GitHub → Settings → Secrets → New repository secret"
echo "   Nom: GOATCOUNTER_TOKEN  |  Valor: el teu token de GoatCounter"
echo ""
echo "2. Copia els fitxers al teu projecte Hugo:"
echo "   cp -r admin/   /el-teu-projecte/static/admin/"
echo "   cp -r scripts/ /el-teu-projecte/scripts/"
echo "   cp .github/workflows/fetch-analytics.yml /el-teu-projecte/.github/workflows/"
echo ""
echo "   Si el teu Hugo publica a docs/ (GitHub Pages), afegeix al workflow:"
echo "   cp static/admin/analytics.json docs/admin/analytics.json"
echo "   git add docs/admin/analytics.json"
echo ""
echo "3. Activa el workflow:"
echo "   GitHub → Actions → Fetch GoatCounter Analytics → Run workflow"
echo ""
echo "4. El dashboard estarà disponible a:"
echo "   https://el-teu-domini.com/admin/"
echo ""
echo "Per canviar la contrasenya en el futur:"
echo "   echo -n 'nova_contrasenya' | sha256sum"
echo "   → substitueix PW_HASH a admin/index.html"
echo ""
