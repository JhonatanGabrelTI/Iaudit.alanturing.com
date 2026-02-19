"""IAudit - Recurring Billing Service."""

import logging
from datetime import datetime, timezone, timedelta, date
from app.database import (
    get_billing_plans, 
    update_billing_plan, 
    create_log,
    get_empresas_ativas
)
from app.services.bradesco import bradesco_service

logger = logging.getLogger(__name__)

class BillingService:
    async def process_recurring_billing(self):
        """
        Job to process recurring billing plans.
        Generates boletos X days before due date.
        """
        logger.info("=== Job: Process Recurring Billing ===")
        
        # Settings
        DAYS_IN_ADVANCE = 10 
        
        plans = get_billing_plans()
        if not plans:
            logger.info("No active billing plans found.")
            return

        today = datetime.now(timezone.utc).date()
        
        count_generated = 0
        
        for plan in plans:
            try:
                empresa_id = plan.get("empresa_id")
                dia_vencimento = plan.get("dia_vencimento", 10)
                valor = plan.get("valor", 0)
                last_processed = plan.get("ultimo_processamento")
                
                # Check if already processed this month
                if last_processed:
                    last_date = datetime.fromisoformat(last_processed).date()
                    if last_date.month == today.month and last_date.year == today.year:
                        continue # Already processed for this month

                # Calculate Next Due Date
                # If today is > due day, move to next month? 
                # Logic: We generate for the current month if not passed, or next month.
                # Standard: Generate for "This Month" if (Due Date - DAYS_IN_ADVANCE) <= Today
                
                # Let's construct the "Target Due Date" for this month
                try:
                    target_due_date = date(today.year, today.month, dia_vencimento)
                except ValueError: 
                    # Handle short months (e.g. Feb 30 -> Feb 28/29)
                    # Simplified: just skip or clamp to last day.
                    # Proper way: max day of month
                    continue
                
                # If target due date is in the past, maybe we missed it or it's for next month?
                # If we haven't processed it yet, and it's passed, should we generate? 
                # Maybe safest is: always aim for "Upcoming" due date.
                
                if target_due_date < today:
                    # Move to next month
                    month = today.month + 1
                    year = today.year
                    if month > 12:
                        month = 1
                        year += 1
                    target_due_date = date(year, month, dia_vencimento)
                
                # Check generation window
                generation_date = target_due_date - timedelta(days=DAYS_IN_ADVANCE)
                
                if today >= generation_date:
                    # Time to generate!
                    logger.info(f"Generating billing for Plan {plan['id']} (Empresa: {empresa_id}) - Due: {target_due_date}")
                    
                    # 1. Fetch Company Data (Mocking join or need a get_empresa)
                    # For demo, we might need enterprise data for the boleto payload
                    # We can use database.get_empresa_by_id if we import it, or pass dummy data that BradescoService accepts?
                    # BradescoService needs pagador info.
                    
                    # We need to fetch the company details to fill Key Boleto Data
                    from app.database import get_empresa_by_id
                    empresa = get_empresa_by_id(empresa_id)
                    
                    if not empresa:
                        logger.error(f"Empresa {empresa_id} not found for plan {plan['id']}")
                        continue
                        
                    # Prepare Boleto Payload
                    # Using empresa data as "Pagador" (assuming B2B billing) or "Beneficiary"? 
                    # Usually "Empresa" in our DB is the Client who PAYS the boleto (Sacado).
                    
                    # Generate a unique invoice number
                    nu_fatura = f"FAT-{today.strftime('%Y%m')}-{plan['id'][:8]}"
                    
                    boleto_data = {
                        "nuFatura": nu_fatura,
                        "vlNominal": int(valor * 100), # Cents
                        "dataVencimento": target_due_date.strftime("%Y-%m-%d"),
                        "pagador_nome": empresa.get("razao_social"),
                        "pagador_documento": empresa.get("cnpj"),
                        "pagador_endereco": "Endereco Cadastrado", # Should extend empresa model
                        "pagador_cep": "00000000",
                        "pagador_uf": "PR",
                        "pagador_cidade": "Curitiba",
                        "pagador_bairro": "Centro"
                    }
                    
                    # 2. Call Bradesco Service
                    resp = await bradesco_service.register_boleto(
                        boleto_data, 
                        recipient_email=empresa.get("email_notificacao"),
                        recipient_phone=empresa.get("whatsapp")
                    )
                    
                    # 3. Log & Update Plan
                    if resp.get("cdErro", 0) == 0:
                        count_generated += 1
                        update_billing_plan(plan["id"], {
                            "ultimo_processamento": datetime.now(timezone.utc).isoformat()
                        })
                        create_log(
                            consulta_id="SYSTEM_BILLING", 
                            nivel="INFO", 
                            mensagem=f"Boleto gerado para {empresa.get('razao_social')}",
                            payload=resp
                        )
                    else:
                        logger.error(f"Failed to generate boleto for plan {plan['id']}: {resp}")
                        
            except Exception as e:
                logger.error(f"Error processing plan {plan.get('id')}: {e}")

        logger.info(f"Billing Job Complete. Generated {count_generated} boletos.")

billing_service = BillingService()
