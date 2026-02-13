import sys

import requests


BASE_URL = "http://localhost:8000"


def ask(question: str) -> None:
    """
    Простой тестовый запрос к API.
    """
    response = requests.post(f"{BASE_URL}/ask", json={"question": question})
    response.raise_for_status()

    data = response.json()
    answer = data.get("answer")
    print(f"Вопрос: {question}\n\nОтвет: {answer}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "What is the capital of France?"
    ask(q)

