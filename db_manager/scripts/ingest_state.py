import sqlite3
import logging
import os
from datetime import datetime
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class FileStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class IngestStateDB:
    def __init__(self, db_path: str = "ingest_state.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    file_path TEXT PRIMARY KEY,
                    sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_error TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON files(status)
            """)
            conn.commit()
    
    def get_file_status(self, file_path: str) -> Optional[Tuple[FileStatus, str]]:
        """
        Возвращает статус файла и его hash.
        
        Returns:
            (status, sha256) или None если файл не найден в БД
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT status, sha256 FROM files WHERE file_path = ?",
                (file_path,)
            )
            row = cursor.fetchone()
            if row:
                return FileStatus(row["status"]), row["sha256"]
            return None
    
    def should_skip_file(self, file_path: str, current_hash: str) -> bool:
        status_info = self.get_file_status(file_path)
        if status_info is None:
            return False
        status, stored_hash = status_info
        return status == FileStatus.DONE and stored_hash == current_hash
    
    def mark_in_progress(self, file_path: str, sha256: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files (file_path, sha256, status, last_error, updated_at)
                VALUES (?, ?, ?, NULL, ?)
                """,
                (file_path, sha256, FileStatus.IN_PROGRESS.value, datetime.utcnow().isoformat())
            )
            conn.commit()
        logger.debug("Файл помечен как in_progress: %s", file_path)
    
    def mark_done(self, file_path: str, sha256: str) -> None:
        """Помечает файл как успешно обработанный."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files (file_path, sha256, status, last_error, updated_at)
                VALUES (?, ?, ?, NULL, ?)
                """,
                (file_path, sha256, FileStatus.DONE.value, datetime.utcnow().isoformat())
            )
            conn.commit()
        logger.debug("Файл помечен как done: %s", file_path)
    
    def mark_failed(self, file_path: str, sha256: str, error: str) -> None:
        """Помечает файл как проваленный с ошибкой."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files (file_path, sha256, status, last_error, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (file_path, sha256, FileStatus.FAILED.value, error[:500], datetime.utcnow().isoformat())
            )
            conn.commit()
        logger.warning("Файл помечен как failed: %s, ошибка: %s", file_path, error[:200])
    
    def get_stats(self) -> dict:
        """Возвращает статистику по статусам файлов."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT status, COUNT(*) as count
                FROM files
                GROUP BY status
                """
            )
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            return {
                "pending": stats.get(FileStatus.PENDING.value, 0),
                "in_progress": stats.get(FileStatus.IN_PROGRESS.value, 0),
                "done": stats.get(FileStatus.DONE.value, 0),
                "failed": stats.get(FileStatus.FAILED.value, 0),
            }
