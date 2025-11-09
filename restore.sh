#!/bin/bash

# SBS Invoice App - Restore from Backup
# Stellt den letzten Stand von GitHub wieder her

echo "========================================="
echo "RESTORE FROM BACKUP"
echo "========================================="
echo ""
echo "⚠️  WARNING: This will overwrite local changes!"
echo ""
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 1
fi

cd /var/www/invoice-app

echo "📥 Fetching latest from GitHub..."
git fetch origin main

echo "🔄 Resetting to latest commit..."
git reset --hard origin/main

echo "🧹 Cleaning untracked files..."
git clean -fd

echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt --break-system-packages

echo "🔄 Restarting services..."
sudo systemctl restart invoice-app
sudo systemctl restart nginx

echo ""
echo "✅ Restore completed!"
echo ""
echo "Check status:"
echo "  sudo systemctl status invoice-app"
echo "  curl http://207.154.200.239/health"
