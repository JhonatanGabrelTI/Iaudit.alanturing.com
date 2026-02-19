import asyncio
import logging
from datetime import datetime, timezone, timedelta

# Mock environment
import sys
import os
sys.path.insert(0, os.getcwd())

from app.database import create_billing_plan, get_billing_plans, get_boletos_ativos, clear_all_empresas, create_empresa
from app.services.billing import billing_service

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_recurring_billing():
    print("--- Setting up Test Environment ---")
    
    # 1. Create Mock Company
    empresa = create_empresa({
        "cnpj": "99.999.999/0001-99",
        "razao_social": "Test Automation Ltd",
        "email_notificacao": "test@example.com",
        "whatsapp": "5511999999999"
    })
    print(f"Created Company: {empresa['id']}")
    
    # 2. Create Billing Plan (Due in 5 days, so inside 10 day window)
    today = datetime.now(timezone.utc)
    due_day = (today + timedelta(days=5)).day
    
    plan = create_billing_plan({
        "empresa_id": empresa['id'],
        "valor": 500.00,
        "dia_vencimento": due_day,
        "periodicidade": "mensal"
    })
    print(f"Created Plan: {plan['id']} (Due Day: {due_day})")
    
    # 3. Run Billing Job
    print("\n--- Running Billing Job ---")
    await billing_service.process_recurring_billing()
    
    # 4. Verify Results
    print("\n--- Verifying Results ---")
    plans = get_billing_plans(empresa['id'])
    updated_plan = plans[0]
    
    if updated_plan.get("ultimo_processamento"):
        print("✅ Plan verified: 'ultimo_processamento' updated.")
    else:
        print("❌ Plan verification failed: 'ultimo_processamento' not set.")
        
    # Check Boletos
    from app.database import DEMO_BOLETOS
    generated_boletos = [b for b in DEMO_BOLETOS if b.get("nuFatura", "").endswith(plan['id'][:8])]
    
    if generated_boletos:
        print(f"✅ Boleto generated: {generated_boletos[0]['nosso_numero']}")
    else:
        print("❌ Boleto verification failed: No boleto found.")

if __name__ == "__main__":
    asyncio.run(test_recurring_billing())
