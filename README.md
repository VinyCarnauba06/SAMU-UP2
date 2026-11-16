# PULSO 192 — Regulação Médica e Despacho Georreferenciado

Sistema acadêmico em Python para despacho de emergência do SAMU e regulação de leitos hospitalares em Maceió-AL. O projeto combina estruturas de dados fundamentais da 1ª unidade com três diferenciais obrigatórios da 2ª unidade: **Tabelas Hash com justificativa matemática de cada método de dispersão e colisão**, **Algoritmos em Grafos Georreferenciados com exportação visual no Matplotlib** e **Algoritmos de Ordenação comparados experimentalmente**.

Demonstração com **24 vértices viários reais de Maceió**, **9 hospitais/UPAs**, **8 viaturas do SAMU (USA e USB)** e **39 corredores viários ponderados por tempo de resposta**.

---

## O que o sistema faz

- **Triagem Dinâmica com Deque**: ocorrências de código vermelho (gravidade 8 a 10) entram no início do Deque em $O(1)$; ocorrências moderadas e leves entram no fim em $O(1)$.
- **Despacho Inteligente via Dijkstra**: calcula a ambulância com menor tempo até o paciente e o hospital com leito vago mais próximo, ponderando distância Haversine, velocidade da via e fator de congestionamento.
- **Cache de Rotas em Tabela Hash**: rotas calculadas são indexadas em memória via método da multiplicação de Knuth e sondagem quadrática, reduzindo buscas a $O(1)$.
- **Hash Criptográfico e Segurança LGPD**: pseudonimização de prontuários com HMAC-SHA256, assinatura digital de despachos e simulação do efeito avalanche.
- **Regulação de Leitos com Fila FIFO**: hospitais lotados mantêm fila de espera por leito; ao liberar vaga, o paciente mais antigo é admitido imediatamente.
- **Transações Reversíveis com Pilha LIFO**: qualquer despacho de viatura ou interdição de avenida é empilhado e pode ser revertido pelo comando Desfazer na ordem inversa exata.
- **Controle de Vias e Malha Viária (DFS)**: simulação de alagamento ou interdição de pistas com reavaliação de conectividade via busca em profundidade.
- **Árvore Geradora Mínima (Algoritmo de Prim)**: extrai a malha viária tronco essencial para circulação de veículos de socorro em Maceió.
- **Comparativo de Ordenação**: ranking de ocupação de leitos, gravidade e quilometragem processado simultaneamente por Bolha, Inserção, Seleção e QuickSort com métricas de tempo, comparações e trocas.
- **Geração Gráfica Matplotlib**: renderiza gráficos da malha viária, da distribuição dos baldes hash e do benchmark dos 4 algoritmos de ordenação, disponíveis para visualização inline e download em PNG.

---

## Tecnologias

- **Backend:** Python 3.10+ e Flask.
- **Visualização Gráfica:** Matplotlib (`Agg` backend para renderização vetorial/rasterizada em servidor).
- **Frontend:** HTML5, CSS3 estruturado e JavaScript moderno com Leaflet para mapa interativo.
- **Testes:** pytest.

---

## Como rodar localmente

Requer Python 3.10 ou superior.

```powershell
# 1. Clonar ou navegar até a pasta
cd "c:\Dev\exercicio\EXERCÍCIOS VITAL\python\Trabalho UP2"

# 2. Criar e ativar o ambiente virtual (opcional se usar Python global)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Executar os testes automatizados
python -m pytest -v

# 5. Iniciar a aplicação
python app.py
```

Abra `http://127.0.0.1:5000` no navegador.

---

## Estrutura do projeto

```text
.
|-- app.py                  # Rotas da API REST e endpoints dos gráficos Matplotlib
|-- requirements.txt        # Dependências mínimas (Flask, matplotlib, pytest)
|-- MODELAGEM.md            # Fundamentação matemática, DER e complexidade das estruturas
|-- backend/
|   |-- config.py           # Configurações de host, porta e modo de execução
|   |-- domain/             # Entidades de domínio (Hospital, Ambulancia, Paciente, Ocorrencia)
|   |-- estruturas/         # Estruturas implementadas manualmente (sem coleções prontas)
|   |   |-- vetor.py        # Vetor dinâmico com redimensionamento geométrico
|   |   |-- lista_encadeada.py # Lista encadeada simples com ponteiro cabeça
|   |   |-- pilha.py        # Pilha LIFO com topo dinâmico
|   |   |-- fila.py         # Fila FIFO com ponteiros início e fim
|   |   |-- deque.py        # Deque com nós duplamente encadeados
|   |   |-- tabela_hash.py  # Tabela Hash (Horner, Multiplicação, Dobra + Encadeamento e Sondagens)
|   |   |-- grafo.py        # Grafo geolocalizado, Dijkstra, BFS, DFS e Prim (MST)
|   |   `-- ordenacao.py    # Bubble Sort, Insertion Sort, Selection Sort e QuickSort
|   |-- repository/
|   |   `-- store.py        # Motor de persistência transacional em memória
|   |-- seed/
|   |   |-- dados.json      # Vértices, arestas, hospitais e frotas reais de Maceió-AL
|   |   `-- loader.py       # Carga inicial do repositório
|   `-- service/
|       |-- regulacao_service.py # Lógica de despacho, triagem e ordenação
|       `-- grafico_service.py   # Renderização e exportação com Matplotlib
|-- frontend/
|   |-- templates/
|   |   `-- index.html      # Interface com mapas, gráficos e painéis operacionais
|   `-- static/
|       |-- css/estilo.css  # Folha de estilos sem frameworks genéricos
|       |-- js/app.js       # Controle de eventos e alternância de visualizações
|       |-- fonts/          # Fontes IBM Plex Sans e Mono locais
|       `-- vendor/leaflet/ # Biblioteca Leaflet local
`-- tests/
    |-- test_estruturas_lineares.py # Testes de Vetor, Lista, Pilha, Fila e Deque
    |-- test_tabela_hash.py         # Testes das 3 variantes de hash e colisões
    |-- test_grafo_e_ordenacao.py   # Testes de Dijkstra, Prim, BFS, DFS e ordenação
    `-- test_regulacao_e_api.py     # Teste ponta a ponta da API e gráficos PNG
```

---

## Mapeamento dos requisitos do edital

| Requisito do Edital | Módulo no Projeto | Aplicação no Domínio do Software |
|---|---|---|
| **Vetor Dinâmico** | `estruturas/vetor.py` | Cadastro contíguo de hospitais e ambulâncias para iteração rápida e lookup indexado. |
| **Lista Encadeada** | `estruturas/lista_encadeada.py` | Prontuário de atendimentos da viatura, listas de adjacência do grafo e baldes de colisão da Hash. |
| **Pilha (LIFO)** | `estruturas/pilha.py` | Histórico transacional para reversão (rollback) de despachos e alterações viárias. |
| **Fila (FIFO)** | `estruturas/fila.py` | Fila de espera por leito hospitalar garantindo atendimento estritamente cronológico. |
| **Deque** | `estruturas/deque.py` | Triagem de ocorrências 192 (casos críticos entram na frente; casos moderados entram no fim). |
| **Diferencial 1: Tabela Hash** | `estruturas/tabela_hash.py` | 3 métodos de hash e 2 tratamentos de colisão justificados conforme a natureza da chave. |
| **Diferencial 2: Grafos + Matplotlib** | `estruturas/grafo.py` e `service/grafico_service.py` | Malha de Maceió com Dijkstra, Prim, BFS, DFS e exportação gráfica direta com Matplotlib. |
| **Diferencial 3: Ordenação** | `estruturas/ordenacao.py` | Bubble Sort, Insertion Sort, Selection Sort e QuickSort com comparativo experimental. |

