# import sys
# import requests

# BASE_URL = "http://localhost:8000"


# def ask(question: str) -> None:
#     """Отправляет один вопрос к API и выводит ответ с источниками."""
#     response = requests.post(f"{BASE_URL}/ask", json={"question": question})
#     response.raise_for_status()

#     data = response.json()
#     print(f"Вопрос: {question}")
#     print(f"Ответ:  {data.get('answer')}")
#     sources = data.get("sources", [])
#     if sources:
#         print("Источники:")
#         for s in sources:
#             print(f"  • {s}")
#     quality = data.get("retrieval_quality") or {}
#     print(
#         f"Retrieval: best_score={quality.get('best_score')}, "
#         f"low_confidence={quality.get('low_confidence')}"
#     )


# if __name__ == "__main__":
#     q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Какова политика отпусков в компании?"
#     ask(q)
