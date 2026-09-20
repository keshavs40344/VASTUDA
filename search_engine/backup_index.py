"""VASTUDA Sovereign Search Engine - Phase 5.4
Atomic Database Backup & Restoration Utility

Features:
- Atomic online backup using SQLite Online Backup API (sqlite3.Connection.backup())
- PRAGMA integrity_check validation of the generated backup
- Automated retention policy (retains last N backups)
- Restore functionality (--restore <backup_path>)
"""

import os
import sys
import time
import shutil
import sqlite3
import argparse
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from search_engine import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VASTUDA_Backup")

BACKUPS_DIR = os.path.join(BASE_DIR, "backups")


def ensure_backup_dir():
    os.makedirs(BACKUPS_DIR, exist_ok=True)


def verify_sqlite_integrity(db_file_path):
    """Run PRAGMA integrity_check on a database file."""
    try:
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        rows = cursor.fetchall()
        conn.close()
        if rows and len(rows) == 1 and rows[0][0] == "ok":
            return True, "ok"
        return False, f"Integrity issues found: {rows}"
    except Exception as e:
        return False, f"Integrity check failed with error: {e}"


def create_backup(source_db_path=None, max_retain=5):
    """Create an atomic snapshot of the SQLite database."""
    if source_db_path is None:
        source_db_path = db.DB_PATH

    if not os.path.exists(source_db_path):
        raise FileNotFoundError(f"Source database does not exist: {source_db_path}")

    ensure_backup_dir()
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    backup_filename = f"vastuda_backup_{timestamp_str}.db"
    backup_target_path = os.path.join(BACKUPS_DIR, backup_filename)

    logger.info(f"Initiating online atomic backup from {source_db_path} to {backup_target_path}...")

    src_conn = sqlite3.connect(source_db_path)
    dst_conn = sqlite3.connect(backup_target_path)

    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=100, progress=None)
        logger.info("SQLite online backup copying completed.")
    finally:
        dst_conn.close()
        src_conn.close()

    # Integrity verification
    is_ok, msg = verify_sqlite_integrity(backup_target_path)
    if not is_ok:
        logger.error(f"Backup integrity verification failed: {msg}")
        if os.path.exists(backup_target_path):
            os.remove(backup_target_path)
        raise RuntimeError(f"Backup failed integrity check: {msg}")

    size_bytes = os.path.getsize(backup_target_path)
    logger.info(f"Backup verified successfully! Size: {size_bytes} bytes ({round(size_bytes / (1024*1024), 2)} MB)")

    # Enforce retention policy
    enforce_retention_policy(max_retain=max_retain)

    return {
        "status": "success",
        "backup_path": backup_target_path,
        "backup_filename": backup_filename,
        "size_bytes": size_bytes,
        "timestamp": timestamp_str
    }


def enforce_retention_policy(max_retain=5):
    """Keep only the most recent N backup files."""
    if not os.path.exists(BACKUPS_DIR):
        return

    files = [
        os.path.join(BACKUPS_DIR, f)
        for f in os.listdir(BACKUPS_DIR)
        if f.startswith("vastuda_backup_") and f.endswith(".db")
    ]
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    if len(files) > max_retain:
        to_delete = files[max_retain:]
        for fpath in to_delete:
            try:
                os.remove(fpath)
                logger.info(f"Pruned older backup: {os.path.basename(fpath)}")
            except Exception as e:
                logger.warning(f"Failed to prune {fpath}: {e}")


def restore_backup(backup_path, target_db_path=None):
    """Restore database from a backup file."""
    if target_db_path is None:
        target_db_path = db.DB_PATH

    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Specified backup does not exist: {backup_path}")

    # Verify backup integrity first
    is_ok, msg = verify_sqlite_integrity(backup_path)
    if not is_ok:
        raise ValueError(f"Cannot restore corrupted backup file: {msg}")

    # Backup current target database before overwriting
    pre_restore_backup = f"{target_db_path}.pre_restore_{int(time.time())}.bak"
    if os.path.exists(target_db_path):
        logger.info(f"Creating pre-restore safety snapshot at {pre_restore_backup}")
        shutil.copy2(target_db_path, pre_restore_backup)

    # Use online backup API for safe restore
    src_conn = sqlite3.connect(backup_path)
    dst_conn = sqlite3.connect(target_db_path)

    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=100)
        logger.info(f"Successfully restored {target_db_path} from {backup_path}")
    finally:
        dst_conn.close()
        src_conn.close()

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VASTUDA Database Backup & Restoration")
    parser.add_argument("--backup", action="store_true", help="Create an atomic database backup")
    parser.add_argument("--restore", type=str, help="Restore database from the given backup file path")
    parser.add_argument("--max-retain", type=int, default=5, help="Number of backups to retain (default: 5)")
    parser.add_argument("--check-integrity", type=str, help="Check integrity of specified database file")

    args = parser.parse_args()

    if args.check_integrity:
        ok, reason = verify_sqlite_integrity(args.check_integrity)
        print(f"Integrity check for {args.check_integrity}: {'OK' if ok else 'FAILED (' + reason + ')'}")
    elif args.restore:
        logger.info(f"Restoring database from {args.restore}...")
        restore_backup(args.restore)
        print("Restoration completed successfully.")
    else:
        # Default action: create backup
        res = create_backup(max_retain=args.max_retain)
        print(f"Backup created: {res['backup_path']} ({res['size_bytes']} bytes)")
