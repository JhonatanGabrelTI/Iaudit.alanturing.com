from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from app.models import BoletoCreate, BoletoResponse, StatusBoleto
from pydantic import BaseModel

from app.services.bradesco import bradesco_service
# Notification logic moved to bradesco_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/registrar", response_model=dict)
async def registrar_boleto(data: BoletoCreate):
    """
    Registers a new boleto with Bradesco and stores the result.
    """
    try:
        # Extract recipient info
        email = getattr(data, 'pagador_email', None)
        phone = getattr(data, 'pagador_whatsapp', None) or getattr(data, 'pagador_celular', None)

        # 1. Call Bradesco API (Trigger notifications internally)
        resp = await bradesco_service.register_boleto(
            data.dict(), 
            recipient_email=email,
            recipient_phone=phone
        )
        
        # Check for business error from Bradesco Service
        if resp.get("cdErro", 0) != 0:
            raise HTTPException(status_code=400, detail=resp.get("msgErro", "Erro ao registrar boleto"))
        
        # 2. Extract key info
        nosso_numero = resp.get("nuNossoNumero")
        linha_digitavel = resp.get("linhaDigitavel")
        
        # 3. Notification already sent by service if vars provided
        
        return {
            "status": "sucesso",
            "nosso_numero": nosso_numero,
            "linha_digitavel": linha_digitavel,
            "bradesco_response": resp
        }
    except Exception as e:
        logger.error(f"Error registering boleto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/billing/run-now")
async def run_billing_now(background_tasks: BackgroundTasks):
    """
    Manually triggers the recurring billing job.
    """
    from app.services.billing import billing_service
    background_tasks.add_task(billing_service.process_recurring_billing)
    return {"message": "Billing job started in background"}

@router.get("/{nosso_numero}/status")
async def consultar_status(nosso_numero: str):
    """
    Checks the status of a specific boleto.
    """
    try:
        status, details = await bradesco_service.consult_status(nosso_numero)
        
        # Logic to update DB would go here
        
        return {
            "nosso_numero": nosso_numero,
            "status": status,
            "details": details
        }
    except Exception as e:
        logger.error(f"Error consulting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def bradesco_webhook(request: Request):
    """
    Endpoint for Bradesco to notify Pago/Erro events.
    """
    try:
        data = await request.json()
        logger.info(f"Webhook received: {data}")
        # Process webhook data
        # Identify title by nosso_numero or jti
        # Update state in database
        return {"status": "received"}
    except Exception:
        return {"status": "ignored"}

class NotificationRequest(BaseModel):
    nosso_numero: str
    empresa_nome: str
    valor: float
    vencimento: str
    linha_digitavel: str
    link_boleto: str
    whatsapp: str | None = None
    email: str | None = None
    event_type: str = "emitido" # emitido, pago, atraso

@router.post("/notify-manual")
async def notify_manual(data: NotificationRequest):
    """
    Manually triggers a WhatsApp/Email notification for a boleto.
    """
    try:
        from app.services.notifications import send_boleto_notification
        
        notif_data = {
            "nomeSacado": data.empresa_nome,
            "valorNominal": int(data.valor * 100), 
            "dataVencimento": data.vencimento,
            "linhaDigitavel": data.linha_digitavel,
            "linkBoleto": data.link_boleto
        }
        
        await send_boleto_notification(
            event=data.event_type, 
            data=notif_data, 
            recipient_email=data.email, 
            recipient_phone=data.whatsapp
        )
        
        return {"status": "sent", "message": f"Notificação ({data.event_type}) enviada para {data.whatsapp or data.email}"}
    except Exception as e:
        logger.error(f"Error sending manual notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_cobranca(cnpj: str):
    """
    Search for billing info by CNPJ.
    Returns company details and associated boletos.
    """
    from app.database import get_empresa_by_cnpj, get_boletos_by_empresa
    
    # 1. Find Company
    # Remove formatting if needed
    clean_cnpj = "".join(filter(str.isdigit, cnpj))
    # Try with formatting first (DB has formatted CNPJ usually)
    empresa = get_empresa_by_cnpj(cnpj)
    if not empresa and len(clean_cnpj) == 14:
         # Try formatting it: XX.XXX.XXX/0001-XX
         formatted = f"{clean_cnpj[:2]}.{clean_cnpj[2:5]}.{clean_cnpj[5:8]}/{clean_cnpj[8:12]}-{clean_cnpj[12:]}"
         empresa = get_empresa_by_cnpj(formatted)
    
    if not empresa:
        # Mock Response for Demo if no real match found but user insists (or if DB empty)
        # But let's try to return what we have.
        return {"found": False, "message": "Empresa não encontrada"}

    # 2. Get Boletos
    boletos = get_boletos_by_empresa(empresa["id"])
    
    return {
        "found": True,
        "empresa": {
            "id": empresa["id"],
            "razao_social": empresa["razao_social"],
            "whatsapp": empresa.get("whatsapp"),
            "email": empresa.get("email_notificacao")
        },
        "boletos": boletos
    }
