# Error Handling System

## Verfügbare Error-Types:

- `file_too_large` - Datei über 20MB
- `invalid_format` - Ungültiges Dateiformat
- `processing_failed` - Verarbeitungsfehler
- `network_error` - Netzwerkprobleme
- `authentication_error` - Login-Fehler
- `quota_exceeded` - Kontingent überschritten

## Verwendung:
```javascript
// Zeige Error mit Lösungsvorschlägen
showError('file_too_large', 'Die Datei ist 25MB groß');

// Toast für kleine Fehler
showToast('Kleine Warnung', 'warning');
```

## Features:

✅ Intelligente Lösungsvorschläge
✅ Kontext-basierte Aktionen
✅ Automatische Fehlerklassifizierung
✅ Global error handler
✅ Offline-Erkennung
