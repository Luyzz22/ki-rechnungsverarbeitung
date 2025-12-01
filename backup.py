#!/usr/bin/env python3
"""
SBS Deutschland – Automatisches Backup
Sichert Datenbank und wichtige Konfigurationsdateien.
"""

import os
import shutil
import gzip
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfiguration
BACKUP_DIR = Path("/var/www/invoice-app/backups")
DB_PATH = Path("/var/www/invoice-app/invoices.db")
MAX_BACKUPS = 30  # Behalte 30 Tage
COMPRESS = True


def create_backup() -> str:
    """
    Erstellt ein Backup der Datenbank.
    
    Returns:
        Pfad zur Backup-Datei
    """
    BACKUP_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"invoices_backup_{timestamp}.db"
    
    if COMPRESS:
        backup_name += ".gz"
        backup_path = BACKUP_DIR / backup_name
        
        # Komprimiertes Backup
        with open(DB_PATH, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        backup_path = BACKUP_DIR / backup_name
        shutil.copy2(DB_PATH, backup_path)
    
    size_mb = backup_path.stat().st_size / (1024 * 1024)
    logger.info(f"✅ Backup erstellt: {backup_path.name} ({size_mb:.2f} MB)")
    
    return str(backup_path)


def cleanup_old_backups():
    """Löscht Backups älter als MAX_BACKUPS Tage."""
    if not BACKUP_DIR.exists():
        return
    
    cutoff = datetime.now() - timedelta(days=MAX_BACKUPS)
    deleted = 0
    
    for backup_file in BACKUP_DIR.glob("invoices_backup_*.db*"):
        # Extrahiere Datum aus Dateiname
        try:
            date_str = backup_file.stem.split('_')[2]  # YYYYMMDD
            file_date = datetime.strptime(date_str, '%Y%m%d')
            
            if file_date < cutoff:
                backup_file.unlink()
                deleted += 1
                logger.info(f"🗑️ Altes Backup gelöscht: {backup_file.name}")
        except (IndexError, ValueError):
            continue
    
    if deleted:
        logger.info(f"✅ {deleted} alte Backups gelöscht")


def restore_backup(backup_path: str) -> bool:
    """
    Stellt ein Backup wieder her.
    
    Args:
        backup_path: Pfad zur Backup-Datei
        
    Returns:
        True bei Erfolg
    """
    backup = Path(backup_path)
    
    if not backup.exists():
        logger.error(f"❌ Backup nicht gefunden: {backup_path}")
        return False
    
    # Aktuelles DB sichern
    if DB_PATH.exists():
        emergency_backup = DB_PATH.with_suffix('.db.emergency')
        shutil.copy2(DB_PATH, emergency_backup)
        logger.info(f"⚠️ Notfall-Backup erstellt: {emergency_backup}")
    
    # Wiederherstellen
    if backup.suffix == '.gz':
        with gzip.open(backup, 'rb') as f_in:
            with open(DB_PATH, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        shutil.copy2(backup, DB_PATH)
    
    logger.info(f"✅ Backup wiederhergestellt: {backup.name}")
    return True


def list_backups() -> list:
    """Listet alle verfügbaren Backups."""
    if not BACKUP_DIR.exists():
        return []
    
    backups = []
    for backup_file in sorted(BACKUP_DIR.glob("invoices_backup_*.db*"), reverse=True):
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        backups.append({
            'name': backup_file.name,
            'path': str(backup_file),
            'size_mb': round(size_mb, 2),
            'created': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
        })
    
    return backups


def get_backup_status() -> dict:
    """Status-Übersicht für Health-Check."""
    backups = list_backups()
    
    return {
        'total_backups': len(backups),
        'latest_backup': backups[0]['name'] if backups else None,
        'latest_date': backups[0]['created'] if backups else None,
        'total_size_mb': sum(b['size_mb'] for b in backups),
        'db_size_mb': round(DB_PATH.stat().st_size / (1024 * 1024), 2) if DB_PATH.exists() else 0
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'create':
            create_backup()
            cleanup_old_backups()
        elif cmd == 'list':
            for b in list_backups():
                print(f"{b['name']} - {b['size_mb']} MB - {b['created']}")
        elif cmd == 'restore' and len(sys.argv) > 2:
            restore_backup(sys.argv[2])
        elif cmd == 'status':
            import json
            print(json.dumps(get_backup_status(), indent=2))
        else:
            print("Usage: backup.py [create|list|restore <path>|status]")
    else:
        # Default: Backup erstellen
        create_backup()
        cleanup_old_backups()
