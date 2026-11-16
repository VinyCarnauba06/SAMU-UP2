import os
import secrets
import sys
import threading
import time
from typing import Any

sys.dont_write_bytecode = True

from flask import Flask, Response, jsonify, render_template, request
from backend.config import carregar_configuracao
from backend.domain.entidades import Paciente
from backend.estruturas import ALGORITMO_QUICKSORT, calcular_haversine
from backend.repository.store import EntidadeNaoEncontradaError, Store
from backend.seed.loader import carregar_seed
from backend.service import (
    GraficoService,
    RegulacaoService,
    SemRecursosDisponiveisError,
    ValidacaoRegulacaoError,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_SEED = os.path.join(BASE_DIR, 'backend', 'seed', 'dados.json')
config = carregar_configuracao()
_INICIADO_EM = time.time()

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'frontend', 'templates'),
    static_folder=os.path.join(BASE_DIR, 'frontend', 'static'),
)
app.secret_key = os.environ.get('PULSO_SECRET_KEY') or secrets.token_hex(32)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

_lock = threading.Lock()
_estado: dict[str, Any] = {}


def _inicializar_sistema() -> dict[str, Any]:
    store = Store()
    carregar_seed(CAMINHO_SEED, store)
    regulacao = RegulacaoService(store)
    graficos = GraficoService(store)
    return {'store': store, 'regulacao': regulacao, 'graficos': graficos}


_estado.update(_inicializar_sistema())


@app.after_request
def aplicar_cabecalhos_seguranca(resposta: Response) -> Response:
    resposta.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resposta.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    resposta.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    return resposta


@app.errorhandler(404)
def tratar_404(_erro: Exception) -> tuple[Response, int]:
    if request.path.startswith('/api/'):
        return (jsonify({'erro': f'Rota nao encontrada: {request.path}'}), 404)
    return (Response(render_template('index.html'), status=404, mimetype='text/html'), 404)


@app.errorhandler(405)
def tratar_405(_erro: Exception) -> tuple[Response, int]:
    return (jsonify({'erro': f'Metodo HTTP {request.method} nao permitido para {request.path}.'}), 405)


@app.errorhandler(500)
def tratar_500(erro: Exception) -> tuple[Response, int]:
    return (jsonify({'erro': 'Erro interno no servidor PULSO 192.', 'detalhe': str(erro)}), 500)


@app.get('/api/health')
@app.get('/healthz')
def healthcheck() -> tuple[Response, int]:
    with _lock:
        store: Store = _estado['store']
        con = store.grafo.dfs_conectividade()
        return (
            jsonify(
                {
                    'status': 'healthy',
                    'servico': 'PULSO 192 - SAMU Maceio',
                    'versao': '1.0',
                    'uptime_segundos': round(time.time() - _INICIADO_EM, 2),
                    'malha_viaria_conexa': con['conexo'],
                    'metricas': {
                        'vertices': len(store.grafo.listar_vertices()),
                        'arestas_unicas': len(store.grafo.listar_arestas_unicas()),
                        'hospitais': len(store.hospitais),
                        'ambulancias': len(store.ambulancias),
                        'chamados_deque_triagem': len(store.deque_triagem),
                        'operacoes_pilha_undo': len(store.historico_operacoes),
                    },
                }
            ),
            200,
        )



@app.get('/')
def index() -> str:
    return render_template('index.html')


@app.get('/favicon.ico')
def favicon() -> Response:
    return Response(status=204)


@app.get('/api/estado-geral')
def estado_geral() -> Response:
    with _lock:
        store: Store = _estado['store']
        regulacao: RegulacaoService = _estado['regulacao']

        vertices = [
            {
                'id': v.id,
                'nome': v.nome,
                'bairro': v.bairro,
                'tipo': v.tipo,
                'latitude': v.latitude,
                'longitude': v.longitude,
            }
            for v in store.grafo.listar_vertices()
        ]

        arestas = []
        for a in store.grafo.listar_arestas_unicas():
            vo = store.grafo.obter_vertice(a.origem_id)
            vd = store.grafo.obter_vertice(a.destino_id)
            dist_hav_m = (
                round(
                    calcular_haversine(
                        (vo.latitude, vo.longitude),
                        (vd.latitude, vd.longitude),
                        em_metros=True,
                    ),
                    2,
                )
                if (vo and vd)
                else round(a.distancia_km * 1000.0, 2)
            )
            arestas.append(
                {
                    'origem_id': a.origem_id,
                    'destino_id': a.destino_id,
                    'nome_via': a.nome_via,
                    'distancia_km': a.distancia_km,
                    'distancia_haversine_m': dist_hav_m,
                    'velocidade_media_kmh': a.velocidade_media_kmh,
                    'fator_transito': a.fator_transito,
                    'bloqueada': a.bloqueada,
                    'tempo_minutos': round(a.tempo_minutos, 2) if not a.bloqueada else None,
                }
            )

        hospitais_json = []
        for h in store.hospitais:
            fila_h = store.filas_espera_hospital.obter(h.id)
            ids_fila = fila_h.para_lista() if fila_h is not None else []
            pacientes_fila = []
            for oid in ids_fila:
                try:
                    oc = store.buscar_ocorrencia(oid)
                    pacientes_fila.append(
                        {
                            'ocorrencia_id': oc.id,
                            'paciente_nome': oc.paciente_nome,
                            'prioridade': oc.prioridade,
                            'nivel_gravidade': oc.nivel_gravidade,
                        }
                    )
                except EntidadeNaoEncontradaError:
                    continue
            hospitais_json.append(
                {
                    'id': h.id,
                    'vertice_id': h.vertice_id,
                    'nome': h.nome,
                    'bairro': h.bairro,
                    'cep': h.cep,
                    'latitude': h.latitude,
                    'longitude': h.longitude,
                    'leitos_totais': h.leitos_totais,
                    'leitos_ocupados': h.leitos_ocupados,
                    'leitos_livres': h.leitos_livres,
                    'taxa_ocupacao': h.taxa_ocupacao,
                    'especialidade_principal': h.especialidade_principal,
                    'fila_espera': pacientes_fila,
                }
            )

        ambulancias_json = []
        for amb in store.ambulancias:
            prontuario = store.prontuario_por_ambulancia.obter(amb.id)
            historico_amb = [
                {
                    'ocorrencia_id': r.ocorrencia_id,
                    'hospital_id': r.hospital_id,
                    'paciente_nome': r.paciente_nome,
                    'prioridade': r.prioridade,
                    'tempo_total_min': r.tempo_total_min,
                    'distancia_km': r.distancia_km,
                    'usou_cache_hash': r.usou_cache_hash,
                }
                for r in (prontuario.para_lista() if prontuario is not None else [])
            ]
            vert_atual = store.grafo.obter_vertice(amb.vertice_atual_id)
            ambulancias_json.append(
                {
                    'id': amb.id,
                    'codigo': amb.codigo,
                    'tipo': amb.tipo,
                    'base_vertice_id': amb.base_vertice_id,
                    'vertice_atual_id': amb.vertice_atual_id,
                    'local_atual_nome': vert_atual.nome if vert_atual else amb.vertice_atual_id,
                    'latitude': vert_atual.latitude if vert_atual else -9.6462,
                    'longitude': vert_atual.longitude if vert_atual else -35.7348,
                    'status': amb.status,
                    'km_rodados': amb.km_rodados,
                    'total_atendimentos': amb.total_atendimentos,
                    'atendimentos_lista_encadeada': historico_amb,
                }
            )

        deque_json = [
            {
                'id': o.id,
                'paciente_cpf': o.paciente_cpf,
                'paciente_nome': o.paciente_nome,
                'vertice_id': o.vertice_id,
                'bairro': o.bairro,
                'descricao': o.descricao,
                'prioridade': o.prioridade,
                'nivel_gravidade': o.nivel_gravidade,
                'status': o.status,
                'criada_em': o.criada_em,
            }
            for o in store.deque_triagem
        ]

        pilha_json = [
            {
                'id': op.id,
                'tipo': op.tipo,
                'descricao': op.descricao,
                'ocorrencia_id': op.ocorrencia_id,
                'ambulancia_id': op.ambulancia_id,
                'hospital_id': op.hospital_id,
            }
            for op in store.historico_operacoes.para_lista()
        ]

        conectividade = store.grafo.dfs_conectividade()

        return jsonify(
            {
                'vertices': vertices,
                'arestas': arestas,
                'hospitais': hospitais_json,
                'ambulancias': ambulancias_json,
                'deque_triagem': deque_json,
                'pilha_historico': pilha_json,
                'conectividade': conectividade,
                'ultimo_caminho_destacado': regulacao.ultimo_caminho_destacado,
                'ultimo_titulo_rota': regulacao.ultimo_titulo_rota,
            }
        )


@app.post('/api/ocorrencias')
def criar_ocorrencia() -> tuple[Response, int]:
    payload = request.get_json(silent=True) or {}
    with _lock:
        regulacao: RegulacaoService = _estado['regulacao']
        try:
            ocorrencia = regulacao.abrir_chamado(
                paciente_cpf=str(payload.get('paciente_cpf', '')),
                paciente_nome=str(payload.get('paciente_nome', '')),
                vertice_id=str(payload.get('vertice_id', '')),
                descricao=str(payload.get('descricao', '')),
                nivel_gravidade=int(payload.get('nivel_gravidade', 5)),
                idade=int(payload.get('idade', 40)),
                tipo_sanguineo=str(payload.get('tipo_sanguineo', 'O+')),
                historico_clinico=str(payload.get('historico_clinico', 'Sem observacoes')),
            )
        except (ValidacaoRegulacaoError, ValueError) as erro:
            return (jsonify({'erro': str(erro)}), 400)

        posicao_inserida = 'inicio (frente)' if ocorrencia.prioridade == 'critica' else 'fim (cauda)'
        return (
            jsonify(
                {
                    'id': ocorrencia.id,
                    'prioridade': ocorrencia.prioridade,
                    'nivel_gravidade': ocorrencia.nivel_gravidade,
                    'extremidade_deque': posicao_inserida,
                    'tamanho_deque': len(_estado['store'].deque_triagem),
                }
            ),
            201,
        )


@app.post('/api/triagem/despachar')
def despachar_triagem() -> tuple[Response, int]:
    payload = request.get_json(silent=True) or {}
    extremidade = str(payload.get('extremidade', 'inicio'))
    if extremidade not in ('inicio', 'fim'):
        return (jsonify({'erro': 'Extremidade do Deque deve ser inicio ou fim.'}), 400)
    with _lock:
        regulacao: RegulacaoService = _estado['regulacao']
        try:
            resultado = regulacao.despachar_deque(extremidade=extremidade)
        except ValidacaoRegulacaoError as erro:
            return (jsonify({'erro': str(erro)}), 400)
        except SemRecursosDisponiveisError as erro:
            return (jsonify({'erro': str(erro)}), 409)
        return (jsonify(resultado), 200)


@app.post('/api/hospitais/<hospital_id>/enfileirar')
def enfileirar_leito(hospital_id: str) -> tuple[Response, int]:
    payload = request.get_json(silent=True) or {}
    ocorrencia_id = str(payload.get('ocorrencia_id', ''))
    if not ocorrencia_id:
        return (jsonify({'erro': 'ocorrencia_id e obrigatorio.'}), 400)
    with _lock:
        regulacao: RegulacaoService = _estado['regulacao']
        try:
            res = regulacao.enviar_para_fila_leito(hospital_id, ocorrencia_id)
        except EntidadeNaoEncontradaError as erro:
            return (jsonify({'erro': str(erro)}), 404)
        return (jsonify(res), 200)


@app.post('/api/hospitais/<hospital_id>/liberar-leito')
def liberar_leito(hospital_id: str) -> tuple[Response, int]:
    with _lock:
        regulacao: RegulacaoService = _estado['regulacao']
        try:
            res = regulacao.liberar_leito_e_atender_fila(hospital_id)
        except EntidadeNaoEncontradaError as erro:
            return (jsonify({'erro': str(erro)}), 404)
        return (jsonify(res), 200)


@app.post('/api/grafo/via')
def alterar_via() -> tuple[Response, int]:
    payload = request.get_json(silent=True) or {}
    origem_id = str(payload.get('origem_id', ''))
    destino_id = str(payload.get('destino_id', ''))
    fator_transito = float(payload.get('fator_transito', 1.0))
    bloqueada = bool(payload.get('bloqueada', False))
    with _lock:
        regulacao: RegulacaoService = _estado['regulacao']
        try:
            res = regulacao.atualizar_via(origem_id, destino_id, fator_transito, bloqueada)
        except KeyError as erro:
            return (jsonify({'erro': str(erro)}), 404)
        return (jsonify(res), 200)


@app.post('/api/grafo/analisar')
def analisar_grafo() -> tuple[Response, int]:
    payload = request.get_json(silent=True) or {}
    algoritmo = str(payload.get('algoritmo', 'dijkstra'))
    origem_id = str(payload.get('origem_id', 'v-samu-farol'))
    destino_id = str(payload.get('destino_id', 'v-hge'))
    max_saltos = int(payload.get('max_saltos', 3))

    with _lock:
        store: Store = _estado['store']
        regulacao: RegulacaoService = _estado['regulacao']
        try:
            if algoritmo == 'mst':
                mst = store.grafo.arvore_geradora_minima_prim(origem_id=origem_id)
                return (
                    jsonify(
                        {
                            'algoritmo': 'mst_prim',
                            'custo_total_min': mst.custo_total_min,
                            'distancia_total_km': mst.distancia_total_km,
                            'total_vertices_conectados': mst.total_vertices_conectados,
                            'conexo': mst.conexo,
                            'arestas': [
                                {
                                    'origem_id': a.origem_id,
                                    'destino_id': a.destino_id,
                                    'nome_via': a.nome_via,
                                    'tempo_minutos': round(a.tempo_minutos, 2),
                                    'distancia_km': a.distancia_km,
                                }
                                for a in mst.arestas
                            ],
                        }
                    ),
                    200,
                )
            if algoritmo == 'bfs':
                alcancados = store.grafo.bfs_por_saltos(origem_id=origem_id, max_saltos=max_saltos)
                return (
                    jsonify(
                        {
                            'algoritmo': 'bfs',
                            'origem_id': origem_id,
                            'max_saltos': max_saltos,
                            'nos_alcancados': alcancados,
                        }
                    ),
                    200,
                )
            if algoritmo == 'dfs':
                con = store.grafo.dfs_conectividade(origem_id=origem_id)
                return (jsonify({'algoritmo': 'dfs', **con}), 200)

            if algoritmo == 'networkx_resiliencia':
                no_indisponivel = str(payload.get('no_indisponivel', '')).strip() or None
                autonomia_raw = payload.get('autonomia_maxima_m', 3500.0)
                autonomia_m = float(autonomia_raw) if autonomia_raw not in (None, '', 0, '0') else None
                criterio_peso = str(payload.get('criterio_peso', 'distancia_haversine_m'))
                res_nx = store.grafo.analisar_resiliencia_networkx(
                    origem_id=origem_id,
                    destino_id=destino_id,
                    no_indisponivel=no_indisponivel,
                    autonomia_maxima_m=autonomia_m,
                    criterio_peso=criterio_peso,
                )
                caminho_dest = (
                    res_nx['contingencia']['caminho_vertices']
                    if (no_indisponivel and res_nx['contingencia']['alcancavel'])
                    else res_nx['rota_principal']['caminho_vertices']
                )
                if caminho_dest:
                    regulacao.ultimo_caminho_destacado = caminho_dest
                    regulacao.ultimo_titulo_rota = (
                        f"NetworkX + Haversine: {origem_id} -> {destino_id} "
                        f"({res_nx['rota_principal']['distancia_haversine_m']} m)"
                    )
                return (jsonify(res_nx), 200)

            if algoritmo == 'representacoes':
                return (
                    jsonify(
                        {
                            'algoritmo': 'representacoes_lista09',
                            'matriz_adjacencia': store.grafo.gerar_matriz_adjacencia(),
                            'lista_adjacencia': store.grafo.gerar_lista_adjacencia(),
                        }
                    ),
                    200,
                )

            rota, em_cache = store.obter_rota_com_cache(origem_id, destino_id)
            if rota.alcancavel:
                regulacao.ultimo_caminho_destacado = rota.caminho_vertices
                regulacao.ultimo_titulo_rota = f'Dijkstra: {origem_id} -> {destino_id} ({rota.tempo_total_min} min)'
            return (
                jsonify(
                    {
                        'algoritmo': 'dijkstra',
                        'origem_id': rota.origem_id,
                        'destino_id': rota.destino_id,
                        'alcancavel': rota.alcancavel,
                        'caminho_vertices': rota.caminho_vertices,
                        'vias_percorridas': rota.vias_percorridas,
                        'tempo_total_min': rota.tempo_total_min if rota.alcancavel else None,
                        'distancia_total_km': rota.distancia_total_km,
                        'nos_visitados': rota.nos_visitados,
                        'cache_hash_hit': em_cache,
                    }
                ),
                200,
            )
        except KeyError as erro:
            return (jsonify({'erro': str(erro)}), 400)


@app.post('/api/operacoes/desfazer')
def desfazer_operacao() -> tuple[Response, int]:
    with _lock:
        regulacao: RegulacaoService = _estado['regulacao']
        try:
            res = regulacao.desfazer_ultima_operacao()
        except ValidacaoRegulacaoError as erro:
            return (jsonify({'erro': str(erro)}), 400)
        return (jsonify(res), 200)


@app.get('/api/hash/inspecionar')
def inspecionar_hash() -> Response:
    tipo_busca = request.args.get('tipo', '').strip()
    chave_busca = request.args.get('chave', '').strip()

    with _lock:
        store: Store = _estado['store']
        est_cpf = store.hash_pacientes_cpf.estatisticas()
        est_rotas = store.hash_cache_rotas.estatisticas()
        est_cep = store.hash_unidades_cep.estatisticas()

        resultado_busca = None
        if tipo_busca and chave_busca:
            if tipo_busca == 'cpf':
                cpf_limpo = ''.join(c for c in chave_busca if c.isdigit())
                indice_base = store.hash_pacientes_cpf.calcular_indice_base(cpf_limpo)
                pac = store.buscar_paciente_por_cpf(cpf_limpo)
                token_lgpd = store.hash_pacientes_cpf.gerar_token_lgpd(cpf_limpo)
                _, digest_hmac = store.hash_pacientes_cpf._chave_para_inteiro_hmac(cpf_limpo)
                resultado_busca = {
                    'tabela': 'hash_pacientes_cpf',
                    'metodo_hash': est_cpf.metodo_hash,
                    'metodo_colisao': est_cpf.metodo_colisao,
                    'chave_normalizada': cpf_limpo,
                    'token_lgpd': token_lgpd,
                    'hmac_sha256_completo': digest_hmac,
                    'indice_base_calculado': indice_base,
                    'encontrado': pac is not None,
                    'dados': (
                        {
                            'cpf': pac.cpf,
                            'nome': pac.nome,
                            'token_lgpd': pac.token_lgpd or token_lgpd,
                            'cartao_sus': pac.cartao_sus,
                            'idade': pac.idade,
                            'tipo_sanguineo': pac.tipo_sanguineo,
                            'historico_clinico': pac.historico_clinico,
                        }
                        if pac is not None
                        else None
                    ),
                }
            elif tipo_busca == 'cep':
                cep_limpo = ''.join(c for c in chave_busca if c.isdigit())
                indice_base = store.hash_unidades_cep.calcular_indice_base(cep_limpo)
                hosp = store.buscar_hospital_por_cep(cep_limpo)
                resultado_busca = {
                    'tabela': 'hash_unidades_cep',
                    'metodo_hash': est_cep.metodo_hash,
                    'metodo_colisao': est_cep.metodo_colisao,
                    'chave_normalizada': cep_limpo,
                    'indice_base_calculado': indice_base,
                    'encontrado': hosp is not None,
                    'dados': (
                        {
                            'id': hosp.id,
                            'nome': hosp.nome,
                            'bairro': hosp.bairro,
                            'cep': hosp.cep,
                            'especialidade': hosp.especialidade_principal,
                        }
                        if hosp is not None
                        else None
                    ),
                }
            elif tipo_busca == 'rota':
                indice_base = store.hash_cache_rotas.calcular_indice_base(chave_busca)
                rota_cached = store.hash_cache_rotas.obter(chave_busca)
                resultado_busca = {
                    'tabela': 'hash_cache_rotas',
                    'metodo_hash': est_rotas.metodo_hash,
                    'metodo_colisao': est_rotas.metodo_colisao,
                    'chave_normalizada': chave_busca,
                    'indice_base_calculado': indice_base,
                    'encontrado': rota_cached is not None,
                    'dados': (
                        {
                            'origem_id': rota_cached.origem_id,
                            'destino_id': rota_cached.destino_id,
                            'tempo_total_min': rota_cached.tempo_total_min,
                            'distancia_total_km': rota_cached.distancia_total_km,
                            'caminho_vertices': rota_cached.caminho_vertices,
                        }
                        if rota_cached is not None
                        else None
                    ),
                }

        pacientes_cadastrados = [
            {
                'cpf': p.cpf,
                'nome': p.nome,
                'token_lgpd': p.token_lgpd or store.hash_pacientes_cpf.gerar_token_lgpd(p.cpf),
                'tipo_sanguineo': p.tipo_sanguineo,
                'indice_hash': store.hash_pacientes_cpf.calcular_indice_base(p.cpf),
            }
            for p in store.hash_pacientes_cpf.valores()
        ]

        ceps_cadastrados = [
            {
                'cep': h.cep,
                'nome': h.nome,
                'indice_hash': store.hash_unidades_cep.calcular_indice_base(''.join(c for c in h.cep if c.isdigit())),
            }
            for h in store.hospitais
        ]

        return jsonify(
            {
                'tabelas': [
                    {
                        'id': 'pacientes_cpf',
                        'titulo': 'Pacientes por CPF',
                        'metodo_hash': 'HMAC-SHA256',
                        'metodo_colisao': 'Encadeamento Separado',
                        'capacidade': est_cpf.capacidade,
                        'tamanho': est_cpf.tamanho,
                        'fator_carga': est_cpf.fator_carga,
                        'total_colisoes': est_cpf.total_colisoes,
                        'maior_cadeia_ou_sondagem': est_cpf.maior_cadeia_ou_sondagem,
                        'ocupacao_por_posicao': est_cpf.ocupacao_por_posicao,
                        'justificativa': est_cpf.justificativa_aplicacao,
                    },
                    {
                        'id': 'cache_rotas',
                        'titulo': 'Cache de Rotas',
                        'metodo_hash': 'Multiplicacao (Knuth)',
                        'metodo_colisao': 'Sondagem Quadratica',
                        'capacidade': est_rotas.capacidade,
                        'tamanho': est_rotas.tamanho,
                        'fator_carga': est_rotas.fator_carga,
                        'total_colisoes': est_rotas.total_colisoes,
                        'maior_cadeia_ou_sondagem': est_rotas.maior_cadeia_ou_sondagem,
                        'ocupacao_por_posicao': est_rotas.ocupacao_por_posicao,
                        'justificativa': est_rotas.justificativa_aplicacao,
                    },
                    {
                        'id': 'unidades_cep',
                        'titulo': 'Hospitais por CEP',
                        'metodo_hash': 'Metodo da Dobra (Folding)',
                        'metodo_colisao': 'Sondagem Linear',
                        'capacidade': est_cep.capacidade,
                        'tamanho': est_cep.tamanho,
                        'fator_carga': est_cep.fator_carga,
                        'total_colisoes': est_cep.total_colisoes,
                        'maior_cadeia_ou_sondagem': est_cep.maior_cadeia_ou_sondagem,
                        'ocupacao_por_posicao': est_cep.ocupacao_por_posicao,
                        'justificativa': est_cep.justificativa_aplicacao,
                    },
                ],
                'pacientes_amostra': pacientes_cadastrados,
                'ceps_amostra': ceps_cadastrados,
                'resultado_busca': resultado_busca,
            }
        )


@app.post('/api/hash/simular-avalanche')
def simular_avalanche() -> Response:
    payload = request.get_json(silent=True) or {}
    chave_a = str(payload.get('chave_a', '10482937401')).strip()
    chave_b = str(payload.get('chave_b', '10482937402')).strip()
    from backend.estruturas.tabela_hash import TabelaHash
    res = TabelaHash.simular_efeito_avalanche(chave_a, chave_b)
    return jsonify(res)


@app.post('/api/pacientes')
def cadastrar_paciente_hash() -> tuple[Response, int]:
    payload = request.get_json(silent=True) or {}
    cpf = ''.join(c for c in str(payload.get('cpf', '')) if c.isdigit())
    nome = str(payload.get('nome', '')).strip()
    if len(cpf) < 6 or not nome:
        return (jsonify({'erro': 'Informe CPF (minimo 6 digitos) e nome completo.'}), 400)
    with _lock:
        store: Store = _estado['store']
        pac = Paciente(
            cpf=cpf,
            nome=nome,
            cartao_sus=str(payload.get('cartao_sus') or f'704{cpf[:11].ljust(11, "0")}9'),
            idade=int(payload.get('idade', 35)),
            tipo_sanguineo=str(payload.get('tipo_sanguineo', 'O+')),
            historico_clinico=str(payload.get('historico_clinico', 'Cadastro direto na TabelaHash')),
        )
        store.adicionar_paciente(pac)
        indice = store.hash_pacientes_cpf.calcular_indice_base(cpf)
        est = store.hash_pacientes_cpf.estatisticas()
        return (
            jsonify(
                {
                    'cpf': pac.cpf,
                    'nome': pac.nome,
                    'indice_balde': indice,
                    'total_colisoes': est.total_colisoes,
                    'fator_carga': est.fator_carga,
                }
            ),
            201,
        )


@app.get('/api/ordenacao')
def executar_ordenacao() -> tuple[Response, int]:
    alvo = request.args.get('alvo', 'hospitais')
    criterio = request.args.get('criterio', 'taxa_ocupacao')
    algoritmo = request.args.get('algoritmo', ALGORITMO_QUICKSORT)
    reverso = request.args.get('reverso', 'true').lower() in ('1', 'true', 'sim')

    with _lock:
        regulacao: RegulacaoService = _estado['regulacao']
        try:
            resultado = regulacao.ordenar_e_comparar(
                alvo=alvo,
                criterio=criterio,
                algoritmo=algoritmo,
                reverso=reverso,
            )
        except ValueError as erro:
            return (jsonify({'erro': str(erro)}), 400)
        return (jsonify(resultado), 200)


@app.post('/api/reiniciar')
def reiniciar_demonstracao() -> Response:
    with _lock:
        _estado.update(_inicializar_sistema())
    return jsonify({'ok': True})


@app.get('/api/graficos/malha-viaria.png')
def grafico_malha_viaria() -> Response:
    modo = request.args.get('modo', 'dijkstra')
    origem_id = request.args.get('origem_id') or None
    destino_id = request.args.get('destino_id') or None
    with _lock:
        graficos: GraficoService = _estado['graficos']
        regulacao: RegulacaoService = _estado['regulacao']
        png = graficos.gerar_grafico_grafo_maceio(
            modo=modo,
            origem_id=origem_id,
            destino_id=destino_id,
            caminho_destaque=regulacao.ultimo_caminho_destacado,
        )
    return Response(png, mimetype='image/png', headers={'Cache-Control': 'no-store'})


@app.get('/api/graficos/ordenacao.png')
def grafico_ordenacao() -> Response:
    n_str = request.args.get('n', '120')
    try:
        n = int(n_str)
    except ValueError:
        n = 120
    with _lock:
        graficos: GraficoService = _estado['graficos']
        png = graficos.gerar_grafico_ordenacao(tamanho_amostra=n)
    return Response(png, mimetype='image/png', headers={'Cache-Control': 'no-store'})


@app.get('/api/graficos/hash.png')
def grafico_hash() -> Response:
    with _lock:
        graficos: GraficoService = _estado['graficos']
        png = graficos.gerar_grafico_hash()
    return Response(png, mimetype='image/png', headers={'Cache-Control': 'no-store'})


@app.get('/api/grafo/representacoes')
def obter_representacoes_grafo() -> Response:
    with _lock:
        store: Store = _estado['store']
        return jsonify(
            {
                'matriz_adjacencia': store.grafo.gerar_matriz_adjacencia(),
                'lista_adjacencia': store.grafo.gerar_lista_adjacencia(),
            }
        )


@app.get('/api/mapa/folium')
def mapa_folium_interativo() -> Response:
    origem_id = request.args.get('origem_id') or None
    destino_id = request.args.get('destino_id') or None
    no_indisponivel = request.args.get('no_indisponivel') or None
    autonomia_str = request.args.get('autonomia_m', '3500')
    baixar = request.args.get('download', '0') in ('1', 'true', 'sim')
    try:
        autonomia_val = float(autonomia_str) if autonomia_str not in ('', '0', 'sem_limite') else None
    except ValueError:
        autonomia_val = 3500.0

    with _lock:
        graficos: GraficoService = _estado['graficos']
        regulacao: RegulacaoService = _estado['regulacao']
        html_folium = graficos.gerar_mapa_folium_html(
            origem_id=origem_id,
            destino_id=destino_id,
            no_indisponivel=no_indisponivel,
            autonomia_maxima_m=autonomia_val,
            caminho_destaque=regulacao.ultimo_caminho_destacado,
        )

    headers = {'Cache-Control': 'no-store'}
    if baixar:
        headers['Content-Disposition'] = 'attachment; filename="mapa_rota_folium_maceio.html"'
    return Response(html_folium, mimetype='text/html; charset=utf-8', headers=headers)


if __name__ == '__main__':
    app.run(host=config.host, port=config.porta, debug=config.debug)

