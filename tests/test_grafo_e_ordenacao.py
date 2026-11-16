import math
from backend.estruturas import (
    GrafoGeolocalizado,
    VerticeGrafo,
    bubble_sort,
    calcular_haversine,
    comparar_todos_algoritmos,
    insertion_sort,
    quick_sort,
    selection_sort,
)


def _construir_grafo_teste() -> GrafoGeolocalizado:
    g = GrafoGeolocalizado()
    g.adicionar_vertice(VerticeGrafo('A', 'Base Farol', 'Farol', 'base_samu', -9.6462, -35.7348))
    g.adicionar_vertice(VerticeGrafo('B', 'Pinheiro', 'Pinheiro', 'cruzamento', -9.6324, -35.7381))
    g.adicionar_vertice(VerticeGrafo('C', 'Levada', 'Levada', 'cruzamento', -9.6652, -35.7485))
    g.adicionar_vertice(VerticeGrafo('D', 'HGE', 'Trapiche', 'hospital', -9.6712, -35.7568))
    g.adicionar_aresta('A', 'B', 'Via AB', velocidade_media_kmh=60.0, distancia_km=2.0)
    g.adicionar_aresta('B', 'D', 'Via BD', velocidade_media_kmh=60.0, distancia_km=3.0)
    g.adicionar_aresta('A', 'C', 'Via AC', velocidade_media_kmh=30.0, distancia_km=4.0)
    g.adicionar_aresta('C', 'D', 'Via CD', velocidade_media_kmh=30.0, distancia_km=4.0)
    return g


def test_grafo_dijkstra_e_bloqueio_via() -> None:
    g = _construir_grafo_teste()
    rota1 = g.dijkstra('A', 'D')
    assert rota1.alcancavel
    assert rota1.caminho_vertices == ['A', 'B', 'D']
    assert rota1.tempo_total_min == 5.0

    g.atualizar_estado_via('B', 'D', bloqueada=True)
    rota2 = g.dijkstra('A', 'D')
    assert rota2.alcancavel
    assert rota2.caminho_vertices == ['A', 'C', 'D']
    assert rota2.tempo_total_min == 16.0


def test_grafo_bfs_dfs_e_mst_prim() -> None:
    g = _construir_grafo_teste()
    bfs = g.bfs_por_saltos('A', max_saltos=1)
    ids_alcancados = {item['id'] for item in bfs}
    assert ids_alcancados == {'A', 'B', 'C'}

    dfs = g.dfs_conectividade('A')
    assert dfs['conexo'] is True

    mst = g.arvore_geradora_minima_prim('A')
    assert mst.conexo is True
    assert len(mst.arestas) == 3


def test_quatro_algoritmos_ordenacao() -> None:
    entrada = [42, 7, 19, 3, 88, 12, 7, 1, 55, 29]
    esperado_crescente = sorted(entrada)
    esperado_decrescente = sorted(entrada, reverse=True)

    for fn in (bubble_sort, insertion_sort, selection_sort, quick_sort):
        ord_cresc, met_c = fn(entrada, reverso=False)
        assert ord_cresc == esperado_crescente
        assert met_c.comparacoes > 0
        assert met_c.tamanho_entrada == len(entrada)

        ord_dec, _ = fn(entrada, reverso=True)
        assert ord_dec == esperado_decrescente

    comp = comparar_todos_algoritmos(entrada)
    assert len(comp) == 4


def test_lista08_lista09_haversine_networkx_autonomia_e_contingencia() -> None:
    sp = (-23.5505, -46.6333)
    rj = (-22.9068, -43.1729)
    dist_km = calcular_haversine(sp, rj, em_metros=False)
    dist_m = calcular_haversine({'lat': sp[0], 'lon': sp[1]}, {'lat': rj[0], 'lon': rj[1]}, em_metros=True)
    assert 350.0 < dist_km < 365.0
    assert math.isclose(dist_km * 1000.0, dist_m, rel_tol=1e-6)

    g = _construir_grafo_teste()
    mat = g.gerar_matriz_adjacencia()
    assert mat['dimensao'] == '4x4'
    assert len(mat['matriz_binaria']) == 4

    lista_adj = g.gerar_lista_adjacencia()
    assert lista_adj['total_vertices'] == 4
    assert 'A' in lista_adj['adjacencia']

    res_nx = g.analisar_resiliencia_networkx(
        origem_id='A',
        destino_id='D',
        no_indisponivel='B',
        autonomia_maxima_m=5000.0,
    )
    assert res_nx['rota_principal']['alcancavel'] is True
    assert res_nx['contingencia']['alcancavel'] is True
    assert 'B' not in res_nx['contingencia']['caminho_vertices']
    assert res_nx['contingencia']['caminho_vertices'] == ['A', 'C', 'D']


