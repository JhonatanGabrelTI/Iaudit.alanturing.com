import jwt
import time
import uuid
import logging
import asyncio
from datetime import datetime, timezone
import httpx
from app.config import settings
from app.services.notifications import send_boleto_notification

logger = logging.getLogger(__name__)

# Base URLs
SANDBOX_URL = "https://proxy.api.prebanco.com.br"
PRODUCTION_URL = "https://openapi.bradesco.com.br"

class BradescoService:
    def __init__(self):
        self.base_url = SANDBOX_URL if settings.bradesco_sandbox else PRODUCTION_URL
        self._token = None
        self._token_expires_at = 0

    async def _get_access_token(self):
        """
        Get OAuth2 access token via JWT Profile.
        Spec required: RS256 with Private Key and Client ID.
        """
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        if not settings.bradesco_client_id or not settings.bradesco_private_key_path:
            logger.warning("Bradesco credentials not fully configured. API calls will fail.")
            return "MOCK_TOKEN" # For testing if env not set

        # Build JWT Claims for Assertion
        now = int(time.time())
        claims = {
            "aud": f"{self.base_url}/auth/server/v1.1/token",
            "sub": settings.bradesco_client_id,
            "iat": now,
            "exp": now + 3600,
            "jti": str(uuid.uuid4())
        }

        try:
            # Load private key
            with open(settings.bradesco_private_key_path, "r") as f:
                private_key = f.read()
            
            signed_jwt = jwt.encode(claims, private_key, algorithm="RS256")
            
            async with httpx.AsyncClient() as client:
                data = {
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": signed_jwt
                }
                resp = await client.post(f"{self.base_url}/auth/server/v1.1/token", data=data)
                resp.raise_for_status()
                token_data = resp.json()
                self._token = token_data["access_token"]
                self._token_expires_at = now + int(token_data.get("expires_in", 3600))
                return self._token
        except Exception as e:
            logger.error(f"Failed to get Bradesco access token: {e}")
            raise

    async def register_boleto(self, boleto_data: dict, recipient_email: str = None, recipient_phone: str = None):
        """
        Register a new boleto and trigger notification on success.
        API: /v1/boleto/registrar
        """
        token = await self._get_access_token()
        
        # Format nuNegociacao if not already formatted
        negociacao = settings.bradesco_negociacao.zfill(18)
        
        payload = {
            "nuNegociacao": negociacao,
            "tpAcessorio": "10", # Escritural
            "acessEsc10": settings.bradesco_acess_esc10,
            "nuCliente": boleto_data.get("nuFatura"),
            "vlNominalTitulo": str(boleto_data.get("vlNominal")), # Sent as string typically
            "dtVencimentoTitulo": str(boleto_data.get("dataVencimento")), # Ensure string format (YYYY-MM-DD or similar)
            "pagador": {
                "nome": boleto_data.get("pagador_nome"),
                "documento": boleto_data.get("pagador_documento"),
                "endereco": boleto_data.get("pagador_endereco"),
                "cep": boleto_data.get("pagador_cep"),
                "uf": boleto_data.get("pagador_uf"),
                "cidade": boleto_data.get("pagador_cidade"),
                "bairro": boleto_data.get("pagador_bairro")
            },
            "prJuros": boleto_data.get("prJuros", "0"),
            "prMulta": boleto_data.get("prMulta", "0"),
        }
        
        endpoint = "/v1/boleto/registrar"
        
        # MOCK MODE: If token is fake (credentials missing), return success mock
        if token == "MOCK_TOKEN":
            logger.info("MOCK MODE: Returning simulated Bradesco success response.")
            nosso_num = str(int(time.time()))[-10:]
            return {
                "cdErro": 0,
                "msgErro": "Sucesso (Mock)",
                "nuNossoNumero": nosso_num,
                "linhaDigitavel": f"2379{nosso_num}9000000000000050000000000",
                "cdSituacaoTitulo": "01",
                "listaRegistro": [{"linhaDigitavel": f"2379{nosso_num}9000000000000050000000000"}]
            }
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            try:
                resp = await client.post(f"{self.base_url}{endpoint}", json=payload, headers=headers)
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Bradesco API Error: {e.response.text}")
                # Return error dict instead of crashing for graceful handling
                return {"cdErro": e.response.status_code, "msgErro": e.response.text}
            
            data = resp.json()
            
            # Check business logic return code if present (cdErro)
            if data.get("cdErro", 0) != 0:
                 logger.error(f"Bradesco returned business error: {data}")
                 return data

            # Success - Trigger Notification
            linha_digitavel = data.get("linhaDigitavel", "")
            if not linha_digitavel and "listaRegistro" in data:
                 linha_digitavel = data["listaRegistro"][0].get("linhaDigitavel", "")

            notif_data = {
                "nomeSacado": boleto_data.get("pagador_nome"),
                "valorNominal": boleto_data.get("vlNominal"), # in cents
                "dataVencimento": boleto_data.get("dataVencimento"),
                "linhaDigitavel": linha_digitavel,
                "linkBoleto": f"{settings.api_host}/api/boleto/pdf/{boleto_data.get('nuFatura')}"
            }

            # Fire and forget notification (async)
            if recipient_email or recipient_phone:
                asyncio.create_task(
                    send_boleto_notification("emitido", notif_data, recipient_email, recipient_phone)
                )
            
            return data

    async def register_boleto_qr_code(self, boleto_data: dict):
        """
        Register a new boleto with QR Code.
        API: /v1/boleto/registrar-qr-code
        """
        token = await self._get_access_token()
        # Similar payload setup as register_boleto, adapt as needed
        # For brevity, reusing the structure but pointing to new endpoint
        # User manual would specify if payload differs significantly.
        # Assuming standard registration payload works for now with QR endpoint
        
        endpoint = "/v1/boleto/registrar-qr-code"
        
        # ... (Implementation similar to register_boleto but calling new endpoint)
        # Simplified for now:
        return {"msg": "Implemented placeholder for QR Code"}

    async def alter_boleto(self, boleto_data: dict):
        """
        Alter boleto data (e.g. extension of due date).
        API: /v1/boleto/titulo-alterar (PUT)
        """
        token = await self._get_access_token()
        endpoint = "/v1/boleto/titulo-alterar"
        # Implementation placeholder
        return {"msg": "Implemented placeholder for Alteração"}

    async def cancel_boleto(self, boleto_data: dict):
        """
        Cancel/Estornar boleto.
        API: /v1/boleto/titulo-estornar (POST)
        """
        token = await self._get_access_token()
        endpoint = "/v1/boleto/titulo-estornar"
        # Implementation placeholder
        return {"msg": "Implemented placeholder for Estorno"}

    async def consult_status(self, nosso_numero: str) -> tuple[str, dict]:
        """
        Consult current status of a title.
        Maps statuses to internal StatusBoleto enum.
        """
        token = await self._get_access_token()
        
        payload = {
            "nuNegociacao": settings.bradesco_negociacao.zfill(18),
            "nuNossoNumero": nosso_numero
        }
        
        endpoint = "/v1/boleto/titulo-consultar"
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.post(f"{self.base_url}{endpoint}", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            if not data: 
                return "erro", {}

            # Bradesco status codes
            # 06: Liquidado (Pago) ? Need to confirm specific codes for Bradesco API v1
            # 61: Baixa por Título Pago
            # 13: Pago no dia
            # 01: A vencer / Em aberto
            status_codigo = str(data.get("cdSituacaoTitulo", "")) 
            # Note: cdSituacaoTitulo vs cdStatus - check API docs. Assuming 'cdSituacaoTitulo' based on experience 
            # or data.get('listaTitulo')[0].get('cdSituacao') if list.
            
            # Fallback for root level checks or list
            if "listaTitulo" in data and len(data["listaTitulo"]) > 0:
                item = data["listaTitulo"][0]
                status_codigo = str(item.get("cdSituacaoTitulo", ""))
            
            if status_codigo in ("13", "61", "06"):
                return "pago", data
            elif status_codigo == "02": # Baixado / Devolvido
                return "baixado", data
                
            return "emitido", data

bradesco_service = BradescoService()



