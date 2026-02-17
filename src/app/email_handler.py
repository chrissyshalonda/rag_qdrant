import imaplib
import email
import os
import logging
from email.header import decode_header
from imaplib import AuthenticationError

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt'}

def download_attachments(user, password, folder_to_save, scope='ALL'):
    """
    scope: 'ALL' — скачать всё за всё время.
           'UNSEEN' — только новые (непрочитанные).
    """
    imaplib._MAXLINE = 10000000 

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    
    try:
        mail.login(user, password)
        mail.select("inbox")
        logger.info(f"Начинаю поиск писем с фильтром: {scope}")
        status, messages = mail.search(None, scope)
        
        if status != "OK" or not messages[0]:
            logger.info("Писем не найдено.")
            return []

        downloaded_files = []
        msg_ids = messages[0].split()
        logger.info(f"Найдено писем для обработки: {len(msg_ids)}")

        for num in msg_ids:
            res, msg_data = mail.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    for part in msg.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue
                        if part.get("Content-Disposition") is None:
                            continue

                        filename = part.get_filename()
                        if filename:
                            decode_file = decode_header(filename)[0]
                            if isinstance(decode_file[0], bytes):
                                filename = decode_file[0].decode(decode_file[1] or 'utf-8')

                            ext = os.path.splitext(filename)[1].lower()
                            if ext not in ALLOWED_EXTENSIONS:
                                continue

                            filepath = os.path.join(folder_to_save, filename)

                            with open(filepath, "wb") as f:
                                f.write(part.get_payload(decode=True))
                            
                            downloaded_files.append(filepath)
                            logger.info(f"Файл сохранен: {filename}")
        
        logger.info(f"Всего скачано файлов: {len(downloaded_files)}")
        return downloaded_files
    except AuthenticationError as er:
        logger.error(f"Ошибка при ауентификации: {er}")
    except Exception as e:
        logger.error(f"Ошибка при работе с Gmail: {e}")
        return []
    finally:
        try:
            mail.logout()
        except:
            pass