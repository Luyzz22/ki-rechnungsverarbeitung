#!/bin/bash
# =============================================================================
# SBS Invoice App – CSS Installation Script
# =============================================================================
# 
# Dieses Script installiert die neuen Design-Token und Component CSS-Dateien.
# 
# Verwendung:
#   1. Script und CSS-Dateien nach /var/www/invoice-app/ kopieren
#   2. chmod +x install-css.sh
#   3. ./install-css.sh
#
# =============================================================================

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Pfade
APP_DIR="/var/www/invoice-app"
CSS_DIR="$APP_DIR/web/static/css"
BACKUP_DIR="$CSS_DIR/_backup_$(date +%Y%m%d_%H%M%S)"

echo ""
echo "================================================"
echo "  SBS Design System Installation"
echo "================================================"
echo ""

# Prüfen ob wir im richtigen Verzeichnis sind
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}Fehler: $APP_DIR existiert nicht!${NC}"
    exit 1
fi

if [ ! -d "$CSS_DIR" ]; then
    echo -e "${RED}Fehler: $CSS_DIR existiert nicht!${NC}"
    exit 1
fi

# Prüfen ob die neuen CSS-Dateien vorhanden sind
if [ ! -f "design-tokens.css" ] || [ ! -f "components.css" ]; then
    echo -e "${RED}Fehler: design-tokens.css und/oder components.css nicht gefunden!${NC}"
    echo "Bitte stelle sicher, dass beide Dateien im aktuellen Verzeichnis sind."
    exit 1
fi

# Backup erstellen
echo -e "${YELLOW}1. Erstelle Backup...${NC}"
mkdir -p "$BACKUP_DIR"
cp "$CSS_DIR"/*.css "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}   Backup erstellt: $BACKUP_DIR${NC}"

# Neue CSS-Dateien kopieren
echo -e "${YELLOW}2. Kopiere neue CSS-Dateien...${NC}"
cp design-tokens.css "$CSS_DIR/"
cp components.css "$CSS_DIR/"
echo -e "${GREEN}   design-tokens.css → $CSS_DIR/${NC}"
echo -e "${GREEN}   components.css → $CSS_DIR/${NC}"

# Berechtigungen setzen
echo -e "${YELLOW}3. Setze Berechtigungen...${NC}"
chmod 644 "$CSS_DIR/design-tokens.css"
chmod 644 "$CSS_DIR/components.css"
echo -e "${GREEN}   Berechtigungen gesetzt${NC}"

echo ""
echo "================================================"
echo -e "${GREEN}  Installation erfolgreich!${NC}"
echo "================================================"
echo ""
echo "Nächste Schritte:"
echo ""
echo "1. Füge in deinen HTML-Templates folgende Zeilen ein"
echo "   (NACH dem <head> Tag, VOR anderen CSS-Dateien):"
echo ""
echo '   <link rel="stylesheet" href="/static/css/design-tokens.css">'
echo '   <link rel="stylesheet" href="/static/css/components.css">'
echo ""
echo "2. Teste die Seite im Browser"
echo ""
echo "3. Bei Problemen: Backup wiederherstellen mit:"
echo "   cp $BACKUP_DIR/*.css $CSS_DIR/"
echo ""
