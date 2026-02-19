import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "history.json")

def load_history():
    """Charge history from local JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {e}")
        return []

def save_to_history(data: dict):
    """Save a search result to the history file, maintaining only the last 20 uniq searches."""
    history = load_history()
    cnpj = data.get("cnpj")
    
    # Remove if already exists to move to top
    history = [item for item in history if item.get("cnpj") != cnpj]
    
    # Add new item at the beginning
    history.insert(0, {
        "cnpj": cnpj,
        "razao_social": data.get("razao_social", "Nome não disponível"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data": data
    })
    
    # Keep only last 20
    history = history[:20]
    
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar histórico: {e}")
