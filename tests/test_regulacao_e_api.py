from app import app


def test_fluxo_completo_api_e_matplotlib() -> None:
    client = app.test_client()

    r_reset = client.post('/api/reiniciar')
    assert r_reset.status_code == 200

    r_est = client.get('/api/estado-geral')
    assert r_est.status_code == 200
    dados = r_est.get_json()
    assert len(dados['hospitais']) == 9
    assert len(dados['ambulancias']) == 8
    assert len(dados['deque_triagem']) == 5
    assert dados['deque_triagem'][0]['prioridade'] == 'critica'

    r_novo = client.post(
        '/api/ocorrencias',
        json={
            'paciente_cpf': '99988877766',
            'paciente_nome': 'Paciente Critico Teste',
            'vertice_id': 'v-mangabeiras',
            'descricao': 'PCR em via publica',
            'nivel_gravidade': 10,
        },
    )
    assert r_novo.status_code == 201
    novo_json = r_novo.get_json()
    assert novo_json['prioridade'] == 'critica'

    r_desp = client.post('/api/triagem/despachar', json={'extremidade': 'inicio'})
    assert r_desp.status_code == 200
    desp_json = r_desp.get_json()
    assert desp_json['ocorrencia_id'] == novo_json['id']
    assert len(desp_json['caminho_vertices']) >= 2

    r_undo = client.post('/api/operacoes/desfazer')
    assert r_undo.status_code == 200
    undo_json = r_undo.get_json()
    assert undo_json['ocorrencia_restaurada'] == novo_json['id']

    r_hash = client.get('/api/hash/inspecionar?tipo=cpf&chave=99988877766')
    assert r_hash.status_code == 200
    hash_json = r_hash.get_json()
    assert hash_json['resultado_busca']['encontrado'] is True

    r_ord = client.get('/api/ordenacao?alvo=hospitais&criterio=taxa_ocupacao&algoritmo=quick_sort&reverso=true')
    assert r_ord.status_code == 200
    ord_json = r_ord.get_json()
    assert len(ord_json['comparativo_4_algoritmos']) == 4

    for rota_img in (
        '/api/graficos/malha-viaria.png?modo=dijkstra&origem_id=v-samu-farol&destino_id=v-hge',
        '/api/graficos/malha-viaria.png?modo=mst',
        '/api/graficos/malha-viaria.png?modo=networkx&origem_id=v-samu-farol&destino_id=v-hge',
        '/api/graficos/ordenacao.png?n=60',
        '/api/graficos/hash.png',
    ):
        resp_img = client.get(rota_img)
        assert resp_img.status_code == 200
        assert resp_img.mimetype == 'image/png'
        assert resp_img.data[:8] == b'\x89PNG\r\n\x1a\n'

    r_health = client.get('/api/health')
    assert r_health.status_code == 200
    assert r_health.headers.get('X-Content-Type-Options') == 'nosniff'
    assert r_health.get_json()['status'] == 'healthy'

    r_nx = client.post(
        '/api/grafo/analisar',
        json={
            'algoritmo': 'networkx_resiliencia',
            'origem_id': 'v-samu-farol',
            'destino_id': 'v-hge',
            'autonomia_maxima_m': 3500,
        },
    )
    assert r_nx.status_code == 200
    nx_json = r_nx.get_json()
    assert nx_json['rota_principal']['alcancavel'] is True
    assert nx_json['contingencia']['alcancavel'] is True

    r_rep = client.get('/api/grafo/representacoes')
    assert r_rep.status_code == 200
    rep_json = r_rep.get_json()
    assert rep_json['matriz_adjacencia']['dimensao'] == '25x25'

    r_folium = client.get('/api/mapa/folium?origem_id=v-samu-farol&destino_id=v-hge&autonomia_m=3500')
    assert r_folium.status_code == 200
    html_folium = r_folium.get_data(as_text=True)
    assert 'poly_line' in html_folium
    assert 'Hospital Geral do Estado' in html_folium


