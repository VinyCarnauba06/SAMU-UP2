import io
import os
from typing import Optional
import folium
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import networkx as nx
from backend.estruturas import calcular_haversine, comparar_todos_algoritmos
from backend.repository.store import Store


class GraficoService:

    def __init__(self, store: Store) -> None:
        self._store = store

    def _renderizar_png(self, fig: Figure) -> bytes:
        buffer = io.BytesIO()
        FigureCanvasAgg(fig).print_png(buffer)
        return buffer.getvalue()

    def gerar_grafico_grafo_maceio(
        self,
        modo: str = 'dijkstra',
        origem_id: Optional[str] = None,
        destino_id: Optional[str] = None,
        caminho_destaque: Optional[list[str]] = None,
    ) -> bytes:
        fig = Figure(figsize=(8.8, 5.2), dpi=110, facecolor='#F6F5F1')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#EFECE6')

        vertices = {v.id: v for v in self._store.grafo.listar_vertices()}
        arestas = self._store.grafo.listar_arestas_unicas()

        pares_destaque: set[tuple[str, str]] = set()
        subtitulo = 'Malha Viária Completa Ponderada por Tempo de Resposta (min)'

        if modo == 'networkx':
            orig_nx = origem_id if (origem_id and origem_id in vertices) else 'v-samu-farol'
            dest_nx = destino_id if (destino_id and destino_id in vertices) else 'v-hge'
            analise_nx = self._store.grafo.analisar_resiliencia_networkx(
                origem_id=orig_nx,
                destino_id=dest_nx,
                autonomia_maxima_m=3500.0,
                criterio_peso='distancia_haversine_m',
            )
            grafo_nx = self._store.grafo.construir_grafo_networkx(direcionado=True)
            pos_nx = {vid: (v.longitude, v.latitude) for vid, v in vertices.items()}
            rotulos_nos = {
                vid: (v.bairro if v.tipo == 'cruzamento' else v.nome.split(' - ')[0])
                for vid, v in vertices.items()
            }
            cores_nos = [
                '#C81E1E' if vertices[n].tipo == 'hospital' else ('#1D4ED8' if vertices[n].tipo == 'base_samu' else '#4B5563')
                for n in grafo_nx.nodes()
            ]
            nx.draw_networkx_edges(
                grafo_nx,
                pos_nx,
                ax=ax,
                edge_color='#9CA3AF',
                width=1.3,
                arrows=True,
                arrowsize=10,
                alpha=0.65,
            )
            caminho_p = analise_nx['rota_principal']['caminho_vertices']
            if len(caminho_p) > 1:
                arestas_p = list(zip(caminho_p, caminho_p[1:]))
                nx.draw_networkx_edges(
                    grafo_nx,
                    pos_nx,
                    edgelist=arestas_p,
                    ax=ax,
                    edge_color='#C81E1E',
                    width=3.2,
                    arrows=True,
                    arrowsize=14,
                )
            caminho_c = analise_nx['contingencia']['caminho_vertices']
            if len(caminho_c) > 1 and caminho_c != caminho_p:
                arestas_c = list(zip(caminho_c, caminho_c[1:]))
                nx.draw_networkx_edges(
                    grafo_nx,
                    pos_nx,
                    edgelist=arestas_c,
                    ax=ax,
                    edge_color='#0F766E',
                    width=2.8,
                    style='dashed',
                    arrows=True,
                    arrowsize=13,
                )
            nx.draw_networkx_nodes(
                grafo_nx,
                pos_nx,
                ax=ax,
                node_color=cores_nos,
                node_size=140,
                edgecolors='#FFFFFF',
                linewidths=1.2,
            )
            nx.draw_networkx_labels(
                grafo_nx,
                pos_nx,
                labels=rotulos_nos,
                ax=ax,
                font_size=7.2,
                font_weight='bold',
                font_color='#14181F',
            )
            arestas_rotulo = {}
            for u, v in zip(caminho_p, caminho_p[1:]):
                if grafo_nx.has_edge(u, v):
                    arestas_rotulo[(u, v)] = f"{int(grafo_nx[u][v]['distancia_haversine_m'])}m"
            if arestas_rotulo:
                nx.draw_networkx_edge_labels(
                    grafo_nx,
                    pos_nx,
                    edge_labels=arestas_rotulo,
                    ax=ax,
                    font_size=6.8,
                    font_color='#991B1B',
                )
            dist_p = analise_nx['rota_principal']['distancia_haversine_m']
            no_ind = analise_nx['contingencia']['no_indisponivel']
            ax.set_title(
                f'Topologia Direcionada e Rota de Contingência — Maceió-AL\n'
                f'Principal: {orig_nx} -> {dest_nx} ({dist_p:.0f} m) | Contingência (sem nó {no_ind}): em verde',
                fontsize=9.2,
                fontweight='bold',
                color='#14181F',
                pad=8,
                wrap=True,
            )
            ax.set_xlabel('Longitude (°O)', fontsize=8.5, color='#374151')
            ax.set_ylabel('Latitude (°S)', fontsize=8.5, color='#374151')
            ax.grid(True, linestyle=':', alpha=0.55, color='#9CA3AF')
            fig.tight_layout()
            return self._renderizar_png(fig)

        if modo == 'mst':
            mst = self._store.grafo.arvore_geradora_minima_prim()
            for a in mst.arestas:
                pares_destaque.add((a.origem_id, a.destino_id))
                pares_destaque.add((a.destino_id, a.origem_id))
            subtitulo = (
                f'Árvore Geradora Mínima (Prim) — {len(mst.arestas)} vias estruturantes\n'
                f'Tempo Total da Rede: {mst.custo_total_min:.1f} min | Extensão: {mst.distancia_total_km:.2f} km'
            )
        else:
            caminho_efetivo: list[str] = []
            if origem_id and destino_id and origem_id in vertices and destino_id in vertices:
                rota, em_cache = self._store.obter_rota_com_cache(origem_id, destino_id)
                caminho_efetivo = rota.caminho_vertices
                if rota.alcancavel:
                    subtitulo = (
                        f'Rota Otimizada (Dijkstra): {origem_id} -> {destino_id}\n'
                        f'Tempo Estimado: {rota.tempo_total_min:.2f} min | Distância: {rota.distancia_total_km:.2f} km'
                    )
                else:
                    subtitulo = f'Rota Inalcançável entre {origem_id} e {destino_id} (Via interditada)'
            elif caminho_destaque:
                caminho_efetivo = caminho_destaque
                subtitulo = 'Último Despacho SAMU 192 Calculado via Algoritmo de Dijkstra'

            for idx in range(len(caminho_efetivo) - 1):
                u = caminho_efetivo[idx]
                v = caminho_efetivo[idx + 1]
                pares_destaque.add((u, v))
                pares_destaque.add((v, u))

        for aresta in arestas:
            vo = vertices.get(aresta.origem_id)
            vd = vertices.get(aresta.destino_id)
            if vo is None or vd is None:
                continue
            xs = [vo.longitude, vd.longitude]
            ys = [vo.latitude, vd.latitude]
            destacada = (aresta.origem_id, aresta.destino_id) in pares_destaque

            if aresta.bloqueada:
                ax.plot(xs, ys, color='#B91C1C', linestyle='--', linewidth=2.0, alpha=0.85, zorder=2)
            elif destacada:
                cor_destaque = '#0F766E' if modo == 'mst' else '#C81E1E'
                ax.plot(xs, ys, color=cor_destaque, linestyle='-', linewidth=3.4, alpha=0.95, zorder=4)
            else:
                cor_via = '#D97706' if aresta.fator_transito >= 1.3 else '#9CA3AF'
                ax.plot(xs, ys, color=cor_via, linestyle='-', linewidth=1.3, alpha=0.7, zorder=1)

            meio_x = (vo.longitude + vd.longitude) / 2.0
            meio_y = (vo.latitude + vd.latitude) / 2.0
            if destacada and not aresta.bloqueada:
                ax.text(
                    meio_x,
                    meio_y,
                    f'{aresta.tempo_minutos:.1f}m',
                    fontsize=7,
                    fontweight='bold',
                    color='#14181F',
                    bbox={'boxstyle': 'round,pad=0.15', 'facecolor': '#FFFBEB', 'edgecolor': '#D97706', 'alpha': 0.9},
                    zorder=6,
                )

        hosp_x, hosp_y = [], []
        base_x, base_y = [], []
        cruz_x, cruz_y = [], []

        for v in vertices.values():
            if v.tipo == 'hospital':
                hosp_x.append(v.longitude)
                hosp_y.append(v.latitude)
            elif v.tipo == 'base_samu':
                base_x.append(v.longitude)
                base_y.append(v.latitude)
            else:
                cruz_x.append(v.longitude)
                cruz_y.append(v.latitude)

            rotulo_curto = v.bairro if v.tipo == 'cruzamento' else v.nome.split(' - ')[0]
            ax.annotate(
                rotulo_curto,
                (v.longitude, v.latitude),
                textcoords='offset points',
                xytext=(5, 5),
                fontsize=7.5,
                fontweight='bold' if v.tipo != 'cruzamento' else 'normal',
                color='#14181F',
                zorder=7,
            )

        ax.scatter(
            cruz_x,
            cruz_y,
            s=55,
            c='#4B5563',
            marker='o',
            edgecolors='#FFFFFF',
            linewidths=1.0,
            label='Bairros / Cruzamentos',
            zorder=5,
        )
        ax.scatter(
            base_x,
            base_y,
            s=115,
            c='#1D4ED8',
            marker='^',
            edgecolors='#FFFFFF',
            linewidths=1.2,
            label='Bases SAMU 192',
            zorder=6,
        )
        ax.scatter(
            hosp_x,
            hosp_y,
            s=120,
            c='#C81E1E',
            marker='s',
            edgecolors='#FFFFFF',
            linewidths=1.2,
            label='Hospitais / UPAs',
            zorder=6,
        )

        ax.set_title(
            f'Grafo Georreferenciado de Maceió-AL (Matplotlib)\n{subtitulo}',
            fontsize=9.2,
            fontweight='bold',
            color='#14181F',
            pad=8,
            wrap=True,
        )
        ax.set_xlim(-35.795, -35.680)
        ax.set_ylim(-9.715, -9.540)
        ax.set_xlabel('Longitude (°O)', fontsize=8.2, color='#374151')
        ax.set_ylabel('Latitude (°S)', fontsize=8.2, color='#374151')
        ax.grid(True, linestyle=':', alpha=0.55, color='#9CA3AF')
        ax.legend(loc='lower right', fontsize=7.5, framealpha=0.92, facecolor='#FFFFFF', edgecolor='#D1D5DB')
        fig.tight_layout()
        return self._renderizar_png(fig)

    def gerar_grafico_ordenacao(self, tamanho_amostra: int = 120) -> bytes:
        n = max(15, min(400, int(tamanho_amostra)))
        amostra_sintetica = [((i * 73 + 41) % 997) for i in range(n)]
        metricas = comparar_todos_algoritmos(amostra_sintetica)

        nomes = [m.algoritmo.replace('_sort', '').upper() for m in metricas]
        comparacoes = [m.comparacoes for m in metricas]
        trocas = [m.trocas for m in metricas]
        tempos = [m.tempo_ms for m in metricas]

        fig = Figure(figsize=(8.8, 4.4), dpi=105, facecolor='#F8FAFC')
        ax1 = fig.add_subplot(121)
        ax2 = fig.add_subplot(122)

        for eixo in (ax1, ax2):
            eixo.set_facecolor('#FFFFFF')
            eixo.grid(axis='y', linestyle=':', alpha=0.5, color='#CBD5E1')

        posicoes = list(range(len(nomes)))
        largura = 0.36
        b1 = ax1.bar(
            [p - largura / 2 for p in posicoes],
            comparacoes,
            width=largura,
            color='#0F172A',
            label='Comparações',
        )
        b2 = ax1.bar(
            [p + largura / 2 for p in posicoes],
            trocas,
            width=largura,
            color='#94A3B8',
            label='Trocas',
        )
        ax1.set_xticks(posicoes)
        ax1.set_xticklabels(nomes, fontsize=8.5, fontweight='bold')
        ax1.set_title(f'Operações Elementares (N = {n})', fontsize=9.5, fontweight='bold', color='#0F172A')
        ax1.set_ylabel('Quantidade de Operações', fontsize=8.5)
        ax1.legend(fontsize=8)

        for barra in list(b1) + list(b2):
            altura = int(barra.get_height())
            ax1.annotate(
                f'{altura}',
                xy=(barra.get_x() + barra.get_width() / 2, altura),
                xytext=(0, 3),
                textcoords='offset points',
                ha='center',
                fontsize=7.2,
            )

        b_tempo = ax2.bar(posicoes, tempos, width=0.48, color='#0F172A')
        ax2.set_xticks(posicoes)
        ax2.set_xticklabels(nomes, fontsize=8.5, fontweight='bold')
        ax2.set_title(f'Tempo de Execução em ms (N = {n})', fontsize=9.5, fontweight='bold', color='#0F172A')
        ax2.set_ylabel('Tempo (ms)', fontsize=8.5)

        for barra in b_tempo:
            altura_t = barra.get_height()
            ax2.annotate(
                f'{altura_t:.3f} ms',
                xy=(barra.get_x() + barra.get_width() / 2, altura_t),
                xytext=(0, 3),
                textcoords='offset points',
                ha='center',
                fontsize=7.5,
                fontweight='bold',
            )

        fig.suptitle(
            f'Desempenho dos Algoritmos de Ordenação (N = {n})',
            fontsize=10.5,
            fontweight='bold',
            color='#0F172A',
        )
        fig.tight_layout()
        return self._renderizar_png(fig)

    def gerar_grafico_hash(self) -> bytes:
        est_cpf = self._store.hash_pacientes_cpf.estatisticas()
        est_rotas = self._store.hash_cache_rotas.estatisticas()
        est_cep = self._store.hash_unidades_cep.estatisticas()

        fig = Figure(figsize=(8.8, 4.6), dpi=105, facecolor='#F8FAFC')
        ax1 = fig.add_subplot(131)
        ax2 = fig.add_subplot(132)
        ax3 = fig.add_subplot(133)

        paineis = [
            (
                ax1,
                est_cpf,
                'Pacientes (CPF)\nHorner + Encadeamento',
                '#0F172A',
            ),
            (
                ax2,
                est_rotas,
                'Cache de Rotas\nMultiplicação + Quadrática',
                '#0F172A',
            ),
            (
                ax3,
                est_cep,
                'Hospitais (CEP)\nDobra + Linear',
                '#0F172A',
            ),
        ]

        for eixo, est, titulo, cor in paineis:
            eixo.set_facecolor('#FFFFFF')
            indices = list(range(len(est.ocupacao_por_posicao)))
            eixo.bar(indices, est.ocupacao_por_posicao, color=cor, alpha=0.9, width=0.72)
            eixo.set_title(
                f'{titulo}\nCap={est.capacidade} | N={est.tamanho} | α={est.fator_carga:.2f} | Col={est.total_colisoes}',
                fontsize=8.0,
                fontweight='bold',
                color='#0F172A',
            )
            eixo.set_xlabel('Posição no Vetor', fontsize=7.8)
            eixo.set_ylabel('Itens por Posição', fontsize=7.8)
            eixo.grid(axis='y', linestyle=':', alpha=0.5, color='#CBD5E1')

        fig.suptitle(
            'Distribuição dos Baldes das Tabelas Hash em Memória',
            fontsize=10.5,
            fontweight='bold',
            color='#0F172A',
        )
        fig.tight_layout()
        return self._renderizar_png(fig)

    def gerar_mapa_folium_html(
        self,
        origem_id: Optional[str] = None,
        destino_id: Optional[str] = None,
        no_indisponivel: Optional[str] = None,
        autonomia_maxima_m: Optional[float] = 3500.0,
        caminho_destaque: Optional[list[str]] = None,
    ) -> str:
        vertices = {v.id: v for v in self._store.grafo.listar_vertices()}
        hospitais_por_vertice = {h.vertice_id: h for h in self._store.hospitais}
        orig = origem_id if (origem_id and origem_id in vertices) else 'v-samu-farol'
        dest = destino_id if (destino_id and destino_id in vertices) else 'v-hge'

        analise = self._store.grafo.analisar_resiliencia_networkx(
            origem_id=orig,
            destino_id=dest,
            no_indisponivel=no_indisponivel,
            autonomia_maxima_m=autonomia_maxima_m,
            criterio_peso='distancia_haversine_m',
        )

        rota_principal = (
            caminho_destaque
            if (caminho_destaque and not origem_id and not destino_id)
            else analise['rota_principal']['caminho_vertices']
        )
        rota_contingencia = analise['contingencia']['caminho_vertices']
        no_falha = analise['contingencia']['no_indisponivel']
        removidas_set = {
            (r['origem_id'], r['destino_id']) for r in analise['arestas_removidas_detalhe']
        } | {
            (r['destino_id'], r['origem_id']) for r in analise['arestas_removidas_detalhe']
        }

        token_mapbox = os.environ.get('MAPBOX_TOKEN', '').strip()
        if token_mapbox:
            url_mapbox = (
                'https://api.mapbox.com/styles/v1/mapbox/traffic-day-v2/tiles/256/{z}/{x}/{y}@2x?access_token='
                + token_mapbox
            )
            attr_mapa = '&copy; Mapbox &copy; OpenStreetMap | PULSO 192 Maceió'
        else:
            url_mapbox = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
            attr_mapa = '&copy; OpenStreetMap &copy; CARTO | PULSO 192 Maceió'
        mapa = folium.Map(
            location=[-9.632, -35.735],
            zoom_start=12,
            tiles=url_mapbox,
            attr=attr_mapa,
            control_scale=True,
            name='Malha Viária',
        )

        folium.TileLayer(
            tiles='https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='&copy; OpenStreetMap contributors',
            name='OpenStreetMap Padrão',
        ).add_to(mapa)

        folium.TileLayer(
            tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            attr='&copy; OpenStreetMap &copy; CARTO',
            name='Mapa Claro (CARTO)',
        ).add_to(mapa)

        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
            attr='Tiles &copy; Esri &mdash; PULSO 192 Maceió',
            name='Esri World Street',
        ).add_to(mapa)

        for aresta in self._store.grafo.listar_arestas_unicas():
            vo = vertices.get(aresta.origem_id)
            vd = vertices.get(aresta.destino_id)
            if vo is None or vd is None:
                continue
            dist_m = round(
                calcular_haversine(
                    (vo.latitude, vo.longitude),
                    (vd.latitude, vd.longitude),
                    em_metros=True,
                ),
                1,
            )
            removida_autonomia = (aresta.origem_id, aresta.destino_id) in removidas_set
            if aresta.bloqueada:
                cor_linha = '#B91C1C'
                peso_linha = 3
                dash = '6, 6'
                status_via = 'VIA INTERDITADA'
            elif removida_autonomia:
                cor_linha = '#D97706'
                peso_linha = 2.5
                dash = '5, 5'
                status_via = f'Excede autonomia ({dist_m} m > {autonomia_maxima_m:.0f} m)'
            else:
                cor_linha = '#64748B'
                peso_linha = 2.5
                dash = None
                status_via = f'Haversine: {dist_m} m | Viário: {aresta.distancia_km} km ({aresta.tempo_minutos:.1f} min)'

            folium.PolyLine(
                locations=[[vo.latitude, vo.longitude], [vd.latitude, vd.longitude]],
                color=cor_linha,
                weight=peso_linha,
                opacity=0.78,
                dash_array=dash,
                tooltip=f'{aresta.nome_via}: {status_via}',
            ).add_to(mapa)

        if len(rota_contingencia) > 1 and rota_contingencia != rota_principal:
            coords_cont = [
                [vertices[vid].latitude, vertices[vid].longitude]
                for vid in rota_contingencia
                if vid in vertices
            ]
            folium.PolyLine(
                locations=coords_cont,
                color='#0F766E',
                weight=5,
                opacity=0.92,
                dash_array='8, 5',
                tooltip=(
                    f"Rota de Contingência (sem {no_falha}): "
                    f"{' -> '.join(rota_contingencia)} ({analise['contingencia']['distancia_haversine_m']} m)"
                ),
            ).add_to(mapa)

        if len(rota_principal) > 1:
            coords_rota = [
                [vertices[vid].latitude, vertices[vid].longitude]
                for vid in rota_principal
                if vid in vertices
            ]
            folium.PolyLine(
                locations=coords_rota,
                color='#C81E1E',
                weight=6,
                opacity=0.95,
                tooltip=(
                    f"Rota Otimizada (NetworkX + Haversine): "
                    f"{' -> '.join(rota_principal)} ({analise['rota_principal']['distancia_haversine_m']} m)"
                ),
            ).add_to(mapa)

        set_rota = set(rota_principal)
        for v in vertices.values():
            hosp = hospitais_por_vertice.get(v.id)
            if v.id == no_falha and no_indisponivel:
                cor_borda = '#000000'
                cor_preenchimento = '#111827'
                raio = 9
            elif v.id in set_rota:
                cor_borda = '#991B1B'
                cor_preenchimento = '#DC2626'
                raio = 8
            elif v.tipo == 'hospital':
                cor_borda = '#991B1B'
                cor_preenchimento = '#EF4444'
                raio = 8
            elif v.tipo == 'base_samu':
                cor_borda = '#1E40AF'
                cor_preenchimento = '#2563EB'
                raio = 8
            else:
                cor_borda = '#374151'
                cor_preenchimento = '#6B7280'
                raio = 6

            detalhe = f'Bairro: {v.bairro}<br>ID: <code>{v.id}</code><br>Coord: ({v.latitude:.4f}, {v.longitude:.4f})'
            if hosp is not None:
                detalhe += (
                    f'<br>Leitos Livres: <b>{hosp.leitos_livres}/{hosp.leitos_totais}</b> '
                    f'({hosp.taxa_ocupacao}% ocup.)<br>CEP: {hosp.cep}'
                )

            folium.CircleMarker(
                location=[v.latitude, v.longitude],
                radius=raio,
                color=cor_borda,
                weight=2.5,
                fill=True,
                fill_color=cor_preenchimento,
                fill_opacity=0.92,
                tooltip=f'{v.nome} ({v.bairro})',
                popup=folium.Popup(f'<b>{v.nome}</b><br>{detalhe}', max_width=280),
            ).add_to(mapa)

        folium.LayerControl().add_to(mapa)
        html_bruto = mapa.get_root().render()
        html_otimizado = (
            html_bruto.replace(
                'https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js',
                '/static/vendor/leaflet/leaflet.js',
            )
            .replace(
                'https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css',
                '/static/vendor/leaflet/leaflet.css',
            )
        )
        script_redimensionamento = (
            '<script>'
            'window.addEventListener("load", function() {'
            '  setTimeout(function() {'
            '    window.dispatchEvent(new Event("resize"));'
            '  }, 120);'
            '});'
            '</script>'
            '</body>'
        )
        return html_otimizado.replace('</body>', script_redimensionamento)


