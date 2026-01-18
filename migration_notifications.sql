-- =============================================================================
-- SBS Deutschland - Enterprise Notifications Migration
-- =============================================================================
-- Ausführen mit: sqlite3 /var/www/invoice-app/data/invoices.db < migration_notifications.sql
-- =============================================================================

-- Neue Spalten zu user_settings hinzufügen (ignoriert wenn schon vorhanden)
-- SQLite unterstützt kein IF NOT EXISTS für ALTER TABLE, daher mit PRAGMA

-- Prüfen und Spalten hinzufügen
PRAGMA foreign_keys=off;

-- Slack Webhook URL
ALTER TABLE user_settings ADD COLUMN slack_webhook_url TEXT DEFAULT NULL;

-- Wöchentlicher Report
ALTER TABLE user_settings ADD COLUMN weekly_report_enabled INTEGER DEFAULT 0;
ALTER TABLE user_settings ADD COLUMN weekly_report_day INTEGER DEFAULT 1;
ALTER TABLE user_settings ADD COLUMN weekly_report_time TEXT DEFAULT '07:00';

PRAGMA foreign_keys=on;

-- Scheduled Reports Tabelle
CREATE TABLE IF NOT EXISTS scheduled_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    user_email TEXT,
    org_id INTEGER,
    name TEXT NOT NULL,
    report_type TEXT NOT NULL DEFAULT 'weekly',
    schedule TEXT NOT NULL DEFAULT 'weekly',
    recipients TEXT,
    filters TEXT,
    is_active INTEGER DEFAULT 1,
    next_run TEXT,
    last_run TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index für schnellere Abfragen
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_user ON scheduled_reports(user_email);
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_next_run ON scheduled_reports(next_run);
CREATE INDEX IF NOT EXISTS idx_user_settings_email ON user_settings(user_email);

-- Notification Log Tabelle
CREATE TABLE IF NOT EXISTS notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,
    notification_type TEXT NOT NULL,  -- 'email', 'slack', 'weekly_report'
    channel TEXT,                      -- 'sendgrid', 'slack_webhook'
    status TEXT NOT NULL,              -- 'sent', 'failed', 'pending'
    message TEXT,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notification_log_user ON notification_log(user_email);
CREATE INDEX IF NOT EXISTS idx_notification_log_type ON notification_log(notification_type);

-- Fertig
SELECT 'Migration erfolgreich abgeschlossen!' as status;
