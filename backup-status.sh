#!/bin/bash

echo "========================================="
echo "BACKUP STATUS"
echo "========================================="
echo ""

cd /var/www/invoice-app

# Last Git Commit
echo "📝 Last Commit:"
git log -1 --pretty=format:"%h - %an, %ar : %s" 2>/dev/null || echo "No commits"
echo ""
echo ""

# GitHub Sync Status
echo "☁️ GitHub Sync:"
git fetch origin main &>/dev/null
LOCAL=$(git rev-parse @ 2>/dev/null)
REMOTE=$(git rev-parse @{u} 2>/dev/null)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "✅ Up to date with GitHub"
else
    echo "⚠️ Local changes not pushed or unable to check!"
fi
echo ""

# Last Backup
echo "⏰ Last Backup:"
if [ -f logs/backup.log ]; then
    grep "BACKUP COMPLETED" logs/backup.log | tail -1
else
    echo "No backups yet"
fi
echo ""

# Cron Jobs
echo "🔄 Scheduled Backups:"
crontab -l 2>/dev/null | grep backup.sh || echo "No cron jobs configured"
echo ""

# Disk Space
echo "💾 Disk Space:"
df -h / | tail -1
echo ""

# Recent System Status Files
echo "📊 Recent System Status Snapshots:"
ls -lht logs/system-status-*.txt 2>/dev/null | head -5 || echo "No snapshots yet"
echo ""

echo "========================================="

