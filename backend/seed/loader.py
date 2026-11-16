import json
from backend.domain.entidades import (
    STATUS_OCORRENCIA_TRIAGEM,
    Ambulancia,
    Hospital,
    Ocorrencia,
    Paciente,
)
from backend.estruturas import VerticeGrafo
from backend.repository.store import Store


def carregar_seed(caminho_json: str, store: Store) -> None:
    with open(caminho_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    for v in dados.get('vertices', []):
        store.grafo.adicionar_vertice(
            VerticeGrafo(
                id=v['id'],
                nome=v['nome'],
                bairro=v['bairro'],
                tipo=v['tipo'],
                latitude=float(v['latitude']),
                longitude=float(v['longitude']),
            )
        )

    for a in dados.get('arestas', []):
        store.grafo.adicionar_aresta(
            origem_id=a['origem_id'],
            destino_id=a['destino_id'],
            nome_via=a['nome_via'],
            velocidade_media_kmh=float(a.get('velocidade_media_kmh', 45.0)),
            fator_transito=float(a.get('fator_transito', 1.0)),
            bidirecional=True,
        )

    for h in dados.get('hospitais', []):
        store.adicionar_hospital(
            Hospital(
                id=h['id'],
                vertice_id=h['vertice_id'],
                nome=h['nome'],
                bairro=h['bairro'],
                cep=h['cep'],
                latitude=float(h['latitude']),
                longitude=float(h['longitude']),
                leitos_totais=int(h['leitos_totais']),
                leitos_ocupados=int(h['leitos_ocupados']),
                especialidade_principal=h['especialidade_principal'],
            )
        )

    for amb in dados.get('ambulancias', []):
        store.adicionar_ambulancia(
            Ambulancia(
                id=amb['id'],
                codigo=amb['codigo'],
                tipo=amb['tipo'],
                base_vertice_id=amb['base_vertice_id'],
                vertice_atual_id=amb['vertice_atual_id'],
                status=amb.get('status', 'disponivel'),
                km_rodados=float(amb.get('km_rodados', 0.0)),
                total_atendimentos=int(amb.get('total_atendimentos', 0)),
            )
        )

    for p in dados.get('pacientes', []):
        store.adicionar_paciente(
            Paciente(
                cpf=p['cpf'],
                nome=p['nome'],
                cartao_sus=p['cartao_sus'],
                idade=int(p['idade']),
                tipo_sanguineo=p['tipo_sanguineo'],
                historico_clinico=p['historico_clinico'],
            )
        )

    for oc in dados.get('ocorrencias_iniciais', []):
        oid = store.novo_id_ocorrencia()
        store.registrar_ocorrencia_triagem(
            Ocorrencia(
                id=oid,
                paciente_cpf=oc['paciente_cpf'],
                paciente_nome=oc['paciente_nome'],
                vertice_id=oc['vertice_id'],
                bairro=oc['bairro'],
                descricao=oc['descricao'],
                prioridade=oc['prioridade'],
                nivel_gravidade=int(oc['nivel_gravidade']),
                status=STATUS_OCORRENCIA_TRIAGEM,
                criada_em=oc.get('criada_em', ''),
            )
        )

    for h_orig in store.hospitais:
        for amb_item in store.ambulancias:
            store.obter_rota_com_cache(amb_item.base_vertice_id, h_orig.vertice_id)

