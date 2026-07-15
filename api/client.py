import requests

BACKEND_URL = "http://127.0.0.1:8001"


def post_pricing(treaty_data: dict) -> dict:
    response = requests.post(f"{BACKEND_URL}/api/pricing/calculate", json=treaty_data)
    response.raise_for_status()
    return response.json()


def post_market_signal(query_data: dict) -> dict:
    response = requests.post(f"{BACKEND_URL}/api/market/signal", json=query_data)
    response.raise_for_status()
    return response.json()


def post_ai_insight(query_data: dict) -> dict:
    response = requests.post(f"{BACKEND_URL}/api/ai/insight", json=query_data)
    response.raise_for_status()
    return response.json()
