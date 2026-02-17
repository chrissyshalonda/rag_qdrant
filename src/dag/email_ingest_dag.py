from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def fetch_emails_step():
    from src.app.email_handler import download_attachments

    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    folder = os.getenv("FOLDER")

    files = download_attachments(user, password, folder, scope='UNSEEN')
    print(f"Скачано файлов: {len(files)}")

def ingest_to_vdb_step():
    from src.scripts.init_db import ingest_docs
    from src.scripts.ingest_config import IngestSettings

    settings = IngestSettings(data_path=os.getenv("FOLDER"))
    ingest_docs(settings)

with DAG(
    'gmail_to_rag_pipeline',
    default_args=default_args,
    description='Download attachments and update RAG vector store',
    schedule='@daily',
    catchup=False,
) as dag:

    task_download = PythonOperator(
        task_id='download_emails',
        python_callable=fetch_emails_step,
    )

    task_ingest = PythonOperator(
        task_id='ingest_to_vdb',
        python_callable=ingest_to_vdb_step,
    )

    task_download >> task_ingest