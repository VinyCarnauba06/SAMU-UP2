from backend.domain.entidades import (
    PRIORIDADE_BAIXA,
    PRIORIDADE_CRITICA,
    PRIORIDADE_MODERADA,
    STATUS_AMB_DISPONIVEL,
    STATUS_AMB_OCUPADA,
    STATUS_OCORRENCIA_DESPACHADA,
    STATUS_OCORRENCIA_FILA_LEITO,
    STATUS_OCORRENCIA_TRIAGEM,
    Ambulancia,
    Hospital,
    Ocorrencia,
    OperacaoHistorico,
    Paciente,
    RegistroAtendimento,
)

__all__ = [
    'Hospital',
    'Ambulancia',
    'Paciente',
    'Ocorrencia',
    'RegistroAtendimento',
    'OperacaoHistorico',
    'PRIORIDADE_CRITICA',
    'PRIORIDADE_MODERADA',
    'PRIORIDADE_BAIXA',
    'STATUS_OCORRENCIA_TRIAGEM',
    'STATUS_OCORRENCIA_DESPACHADA',
    'STATUS_OCORRENCIA_FILA_LEITO',
    'STATUS_AMB_DISPONIVEL',
    'STATUS_AMB_OCUPADA',
]

