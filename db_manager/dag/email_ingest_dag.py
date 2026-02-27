from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _fetch_emails():
    # Note: email_handler remains in the main app src as it might be used there too?
    # Or should we move the logic? Let's keep it in src for now and import relatively or through env.
    # Actually, the user wants db_manager to be independent.
    # I'll keep the import as is for now, but will likely need to adjust if db_manager is a separate project.
    from app.email_handler import download_attachments

    files = download_attachments(
        user=os.getenv("EMAIL_USER"),
        password=os.getenv("EMAIL_PASSWORD"),
        folder_to_save=os.getenv("FOLDER"),
        scope="UNSEEN",  # только новые письма
    )
    print(f"Скачано вложений: {len(files)}")


def _ingest_to_vdb():
    from scripts.init_db import ingest_docs
    from scripts.ingest_config import IngestSettings

    ingest_docs(IngestSettings(data_path=os.getenv("FOLDER")))


with DAG(
    "company_docs_ingest",
    default_args=default_args,
    description="Загрузка вложений из корпоративной почты и обновление базы знаний",
    schedule="@hourly",
    catchup=False,
) as dag:

    task_download = PythonOperator(
        task_id="download_email_attachments",
        python_callable=_fetch_emails,
    )

    task_ingest = PythonOperator(
        task_id="ingest_to_vector_db",
        python_callable=_ingest_to_vdb,
    )

    task_download >> task_ingest
