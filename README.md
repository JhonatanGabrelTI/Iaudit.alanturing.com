# IAudit — Sistema de Automação Fiscal

> Plataforma SaaS para monitoramento automático de débitos fiscais e certidões negativas, integrando APIs governamentais brasileiras (Receita Federal, SEFAZ PR, CAIXA FGTS).

**Domínio:** `iaudit.allanturing.com`

---

## 🏗️ Arquitetura

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Streamlit UI   │────▶│   FastAPI + APSch │────▶│    Supabase      │
│   (port 8501)    │     │   (port 8000)     │     │   PostgreSQL     │
└──────────────────┘     └────────┬─────────┘     └──────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              InfoSimples    Google Drive    Resend/SMTP
              (CND/FGTS)     (PDFs)         (Alertas)
```

- **Backend:** Python FastAPI + APScheduler (substituição completa do N8N)
- **Frontend:** Streamlit (dashboard interativo)
- **Banco:** Supabase PostgreSQL com RLS
- **Storage:** Google Drive API (PDFs)
- **Deploy:** Docker / Google Cloud Run

---

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.11+
- Docker & Docker Compose (opcional)
- Conta Supabase com as tabelas criadas
- Token InfoSimples
- Service Account Google Cloud (para Drive)

### 1. Setup do Banco de Dados

Execute o SQL em `sql/schema.sql` no SQL Editor do Supabase para criar todas as tabelas, índices, RLS e funções.

### 2. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
# Edite .env com suas credenciais:
# - SUPABASE_URL e SUPABASE_KEY
# - INFOSIMPLES_TOKEN
# - GOOGLE_DRIVE_CREDENTIALS_PATH
# - RESEND_API_KEY ou SMTP_*
```

### 3. Rodar com Docker Compose

```bash
docker-compose up --build
```

Acesse:
- **Dashboard:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs

### 4. Deploy com Portainer

1. Crie uma nova **Stack** no Portainer.
2. Copie o conteúdo do arquivo `portainer-stack.yml`.
3. Defina as variáveis de ambiente no Portainer (ex: `SUPABASE_URL`, `SUPABASE_KEY`).
4. **Para mudar o domínio:** Adicione a variável `DOMAIN_NAME` com o valor desejado (ex: `meusite.com`).

### 5. Rodar Localmente (dev)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (em outro terminal)
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

---

## 📋 Funcionalidades

### Fluxo 1: Cadastro de Empresas
- Upload CSV/Excel com validação de CNPJ (dígitos verificadores)
- Cadastro individual via formulário
- Agendamento automático de consultas

### Fluxo 2: Execução Automática de Consultas
- APScheduler polla a cada 5 minutos por consultas pendentes
- Agendador diário cria novas consultas baseado na periodicidade
- Rate limiting: 3s entre requisições InfoSimples
- Retry automático: 3 tentativas com 5min de intervalo
- Download e upload automático de PDFs para Google Drive

### Fluxo 3: Dashboard e Alertas
- KPIs em tempo real (empresas, consultas, alertas, taxa de sucesso)
- Gráfico de consultas por dia (7 dias)
- Alertas automáticos quando CND negativa ou FGTS irregular
- Notificações por email (Resend ou SMTP)

---

## 🔌 APIs Integradas

| API | Endpoint | Tipo |
|-----|----------|------|
| CND Federal | `/api/v2/consultas/receita-federal/pgfn/nova` | POST |
| CND Paraná | `/api/v2/consultas/sefaz/pr/certidao-debitos` | POST |
| FGTS Regularidade | `/api/v2/consultas/caixa/regularidade` | POST |

---

## 🗂 Estrutura de Pastas

```
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI + APScheduler
│   │   ├── config.py         # Settings (env vars)
│   │   ├── database.py       # Supabase client
│   │   ├── models.py         # Pydantic schemas
│   │   ├── routes/           # API endpoints
│   │   └── services/         # Business logic
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app.py                # Streamlit main
│   ├── pages/                # Dashboard, Empresas, Upload, Detalhes
│   ├── components/           # Charts
│   ├── Dockerfile
│   └── requirements.txt
├── sql/schema.sql
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## ☁️ Deploy no Google Cloud Run

### 1. Build e Push das Imagens

```bash
# Backend
cd backend
gcloud builds submit --tag gcr.io/YOUR_PROJECT/iaudit-backend

# Frontend
cd frontend
gcloud builds submit --tag gcr.io/YOUR_PROJECT/iaudit-frontend
```

### 2. Deploy

```bash
# Backend
gcloud run deploy iaudit-backend \
  --image gcr.io/YOUR_PROJECT/iaudit-backend \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars "SUPABASE_URL=...,SUPABASE_KEY=...,INFOSIMPLES_TOKEN=..."

# Frontend
gcloud run deploy iaudit-frontend \
  --image gcr.io/YOUR_PROJECT/iaudit-frontend \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars "BACKEND_URL=https://iaudit-backend-xxx.run.app"
```

### 3. Domínio Customizado

```bash
gcloud run domain-mappings create \
  --service iaudit-frontend \
  --domain iaudit.allanturing.com \
  --region us-east1
```

---

## 🔐 Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|----------|-----------|:-----------:|
| `SUPABASE_URL` | URL do projeto Supabase | ✅ |
| `SUPABASE_KEY` | Service role key | ✅ |
| `INFOSIMPLES_TOKEN` | Token da API InfoSimples | ✅ |
| `GOOGLE_DRIVE_CREDENTIALS_PATH` | Caminho do JSON da service account | ⚠️ |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | ID da pasta raiz no Drive | ⚠️ |
| `RESEND_API_KEY` | API key do Resend | ⚠️ |
| `EMAIL_FROM` | Email remetente | ⚠️ |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Config SMTP | ⚠️ |

✅ = obrigatória | ⚠️ = recomendada (funcionalidade parcial sem)

---

## 📊 Modelo de Dados

### Tabela `empresas`
Cadastro de empresas monitoradas com configuração de periodicidade.

### Tabela `consultas`
Registro de cada consulta fiscal com status, resultado e PDF.

### Tabela `logs_execucao`
Log de execução detalhado para auditoria.

---

## 📄 Licença

Proprietary — IAudit © 2026
