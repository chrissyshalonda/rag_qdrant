import logging
import sys
from typing import Callable

from src.config.config import Settings
from src.app.core.rag_chain import create_rag_chain

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run_cli(answer_fn: Callable[[str], str]) -> None:
    """
    Простой CLI-интерфейс для общения с моделью.
    """
    logger.info("RAG-ассистент запущен.")
    logger.info("Введите ваш вопрос и нажмите Enter.")
    logger.info("Для выхода введите 'exit', 'quit' или 'выход'.\n")

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.info("\nЗавершение работы.")
            break

        if not query:
            continue

        if query.lower() in {"exit", "quit", "выход"}:
            logger.info("Завершение работы.   ")
            break

        logger.info(f"Отправка запроса: {query}")
        try:
            result = answer_fn(query)
            logger.info(f"\n--- ОТВЕТ ---\n{result}\n")
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса: {e}", exc_info=True)


def main() -> None:
    try:
        settings = Settings()
        answer_fn = create_rag_chain(settings)
        
        run_cli(answer_fn)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    main()