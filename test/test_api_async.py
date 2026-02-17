import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE_URL = "http://localhost:8000"

# 5 базовых вопросов для теста
QUESTIONS = [
    "What is the capital of France?",
    "Who wrote Romeo and Juliet?",
    "What is 2 + 2?",
    "What is the largest planet in our solar system?",
    "In which year did World War II end?",
]


def ask_one(question: str) -> tuple[str, str]:
    """Один запрос к /ask. Возвращает (вопрос, ответ)."""
    response = requests.post(f"{BASE_URL}/ask", json={"question": question})
    response.raise_for_status()
    data = response.json()
    return question, data.get("answer", "")


def run_async(questions: list[str] | None = None) -> None:
    """Выполняет запросы параллельно и выводит ответы по мере готовности."""
    qs = questions or QUESTIONS
    with ThreadPoolExecutor(max_workers=len(qs)) as executor:
        futures = {executor.submit(ask_one, q): q for q in qs}
        for future in as_completed(futures):
            question, answer = future.result()
            print(f"Вопрос: {question}\nОтвет: {answer}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        custom = [" ".join(sys.argv[1:])]
        run_async(custom)
    else:
        run_async()
