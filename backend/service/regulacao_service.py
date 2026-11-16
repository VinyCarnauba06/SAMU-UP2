import hashlib
from datetime import datetime
from typing import Any, Optional
from backend.domain.entidades import (
    PRIORIDADE_BAIXA,
    PRIORIDADE_CRITICA,
    PRIORIDADE_MODERADA,
    STATUS_AMB_DISPONIVEL,
    STATUS_OCORRENCIA_DESPACHADA,
    STATUS_OCORRENCIA_FILA_LEITO,
    STATUS_OCORRENCIA_TRIAGEM,
    Hospital,
    Ocorrencia,
    OperacaoHistorico,
    Paciente,
    RegistroAtendimento,
)
from backend.estruturas import (
    ALGORITMO_QUICKSORT,
    DequeVazioError,
    MetricasOrdenacao,
    Pilha,
    ResultadoCaminhoMinimo,
    comparar_todos_algoritmos,
    ordenar_com_algoritmo,
)
from backend.repository.store import EntidadeNaoEncontradaError, Store


class ValidacaoRegulacaoError(Exception):
    pass


class SemRecursosDisponiveisError(Exception):
    pass


class RegulacaoService:

    def __init__(self, store: Store) -> None:
        self._store = store
        self.ultimo_caminho_destacado: list[str] = []
        self.ultimo_titulo_rota: str = ''

    def abrir_chamado(
        self,
        paciente_cpf: str,
        paciente_nome: str,
        vertice_id: str,
        descricao: str,
        nivel_gravidade: int,
        idade: int = 40,
        tipo_sanguineo: str = 'O+',
        historico_clinico: str = 'Nao informado',
    ) -> Ocorrencia:
        cpf_limpo = ''.join(c for c in str(paciente_cpf or '') if c.isdigit())
        if len(cpf_limpo) < 6:
            raise ValidacaoRegulacaoError('Informe um CPF valido (minimo 6 digitos para demonstracao).')
        nome_limpo = str(paciente_nome or '').strip()
        if not nome_limpo:
            raise ValidacaoRegulacaoError('Nome do paciente e obrigatorio.')
        desc_limpa = str(descricao or '').strip()
        if not desc_limpa:
            raise ValidacaoRegulacaoError('Descricao clinica do chamado e obrigatoria.')

        vertice = self._store.grafo.obter_vertice(vertice_id)
        if vertice is None:
            raise ValidacaoRegulacaoError(f'Localizacao {vertice_id} nao existe na malha de Maceio.')

        gravidade = max(1, min(10, int(nivel_gravidade)))
        if gravidade >= 8:
            prioridade = PRIORIDADE_CRITICA
        elif gravidade >= 4:
            prioridade = PRIORIDADE_MODERADA
        else:
            prioridade = PRIORIDADE_BAIXA

        paciente = self._store.buscar_paciente_por_cpf(cpf_limpo)
        if paciente is None:
            paciente = Paciente(
                cpf=cpf_limpo,
                nome=nome_limpo,
                cartao_sus=f'704{cpf_limpo[:11].ljust(11, "0")}9',
                idade=max(0, min(120, int(idade))),
                tipo_sanguineo=tipo_sanguineo or 'O+',
                historico_clinico=historico_clinico or 'Cadastrado na triagem 192',
            )
            self._store.adicionar_paciente(paciente)

        ocorrencia = Ocorrencia(
            id=self._store.novo_id_ocorrencia(),
            paciente_cpf=paciente.cpf,
            paciente_nome=paciente.nome,
            vertice_id=vertice.id,
            bairro=vertice.bairro,
            descricao=desc_limpa,
            prioridade=prioridade,
            nivel_gravidade=gravidade,
            status=STATUS_OCORRENCIA_TRIAGEM,
            criada_em=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
        return self._store.registrar_ocorrencia_triagem(ocorrencia)

    def despachar_deque(self, extremidade: str = 'inicio') -> dict[str, Any]:
        if self._store.deque_triagem.esta_vazio():
            raise ValidacaoRegulacaoError('O Deque de triagem 192 esta vazio.')

        ocorrencia = (
            self._store.deque_triagem.frente_valor()
            if extremidade == 'inicio'
            else self._store.deque_triagem.fim_valor()
        )

        melhor_amb = None
        melhor_rota_amb: Optional[ResultadoCaminhoMinimo] = None
        usou_cache_amb = False
        menor_score_amb = float('inf')

        for amb in self._store.ambulancias:
            if amb.status != STATUS_AMB_DISPONIVEL:
                continue
            rota, em_cache = self._store.obter_rota_com_cache(amb.vertice_atual_id, ocorrencia.vertice_id)
            if not rota.alcancavel:
                continue
            penalidade_tipo = 0.0
            if ocorrencia.prioridade == PRIORIDADE_CRITICA and amb.tipo != 'USA':
                penalidade_tipo = 2.5
            score = rota.tempo_total_min + penalidade_tipo
            if score < menor_score_amb:
                menor_score_amb = score
                melhor_amb = amb
                melhor_rota_amb = rota
                usou_cache_amb = em_cache

        if melhor_amb is None or melhor_rota_amb is None:
            raise SemRecursosDisponiveisError(
                'Nenhuma ambulancia consegue alcancar o local (verifique bloqueios de vias na malha).'
            )

        melhor_hosp: Optional[Hospital] = None
        melhor_rota_hosp: Optional[ResultadoCaminhoMinimo] = None
        usou_cache_hosp = False
        menor_tempo_hosp = float('inf')

        hospitais_com_vaga = [h for h in self._store.hospitais if h.leitos_livres > 0]
        candidatos_hosp = hospitais_com_vaga if hospitais_com_vaga else self._store.hospitais.para_lista()

        for hosp in candidatos_hosp:
            rota_h, cache_h = self._store.obter_rota_com_cache(ocorrencia.vertice_id, hosp.vertice_id)
            if not rota_h.alcancavel:
                continue
            if rota_h.tempo_total_min < menor_tempo_hosp:
                menor_tempo_hosp = rota_h.tempo_total_min
                melhor_hosp = hosp
                melhor_rota_hosp = rota_h
                usou_cache_hosp = cache_h

        if melhor_hosp is None or melhor_rota_hosp is None:
            raise SemRecursosDisponiveisError('Nenhum hospital alcancavel a partir do local da ocorrencia.')

        if extremidade == 'inicio':
            self._store.deque_triagem.remover_inicio()
        else:
            self._store.deque_triagem.remover_fim()

        vertice_anterior_amb = melhor_amb.vertice_atual_id
        caminho_completo = list(melhor_rota_amb.caminho_vertices)
        if melhor_rota_hosp.caminho_vertices:
            caminho_completo.extend(melhor_rota_hosp.caminho_vertices[1:])

        tempo_total = round(melhor_rota_amb.tempo_total_min + melhor_rota_hosp.tempo_total_min, 2)
        dist_total = round(melhor_rota_amb.distancia_total_km + melhor_rota_hosp.distancia_total_km, 2)

        payload_ass = f'{ocorrencia.id}|{melhor_amb.id}|{melhor_hosp.id}|{tempo_total}|{dist_total}|{caminho_completo}'
        assinatura_sha256 = hashlib.sha256(payload_ass.encode('utf-8')).hexdigest()

        melhor_amb.vertice_atual_id = melhor_hosp.vertice_id
        melhor_amb.km_rodados = round(melhor_amb.km_rodados + dist_total, 2)
        melhor_amb.total_atendimentos += 1

        ocupou_leito = False
        entrou_fila = False
        if melhor_hosp.leitos_livres > 0:
            melhor_hosp.leitos_ocupados += 1
            ocorrencia.status = STATUS_OCORRENCIA_DESPACHADA
            ocupou_leito = True
        else:
            fila_h = self._store.filas_espera_hospital.obter(melhor_hosp.id)
            if fila_h is not None:
                fila_h.enfileirar(ocorrencia.id)
            ocorrencia.status = STATUS_OCORRENCIA_FILA_LEITO
            entrou_fila = True

        ocorrencia.ambulancia_id = melhor_amb.id
        ocorrencia.hospital_id = melhor_hosp.id
        ocorrencia.tempo_resposta_min = tempo_total
        ocorrencia.distancia_total_km = dist_total
        ocorrencia.caminho_vertices = caminho_completo

        prontuario = self._store.prontuario_por_ambulancia.obter(melhor_amb.id)
        if prontuario is not None:
            prontuario.inserir_no_inicio(
                RegistroAtendimento(
                    ocorrencia_id=ocorrencia.id,
                    ambulancia_id=melhor_amb.id,
                    hospital_id=melhor_hosp.id,
                    paciente_nome=ocorrencia.paciente_nome,
                    prioridade=ocorrencia.prioridade,
                    tempo_total_min=tempo_total,
                    distancia_km=dist_total,
                    caminho_vertices=caminho_completo,
                    usou_cache_hash=usou_cache_amb or usou_cache_hosp,
                    assinatura_digital_sha256=assinatura_sha256[:16],
                )
            )

        op = OperacaoHistorico(
            id=self._store.novo_id_operacao(),
            tipo='despacho',
            descricao=(
                f'Despacho {ocorrencia.id} ({ocorrencia.paciente_nome}) via {melhor_amb.codigo} '
                f'-> {melhor_hosp.nome} ({tempo_total} min)'
            ),
            ocorrencia_id=ocorrencia.id,
            ambulancia_id=melhor_amb.id,
            vertice_anterior_amb=vertice_anterior_amb,
            hospital_id=melhor_hosp.id,
            ocupou_leito=ocupou_leito,
            entrou_fila_leito=entrou_fila,
            distancia_adicionada_km=dist_total,
            assinatura_digital_sha256=assinatura_sha256[:16],
        )
        self._store.historico_operacoes.empilhar(op)

        self.ultimo_caminho_destacado = caminho_completo
        self.ultimo_titulo_rota = f'{melhor_amb.codigo} -> {ocorrencia.bairro} -> {melhor_hosp.nome} ({tempo_total} min)'

        return {
            'ocorrencia_id': ocorrencia.id,
            'paciente_nome': ocorrencia.paciente_nome,
            'prioridade': ocorrencia.prioridade,
            'extremidade_deque': extremidade,
            'ambulancia_id': melhor_amb.id,
            'ambulancia_codigo': melhor_amb.codigo,
            'hospital_id': melhor_hosp.id,
            'hospital_nome': melhor_hosp.nome,
            'tempo_ate_vitima_min': melhor_rota_amb.tempo_total_min,
            'tempo_ate_hospital_min': melhor_rota_hosp.tempo_total_min,
            'tempo_total_min': tempo_total,
            'distancia_total_km': dist_total,
            'caminho_vertices': caminho_completo,
            'vias_percorridas': melhor_rota_amb.vias_percorridas + melhor_rota_hosp.vias_percorridas,
            'ocupou_leito': ocupou_leito,
            'entrou_fila_espera': entrou_fila,
            'cache_hash_atingido': usou_cache_amb or usou_cache_hosp,
            'assinatura_digital_sha256': assinatura_sha256,
        }

    def enviar_para_fila_leito(self, hospital_id: str, ocorrencia_id: str) -> dict[str, Any]:
        hosp = self._store.buscar_hospital(hospital_id)
        ocor = self._store.buscar_ocorrencia(ocorrencia_id)
        fila = self._store.filas_espera_hospital.obter(hosp.id)
        if fila is None:
            raise EntidadeNaoEncontradaError(f'fila do hospital {hospital_id} nao encontrada')
        self._store.deque_triagem.remover_onde(lambda o: o.id == ocor.id)
        ocor.status = STATUS_OCORRENCIA_FILA_LEITO
        ocor.hospital_id = hosp.id
        fila.enfileirar(ocor.id)
        return {
            'hospital_id': hosp.id,
            'hospital_nome': hosp.nome,
            'ocorrencia_id': ocor.id,
            'posicao_fila': len(fila),
        }

    def liberar_leito_e_atender_fila(self, hospital_id: str) -> dict[str, Any]:
        hosp = self._store.buscar_hospital(hospital_id)
        fila = self._store.filas_espera_hospital.obter(hosp.id)
        paciente_admitido: Optional[str] = None
        ocorrencia_admitida: Optional[str] = None

        if fila is not None and not fila.esta_vazia():
            prox_id = fila.desenfileirar()
            ocor = self._store.buscar_ocorrencia(prox_id)
            ocor.status = STATUS_OCORRENCIA_DESPACHADA
            ocorrencia_admitida = ocor.id
            paciente_admitido = ocor.paciente_nome
            if hosp.leitos_ocupados < hosp.leitos_totais:
                hosp.leitos_ocupados += 1
        else:
            if hosp.leitos_ocupados > 0:
                hosp.leitos_ocupados -= 1

        return {
            'hospital_id': hosp.id,
            'hospital_nome': hosp.nome,
            'leitos_ocupados': hosp.leitos_ocupados,
            'leitos_livres': hosp.leitos_livres,
            'ocorrencia_admitida_da_fila': ocorrencia_admitida,
            'paciente_admitido': paciente_admitido,
            'restantes_na_fila': len(fila) if fila is not None else 0,
        }

    def atualizar_via(
        self,
        origem_id: str,
        destino_id: str,
        fator_transito: float,
        bloqueada: bool,
    ) -> dict[str, Any]:
        fator_ant, bloq_ant = self._store.grafo.atualizar_estado_via(
            origem_id=origem_id,
            destino_id=destino_id,
            fator_transito=fator_transito,
            bloqueada=bloqueada,
        )
        self._store.invalidar_cache_rotas()
        estado_txt = 'INTERDITADA' if bloqueada else f'fator {fator_transito:.1f}x'
        op = OperacaoHistorico(
            id=self._store.novo_id_operacao(),
            tipo='via',
            descricao=f'Alteracao viaria {origem_id} <-> {destino_id} ({estado_txt})',
            via_origem_id=origem_id,
            via_destino_id=destino_id,
            fator_transito_anterior=fator_ant,
            bloqueada_anterior=bloq_ant,
        )
        self._store.historico_operacoes.empilhar(op)
        conectividade = self._store.grafo.dfs_conectividade()
        return {
            'origem_id': origem_id,
            'destino_id': destino_id,
            'fator_transito': fator_transito,
            'bloqueada': bloqueada,
            'malha_conexa': conectividade['conexo'],
            'vertices_isolados': conectividade['isolados'],
        }

    def desfazer_ultima_operacao(self) -> dict[str, Any]:
        if self._store.historico_operacoes.esta_vazia():
            raise ValidacaoRegulacaoError('Pilha de historico vazia: nenhuma operacao para desfazer.')

        op = self._store.historico_operacoes.desempilhar()
        if op.tipo == 'via' and op.via_origem_id and op.via_destino_id:
            self._store.grafo.atualizar_estado_via(
                origem_id=op.via_origem_id,
                destino_id=op.via_destino_id,
                fator_transito=op.fator_transito_anterior,
                bloqueada=op.bloqueada_anterior,
            )
            self._store.invalidar_cache_rotas()
            return {
                'desfeita_id': op.id,
                'tipo': 'via',
                'descricao': op.descricao,
            }

        if op.tipo == 'despacho' and op.ocorrencia_id and op.ambulancia_id and op.hospital_id:
            ocor = self._store.buscar_ocorrencia(op.ocorrencia_id)
            amb = self._store.buscar_ambulancia(op.ambulancia_id)
            hosp = self._store.buscar_hospital(op.hospital_id)

            if op.vertice_anterior_amb:
                amb.vertice_atual_id = op.vertice_anterior_amb
            amb.km_rodados = max(0.0, round(amb.km_rodados - op.distancia_adicionada_km, 2))
            amb.total_atendimentos = max(0, amb.total_atendimentos - 1)

            prontuario = self._store.prontuario_por_ambulancia.obter(amb.id)
            if prontuario is not None:
                prontuario.remover_onde(lambda r: r.ocorrencia_id == ocor.id)

            if op.ocupou_leito and hosp.leitos_ocupados > 0:
                hosp.leitos_ocupados -= 1

            if op.entrou_fila_leito:
                fila_orig = self._store.filas_espera_hospital.obter(hosp.id)
                if fila_orig is not None:
                    aux = Pilha[str]()
                    itens_f = fila_orig.para_lista()
                    while not fila_orig.esta_vazia():
                        fila_orig.desenfileirar()
                    for item_id in itens_f:
                        if item_id != ocor.id:
                            fila_orig.enfileirar(item_id)
                    _ = aux

            ocor.status = STATUS_OCORRENCIA_TRIAGEM
            ocor.ambulancia_id = None
            ocor.hospital_id = None
            ocor.tempo_resposta_min = 0.0
            ocor.distancia_total_km = 0.0
            ocor.caminho_vertices = []

            if ocor.prioridade == PRIORIDADE_CRITICA:
                self._store.deque_triagem.inserir_inicio(ocor)
            else:
                self._store.deque_triagem.inserir_fim(ocor)

            self.ultimo_caminho_destacado = []
            self.ultimo_titulo_rota = ''

            return {
                'desfeita_id': op.id,
                'tipo': 'despacho',
                'descricao': op.descricao,
                'ocorrencia_restaurada': ocor.id,
            }

        return {'desfeita_id': op.id, 'tipo': op.tipo, 'descricao': op.descricao}

    def ordenar_e_comparar(
        self,
        alvo: str = 'hospitais',
        criterio: str = 'taxa_ocupacao',
        algoritmo: str = ALGORITMO_QUICKSORT,
        reverso: bool = True,
    ) -> dict[str, Any]:
        if alvo == 'hospitais':
            colecao = self._store.hospitais.para_lista()
            seletores = {
                'taxa_ocupacao': lambda h: h.taxa_ocupacao,
                'leitos_livres': lambda h: h.leitos_livres,
                'leitos_totais': lambda h: h.leitos_totais,
                'nome': lambda h: h.nome,
            }
            fn_chave = seletores.get(criterio, seletores['taxa_ocupacao'])
            ordenados, metrica_escolhida = ordenar_com_algoritmo(algoritmo, colecao, chave=fn_chave, reverso=reverso)
            comparativo = comparar_todos_algoritmos(colecao, chave=fn_chave, reverso=reverso)
            itens_json = [
                {
                    'id': h.id,
                    'nome': h.nome,
                    'bairro': h.bairro,
                    'cep': h.cep,
                    'taxa_ocupacao': h.taxa_ocupacao,
                    'leitos_livres': h.leitos_livres,
                    'leitos_totais': h.leitos_totais,
                }
                for h in ordenados
            ]
        elif alvo == 'ambulancias':
            colecao_amb = self._store.ambulancias.para_lista()
            seletores_amb = {
                'km_rodados': lambda a: a.km_rodados,
                'total_atendimentos': lambda a: a.total_atendimentos,
                'codigo': lambda a: a.codigo,
            }
            fn_chave_amb = seletores_amb.get(criterio, seletores_amb['km_rodados'])
            ordenados_amb, metrica_escolhida = ordenar_com_algoritmo(
                algoritmo, colecao_amb, chave=fn_chave_amb, reverso=reverso
            )
            comparativo = comparar_todos_algoritmos(colecao_amb, chave=fn_chave_amb, reverso=reverso)
            itens_json = [
                {
                    'id': a.id,
                    'codigo': a.codigo,
                    'tipo': a.tipo,
                    'km_rodados': a.km_rodados,
                    'total_atendimentos': a.total_atendimentos,
                }
                for a in ordenados_amb
            ]
        else:
            colecao_oc = self._store.listar_ocorrencias_todas()
            seletores_oc = {
                'nivel_gravidade': lambda o: o.nivel_gravidade,
                'tempo_resposta_min': lambda o: o.tempo_resposta_min,
                'id': lambda o: o.id,
            }
            fn_chave_oc = seletores_oc.get(criterio, seletores_oc['nivel_gravidade'])
            ordenados_oc, metrica_escolhida = ordenar_com_algoritmo(
                algoritmo, colecao_oc, chave=fn_chave_oc, reverso=reverso
            )
            comparativo = comparar_todos_algoritmos(colecao_oc, chave=fn_chave_oc, reverso=reverso)
            itens_json = [
                {
                    'id': o.id,
                    'paciente_nome': o.paciente_nome,
                    'bairro': o.bairro,
                    'prioridade': o.prioridade,
                    'nivel_gravidade': o.nivel_gravidade,
                    'status': o.status,
                    'tempo_resposta_min': o.tempo_resposta_min,
                }
                for o in ordenados_oc
            ]

        return {
            'alvo': alvo,
            'criterio': criterio,
            'algoritmo_selecionado': self._metrica_para_dict(metrica_escolhida),
            'comparativo_4_algoritmos': [self._metrica_para_dict(m) for m in comparativo],
            'itens': itens_json,
        }

    def _metrica_para_dict(self, m: MetricasOrdenacao) -> dict[str, Any]:
        return {
            'algoritmo': m.algoritmo,
            'nome_exibicao': m.nome_exibicao,
            'tamanho_entrada': m.tamanho_entrada,
            'comparacoes': m.comparacoes,
            'trocas': m.trocas,
            'tempo_ms': m.tempo_ms,
            'complexidade_melhor': m.complexidade_melhor,
            'complexidade_medio': m.complexidade_medio,
            'complexidade_pior': m.complexidade_pior,
            'estavel': m.estavel,
        }
