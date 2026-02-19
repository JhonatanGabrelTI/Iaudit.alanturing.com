"""IAudit - Boleto Monitoring Service."""

import logging
import asyncio
from datetime import datetime, timezone, date
from app.config import settings
from app.database import (
    get_boletos_ativos, # Need to implement this in database.py
    update_boleto_status, # Need to implement this in database.py
    create_log
)
from app.services.bradesco import bradesco_service
from app.services.notifications import send_boleto_notification

logger = logging.getLogger(__name__)

async def monitor_boletos():
    """
    Periodic job to check status of active boletos.
    Active boletos are those with status 'emitido' or 'atraso'.
    """
    logger.info("=== Job: Monitor Boletos ===")
    
    # This function needs to be added to database.py
    # For now, let's assume we can fetch them.
    # We might need to execute a raw query if not available.
    try:
        boletos = get_boletos_ativos() 
    except NameError:
        logger.warning("get_boletos_ativos not implemented yet.")
        return

    logger.info(f"Checking status for {len(boletos)} boletos.")

    for boleto in boletos:
        # Avoid rate limits
        await asyncio.sleep(0.5)
        
        boleto_id = boleto["id"]
        nosso_numero = boleto.get("nosso_numero")
        current_status = boleto.get("status")
        vencimento = boleto.get("data_vencimento") # date object or string
        
        if not nosso_numero:
            continue

        try:
            # 1. Consult Bradesco
            new_status_code, bradesco_data = await bradesco_service.consult_status(nosso_numero)
            
            # 2. Status Transition Logic
            
            # Case A: Payment Confirmed
            if new_status_code == "pago" and current_status != "pago":
                logger.info(f"Boleto {boleto_id} paid.")
                update_boleto_status(boleto_id, "pago", bradesco_data)
                
                # Trigger Notification
                await send_boleto_notification(
                    "pago", 
                    {
                        "nomeSacado": boleto.get("pagador_nome"),
                        "valorNominal": boleto.get("vl_nominal"),
                        "dataVencimento": vencimento,
                        "linkBoleto": "", # No link needed for receipt usually
                    },
                    boleto.get("email_notificacao"), # Need to join with empresa data
                    boleto.get("whatsapp")
                )
                continue

            # Case B: Overdue Detection (Local check + Status)
            # If Bradesco says "emitido" (01) but date > vencimento
            if new_status_code == "emitido":
                if isinstance(vencimento, str):
                    venc_date = datetime.strptime(vencimento, "%Y-%m-%d").date()
                else:
                    venc_date = vencimento
                
                today = datetime.now(timezone.utc).date()
                
                if today > venc_date and current_status != "atraso":
                    logger.info(f"Boleto {boleto_id} is overdue.")
                    update_boleto_status(boleto_id, "atraso", bradesco_data)
                    
                    # Trigger Notification
                    await send_boleto_notification(
                        "atraso", 
                        {
                            "nomeSacado": boleto.get("pagador_nome"),
                            "valorNominal": boleto.get("vl_nominal"),
                            "dataVencimento": vencimento,
                            "linkBoleto": f"{settings.api_host}/api/boleto/pdf/{boleto.get('nosso_numero')}",
                            "linhaDigitavel": boleto.get("linha_digitavel")
                        },
                        boleto.get("email_notificacao"),
                        boleto.get("whatsapp")
                    )

            # Case C: Baixado/Devolvido
            if new_status_code == "baixado" and current_status != "baixado":
                 update_boleto_status(boleto_id, "baixado", bradesco_data)

        except Exception as e:
            logger.error(f"Failed to monitor boleto {boleto_id}: {e}")
