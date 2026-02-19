"""IAudit - Pydantic models / schemas."""

from __future__ import annotations

from datetime import datetime, date, time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ─── Enums ───────────────────────────────────────────────────────────

class Periodicidade(str, Enum):
    diario = "diario"
    semanal = "semanal"
    quinzenal = "quinzenal"
    mensal = "mensal"


class TipoConsulta(str, Enum):
    cnd_federal = "cnd_federal"
    cnd_pr = "cnd_pr"
    fgts_regularidade = "fgts_regularidade"


class StatusConsulta(str, Enum):
    agendada = "agendada"
    processando = "processando"
    concluida = "concluida"
    erro = "erro"


class Situacao(str, Enum):
    positiva = "positiva"
    negativa = "negativa"
    regular = "regular"
    irregular = "irregular"
    erro = "erro"


class StatusBoleto(str, Enum):
    emitido = "emitido"
    pago = "pago"
    vencido = "vencido"
    baixado = "baixado"
    erro = "erro"


class CommunicationChannel(str, Enum):
    email = "email"
    whatsapp = "whatsapp"


class CommunicationStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


# ─── Empresa ─────────────────────────────────────────────────────────

class EmpresaCreate(BaseModel):
    cnpj: str
    razao_social: str
    inscricao_estadual_pr: str | None = None
    email_notificacao: str | None = None
    whatsapp: str | None = None
    periodicidade: Periodicidade = Periodicidade.mensal
    dia_semana: int | None = Field(None, ge=0, le=6)
    dia_mes: int | None = Field(None, ge=1, le=31)
    horario: str = "08:00:00"
    ativo: bool = True

    @field_validator("cnpj", mode="before")
    @classmethod
    def strip_cnpj(cls, v: str) -> str:
        import re
        return re.sub(r"\D", "", v)


class EmpresaUpdate(BaseModel):
    razao_social: str | None = None
    inscricao_estadual_pr: str | None = None
    email_notificacao: str | None = None
    whatsapp: str | None = None
    periodicidade: Periodicidade | None = None
    dia_semana: int | None = Field(None, ge=0, le=6)
    dia_mes: int | None = Field(None, ge=1, le=31)
    horario: str | None = None
    ativo: bool | None = None


class EmpresaResponse(BaseModel):
    id: str
    cnpj: str
    razao_social: str
    inscricao_estadual_pr: str | None = None
    email_notificacao: str | None = None
    whatsapp: str | None = None
    periodicidade: str
    dia_semana: int | None = None
    dia_mes: int | None = None
    horario: str
    ativo: bool
    created_at: str | None = None
    updated_at: str | None = None


# ─── Consulta ────────────────────────────────────────────────────────

class ConsultaResponse(BaseModel):
    id: str
    empresa_id: str
    tipo: str
    status: str
    situacao: str | None = None
    resultado_json: dict[str, Any] | None = None
    pdf_url: str | None = None
    mensagem_erro: str | None = None
    data_agendada: str
    data_execucao: str | None = None
    data_validade: str | None = None
    tentativas: int = 0
    created_at: str | None = None
    empresas: dict | None = None  # joined data


# ─── Dashboard ───────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_empresas: int = 0
    empresas_ativas: int = 0
    consultas_hoje: int = 0
    alertas_ativos: int = 0
    taxa_sucesso: float = 0.0


class ChartData(BaseModel):
    data: str
    total: int
    sucessos: int
    erros: int


class AlertItem(BaseModel):
    consulta_id: str
    cnpj: str
    razao_social: str
    tipo: str
    situacao: str
    data_execucao: str | None = None


class UpcomingItem(BaseModel):
    consulta_id: str
    cnpj: str
    razao_social: str
    tipo: str
    data_agendada: str


# ─── Upload ──────────────────────────────────────────────────────────

class UploadResult(BaseModel):
    total: int = 0
    criadas: int = 0
    duplicadas: int = 0
    invalidas: int = 0
    erros: list[str] = Field(default_factory=list)


class ForceQueryRequest(BaseModel):
    tipos: list[TipoConsulta] = Field(
        default_factory=lambda: [
            TipoConsulta.cnd_federal,
            TipoConsulta.cnd_pr,
        ]
    )


# ─── Cobrança Bradesco ──────────────────────────────────────────────

class BoletoCreate(BaseModel):
    empresa_id: str
    nuFatura: str
    vlNominal: int  # em centavos
    dataVencimento: date
    pagador_nome: str
    pagador_documento: str
    pagador_endereco: str
    pagador_cep: str
    pagador_uf: str
    pagador_cidade: str
    pagador_bairro: str


class BoletoResponse(BaseModel):
    id: str
    nossoNumero: str | None = None
    linhaDigitavel: str | None = None
    codigoBarras: str | None = None
    status: StatusBoleto
    vlNominal: int
    dataVencimento: date
    pdf_url: str | None = None
    created_at: datetime


# ─── Comunicação ──────────────────────────────────────────────────

class CommunicationLog(BaseModel):
    id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    channel: CommunicationChannel
    recipient: str
    subject: str | None = None
    content: str
    status: CommunicationStatus = CommunicationStatus.pending
    error_message: str | None = None
    metadata: dict[str, Any] | None = None
