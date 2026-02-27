import requests

BASE_URL = "http://localhost:8000"


def test_health():
    response = requests.get(f"{BASE_URL}/health")
    response.raise_for_status()
    data = response.json()
    assert data.get("status") == "ok", f"Неожиданный статус: {data}"
    print("✓ /health:", data)


def test_root():
    response = requests.get(f"{BASE_URL}/")
    response.raise_for_status()
    data = response.json()
    assert "name" in data, f"Поле 'name' отсутствует: {data}"
    assert "version" in data, f"Поле 'version' отсутствует: {data}"
    print("✓ /:", data)


if __name__ == "__main__":
    test_health()
    test_root()
    print("\nВсе проверки пройдены.")
