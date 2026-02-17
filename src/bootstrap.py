import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app.email_handler import download_attachments
from src.scripts.init_db import ingest_docs
from src.scripts.ingest_config import IngestSettings

logging.basicConfig(level=logging.INFO)

def run():
    settings = IngestSettings()

    download_attachments(
        user=os.getenv("EMAIL_USER"),
        password=os.getenv("EMAIL_PASSWORD"),
        folder_to_save=settings.data_path,
        scope='ALL'
    )
    

    ingest_docs(settings)

if __name__ == "__main__":
    run()