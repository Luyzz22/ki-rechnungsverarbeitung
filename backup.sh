#!/bin/bash

# SBS Invoice App - Automated Backup Script
# Sichert Code, Config (ohne Secrets), und System-Status

BACKUP_DIR="/var/www/invoice-app"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_DIR/logs/backup.log"

# Log Directory erstellen falls nicht vorhanden
mkdir -p $BACKUP_DIR/logs

echo "=========================================" | tee -a $LOG_FILE
echo "BACKUP STARTED: $(date)" | tee -a $LOG_FILE
echo "=========================================" | tee -a $LOG_FILE

cd $BACKUP_DIR

# Git Status prüfen
echo "📊 Checking Git status..." | tee -a $LOG_FILE

# Uncommitted Changes?
if [[ $(git status --porcelain) ]]; then
    echo "📝 Found changes, committing..." | tee -a $LOG_FILE
    
    # Add all tracked files (respects .gitignore)
    git add -A
    
    # Commit mit Timestamp
    git commit -m "🔄 Auto-backup: $TIMESTAMP" | tee -a $LOG_FILE
    
    # Push zu GitHub
    echo "☁️ Pushing to GitHub..." | tee -a $LOG_FILE
    if git push origin main 2>&1 | tee -a $LOG_FILE; then
        echo "✅ Backup successful!" | tee -a $LOG_FILE
    else
        echo "❌ Backup failed!" | tee -a $LOG_FILE
        exit 1
    fi
else
    echo "✅ No changes to backup" | tee -a $LOG_FILE
fi

# System Status speichern
echo "📊 Saving system status..." | tee -a $LOG_FILE
{
    echo "=== System Status: $TIMESTAMP ==="
    echo ""
    echo "Disk Usage:"
    df -h /
    echo ""
    echo "Memory:"
    free -h
    echo ""
    echo "Services:"
    systemctl status invoice-app --no-pager | head -10
    systemctl status nginx --no-pager | head -10
    echo ""
    echo "Last 10 App Logs:"
    tail -10 $BACKUP_DIR/logs/app.log 2>/dev/null || echo "No app logs yet"
} > "$BACKUP_DIR/logs/system-status-$TIMESTAMP.txt"

echo "=========================================" | tee -a $LOG_FILE
echo "BACKUP COMPLETED: $(date)" | tee -a $LOG_FILE
echo "=========================================" | tee -a $LOG_FILE

