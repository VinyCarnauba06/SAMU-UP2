import threading
from typing import Optional
from backend.domain.entidades import (
    PRIORIDADE_CRITICA,
    Ambulancia,
    Hospital,
    Ocorrencia,
    OperacaoHistorico,
    Paciente,
    RegistroAtendimento,
)
from backend.estruturas import (
    COLISAO_ENCADEAMENTO,
    COLISAO_SONDAGEM_LINEAR,
    COLISAO_SONDAGEM_QUADRATICA,
    METODO_DIVISAO_HORNER,
    METODO_DOBRA,
    METODO_HASH_HMAC_SHA256,
    METODO_MULTIPLICACAO,
    Deque,
    Fila,
    GrafoGeolocalizado,
    ListaEncadeada,
    Pilha,
    ResultadoCaminhoMinimo,
    TabelaHash,
    Vetor,
)


class EntidadeNaoEncontradaError(Exception):
    pass


class Store:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq_ocorrencia = 0
        self._seq_operacao = 0

        self.hospitais: Vetor[Hospital] = Vetor()
        self.ambulancias: Vetor[Ambulancia] = Vetor()
        self.grafo: GrafoGeolocalizado = GrafoGeolocalizado()

        self.deque_triagem: Deque[Ocorrencia] = Deque()
        self.historico_operacoes: Pilha[OperacaoHistorico] = Pilha()

        self.filas_espera_hospital: TabelaHash[str, Fila[str]] = TabelaHash(
            capacidade_inicial=17,
            metodo_hash=METODO_DIVISAO_HORNER,
            metodo_colisao=COLISAO_ENCADEAMENTO,
            justificativa_aplicacao='Fila de espera por leito de cada hospital.',
        )

        self.prontuario_por_ambulancia: TabelaHash[str, ListaEncadeada[RegistroAtendimento]] = TabelaHash(
            capacidade_inicial=17,
            metodo_hash=METODO_DIVISAO_HORNER,
            metodo_colisao=COLISAO_ENCADEAMENTO,
            justificativa_aplicacao='Historico de atendimentos de cada viatura.',
        )

        self.hash_pacientes_cpf: TabelaHash[str, Paciente] = TabelaHash(
            capacidade_inicial=19,
            metodo_hash=METODO_HASH_HMAC_SHA256,
            metodo_colisao=COLISAO_ENCADEAMENTO,
            justificativa_aplicacao='Busca de pacientes por CPF usando HMAC-SHA256 e encadeamento separado.',
        )

        self.hash_cache_rotas: TabelaHash[str, ResultadoCaminhoMinimo] = TabelaHash(
            capacidade_inicial=29,
            metodo_hash=METODO_MULTIPLICACAO,
            metodo_colisao=COLISAO_SONDAGEM_QUADRATICA,
            justificativa_aplicacao='Cache de rotas calculadas usando multiplicacao de Knuth e sondagem quadratica.',
        )

        self.hash_unidades_cep: TabelaHash[str, Hospital] = TabelaHash(
            capacidade_inicial=17,
            metodo_hash=METODO_DOBRA,
            metodo_colisao=COLISAO_SONDAGEM_LINEAR,
            justificativa_aplicacao='Indice de hospitais por CEP usando metodo da dobra e sondagem linear.',
        )

        self.hash_ocorrencias_id: TabelaHash[str, Ocorrencia] = TabelaHash(
            capacidade_inicial=23,
            metodo_hash=METODO_DIVISAO_HORNER,
            metodo_colisao=COLISAO_ENCADEAMENTO,
            justificativa_aplicacao='Indice de ocorrencias por id.',
        )

    def novo_id_ocorrencia(self) -> str:
        self._seq_ocorrencia += 1
        return f'ocor-{self._seq_ocorrencia:03d}'

    def novo_id_operacao(self) -> str:
        self._seq_operacao += 1
        return f'op-{self._seq_operacao:03d}'

    def adicionar_hospital(self, hospital: Hospital) -> None:
        self.hospitais.adicionar(hospital)
        self.filas_espera_hospital.inserir(hospital.id, Fila())
        cep_limpo = ''.join(c for c in hospital.cep if c.isdigit())
        self.hash_unidades_cep.inserir(cep_limpo, hospital)

    def adicionar_ambulancia(self, ambulancia: Ambulancia) -> None:
        self.ambulancias.adicionar(ambulancia)
        self.prontuario_por_ambulancia.inserir(ambulancia.id, ListaEncadeada())

    def adicionar_paciente(self, paciente: Paciente) -> None:
        cpf_limpo = ''.join(c for c in paciente.cpf if c.isdigit())
        paciente.cpf = cpf_limpo
        paciente.token_lgpd = self.hash_pacientes_cpf.gerar_token_lgpd(cpf_limpo)
        self.hash_pacientes_cpf.inserir(cpf_limpo, paciente)

    def registrar_ocorrencia_triagem(self, ocorrencia: Ocorrencia) -> Ocorrencia:
        self.hash_ocorrencias_id.inserir(ocorrencia.id, ocorrencia)
        if ocorrencia.prioridade == PRIORIDADE_CRITICA:
            self.deque_triagem.inserir_inicio(ocorrencia)
        else:
            self.deque_triagem.inserir_fim(ocorrencia)
        return ocorrencia

    def buscar_hospital(self, hospital_id: str) -> Hospital:
        hosp = self.hospitais.encontrar(lambda h: h.id == hospital_id)
        if hosp is None:
            raise EntidadeNaoEncontradaError(f'hospital {hospital_id} nao encontrado')
        return hosp

    def buscar_hospital_por_cep(self, cep: str) -> Optional[Hospital]:
        cep_limpo = ''.join(c for c in cep if c.isdigit())
        return self.hash_unidades_cep.obter(cep_limpo)

    def buscar_ambulancia(self, ambulancia_id: str) -> Ambulancia:
        amb = self.ambulancias.encontrar(lambda a: a.id == ambulancia_id)
        if amb is None:
            raise EntidadeNaoEncontradaError(f'ambulancia {ambulancia_id} nao encontrada')
        return amb

    def buscar_paciente_por_cpf(self, cpf: str) -> Optional[Paciente]:
        cpf_limpo = ''.join(c for c in cpf if c.isdigit())
        return self.hash_pacientes_cpf.obter(cpf_limpo)

    def buscar_ocorrencia(self, ocorrencia_id: str) -> Ocorrencia:
        ocor = self.hash_ocorrencias_id.obter(ocorrencia_id)
        if ocor is None:
            raise EntidadeNaoEncontradaError(f'ocorrencia {ocorrencia_id} nao encontrada')
        return ocor

    def invalidar_cache_rotas(self) -> None:
        self.hash_cache_rotas = TabelaHash(
            capacidade_inicial=29,
            metodo_hash=METODO_MULTIPLICACAO,
            metodo_colisao=COLISAO_SONDAGEM_QUADRATICA,
            justificativa_aplicacao=self.hash_cache_rotas.estatisticas().justificativa_aplicacao,
        )

    def obter_rota_com_cache(self, origem_id: str, destino_id: str) -> tuple[ResultadoCaminhoMinimo, bool]:
        chave = f'{origem_id}->{destino_id}'
        em_cache = self.hash_cache_rotas.obter(chave)
        if em_cache is not None:
            return (em_cache, True)
        calculada = self.grafo.dijkstra(origem_id, destino_id)
        if calculada.alcancavel:
            self.hash_cache_rotas.inserir(chave, calculada)
        return (calculada, False)

    def listar_ocorrencias_todas(self) -> list[Ocorrencia]:
        return self.hash_ocorrencias_id.valores()

