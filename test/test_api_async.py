import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE_URL = "http://localhost:8000"

# Тестовые вопросы для корпоративного ассистента
QUESTIONS = [
    "Какова политика удалённой работы в компании?",
    "Как согласовать отпуск?",
    "Какие льготы предусмотрены для сотрудников?",
    "Каков порядок выплаты премий?",
    "Как организован процесс онбординга?",
]


def ask_one(question: str) -> tuple[str, str, list]:
    """Один запрос к /ask. Возвращает (вопрос, ответ, источники)."""
    response = requests.post(f"{BASE_URL}/ask", json={"question": question})
    response.raise_for_status()
    data = response.json()
    return question, data.get("answer", ""), data.get("sources", [])


def run_async(questions: list[str] | None = None) -> None:
    """Выполняет запросы параллельно и выводит ответы по мере готовности."""
    qs = questions or QUESTIONS
    with ThreadPoolExecutor(max_workers=len(qs)) as executor:
        futures = {executor.submit(ask_one, q): q for q in qs}
        for future in as_completed(futures):
            question, answer, sources = future.result()
            print(f"Вопрос: {question}")
            print(f"Ответ:  {answer}")
            if sources:
                print("Источники: " + ", ".join(sources))
            print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_async([" ".join(sys.argv[1:])])
    else:
        run_async()
