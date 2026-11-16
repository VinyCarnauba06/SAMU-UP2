from dataclasses import dataclass, field
from typing import Optional

PRIORIDADE_CRITICA = 'critica'
PRIORIDADE_MODERADA = 'moderada'
PRIORIDADE_BAIXA = 'baixa'

STATUS_OCORRENCIA_TRIAGEM = 'triagem'
STATUS_OCORRENCIA_DESPACHADA = 'despachada'
STATUS_OCORRENCIA_FILA_LEITO = 'aguardando_leito'

STATUS_AMB_DISPONIVEL = 'disponivel'
STATUS_AMB_OCUPADA = 'em_atendimento'


@dataclass
class Hospital:
    id: str
    vertice_id: str
    nome: str
    bairro: str
    cep: str
    latitude: float
    longitude: float
    leitos_totais: int
    leitos_ocupados: int
    especialidade_principal: str

    @property
    def leitos_livres(self) -> int:
        return max(0, self.leitos_totais - self.leitos_ocupados)

    @property
    def taxa_ocupacao(self) -> float:
        if self.leitos_totais <= 0:
            return 100.0
        return round((self.leitos_ocupados / self.leitos_totais) * 100.0, 1)


@dataclass
class Ambulancia:
    id: str
    codigo: str
    tipo: str
    base_vertice_id: str
    vertice_atual_id: str
    status: str = STATUS_AMB_DISPONIVEL
    km_rodados: float = 0.0
    total_atendimentos: int = 0


@dataclass
class Paciente:
    cpf: str
    nome: str
    cartao_sus: str
    idade: int
    tipo_sanguineo: str
    historico_clinico: str
    token_lgpd: str = ''


@dataclass
class Ocorrencia:
    id: str
    paciente_cpf: str
    paciente_nome: str
    vertice_id: str
    bairro: str
    descricao: str
    prioridade: str
    nivel_gravidade: int
    status: str = STATUS_OCORRENCIA_TRIAGEM
    criada_em: str = ''
    ambulancia_id: Optional[str] = None
    hospital_id: Optional[str] = None
    tempo_resposta_min: float = 0.0
    distancia_total_km: float = 0.0
    caminho_vertices: list[str] = field(default_factory=list)


@dataclass
class RegistroAtendimento:
    ocorrencia_id: str
    ambulancia_id: str
    hospital_id: str
    paciente_nome: str
    prioridade: str
    tempo_total_min: float
    distancia_km: float
    caminho_vertices: list[str]
    usou_cache_hash: bool
    assinatura_digital_sha256: str = ''


@dataclass
class OperacaoHistorico:
    id: str
    tipo: str
    descricao: str
    ocorrencia_id: Optional[str] = None
    ambulancia_id: Optional[str] = None
    vertice_anterior_amb: Optional[str] = None
    hospital_id: Optional[str] = None
    ocupou_leito: bool = False
    entrou_fila_leito: bool = False
    distancia_adicionada_km: float = 0.0
    via_origem_id: Optional[str] = None
    via_destino_id: Optional[str] = None
    fator_transito_anterior: float = 1.0
    bloqueada_anterior: bool = False
    assinatura_digital_sha256: str = ''

