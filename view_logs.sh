#!/bin/bash

LOG_FILE="/var/www/invoice-app/logs/app.log"

echo "==================================="
echo "SBS INVOICE APP - LIVE LOGS"
echo "==================================="
echo ""

if [ "$1" = "follow" ]; then
    echo "📡 Following logs (Ctrl+C to stop)..."
    tail -f $LOG_FILE
elif [ "$1" = "errors" ]; then
    echo "❌ Error logs:"
    grep -i "error\|exception\|failed" $LOG_FILE | tail -20
elif [ "$1" = "today" ]; then
    echo "📅 Today's logs:"
    grep "$(date +%Y-%m-%d)" $LOG_FILE
else
    echo "📋 Last 50 log entries:"
    tail -50 $LOG_FILE
    echo ""
    echo "Usage:"
    echo "  ./view_logs.sh          - Last 50 entries"
    echo "  ./view_logs.sh follow   - Live tail"
    echo "  ./view_logs.sh errors   - Only errors"
    echo "  ./view_logs.sh today    - Today's logs"
fi
