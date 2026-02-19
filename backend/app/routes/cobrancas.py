from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from app.models import BoletoCreate, BoletoResponse, StatusBoleto
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
