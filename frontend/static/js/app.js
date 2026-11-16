const MAPBOX_TOKEN = window.MAPBOX_TOKEN || '';

const estadoLocal = {
  dados: null,
  mapa: null,
  camadaBaseMapbox: null,
  camadaArestas: null,
  camadaRotaDestaque: null,
  camadaMst: null,
  camadaVertices: null,
  camadaAnimacaoViatura: null,
  animacaoViaturaId: null,
  arestasMstAtuais: [],
};

function notificar(mensagem, erro = false) {
  const barra = document.getElementById('barra-notificacao');
  barra.textContent = mensagem;
  barra.classList.remove('oculto', 'erro');
  if (erro) {
    barra.classList.add('erro');
  }
  window.clearTimeout(barra._timer);
  barra._timer = window.setTimeout(() => {
    barra.classList.add('oculto');
  }, 5500);
}

async function requisitarJson(url, opcoes = {}) {
  const resposta = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opcoes,
  });
  const corpo = await resposta.json();
  if (!resposta.ok) {
    throw new Error(corpo.erro || `Falha HTTP ${resposta.status}`);
  }
  return corpo;
}

function inicializarMapa() {
  const container = document.getElementById('mapa-leaflet');
  if (!container || estadoLocal.mapa) {
    return;
  }
  const mapa = window.L.map(container, {
    center: [-9.632, -35.735],
    zoom: 12,
    zoomControl: true,
  });

  const camadaBase = MAPBOX_TOKEN
    ? window.L.tileLayer(
        `https://api.mapbox.com/styles/v1/mapbox/traffic-day-v2/tiles/256/{z}/{x}/{y}@2x?access_token=${MAPBOX_TOKEN}`,
        {
          attribution: '&copy; Mapbox &copy; OpenStreetMap',
          maxZoom: 19,
          tileSize: 256,
          zoomOffset: 0,
        }
      )
    : window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
      });

  camadaBase.addTo(mapa);
  estadoLocal.camadaBaseMapbox = camadaBase;

  estadoLocal.mapa = mapa;
  estadoLocal.camadaArestas = window.L.layerGroup().addTo(mapa);
  estadoLocal.camadaMst = window.L.layerGroup().addTo(mapa);
  estadoLocal.camadaRotaDestaque = window.L.layerGroup().addTo(mapa);
  estadoLocal.camadaVertices = window.L.layerGroup().addTo(mapa);
  estadoLocal.camadaAnimacaoViatura = window.L.layerGroup().addTo(mapa);
}

function trocarEstiloMapbox(estilo) {
  if (!estadoLocal.mapa) return;
  if (estadoLocal.camadaBaseMapbox) {
    estadoLocal.mapa.removeLayer(estadoLocal.camadaBaseMapbox);
  }
  const novaCamada = MAPBOX_TOKEN
    ? window.L.tileLayer(
        `https://api.mapbox.com/styles/v1/mapbox/${estilo}/tiles/256/{z}/{x}/{y}@2x?access_token=${MAPBOX_TOKEN}`,
        {
          attribution: '&copy; Mapbox &copy; OpenStreetMap',
          maxZoom: 19,
          tileSize: 256,
          zoomOffset: 0,
        }
      )
    : window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
      });
  novaCamada.addTo(estadoLocal.mapa);
  novaCamada.bringToBack();
  estadoLocal.camadaBaseMapbox = novaCamada;
}

function desenharMapa() {
  if (!estadoLocal.mapa || !estadoLocal.dados) {
    return;
  }
  const { vertices, arestas, hospitais, ultimo_caminho_destacado, ultimo_titulo_rota } = estadoLocal.dados;
  const mapaVertices = new Map(vertices.map((v) => [v.id, v]));
  const mapaHospPorVertice = new Map(hospitais.map((h) => [h.vertice_id, h]));

  estadoLocal.camadaArestas.clearLayers();
  estadoLocal.camadaMst.clearLayers();
  estadoLocal.camadaRotaDestaque.clearLayers();
  estadoLocal.camadaVertices.clearLayers();

  for (const a of arestas) {
    const vo = mapaVertices.get(a.origem_id);
    const vd = mapaVertices.get(a.destino_id);
    if (!vo || !vd) continue;

    let cor = '#64748B';
    let dashArray = null;
    let peso = 2.5;
    if (a.bloqueada) {
      cor = '#B91C1C';
      dashArray = '6, 6';
      peso = 3.5;
    } else if (a.fator_transito >= 1.35) {
      cor = '#D97706';
      peso = 3.0;
    }

    const linha = window.L.polyline(
      [
        [vo.latitude, vo.longitude],
        [vd.latitude, vd.longitude],
      ],
      { color: cor, weight: peso, opacity: 0.78, dashArray }
    );
    const statusTxt = a.bloqueada ? 'INTERDITADA' : `${a.tempo_minutos} min (${a.distancia_km} km | trânsito ${a.fator_transito}x)`;
    linha.bindTooltip(`<strong>${a.nome_via}</strong><br>${statusTxt}`);
    linha.addTo(estadoLocal.camadaArestas);
  }

  for (const aMst of estadoLocal.arestasMstAtuais) {
    const vo = mapaVertices.get(aMst.origem_id);
    const vd = mapaVertices.get(aMst.destino_id);
    if (!vo || !vd) continue;
    window.L.polyline(
      [
        [vo.latitude, vo.longitude],
        [vd.latitude, vd.longitude],
      ],
      { color: '#0F766E', weight: 5, opacity: 0.9 }
    ).addTo(estadoLocal.camadaMst);
  }

  if (Array.isArray(ultimo_caminho_destacado) && ultimo_caminho_destacado.length > 1) {
    const coords = [];
    for (const vid of ultimo_caminho_destacado) {
      const v = mapaVertices.get(vid);
      if (v) coords.push([v.latitude, v.longitude]);
    }
    if (coords.length > 1) {
      window.L.polyline(coords, {
        color: '#C81E1E',
        weight: 6,
        opacity: 0.95,
      }).addTo(estadoLocal.camadaRotaDestaque);
    }
  }

  for (const v of vertices) {
    let corPreenchimento = '#4B5563';
    let raio = 6;
    if (v.tipo === 'hospital') {
      corPreenchimento = '#C81E1E';
      raio = 9;
    } else if (v.tipo === 'base_samu') {
      corPreenchimento = '#1D4ED8';
      raio = 8;
    }

    const marcador = window.L.circleMarker([v.latitude, v.longitude], {
      radius: raio,
      fillColor: corPreenchimento,
      color: '#FFFFFF',
      weight: 2,
      fillOpacity: 0.95,
    });

    const hosp = mapaHospPorVertice.get(v.id);
    let detalheExtra = `Bairro: ${v.bairro} | ID: ${v.id}`;
    if (hosp) {
      detalheExtra = `Leitos livres: <strong>${hosp.leitos_livres}/${hosp.leitos_totais}</strong> (${hosp.taxa_ocupacao}% ocup.)<br>Aguardando leito: ${hosp.fila_espera.length} paciente(s)`;
    }
    marcador.bindPopup(`<strong>${v.nome}</strong><br>${detalheExtra}`);
    marcador.addTo(estadoLocal.camadaVertices);
  }

  const rotuloRota = document.getElementById('rotulo-rota-ativa');
  rotuloRota.textContent = ultimo_titulo_rota || 'Malha viária ativa de Maceió (24 pontos monitorados)';
}

function animarDeslocamentoAmbulancia(caminhoVertices, codigoAmbulancia = 'SAMU 192', hospitalNome = '', pacienteNome = '') {
  if (!estadoLocal.mapa || !Array.isArray(caminhoVertices) || caminhoVertices.length < 2) {
    return;
  }
  alternarModoVisual('mapa');

  if (estadoLocal.animacaoViaturaId) {
    window.clearInterval(estadoLocal.animacaoViaturaId);
    estadoLocal.animacaoViaturaId = null;
  }
  if (!estadoLocal.camadaAnimacaoViatura) {
    estadoLocal.camadaAnimacaoViatura = window.L.layerGroup().addTo(estadoLocal.mapa);
  }
  estadoLocal.camadaAnimacaoViatura.clearLayers();

  const vertices = estadoLocal.dados?.vertices || [];
  const mapaVertices = new Map(vertices.map((v) => [v.id, v]));

  const pontosRota = [];
  for (const vid of caminhoVertices) {
    const v = mapaVertices.get(vid);
    if (v) {
      pontosRota.push({ lat: v.latitude, lng: v.longitude, nome: v.nome, bairro: v.bairro, id: v.id });
    }
  }
  if (pontosRota.length < 2) return;

  const latlngs = pontosRota.map((p) => [p.lat, p.lng]);
  const bounds = window.L.latLngBounds(latlngs);
  estadoLocal.mapa.fitBounds(bounds, { padding: [60, 60], maxZoom: 14 });

  const micropontos = [];
  const passosPorAresta = 48;
  for (let i = 0; i < pontosRota.length - 1; i++) {
    const pA = pontosRota[i];
    const pB = pontosRota[i + 1];
    for (let s = 0; s < passosPorAresta; s++) {
      const t = s / passosPorAresta;
      micropontos.push({
        lat: pA.lat + t * (pB.lat - pA.lat),
        lng: pA.lng + t * (pB.lng - pA.lng),
        trecho: `${pA.nome.split(' - ')[0]} ➔ ${pB.nome.split(' - ')[0]}`,
        progressoPct: Math.round(((i * passosPorAresta + s) / ((pontosRota.length - 1) * passosPorAresta)) * 100),
      });
    }
  }
  const pontoFinal = pontosRota[pontosRota.length - 1];
  micropontos.push({
    lat: pontoFinal.lat,
    lng: pontoFinal.lng,
    trecho: `Destino: ${hospitalNome || pontoFinal.nome}`,
    progressoPct: 100,
  });

  const linhaRastro = window.L.polyline([[micropontos[0].lat, micropontos[0].lng]], {
    color: '#06B6D4',
    weight: 5,
    opacity: 0.95,
    dashArray: '5, 5',
  }).addTo(estadoLocal.camadaAnimacaoViatura);

  const iconeViatura = window.L.divIcon({
    className: 'container-icone-viatura',
    html: `
      <div class="bolha-ambulancia-sirene">
        <div class="indicador-viatura-ponto"></div>
      </div>
      <div class="etiqueta-viatura-mapa">${codigoAmbulancia}</div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });

  const marcadorViatura = window.L.marker([micropontos[0].lat, micropontos[0].lng], {
    icon: iconeViatura,
    zIndexOffset: 1200,
  }).addTo(estadoLocal.camadaAnimacaoViatura);

  const rotuloRota = document.getElementById('rotulo-rota-ativa');
  let frame = 0;
  const totalFrames = micropontos.length;
  const coordsPercorridas = [[micropontos[0].lat, micropontos[0].lng]];

  estadoLocal.animacaoViaturaId = window.setInterval(() => {
    frame++;
    if (frame >= totalFrames) {
      window.clearInterval(estadoLocal.animacaoViaturaId);
      estadoLocal.animacaoViaturaId = null;

      marcadorViatura.setLatLng([pontoFinal.lat, pontoFinal.lng]);
      coordsPercorridas.push([pontoFinal.lat, pontoFinal.lng]);
      linhaRastro.setLatLngs(coordsPercorridas);

      marcadorViatura.bindPopup(
        `<div style="font-family: var(--font-sans); font-size: 12px; line-height: 1.4;">
           <div style="font-weight: 600; color: #0F172A; margin-bottom: 2px;">
             Deslocamento concluído
           </div>
           <div style="color: #475569;">
             Viatura <strong>${codigoAmbulancia}</strong><br>
             ${pacienteNome ? `Paciente: <strong>${pacienteNome}</strong><br>` : ''}
             Destino: <strong>${hospitalNome || pontoFinal.nome}</strong>
           </div>
         </div>`
      ).openPopup();

      if (rotuloRota) {
        rotuloRota.innerHTML = `Viatura <strong>${codigoAmbulancia}</strong> no destino: <strong>${hospitalNome || pontoFinal.nome}</strong>.`;
      }
      return;
    }

    const pAtual = micropontos[frame];
    marcadorViatura.setLatLng([pAtual.lat, pAtual.lng]);
    coordsPercorridas.push([pAtual.lat, pAtual.lng]);
    linhaRastro.setLatLngs(coordsPercorridas);

    if (frame % 10 === 0) {
      estadoLocal.mapa.panTo([pAtual.lat, pAtual.lng], { animate: true, duration: 0.4 });
    }

    if (rotuloRota) {
      const velAprox = 48 + ((frame * 7) % 18);
      rotuloRota.innerHTML = `🚨 <strong style="color: #DC2626;">${codigoAmbulancia}</strong> em rota de socorro (${pAtual.progressoPct}% · ${velAprox} km/h): <em>${pAtual.trecho}</em>`;
    }
  }, 45);
}

function preencherSelectsVerticesEArestas() {
  if (!estadoLocal.dados) return;
  const { vertices, arestas } = estadoLocal.dados;

  const idsSelectVertice = [
    'chamado-vertice',
    'grafo-origem',
    'grafo-destino',
    'mpl-grafo-origem',
    'mpl-grafo-destino',
    'folium-origem',
    'folium-destino',
  ];

  for (const idSel of idsSelectVertice) {
    const sel = document.getElementById(idSel);
    if (!sel) continue;
    const valorAnterior = sel.value;
    sel.innerHTML = '';
    for (const v of vertices) {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = `${v.nome} (${v.bairro})`;
      sel.appendChild(opt);
    }
    if (valorAnterior && vertices.some((v) => v.id === valorAnterior)) {
      sel.value = valorAnterior;
    } else if (idSel.includes('origem')) {
      sel.value = 'v-samu-farol';
    } else if (idSel.includes('destino')) {
      sel.value = 'v-hge';
    } else if (idSel === 'chamado-vertice') {
      sel.value = 'v-jatiuca';
    }
  }

  for (const idNoInd of ['grafo-no-indisponivel', 'folium-no-indisponivel']) {
    const selInd = document.getElementById(idNoInd);
    if (!selInd) continue;
    const valAnt = selInd.value;
    selInd.innerHTML = '<option value="">Automático (Nó Intermediário da Rota)</option>';
    for (const v of vertices) {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = `${v.nome} (${v.id})`;
      selInd.appendChild(opt);
    }
    if (valAnt && vertices.some((v) => v.id === valAnt)) {
      selInd.value = valAnt;
    }
  }

  const selVia = document.getElementById('via-selecionada');
  if (selVia) {
    const valorAnt = selVia.value;
    selVia.innerHTML = '';
    for (const a of arestas) {
      const opt = document.createElement('option');
      opt.value = `${a.origem_id}|${a.destino_id}`;
      const tag = a.bloqueada ? '[INTERDITADA]' : `[${a.fator_transito}x]`;
      opt.textContent = `${a.nome_via} (${a.origem_id} <-> ${a.destino_id}) ${tag}`;
      selVia.appendChild(opt);
    }
    if (valorAnt) selVia.value = valorAnt;
  }
}

function renderizarTriagemEUp1() {
  const { deque_triagem, hospitais, ambulancias, pilha_historico, conectividade } = estadoLocal.dados;

  const totalLeitosLivres = hospitais.reduce((acc, h) => acc + (h.leitos_livres || 0), 0);
  const ambDisponiveis = ambulancias.filter((a) => a.status === 'disponivel').length;

  document.getElementById('kpi-deque').textContent = String(deque_triagem.length);
  const elFrota = document.getElementById('kpi-frota');
  if (elFrota) elFrota.textContent = `${ambDisponiveis}/${ambulancias.length}`;
  const elLeitos = document.getElementById('kpi-leitos');
  if (elLeitos) elLeitos.textContent = String(totalLeitosLivres);

  document.getElementById('kpi-pilha').textContent = String(pilha_historico.length);
  document.getElementById('kpi-malha').textContent = conectividade.conexo
    ? '100%'
    : `${conectividade.isolados.length} isolados`;

  const contDeque = document.getElementById('lista-deque-triagem');
  contDeque.innerHTML = '';
  if (deque_triagem.length === 0) {
    contDeque.innerHTML = '<div class="cartao-item">Nenhum chamado pendente na triagem.</div>';
  } else {
    deque_triagem.forEach((oc, idx) => {
      const posTag = idx === 0 ? 'Próximo' : idx === deque_triagem.length - 1 ? 'Final' : `#${idx + 1}`;
      const div = document.createElement('div');
      div.className = 'cartao-item';
      div.innerHTML = `
        <div class="linha-topo-cartao">
          <span><span class="ponto-status ${oc.prioridade}"></span><strong>${oc.id}</strong> · ${oc.paciente_nome}</span>
          <span class="badge ${oc.prioridade}">${posTag} · G${oc.nivel_gravidade}</span>
        </div>
        <div style="font-size: 11px; color: var(--text-secondary);">${oc.bairro} · ${oc.descricao}</div>
      `;
      contDeque.appendChild(div);
    });
  }

  const contHosp = document.getElementById('lista-hospitais-regulacao');
  contHosp.innerHTML = '';
  for (const h of hospitais) {
    const classeBarra = h.taxa_ocupacao >= 95 ? 'lotado' : h.taxa_ocupacao >= 80 ? 'alerta' : '';
    const filaTexto = h.fila_espera.length > 0
      ? `Fila (${h.fila_espera.length}): ` + h.fila_espera.map((p) => p.ocorrencia_id).join(', ')
      : 'Fila vazia';
    const primeiroDequeId = deque_triagem.length > 0 ? deque_triagem[0].id : '';

    const div = document.createElement('div');
    div.className = 'cartao-item';
    div.innerHTML = `
      <div class="linha-topo-cartao">
        <strong>${h.nome}</strong>
        <span class="badge ${h.leitos_livres > 0 ? 'ok' : 'critica'}">
          ${h.leitos_ocupados}/${h.leitos_totais} (${h.leitos_livres} livres)
        </span>
      </div>
      <div class="barra-ocupacao">
        <div class="barra-ocupacao-preenchimento ${classeBarra}" style="width: ${Math.min(100, h.taxa_ocupacao)}%"></div>
      </div>
      <div style="font-size: 11px; color: var(--text-secondary);">${h.bairro} · ${filaTexto}</div>
      <div class="grupo-botoes-compacto">
        <button type="button" class="botao botao-secundario btn-liberar-leito" data-hosp="${h.id}">
          Liberar leito
        </button>
        ${
          primeiroDequeId
            ? `<button type="button" class="botao botao-secundario btn-enfileirar-hosp" data-hosp="${h.id}" data-ocor="${primeiroDequeId}">
                Enfileirar ${primeiroDequeId}
              </button>`
            : ''
        }
      </div>
    `;
    contHosp.appendChild(div);
  }

  contHosp.querySelectorAll('.btn-liberar-leito').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try {
        const hid = btn.getAttribute('data-hosp');
        const res = await requisitarJson(`/api/hospitais/${hid}/liberar-leito`, { method: 'POST' });
        const msgExtra = res.paciente_admitido
          ? `Paciente ${res.paciente_admitido} (${res.ocorrencia_admitida_da_fila}) admitido em leito hospitalar.`
          : `Leito liberado em ${res.hospital_nome} (${res.leitos_livres} livres).`;
        notificar(msgExtra);
        await carregarEstadoGeral();
      } catch (e) {
        notificar(e.message, true);
      }
    });
  });

  contHosp.querySelectorAll('.btn-enfileirar-hosp').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try {
        const hid = btn.getAttribute('data-hosp');
        const oid = btn.getAttribute('data-ocor');
        const res = await requisitarJson(`/api/hospitais/${hid}/enfileirar`, {
          method: 'POST',
          body: JSON.stringify({ ocorrencia_id: oid }),
        });
        notificar(`Ocorrência ${res.ocorrencia_id} encaminhada para a posição ${res.posicao_fila} de espera em ${res.hospital_nome}.`);
        await carregarEstadoGeral();
      } catch (e) {
        notificar(e.message, true);
      }
    });
  });

  const contAmb = document.getElementById('lista-ambulancias');
  contAmb.innerHTML = '';
  for (const a of ambulancias) {
    const listaEnc = a.atendimentos_lista_encadeada;
    const resumoLista = listaEnc.length > 0
      ? listaEnc.map((r) => `${r.ocorrencia_id} (${r.paciente_nome})`).join(' · ')
      : 'Nenhum despacho no turno';
    const ultimoAtend = listaEnc.length > 0 ? listaEnc[0] : null;
    const temRota = ultimoAtend && Array.isArray(ultimoAtend.caminho_vertices) && ultimoAtend.caminho_vertices.length > 1;

    const div = document.createElement('div');
    div.className = 'cartao-item';
    div.innerHTML = `
      <div class="linha-topo-cartao">
        <strong>${a.codigo}</strong>
        <span class="badge ok">${a.km_rodados} km · ${a.total_atendimentos} atend.</span>
      </div>
      <div style="font-size: 11px; color: var(--text-secondary);">${a.local_atual_nome} · ${resumoLista}</div>
      ${
        temRota
          ? `<button type="button" class="botao botao-secundario btn-animar-amb" style="font-size: 11px; padding: 2px 6px; margin-top: 4px;">Acompanhar no mapa</button>`
          : ''
      }
    `;
    if (temRota) {
      div.querySelector('.btn-animar-amb')?.addEventListener('click', () => {
        animarDeslocamentoAmbulancia(ultimoAtend.caminho_vertices, a.codigo, ultimoAtend.hospital_id, ultimoAtend.paciente_nome);
      });
    }
    contAmb.appendChild(div);
  }

  const contPilha = document.getElementById('lista-pilha-historico');
  contPilha.innerHTML = '';
  if (pilha_historico.length === 0) {
    contPilha.innerHTML = '<div class="cartao-item" style="color: var(--text-muted); font-size: 12px;">Nenhuma ação registrada.</div>';
  } else {
    pilha_historico.forEach((op, idx) => {
      const div = document.createElement('div');
      div.className = 'cartao-item';
      div.innerHTML = `
        <div class="linha-topo-cartao">
          <span><span class="ponto-status ${idx === 0 ? 'critica' : 'neutro'}"></span><strong>${op.id}</strong> · ${op.tipo.toUpperCase()}</span>
          <span class="badge ${idx === 0 ? 'critica' : 'ok'}">${idx === 0 ? 'Topo da pilha' : `#${idx + 1}`}</span>
        </div>
        <div style="font-size: 11px; color: var(--text-secondary);">${op.descricao}</div>
      `;
      contPilha.appendChild(div);
    });
  }
}

async function carregarPainelHash(tipoBusca = '', chaveBusca = '') {
  const params = new URLSearchParams();
  if (tipoBusca && chaveBusca) {
    params.set('tipo', tipoBusca);
    params.set('chave', chaveBusca);
  }
  const dadosHash = await requisitarJson(`/api/hash/inspecionar?${params.toString()}`);
  const container = document.getElementById('painel-tabelas-hash');
  container.innerHTML = '';

  for (const t of dadosHash.tabelas) {
    const celulasHtml = t.ocupacao_por_posicao
      .map((qtd, idx) => {
        const cls = qtd > 1 ? 'colisao' : qtd === 1 ? 'ocupado' : '';
        return `<span class="celula-balde ${cls}" title="Posição ${idx}: ${qtd} item(ns)">[${idx}]:${qtd}</span>`;
      })
      .join('');

    const div = document.createElement('div');
    div.className = 'cartao-item';
    div.innerHTML = `
      <div class="linha-topo-cartao">
        <strong>${t.titulo}</strong>
        <span class="badge ok">Cap=${t.capacidade} · N=${t.tamanho} · α=${t.fator_carga} · Col=${t.total_colisoes}</span>
      </div>
      <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">
        ${t.metodo_hash} · ${t.metodo_colisao} · ${t.justificativa}
      </div>
      <div class="grade-baldes-hash">${celulasHtml}</div>
    `;
    container.appendChild(div);
  }

  if (dadosHash.resultado_busca) {
    document.getElementById('resultado-busca-hash').textContent = JSON.stringify(dadosHash.resultado_busca, null, 2);
  }
}

async function carregarPainelOrdenacao() {
  const alvo = document.getElementById('ord-alvo').value;
  const criterio = document.getElementById('ord-criterio').value;
  const algoritmo = document.getElementById('ord-algoritmo').value;
  const reverso = document.getElementById('ord-direcao').value;

  const params = new URLSearchParams({ alvo, criterio, algoritmo, reverso });
  const res = await requisitarJson(`/api/ordenacao?${params.toString()}`);

  const tbody = document.getElementById('tabela-comparativo-ordenacao');
  tbody.innerHTML = '';
  for (const m of res.comparativo_4_algoritmos) {
    const tr = document.createElement('tr');
    if (m.algoritmo === algoritmo) {
      tr.style.backgroundColor = '#F1F5F9';
      tr.style.fontWeight = '600';
    }
    tr.innerHTML = `
      <td>${m.nome_exibicao}</td>
      <td>${m.comparacoes}</td>
      <td>${m.trocas}</td>
      <td>${m.tempo_ms.toFixed(4)} ms</td>
      <td>${m.complexidade_melhor} / ${m.complexidade_medio} / ${m.complexidade_pior}</td>
      <td>${m.estavel ? 'Sim' : 'Não'}</td>
    `;
    tbody.appendChild(tr);
  }

  const listaOrd = document.getElementById('lista-resultado-ordenado');
  listaOrd.innerHTML = '';
  res.itens.forEach((item, i) => {
    const div = document.createElement('div');
    div.className = 'cartao-item';
    if (alvo === 'hospitais') {
      div.innerHTML = `
        <div class="linha-topo-cartao">
          <strong>#${i + 1} · ${item.nome}</strong>
          <span class="badge ok">${item.taxa_ocupacao}% ocup. · ${item.leitos_livres}/${item.leitos_totais} livres</span>
        </div>
        <div style="font-size: 11px; color: var(--text-secondary);">${item.bairro}</div>
      `;
    } else if (alvo === 'ambulancias') {
      div.innerHTML = `
        <div class="linha-topo-cartao">
          <strong>#${i + 1} · ${item.codigo}</strong>
          <span class="badge ok">${item.km_rodados} km · ${item.total_atendimentos} atend.</span>
        </div>
        <div style="font-size: 11px; color: var(--text-secondary);">${item.local_atual_nome}</div>
      `;
    } else {
      div.innerHTML = `
        <div class="linha-topo-cartao">
          <span><span class="ponto-status ${item.prioridade}"></span><strong>#${i + 1}</strong> · ${item.id} — ${item.paciente_nome}</span>
          <span class="badge ${item.prioridade}">G${item.nivel_gravidade} · ${item.tempo_resposta_min} min</span>
        </div>
        <div style="font-size: 11px; color: var(--text-secondary);">${item.bairro}</div>
      `;
    }
    listaOrd.appendChild(div);
  });
}

function atualizarMapaFolium() {
  const iframe = document.getElementById('iframe-folium');
  if (!iframe) return;
  const orig = document.getElementById('folium-origem')?.value || 'v-samu-farol';
  const dest = document.getElementById('folium-destino')?.value || 'v-hge';
  const noInd = document.getElementById('folium-no-indisponivel')?.value || '';
  const autonomia = document.getElementById('folium-autonomia')?.value || '3500';
  const params = new URLSearchParams({
    origem_id: orig,
    destino_id: dest,
    no_indisponivel: noInd,
    autonomia_m: autonomia,
    t: String(Date.now()),
  });
  iframe.src = `/api/mapa/folium?${params.toString()}`;
  const linkDl = document.getElementById('link-download-folium');
  if (linkDl) {
    params.set('download', '1');
    linkDl.href = `/api/mapa/folium?${params.toString()}`;
  }
}

function atualizarImagensMatplotlib() {
  const ts = Date.now();
  const modoGrafo = document.getElementById('mpl-grafo-modo').value;
  const origGrafo = document.getElementById('mpl-grafo-origem').value;
  const destGrafo = document.getElementById('mpl-grafo-destino').value;
  const urlGrafo = `/api/graficos/malha-viaria.png?modo=${encodeURIComponent(modoGrafo)}&origem_id=${encodeURIComponent(origGrafo)}&destino_id=${encodeURIComponent(destGrafo)}&t=${ts}`;
  document.getElementById('img-mpl-grafo').src = urlGrafo;
  document.getElementById('link-download-mpl-grafo').href = urlGrafo;

  document.getElementById('img-mpl-hash').src = `/api/graficos/hash.png?t=${ts}`;

  const nOrd = document.getElementById('mpl-ord-n').value;
  const urlOrd = `/api/graficos/ordenacao.png?n=${encodeURIComponent(nOrd)}&t=${ts}`;
  document.getElementById('img-mpl-ordenacao').src = urlOrd;
  document.getElementById('link-download-mpl-ord').href = urlOrd;
}

async function carregarEstadoGeral() {
  estadoLocal.dados = await requisitarJson('/api/estado-geral');
  preencherSelectsVerticesEArestas();
  renderizarTriagemEUp1();
  desenharMapa();
  await carregarPainelHash();
  await carregarPainelOrdenacao();
  atualizarMapaFolium();
}

function alternarModoVisual(modo) {
  document.querySelectorAll('.aba-visual').forEach((btn) => {
    const ativo = btn.getAttribute('data-vis') === modo;
    btn.classList.toggle('ativa', ativo);
    btn.setAttribute('aria-selected', String(ativo));
  });
  document.querySelectorAll('.container-visual').forEach((painel) => {
    painel.classList.toggle('ativo', painel.id === `painel-vis-${modo}`);
  });
  if (modo === 'mapa' && estadoLocal.mapa) {
    window.setTimeout(() => estadoLocal.mapa.invalidateSize(), 60);
  } else if (modo === 'folium') {
    atualizarMapaFolium();
  } else {
    atualizarImagensMatplotlib();
  }
}

function configurarEventos() {
  document.querySelectorAll('.aba-visual').forEach((btn) => {
    btn.addEventListener('click', () => alternarModoVisual(btn.getAttribute('data-vis')));
  });

  document.querySelectorAll('.aba-op').forEach((btn) => {
    btn.addEventListener('click', () => {
      const alvo = btn.getAttribute('data-aba');
      document.querySelectorAll('.aba-op').forEach((b) => {
        const ativo = b === btn;
        b.classList.toggle('ativa', ativo);
        b.setAttribute('aria-selected', String(ativo));
      });
      document.querySelectorAll('.conteudo-aba').forEach((sec) => {
        sec.classList.toggle('ativo', sec.id === `aba-${alvo}`);
      });
    });
  });

  document.getElementById('btn-despachar-inicio').addEventListener('click', async () => {
    try {
      const res = await requisitarJson('/api/triagem/despachar', {
        method: 'POST',
        body: JSON.stringify({ extremidade: 'inicio' }),
      });
      estadoLocal.arestasMstAtuais = [];
      notificar(
        `Despacho início: ${res.ocorrencia_id} · ${res.ambulancia_codigo} ➔ ${res.hospital_nome} (${res.tempo_total_min} min, ${res.distancia_total_km} km)`
      );
      await carregarEstadoGeral();
      atualizarImagensMatplotlib();
      if (res.caminho_vertices && res.caminho_vertices.length > 1) {
        animarDeslocamentoAmbulancia(res.caminho_vertices, res.ambulancia_codigo, res.hospital_nome, res.paciente_nome);
      }
    } catch (e) {
      notificar(e.message, true);
    }
  });

  document.getElementById('btn-despachar-fim').addEventListener('click', async () => {
    try {
      const res = await requisitarJson('/api/triagem/despachar', {
        method: 'POST',
        body: JSON.stringify({ extremidade: 'fim' }),
      });
      estadoLocal.arestasMstAtuais = [];
      notificar(
        `Despacho fim: ${res.ocorrencia_id} · ${res.ambulancia_codigo} ➔ ${res.hospital_nome} (${res.tempo_total_min} min)`
      );
      await carregarEstadoGeral();
      atualizarImagensMatplotlib();
      if (res.caminho_vertices && res.caminho_vertices.length > 1) {
        animarDeslocamentoAmbulancia(res.caminho_vertices, res.ambulancia_codigo, res.hospital_nome, res.paciente_nome);
      }
    } catch (e) {
      notificar(e.message, true);
    }
  });

  document.getElementById('form-novo-chamado').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      const payload = {
        paciente_cpf: document.getElementById('chamado-cpf').value,
        paciente_nome: document.getElementById('chamado-nome').value,
        vertice_id: document.getElementById('chamado-vertice').value,
        nivel_gravidade: Number(document.getElementById('chamado-gravidade').value),
        descricao: document.getElementById('chamado-descricao').value,
      };
      const res = await requisitarJson('/api/ocorrencias', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      notificar(`Chamado ${res.id} registrado na triagem (${res.prioridade}).`);
      ev.target.reset();
      document.getElementById('chamado-gravidade').value = '9';
      await carregarEstadoGeral();
    } catch (e) {
      notificar(e.message, true);
    }
  });

  document.getElementById('form-busca-hash').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      const tipo = document.getElementById('hash-tipo').value;
      const chave = document.getElementById('hash-chave').value;
      await carregarPainelHash(tipo, chave);
      notificar(`Consulta concluída para a chave "${chave}".`);
    } catch (e) {
      notificar(e.message, true);
    }
  });

  document.getElementById('hash-tipo').addEventListener('change', (ev) => {
    const campoChave = document.getElementById('hash-chave');
    if (ev.target.value === 'cpf') campoChave.value = '10482937401';
    if (ev.target.value === 'cep') campoChave.value = '57010-300';
    if (ev.target.value === 'rota') campoChave.value = 'v-samu-farol->v-hge';
  });

  document.getElementById('form-novo-paciente-hash').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      const payload = {
        cpf: document.getElementById('pac-cpf').value,
        nome: document.getElementById('pac-nome').value,
        tipo_sanguineo: document.getElementById('pac-sangue').value,
        idade: Number(document.getElementById('pac-idade').value),
      };
      const res = await requisitarJson('/api/pacientes', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      notificar(
        `Paciente ${res.nome} cadastrado (posição [${res.indice_balde}], α=${res.fator_carga}).`
      );
      ev.target.reset();
      await carregarPainelHash('cpf', res.cpf);
      atualizarImagensMatplotlib();
    } catch (e) {
      notificar(e.message, true);
    }
  });

  document.getElementById('form-analise-grafo').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      const algoritmo = document.getElementById('grafo-algoritmo').value;
      const origem_id = document.getElementById('grafo-origem').value;
      const destino_id = document.getElementById('grafo-destino').value;
      const no_indisponivel = document.getElementById('grafo-no-indisponivel')?.value || '';
      const autonomia_maxima_m = Number(document.getElementById('grafo-autonomia')?.value || 3500);
      const res = await requisitarJson('/api/grafo/analisar', {
        method: 'POST',
        body: JSON.stringify({
          algoritmo,
          origem_id,
          destino_id,
          no_indisponivel,
          autonomia_maxima_m,
          max_saltos: 3,
        }),
      });
      document.getElementById('resultado-analise-grafo').textContent = JSON.stringify(res, null, 2);

      if (algoritmo === 'mst') {
        estadoLocal.arestasMstAtuais = res.arestas || [];
        document.getElementById('mpl-grafo-modo').value = 'mst';
        notificar(`Malha tronco mínima calculada: ${res.arestas.length} corredores (${res.custo_total_min} min).`);
      } else if (algoritmo === 'networkx_resiliencia') {
        estadoLocal.arestasMstAtuais = [];
        document.getElementById('mpl-grafo-modo').value = 'networkx';
        document.getElementById('mpl-grafo-origem').value = origem_id;
        document.getElementById('mpl-grafo-destino').value = destino_id;
        document.getElementById('folium-origem').value = origem_id;
        document.getElementById('folium-destino').value = destino_id;
        document.getElementById('folium-no-indisponivel').value = no_indisponivel || '';
        document.getElementById('folium-autonomia').value = autonomia_maxima_m > 0 ? String(autonomia_maxima_m) : 'sem_limite';
        notificar(
          `Rota calculada: ${res.rota_principal.distancia_haversine_m} m | Rota de contingência (sem ${res.contingencia.no_indisponivel}): ${res.contingencia.distancia_haversine_m} m.`
        );
      } else if (algoritmo === 'representacoes') {
        notificar(
          `Topologia exportada: Matriz (${res.matriz_adjacencia.dimensao}) e Lista de Adjacência (${res.lista_adjacencia.complexidade_espaco}).`
        );
      } else {
        estadoLocal.arestasMstAtuais = [];
        document.getElementById('mpl-grafo-modo').value = 'dijkstra';
        document.getElementById('mpl-grafo-origem').value = origem_id;
        document.getElementById('mpl-grafo-destino').value = destino_id;
        notificar(`Análise de rede (${algoritmo.toUpperCase()}) concluída.`);
      }
      await carregarEstadoGeral();
      atualizarImagensMatplotlib();
      atualizarMapaFolium();
      if (algoritmo === 'dijkstra' && res.caminho_vertices && res.caminho_vertices.length > 1) {
        animarDeslocamentoAmbulancia(res.caminho_vertices, 'Viatura SAMU', destino_id);
      } else if (algoritmo === 'networkx_resiliencia' && res.rota_principal && res.rota_principal.caminho_vertices && res.rota_principal.caminho_vertices.length > 1) {
        animarDeslocamentoAmbulancia(res.rota_principal.caminho_vertices, 'Viatura SAMU', destino_id);
      }
    } catch (e) {
      notificar(e.message, true);
    }
  });

  document.getElementById('form-alterar-via').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      const [origem_id, destino_id] = document.getElementById('via-selecionada').value.split('|');
      const fator_transito = Number(document.getElementById('via-fator').value);
      const bloqueada = document.getElementById('via-bloqueada').value === 'true';
      const res = await requisitarJson('/api/grafo/via', {
        method: 'POST',
        body: JSON.stringify({ origem_id, destino_id, fator_transito, bloqueada }),
      });
      notificar(
        `Trecho ${origem_id} <-> ${destino_id} atualizado. Conexo: ${res.malha_conexa ? 'Sim' : 'Não'}.`
      );
      await carregarEstadoGeral();
      atualizarImagensMatplotlib();
    } catch (e) {
      notificar(e.message, true);
    }
  });

  document.getElementById('ord-alvo').addEventListener('change', (ev) => {
    const selCrit = document.getElementById('ord-criterio');
    const alvo = ev.target.value;
    if (alvo === 'hospitais') {
      selCrit.innerHTML = `
        <option value="taxa_ocupacao">Taxa de Ocupação (%)</option>
        <option value="leitos_livres">Leitos Livres</option>
        <option value="leitos_totais">Capacidade Total</option>
        <option value="nome">Ordem Alfabética</option>
      `;
    } else if (alvo === 'ambulancias') {
      selCrit.innerHTML = `
        <option value="km_rodados">Quilômetros Rodados (km)</option>
        <option value="total_atendimentos">Total de Atendimentos</option>
        <option value="codigo">Código da Viatura</option>
      `;
    } else {
      selCrit.innerHTML = `
        <option value="nivel_gravidade">Nível de Gravidade (1-10)</option>
        <option value="tempo_resposta_min">Tempo de Resposta (min)</option>
        <option value="id">Protocolo da Ocorrência</option>
      `;
    }
  });

  document.getElementById('form-ordenacao').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      await carregarPainelOrdenacao();
      notificar('Ordenação atualizada com sucesso.');
    } catch (e) {
      notificar(e.message, true);
    }
  });

  const executarDesfazer = async () => {
    try {
      const res = await requisitarJson('/api/operacoes/desfazer', { method: 'POST' });
      notificar(`Ação desfeita: ${res.descricao}`);
      await carregarEstadoGeral();
      atualizarImagensMatplotlib();
    } catch (e) {
      notificar(e.message, true);
    }
  };

  document.getElementById('btn-desfazer-topo').addEventListener('click', executarDesfazer);
  document.getElementById('btn-desfazer-aba').addEventListener('click', executarDesfazer);

  document.getElementById('btn-reiniciar').addEventListener('click', async () => {
    try {
      await requisitarJson('/api/reiniciar', { method: 'POST' });
      estadoLocal.arestasMstAtuais = [];
      notificar('Dados reiniciados para o estado padrão.');
      await carregarEstadoGeral();
      atualizarImagensMatplotlib();
    } catch (e) {
      notificar(e.message, true);
    }
  });

  document.getElementById('btn-atualizar-mpl-grafo').addEventListener('click', atualizarImagensMatplotlib);
  document.getElementById('btn-atualizar-mpl-hash').addEventListener('click', atualizarImagensMatplotlib);
  document.getElementById('btn-atualizar-mpl-ord').addEventListener('click', atualizarImagensMatplotlib);
  document.getElementById('btn-atualizar-folium')?.addEventListener('click', atualizarMapaFolium);
  ['folium-origem', 'folium-destino', 'folium-no-indisponivel', 'folium-autonomia'].forEach((id) => {
    document.getElementById(id)?.addEventListener('change', atualizarMapaFolium);
  });

  document.getElementById('btn-ver-grafico-hash').addEventListener('click', () => alternarModoVisual('mpl-hash'));
  document.getElementById('btn-ver-grafico-ord').addEventListener('click', () => alternarModoVisual('mpl-ordenacao'));
  document.getElementById('btn-ver-mapa-folium')?.addEventListener('click', () => alternarModoVisual('folium'));

  const selEstiloMapa = document.getElementById('seletor-estilo-mapa');
  if (selEstiloMapa) {
    selEstiloMapa.addEventListener('change', (ev) => {
      trocarEstiloMapbox(ev.target.value);
    });
  }

  const formAvalanche = document.getElementById('form-avalanche-hash');
  if (formAvalanche) {
    formAvalanche.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      try {
        const chave_a = document.getElementById('avalanche-cpf-1').value;
        const chave_b = document.getElementById('avalanche-cpf-2').value;
        const res = await requisitarJson('/api/hash/simular-avalanche', {
          method: 'POST',
          body: JSON.stringify({ chave_a, chave_b }),
        });
        const container = document.getElementById('resultado-avalanche-hash');
        container.style.display = 'block';
        container.textContent = JSON.stringify(res, null, 2);
        notificar(`Efeito avalanche: ${res.taxa_avalanche_hmac_pct}% dos bits alterados com 1 dígito de diferença.`);
      } catch (e) {
        notificar(e.message, true);
      }
    });
  }
}

window.addEventListener('DOMContentLoaded', async () => {
  inicializarMapa();
  configurarEventos();
  await carregarEstadoGeral();
});

