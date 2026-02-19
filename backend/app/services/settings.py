import json
import os
from typing import Dict, Any

SETTINGS_FILE = "backend/data/settings.json"

DEFAULT_SETTINGS = {
    "robo_ativo": True,
    "mensagens_ativas": True,
    "notificar_erro": True,
    "notificar_sucesso": False,
    "whatsapp_provider": "Evolution API",
    "gmail_method": "SMTP Fallback",
    "template_wa_cobranca": "iAudit: Seu boleto vence em {vencimento}. Valor: R$ {valor}. Linha: {linha}",
    "template_wa_atraso": "iAudit: Constatamos que seu boleto venceu em {vencimento}. Regularize para evitar protesto.",
    "template_wa_alerta": "🚨 IAudit Alerta: Empresa {empresa} possui pendência {tipo}. Situação: {situacao}.",
}

class DynamicSettingsService:
    def __init__(self):
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        if not os.path.exists(SETTINGS_FILE):
            self._write_settings(DEFAULT_SETTINGS)

    def _read_settings(self) -> Dict[str, Any]:
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Merge with defaults for missing keys
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            return DEFAULT_SETTINGS

    def _write_settings(self, settings: Dict[str, Any]):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

    def get_settings(self) -> Dict[str, Any]:
        return self._read_settings()

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        current = self._read_settings()
        updated = {**current, **new_settings}
        self._write_settings(updated)
        return updated

    def is_robo_ativo(self) -> bool:
        return self._read_settings().get("robo_ativo", True)

dynamic_settings = DynamicSettingsService()
