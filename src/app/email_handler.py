import email
import imaplib
import json
import logging
import os
from email.header import decode_header
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt"}


def _decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for text, enc in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(enc or "utf-8", errors="ignore"))
        else:
            decoded.append(text)
    return "".join(decoded)


def _decode_filename(part) -> str | None:
    """Возвращает декодированное имя вложения или None."""
    raw = part.get_filename()
    if not raw:
        return None
    decoded, enc = decode_header(raw)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(enc or "utf-8", errors="ignore")
    return decoded


def _save_attachment(part, folder: str, email_meta: dict) -> str | None:
    """
    Сохраняет вложение письма на диск вместе с sidecar-файлом метаданных.

    Returns:
        Путь к сохранённому файлу или None если вложение пропущено.
    """
    filename = _decode_filename(part)
    if not filename:
        return None

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None

    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as f:
        f.write(part.get_payload(decode=True))

    meta_path = filepath + ".meta.json"
    try:
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(email_meta, mf, ensure_ascii=False)
    except Exception as exc:
        logger.warning("Не удалось записать метаданные %s: %s", meta_path, exc)

    logger.info("Сохранено вложение: %s", filename)
    return filepath


def download_attachments(
    user: str,
    password: str,
    folder_to_save: str,
    scope: str = "UNSEEN",
) -> list[str]:
    """
    Скачивает вложения из Gmail и сохраняет в folder_to_save.

    Args:
        scope: 'ALL' — все письма, 'UNSEEN' — только непрочитанные.

    Returns:
        Список путей к скачанным файлам.
    """
    imaplib._MAXLINE = 10_000_000
    os.makedirs(folder_to_save, exist_ok=True)

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        mail.login(user, password)
        mail.select("inbox")
        logger.info("Поиск писем, фильтр: %s", scope)

        status, messages = mail.search(None, scope)
        if status != "OK" or not messages[0]:
            logger.info("Новых писем нет.")
            return []

        msg_ids = messages[0].split()
        logger.info("Найдено писем: %d", len(msg_ids))

        downloaded: list[str] = []
        for num in msg_ids:
            _, msg_data = mail.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if not isinstance(response_part, tuple):
                    continue

                msg = email.message_from_bytes(response_part[1])
                raw_date = msg.get("Date")
                try:
                    dt = parsedate_to_datetime(raw_date) if raw_date else None
                    date_iso = dt.isoformat() if dt else ""
                except Exception:
                    date_iso = raw_date or ""

                email_meta = {
                    "email_from": _decode_mime_header(msg.get("From")),
                    "email_to": _decode_mime_header(msg.get("To")),
                    "email_subject": _decode_mime_header(msg.get("Subject")),
                    "email_date": date_iso,
                    "email_message_id": msg.get("Message-Id", ""),
                }

                for part in msg.walk():
                    if part.get_content_maintype() == "multipart":
                        continue
                    if part.get("Content-Disposition") is None:
                        continue
                    path = _save_attachment(part, folder_to_save, email_meta)
                    if path:
                        downloaded.append(path)

        logger.info("Итого скачано файлов: %d", len(downloaded))
        return downloaded

    except imaplib.IMAP4.error as e:
        logger.error("Ошибка аутентификации IMAP: %s", e)
        return []
    except Exception as e:
        logger.error("Ошибка при работе с Gmail: %s", e)
        return []
    finally:
        try:
            mail.logout()
        except Exception:
            pass