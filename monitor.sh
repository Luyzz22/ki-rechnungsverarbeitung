#!/bin/bash

echo "========================================="
echo "SBS INVOICE APP - SYSTEM MONITOR"
echo "========================================="
echo ""

# Service Status
echo "📊 SERVICE STATUS:"
systemctl status invoice-app --no-pager | head -5
echo ""

# Disk Usage
echo "💾 DISK USAGE:"
df -h / | tail -1
echo ""

# Memory Usage
echo "🧠 MEMORY USAGE:"
free -h | grep Mem
echo ""

# CPU Load
echo "⚡ CPU LOAD:"
uptime
echo ""

# Last 10 Log Entries
echo "📝 LAST 10 APP LOGS:"
if [ -f /var/www/invoice-app/logs/app.log ]; then
    tail -10 /var/www/invoice-app/logs/app.log
else
    echo "No logs yet"
fi
echo ""

# Recent Uploads
echo "📁 RECENT UPLOADS (last 24h):"
find /tmp -name "invoice_*.pdf" -mtime -1 -ls 2>/dev/null | wc -l
echo ""

# Network Connections
echo "🌐 ACTIVE CONNECTIONS:"
netstat -an | grep :8000 | grep ESTABLISHED | wc -l
echo ""

echo "========================================="
echo "Monitor completed at $(date)"
echo "========================================="01~
