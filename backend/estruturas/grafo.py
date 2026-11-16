import math
from dataclasses import dataclass
from typing import Any, Optional, Union
import networkx as nx
from backend.estruturas.ordenacao import quick_sort
from backend.estruturas.fila import Fila
from backend.estruturas.lista_encadeada import ListaEncadeada
from backend.estruturas.pilha import Pilha
from backend.estruturas.tabela_hash import (
    COLISAO_ENCADEAMENTO,
    METODO_DIVISAO_HORNER,
    TabelaHash,
)

RAIO_TERRA_KM = 6371.0
RAIO_TERRA_M = 6_371_000.0

CoordenadaGeografica = Union[tuple[float, float], dict[str, float]]


def _extrair_lat_lon(coord: CoordenadaGeografica) -> tuple[float, float]:
    if isinstance(coord, dict):
        lat = coord.get('lat', coord.get('latitude', 0.0))
        lon = coord.get('lon', coord.get('longitude', 0.0))
        return (float(lat), float(lon))
    return (float(coord[0]), float(coord[1]))


def calcular_haversine(
    coord1: CoordenadaGeografica,
    coord2: CoordenadaGeografica,
    em_metros: bool = False,
) -> float:
    lat1, lon1 = _extrair_lat_lon(coord1)
    lat2, lon2 = _extrair_lat_lon(coord2)
    raio = RAIO_TERRA_M if em_metros else RAIO_TERRA_KM
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return raio * c


def distancia_haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return calcular_haversine((lat1, lon1), (lat2, lon2), em_metros=False)



@dataclass
class VerticeGrafo:
    id: str
    nome: str
    bairro: str
    tipo: str
    latitude: float
    longitude: float


@dataclass
class ArestaGrafo:
    origem_id: str
    destino_id: str
    nome_via: str
    distancia_km: float
    velocidade_media_kmh: float
    fator_transito: float = 1.0
    bloqueada: bool = False

    @property
    def tempo_minutos(self) -> float:
        if self.bloqueada:
            return float('inf')
        velocidade_efetiva = max(5.0, self.velocidade_media_kmh / max(0.2, self.fator_transito))
        return (self.distancia_km / velocidade_efetiva) * 60.0


@dataclass
class ResultadoCaminhoMinimo:
    origem_id: str
    destino_id: str
    caminho_vertices: list[str]
    vias_percorridas: list[str]
    tempo_total_min: float
    distancia_total_km: float
    nos_visitados: int
    alcancavel: bool


@dataclass
class ResultadoMST:
    arestas: list[ArestaGrafo]
    custo_total_min: float
    distancia_total_km: float
    total_vertices_conectados: int
    conexo: bool


class GrafoGeolocalizado:

    def __init__(self) -> None:
        self._vertices: TabelaHash[str, VerticeGrafo] = TabelaHash(
            capacidade_inicial=53,
            metodo_hash=METODO_DIVISAO_HORNER,
            metodo_colisao=COLISAO_ENCADEAMENTO,
            justificativa_aplicacao='Indice de vertices do grafo urbano por ID',
        )
        self._adjacencia: TabelaHash[str, ListaEncadeada[ArestaGrafo]] = TabelaHash(
            capacidade_inicial=53,
            metodo_hash=METODO_DIVISAO_HORNER,
            metodo_colisao=COLISAO_ENCADEAMENTO,
            justificativa_aplicacao='Lista de adjacencia encadeada de cada no viario',
        )

    def adicionar_vertice(self, vertice: VerticeGrafo) -> None:
        self._vertices.inserir(vertice.id, vertice)
        if not self._adjacencia.contem(vertice.id):
            self._adjacencia.inserir(vertice.id, ListaEncadeada())

    def obter_vertice(self, vertice_id: str) -> Optional[VerticeGrafo]:
        return self._vertices.obter(vertice_id)

    def listar_vertices(self) -> list[VerticeGrafo]:
        return self._vertices.valores()

    def adicionar_aresta(
        self,
        origem_id: str,
        destino_id: str,
        nome_via: str,
        velocidade_media_kmh: float = 45.0,
        fator_transito: float = 1.0,
        bidirecional: bool = True,
        distancia_km: Optional[float] = None,
    ) -> None:
        v_orig = self._vertices.obter(origem_id)
        v_dest = self._vertices.obter(destino_id)
        if v_orig is None or v_dest is None:
            raise KeyError(f'vertice inexistente para aresta {origem_id} -> {destino_id}')
        dist = (
            distancia_km
            if distancia_km is not None
            else round(distancia_haversine_km(v_orig.latitude, v_orig.longitude, v_dest.latitude, v_dest.longitude) * 1.22, 2)
        )
        dist = max(0.15, dist)
        self._inserir_aresta_direcionada(
            ArestaGrafo(
                origem_id=origem_id,
                destino_id=destino_id,
                nome_via=nome_via,
                distancia_km=dist,
                velocidade_media_kmh=velocidade_media_kmh,
                fator_transito=fator_transito,
                bloqueada=False,
            )
        )
        if bidirecional:
            self._inserir_aresta_direcionada(
                ArestaGrafo(
                    origem_id=destino_id,
                    destino_id=origem_id,
                    nome_via=nome_via,
                    distancia_km=dist,
                    velocidade_media_kmh=velocidade_media_kmh,
                    fator_transito=fator_transito,
                    bloqueada=False,
                )
            )

    def _inserir_aresta_direcionada(self, aresta: ArestaGrafo) -> None:
        adj = self._adjacencia.obter(aresta.origem_id)
        if adj is None:
            adj = ListaEncadeada()
            self._adjacencia.inserir(aresta.origem_id, adj)
        adj.remover_onde(lambda a: a.destino_id == aresta.destino_id)
        adj.inserir_no_fim(aresta)

    def vizinhos(self, vertice_id: str) -> list[ArestaGrafo]:
        adj = self._adjacencia.obter(vertice_id)
        return adj.para_lista() if adj is not None else []

    def listar_arestas_unicas(self) -> list[ArestaGrafo]:
        vistas: set[tuple[str, str]] = set()
        saida: list[ArestaGrafo] = []
        for vertice_id, lista_adj in self._adjacencia.itens():
            for aresta in lista_adj:
                par = (
                    (aresta.origem_id, aresta.destino_id)
                    if aresta.origem_id <= aresta.destino_id
                    else (aresta.destino_id, aresta.origem_id)
                )
                if par not in vistas:
                    vistas.add(par)
                    saida.append(aresta)
        return saida

    def atualizar_estado_via(
        self,
        origem_id: str,
        destino_id: str,
        fator_transito: Optional[float] = None,
        bloqueada: Optional[bool] = None,
    ) -> tuple[float, bool]:
        aresta_ab = self._buscar_aresta(origem_id, destino_id)
        aresta_ba = self._buscar_aresta(destino_id, origem_id)
        if aresta_ab is None:
            raise KeyError(f'via nao encontrada entre {origem_id} e {destino_id}')
        fator_anterior = aresta_ab.fator_transito
        bloqueada_anterior = aresta_ab.bloqueada
        for aresta in (aresta_ab, aresta_ba):
            if aresta is not None:
                if fator_transito is not None:
                    aresta.fator_transito = max(0.5, min(5.0, float(fator_transito)))
                if bloqueada is not None:
                    aresta.bloqueada = bool(bloqueada)
        return (fator_anterior, bloqueada_anterior)

    def _buscar_aresta(self, origem_id: str, destino_id: str) -> Optional[ArestaGrafo]:
        adj = self._adjacencia.obter(origem_id)
        if adj is None:
            return None
        return adj.encontrar(lambda a: a.destino_id == destino_id)

    def dijkstra(self, origem_id: str, destino_id: str) -> ResultadoCaminhoMinimo:
        if self._vertices.obter(origem_id) is None or self._vertices.obter(destino_id) is None:
            raise KeyError('vertice de origem ou destino inexistente')

        todos_ids = self._vertices.chaves()
        dist_min: dict[str, float] = {vid: float('inf') for vid in todos_ids}
        dist_km_acum: dict[str, float] = {vid: 0.0 for vid in todos_ids}
        anterior: dict[str, Optional[str]] = {vid: None for vid in todos_ids}
        via_anterior: dict[str, str] = {}
        visitados: set[str] = set()

        dist_min[origem_id] = 0.0
        nos_visitados = 0

        while len(visitados) < len(todos_ids):
            atual: Optional[str] = None
            menor_custo = float('inf')
            for vid in todos_ids:
                if vid not in visitados and dist_min[vid] < menor_custo:
                    menor_custo = dist_min[vid]
                    atual = vid
            if atual is None or menor_custo == float('inf'):
                break
            visitados.add(atual)
            nos_visitados += 1
            if atual == destino_id:
                break

            for aresta in self.vizinhos(atual):
                if aresta.bloqueada or aresta.destino_id in visitados:
                    continue
                novo_tempo = dist_min[atual] + aresta.tempo_minutos
                if novo_tempo < dist_min[aresta.destino_id]:
                    dist_min[aresta.destino_id] = novo_tempo
                    dist_km_acum[aresta.destino_id] = dist_km_acum[atual] + aresta.distancia_km
                    anterior[aresta.destino_id] = atual
                    via_anterior[aresta.destino_id] = aresta.nome_via

        if dist_min[destino_id] == float('inf'):
            return ResultadoCaminhoMinimo(
                origem_id=origem_id,
                destino_id=destino_id,
                caminho_vertices=[],
                vias_percorridas=[],
                tempo_total_min=float('inf'),
                distancia_total_km=0.0,
                nos_visitados=nos_visitados,
                alcancavel=False,
            )

        pilha_caminho: Pilha[str] = Pilha()
        cursor: Optional[str] = destino_id
        while cursor is not None:
            pilha_caminho.empilhar(cursor)
            cursor = anterior[cursor]

        caminho = pilha_caminho.para_lista()
        vias: list[str] = []
        for idx in range(1, len(caminho)):
            vias.append(via_anterior.get(caminho[idx], ''))

        return ResultadoCaminhoMinimo(
            origem_id=origem_id,
            destino_id=destino_id,
            caminho_vertices=caminho,
            vias_percorridas=vias,
            tempo_total_min=round(dist_min[destino_id], 2),
            distancia_total_km=round(dist_km_acum[destino_id], 2),
            nos_visitados=nos_visitados,
            alcancavel=True,
        )

    def bfs_por_saltos(self, origem_id: str, max_saltos: int = 3) -> list[dict[str, object]]:
        if self._vertices.obter(origem_id) is None:
            raise KeyError(f'vertice inexistente: {origem_id}')
        fila: Fila[tuple[str, int]] = Fila()
        visitados: set[str] = {origem_id}
        fila.enfileirar((origem_id, 0))
        resultado: list[dict[str, object]] = []

        while not fila.esta_vazia():
            atual_id, saltos = fila.desenfileirar()
            vertice = self._vertices.obter(atual_id)
            if vertice is not None:
                resultado.append(
                    {
                        'id': vertice.id,
                        'nome': vertice.nome,
                        'bairro': vertice.bairro,
                        'tipo': vertice.tipo,
                        'saltos': saltos,
                    }
                )
            if saltos >= max_saltos:
                continue
            for aresta in self.vizinhos(atual_id):
                if not aresta.bloqueada and aresta.destino_id not in visitados:
                    visitados.add(aresta.destino_id)
                    fila.enfileirar((aresta.destino_id, saltos + 1))
        return resultado

    def dfs_conectividade(self, origem_id: Optional[str] = None) -> dict[str, object]:
        todos_ids = self._vertices.chaves()
        if not todos_ids:
            return {'conexo': True, 'alcancados': [], 'isolados': []}
        inicio = origem_id if origem_id in todos_ids else todos_ids[0]
        pilha: Pilha[str] = Pilha()
        visitados: set[str] = set()
        ordem_visita: list[str] = []
        pilha.empilhar(inicio)

        while not pilha.esta_vazia():
            atual = pilha.desempilhar()
            if atual in visitados:
                continue
            visitados.add(atual)
            ordem_visita.append(atual)
            for aresta in self.vizinhos(atual):
                if not aresta.bloqueada and aresta.destino_id not in visitados:
                    pilha.empilhar(aresta.destino_id)

        isolados = [vid for vid in todos_ids if vid not in visitados]
        return {
            'conexo': len(isolados) == 0,
            'origem_busca': inicio,
            'total_vertices': len(todos_ids),
            'alcancados': ordem_visita,
            'isolados': isolados,
        }

    def arvore_geradora_minima_prim(self, origem_id: Optional[str] = None) -> ResultadoMST:
        todos_ids = self._vertices.chaves()
        if not todos_ids:
            return ResultadoMST(arestas=[], custo_total_min=0.0, distancia_total_km=0.0, total_vertices_conectados=0, conexo=True)

        inicio = origem_id if origem_id in todos_ids else todos_ids[0]
        na_arvore: set[str] = {inicio}
        arestas_mst: list[ArestaGrafo] = []
        custo_total = 0.0
        dist_total = 0.0

        while len(na_arvore) < len(todos_ids):
            melhor_aresta: Optional[ArestaGrafo] = None
            menor_peso = float('inf')
            for u in na_arvore:
                for aresta in self.vizinhos(u):
                    if aresta.bloqueada or aresta.destino_id in na_arvore:
                        continue
                    if aresta.tempo_minutos < menor_peso:
                        menor_peso = aresta.tempo_minutos
                        melhor_aresta = aresta
            if melhor_aresta is None:
                break
            na_arvore.add(melhor_aresta.destino_id)
            arestas_mst.append(melhor_aresta)
            custo_total += melhor_aresta.tempo_minutos
            dist_total += melhor_aresta.distancia_km

        return ResultadoMST(
            arestas=arestas_mst,
            custo_total_min=round(custo_total, 2),
            distancia_total_km=round(dist_total, 2),
            total_vertices_conectados=len(na_arvore),
            conexo=len(na_arvore) == len(todos_ids),
        )

    def gerar_matriz_adjacencia(self) -> dict[str, Any]:
        vertices_ordenados = quick_sort(self.listar_vertices(), chave=lambda v: v.id)[0]
        ids = [v.id for v in vertices_ordenados]
        indice_por_id = {vid: idx for idx, vid in enumerate(ids)}
        n = len(ids)
        matriz_binaria = [[0] * n for _ in range(n)]
        matriz_pesos_min = [[0.0] * n for _ in range(n)]

        for u_id in ids:
            i = indice_por_id[u_id]
            for aresta in self.vizinhos(u_id):
                if aresta.bloqueada or aresta.destino_id not in indice_por_id:
                    continue
                j = indice_por_id[aresta.destino_id]
                matriz_binaria[i][j] = 1
                matriz_pesos_min[i][j] = round(aresta.tempo_minutos, 2)

        return {
            'ordem_vertices': ids,
            'dimensao': f'{n}x{n}',
            'complexidade_espaco': f'O(V^2) = {n * n} celulas',
            'matriz_binaria': matriz_binaria,
            'matriz_pesos_min': matriz_pesos_min,
        }

    def gerar_lista_adjacencia(self) -> dict[str, Any]:
        vertices_ordenados = quick_sort(self.listar_vertices(), chave=lambda v: v.id)[0]
        lista_adj: dict[str, list[dict[str, Any]]] = {}
        total_arestas_ativas = 0

        for v in vertices_ordenados:
            vizinhos_formatados = []
            for aresta in self.vizinhos(v.id):
                vd = self.obter_vertice(aresta.destino_id)
                dist_haversine_m = (
                    round(
                        calcular_haversine(
                            (v.latitude, v.longitude),
                            (vd.latitude, vd.longitude),
                            em_metros=True,
                        ),
                        2,
                    )
                    if vd is not None
                    else round(aresta.distancia_km * 1000.0, 2)
                )
                if not aresta.bloqueada:
                    total_arestas_ativas += 1
                vizinhos_formatados.append(
                    {
                        'destino_id': aresta.destino_id,
                        'nome_via': aresta.nome_via,
                        'tempo_minutos': round(aresta.tempo_minutos, 2) if not aresta.bloqueada else None,
                        'distancia_km': aresta.distancia_km,
                        'distancia_haversine_m': dist_haversine_m,
                        'bloqueada': aresta.bloqueada,
                    }
                )
            lista_adj[v.id] = vizinhos_formatados

        return {
            'total_vertices': len(vertices_ordenados),
            'total_arestas_direcionadas_ativas': total_arestas_ativas,
            'complexidade_espaco': f'O(V + A) = {len(vertices_ordenados)} + {total_arestas_ativas}',
            'adjacencia': lista_adj,
        }

    def construir_grafo_networkx(
        self,
        direcionado: bool = True,
        criterio_peso: str = 'distancia_haversine_m',
    ) -> Union[nx.DiGraph, nx.Graph]:
        grafo_nx: Union[nx.DiGraph, nx.Graph] = nx.DiGraph() if direcionado else nx.Graph()
        vertices = {v.id: v for v in self.listar_vertices()}

        for v in vertices.values():
            grafo_nx.add_node(
                v.id,
                pos=(v.latitude, v.longitude),
                lat=v.latitude,
                lon=v.longitude,
                nome=v.nome,
                bairro=v.bairro,
                tipo=v.tipo,
            )

        for v_id, v_orig in vertices.items():
            for aresta in self.vizinhos(v_id):
                if aresta.bloqueada:
                    continue
                v_dest = vertices.get(aresta.destino_id)
                if v_dest is None:
                    continue
                dist_hav_m = round(
                    calcular_haversine(
                        {'lat': v_orig.latitude, 'lon': v_orig.longitude},
                        {'lat': v_dest.latitude, 'lon': v_dest.longitude},
                        em_metros=True,
                    ),
                    2,
                )
                dist_hav_km = round(dist_hav_m / 1000.0, 3)
                tempo_min = round(aresta.tempo_minutos, 2)

                if criterio_peso == 'tempo_minutos':
                    peso_principal = tempo_min
                elif criterio_peso == 'distancia_km':
                    peso_principal = aresta.distancia_km
                else:
                    peso_principal = dist_hav_m

                grafo_nx.add_edge(
                    aresta.origem_id,
                    aresta.destino_id,
                    weight=peso_principal,
                    distancia_haversine_m=dist_hav_m,
                    distancia_haversine_km=dist_hav_km,
                    distancia_viaria_km=aresta.distancia_km,
                    tempo_minutos=tempo_min,
                    nome_via=aresta.nome_via,
                )

        return grafo_nx

    def aplicar_restricao_autonomia_nx(
        self,
        grafo_nx: Union[nx.DiGraph, nx.Graph],
        autonomia_maxima_m: float = 3500.0,
    ) -> tuple[Union[nx.DiGraph, nx.Graph], list[dict[str, Any]]]:
        grafo_filtrado = grafo_nx.copy()
        arestas_removidas: list[dict[str, Any]] = []
        pares_remover: list[tuple[str, str]] = []

        for u, v, dados in grafo_filtrado.edges(data=True):
            dist_m = float(dados.get('distancia_haversine_m', dados.get('weight', 0.0)))
            if dist_m > autonomia_maxima_m:
                pares_remover.append((u, v))
                arestas_removidas.append(
                    {
                        'origem_id': u,
                        'destino_id': v,
                        'nome_via': dados.get('nome_via', ''),
                        'distancia_haversine_m': round(dist_m, 2),
                    }
                )

        grafo_filtrado.remove_edges_from(pares_remover)
        return (grafo_filtrado, arestas_removidas)

    def analisar_resiliencia_networkx(
        self,
        origem_id: str,
        destino_id: str,
        no_indisponivel: Optional[str] = None,
        autonomia_maxima_m: Optional[float] = None,
        criterio_peso: str = 'distancia_haversine_m',
    ) -> dict[str, Any]:
        if self._vertices.obter(origem_id) is None or self._vertices.obter(destino_id) is None:
            raise KeyError('vertice de origem ou destino inexistente')

        grafo_base = self.construir_grafo_networkx(direcionado=True, criterio_peso=criterio_peso)
        arestas_removidas: list[dict[str, Any]] = []

        if autonomia_maxima_m is not None and autonomia_maxima_m > 0:
            grafo_operacional, arestas_removidas = self.aplicar_restricao_autonomia_nx(
                grafo_base, autonomia_maxima_m=float(autonomia_maxima_m)
            )
        else:
            grafo_operacional = grafo_base.copy()

        rota_principal: list[str] = []
        custo_principal: Optional[float] = None
        dist_haversine_principal_m = 0.0
        tempo_principal_min = 0.0
        alcancavel_principal = False

        try:
            if nx.has_path(grafo_operacional, origem_id, destino_id):
                rota_principal = list(
                    nx.shortest_path(grafo_operacional, source=origem_id, target=destino_id, weight='weight')
                )
                custo_principal = round(
                    float(
                        nx.shortest_path_length(
                            grafo_operacional, source=origem_id, target=destino_id, weight='weight'
                        )
                    ),
                    2,
                )
                for u, v in zip(rota_principal, rota_principal[1:]):
                    dados_uv = grafo_operacional[u][v]
                    dist_haversine_principal_m += float(dados_uv.get('distancia_haversine_m', 0.0))
                    tempo_principal_min += float(dados_uv.get('tempo_minutos', 0.0))
                alcancavel_principal = True
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            alcancavel_principal = False

        no_falha_efetivo = (no_indisponivel or '').strip()
        escolha_automatica = not no_falha_efetivo or no_falha_efetivo in (origem_id, destino_id)
        if escolha_automatica:
            intermediarios = rota_principal[1:-1] if len(rota_principal) >= 3 else []
            escolhido = ''
            for cand in intermediarios:
                g_teste = grafo_operacional.copy()
                if cand in g_teste:
                    g_teste.remove_node(cand)
                    if nx.has_path(g_teste, origem_id, destino_id):
                        escolhido = cand
                        break
            if not escolhido and intermediarios:
                escolhido = intermediarios[0]
            elif not escolhido:
                candidatos = [vid for vid in self._vertices.chaves() if vid not in (origem_id, destino_id)]
                escolhido = candidatos[0] if candidatos else ''
            no_falha_efetivo = escolhido

        grafo_contingencia = grafo_operacional.copy()
        if no_falha_efetivo and no_falha_efetivo in grafo_contingencia:
            grafo_contingencia.remove_node(no_falha_efetivo)
        if (
            escolha_automatica
            and origem_id in grafo_contingencia
            and destino_id in grafo_contingencia
            and not nx.has_path(grafo_contingencia, origem_id, destino_id)
        ):
            grafo_contingencia = grafo_base.copy()
            if no_falha_efetivo and no_falha_efetivo in grafo_contingencia:
                grafo_contingencia.remove_node(no_falha_efetivo)

        rota_contingencia: list[str] = []
        custo_contingencia: Optional[float] = None
        dist_haversine_contingencia_m = 0.0
        tempo_contingencia_min = 0.0
        alcancavel_contingencia = False

        try:
            if (
                origem_id in grafo_contingencia
                and destino_id in grafo_contingencia
                and nx.has_path(grafo_contingencia, origem_id, destino_id)
            ):
                rota_contingencia = list(
                    nx.shortest_path(grafo_contingencia, source=origem_id, target=destino_id, weight='weight')
                )
                custo_contingencia = round(
                    float(
                        nx.shortest_path_length(
                            grafo_contingencia, source=origem_id, target=destino_id, weight='weight'
                        )
                    ),
                    2,
                )
                for u, v in zip(rota_contingencia, rota_contingencia[1:]):
                    dados_uv = grafo_contingencia[u][v]
                    dist_haversine_contingencia_m += float(dados_uv.get('distancia_haversine_m', 0.0))
                    tempo_contingencia_min += float(dados_uv.get('tempo_minutos', 0.0))
                alcancavel_contingencia = True
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            alcancavel_contingencia = False

        arestas_mantidas_unicas = []
        vistas_mantidas: set[tuple[str, str]] = set()
        for u, v, d in grafo_operacional.edges(data=True):
            par = (u, v) if u <= v else (v, u)
            if par not in vistas_mantidas:
                vistas_mantidas.add(par)
                arestas_mantidas_unicas.append(
                    {
                        'origem_id': u,
                        'destino_id': v,
                        'nome_via': d.get('nome_via', ''),
                        'distancia_haversine_m': d.get('distancia_haversine_m', 0.0),
                        'tempo_minutos': d.get('tempo_minutos', 0.0),
                    }
                )

        arestas_removidas_unicas = []
        vistas_rem: set[tuple[str, str]] = set()
        for item in arestas_removidas:
            u, v = item['origem_id'], item['destino_id']
            par = (u, v) if u <= v else (v, u)
            if par not in vistas_rem:
                vistas_rem.add(par)
                arestas_removidas_unicas.append(item)

        return {
            'algoritmo': 'networkx_haversine_resiliencia',
            'referencia_listas': 'Lista 08 (Haversine + NetworkX + Folium) & Lista 09 (Autonomia + Contingência + Matriz/Lista Adj)',
            'origem_id': origem_id,
            'destino_id': destino_id,
            'criterio_peso': criterio_peso,
            'autonomia_maxima_m': autonomia_maxima_m,
            'metricas_grafo_nx': {
                'tipo_grafo': 'nx.DiGraph (Direcionado e Ponderado)',
                'total_vertices': grafo_operacional.number_of_nodes(),
                'arestas_ativas_direcionadas': grafo_operacional.number_of_edges(),
                'arestas_mantidas_unicas': len(arestas_mantidas_unicas),
                'arestas_removidas_por_autonomia': len(arestas_removidas_unicas),
                'densidade': round(nx.density(grafo_operacional), 4),
            },
            'rota_principal': {
                'alcancavel': alcancavel_principal,
                'caminho_vertices': rota_principal,
                'custo_ponderado': custo_principal,
                'distancia_haversine_m': round(dist_haversine_principal_m, 2),
                'distancia_haversine_km': round(dist_haversine_principal_m / 1000.0, 2),
                'tempo_estimado_min': round(tempo_principal_min, 2),
            },
            'contingencia': {
                'no_indisponivel': no_falha_efetivo,
                'alcancavel': alcancavel_contingencia,
                'caminho_vertices': rota_contingencia,
                'custo_ponderado': custo_contingencia,
                'distancia_haversine_m': round(dist_haversine_contingencia_m, 2),
                'distancia_haversine_km': round(dist_haversine_contingencia_m / 1000.0, 2),
                'tempo_estimado_min': round(tempo_contingencia_min, 2),
                'desvio_necessario': rota_principal != rota_contingencia,
            },
            'arestas_removidas_detalhe': arestas_removidas_unicas,
        }


