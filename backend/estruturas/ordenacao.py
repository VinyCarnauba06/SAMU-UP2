import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

T = TypeVar('T')

ALGORITMO_BOLHA = 'bubble_sort'
ALGORITMO_INSERCAO = 'insertion_sort'
ALGORITMO_SELECAO = 'selection_sort'
ALGORITMO_QUICKSORT = 'quick_sort'


@dataclass
class MetricasOrdenacao:
    algoritmo: str
    nome_exibicao: str
    tamanho_entrada: int
    comparacoes: int
    trocas: int
    tempo_ms: float
    complexidade_melhor: str
    complexidade_medio: str
    complexidade_pior: str
    estavel: bool


def bubble_sort(
    itens: list[T],
    chave: Callable[[T], Any] = lambda x: x,
    reverso: bool = False,
) -> tuple[list[T], MetricasOrdenacao]:
    dados = list(itens)
    n = len(dados)
    comparacoes = 0
    trocas = 0
    inicio = time.perf_counter()

    for i in range(n):
        trocou = False
        for j in range(0, n - i - 1):
            comparacoes += 1
            val_esq = chave(dados[j])
            val_dir = chave(dados[j + 1])
            fora_de_ordem = val_esq < val_dir if reverso else val_esq > val_dir
            if fora_de_ordem:
                dados[j], dados[j + 1] = dados[j + 1], dados[j]
                trocas += 1
                trocou = True
        if not trocou:
            break

    tempo_ms = (time.perf_counter() - inicio) * 1000.0
    metricas = MetricasOrdenacao(
        algoritmo=ALGORITMO_BOLHA,
        nome_exibicao='Método da Bolha (Bubble Sort)',
        tamanho_entrada=n,
        comparacoes=comparacoes,
        trocas=trocas,
        tempo_ms=round(tempo_ms, 4),
        complexidade_melhor='O(n)',
        complexidade_medio='O(n²)',
        complexidade_pior='O(n²)',
        estavel=True,
    )
    return (dados, metricas)


def insertion_sort(
    itens: list[T],
    chave: Callable[[T], Any] = lambda x: x,
    reverso: bool = False,
) -> tuple[list[T], MetricasOrdenacao]:
    dados = list(itens)
    n = len(dados)
    comparacoes = 0
    trocas = 0
    inicio = time.perf_counter()

    for i in range(1, n):
        elemento_atual = dados[i]
        chave_atual = chave(elemento_atual)
        j = i - 1
        while j >= 0:
            comparacoes += 1
            chave_j = chave(dados[j])
            deve_deslocar = chave_j < chave_atual if reverso else chave_j > chave_atual
            if deve_deslocar:
                dados[j + 1] = dados[j]
                trocas += 1
                j -= 1
            else:
                break
        dados[j + 1] = elemento_atual

    tempo_ms = (time.perf_counter() - inicio) * 1000.0
    metricas = MetricasOrdenacao(
        algoritmo=ALGORITMO_INSERCAO,
        nome_exibicao='Método da Inserção (Insertion Sort)',
        tamanho_entrada=n,
        comparacoes=comparacoes,
        trocas=trocas,
        tempo_ms=round(tempo_ms, 4),
        complexidade_melhor='O(n)',
        complexidade_medio='O(n²)',
        complexidade_pior='O(n²)',
        estavel=True,
    )
    return (dados, metricas)


def selection_sort(
    itens: list[T],
    chave: Callable[[T], Any] = lambda x: x,
    reverso: bool = False,
) -> tuple[list[T], MetricasOrdenacao]:
    dados = list(itens)
    n = len(dados)
    comparacoes = 0
    trocas = 0
    inicio = time.perf_counter()

    for i in range(n):
        indice_extremo = i
        chave_extrema = chave(dados[i])
        for j in range(i + 1, n):
            comparacoes += 1
            chave_j = chave(dados[j])
            melhor = chave_j > chave_extrema if reverso else chave_j < chave_extrema
            if melhor:
                indice_extremo = j
                chave_extrema = chave_j
        if indice_extremo != i:
            dados[i], dados[indice_extremo] = dados[indice_extremo], dados[i]
            trocas += 1

    tempo_ms = (time.perf_counter() - inicio) * 1000.0
    metricas = MetricasOrdenacao(
        algoritmo=ALGORITMO_SELECAO,
        nome_exibicao='Método da Seleção (Selection Sort)',
        tamanho_entrada=n,
        comparacoes=comparacoes,
        trocas=trocas,
        tempo_ms=round(tempo_ms, 4),
        complexidade_melhor='O(n²)',
        complexidade_medio='O(n²)',
        complexidade_pior='O(n²)',
        estavel=False,
    )
    return (dados, metricas)


def quick_sort(
    itens: list[T],
    chave: Callable[[T], Any] = lambda x: x,
    reverso: bool = False,
) -> tuple[list[T], MetricasOrdenacao]:
    dados = list(itens)
    n = len(dados)
    contadores = {'comparacoes': 0, 'trocas': 0}
    inicio = time.perf_counter()

    def _comparar_menor_ou_igual(a: Any, b: Any) -> bool:
        contadores['comparacoes'] += 1
        return a >= b if reverso else a <= b

    def _escolher_pivo_mediana_de_tres(baixo: int, alto: int) -> None:
        meio = (baixo + alto) // 2
        if not _comparar_menor_ou_igual(chave(dados[baixo]), chave(dados[meio])):
            dados[baixo], dados[meio] = dados[meio], dados[baixo]
            contadores['trocas'] += 1
        if not _comparar_menor_ou_igual(chave(dados[baixo]), chave(dados[alto])):
            dados[baixo], dados[alto] = dados[alto], dados[baixo]
            contadores['trocas'] += 1
        if not _comparar_menor_ou_igual(chave(dados[meio]), chave(dados[alto])):
            dados[meio], dados[alto] = dados[alto], dados[meio]
            contadores['trocas'] += 1
        dados[meio], dados[alto] = dados[alto], dados[meio]
        contadores['trocas'] += 1

    def _particionar(baixo: int, alto: int) -> int:
        if alto - baixo >= 2:
            _escolher_pivo_mediana_de_tres(baixo, alto)
        pivo_val = chave(dados[alto])
        i = baixo - 1
        for j in range(baixo, alto):
            if _comparar_menor_ou_igual(chave(dados[j]), pivo_val):
                i += 1
                if i != j:
                    dados[i], dados[j] = dados[j], dados[i]
                    contadores['trocas'] += 1
        if i + 1 != alto:
            dados[i + 1], dados[alto] = dados[alto], dados[i + 1]
            contadores['trocas'] += 1
        return i + 1

    def _quicksort_recursivo(baixo: int, alto: int) -> None:
        if baixo < alto:
            indice_pivo = _particionar(baixo, alto)
            _quicksort_recursivo(baixo, indice_pivo - 1)
            _quicksort_recursivo(indice_pivo + 1, alto)

    if n > 1:
        _quicksort_recursivo(0, n - 1)

    tempo_ms = (time.perf_counter() - inicio) * 1000.0
    metricas = MetricasOrdenacao(
        algoritmo=ALGORITMO_QUICKSORT,
        nome_exibicao='QuickSort (Mediana de Três)',
        tamanho_entrada=n,
        comparacoes=contadores['comparacoes'],
        trocas=contadores['trocas'],
        tempo_ms=round(tempo_ms, 4),
        complexidade_melhor='O(n log n)',
        complexidade_medio='O(n log n)',
        complexidade_pior='O(n²)',
        estavel=False,
    )
    return (dados, metricas)


def ordenar_com_algoritmo(
    algoritmo: str,
    itens: list[T],
    chave: Callable[[T], Any] = lambda x: x,
    reverso: bool = False,
) -> tuple[list[T], MetricasOrdenacao]:
    mapa = {
        ALGORITMO_BOLHA: bubble_sort,
        ALGORITMO_INSERCAO: insertion_sort,
        ALGORITMO_SELECAO: selection_sort,
        ALGORITMO_QUICKSORT: quick_sort,
    }
    if algoritmo not in mapa:
        raise ValueError(f'algoritmo de ordenacao invalido: {algoritmo}')
    return mapa[algoritmo](itens, chave=chave, reverso=reverso)


def comparar_todos_algoritmos(
    itens: list[T],
    chave: Callable[[T], Any] = lambda x: x,
    reverso: bool = False,
) -> list[MetricasOrdenacao]:
    resultados: list[MetricasOrdenacao] = []
    for fn in (bubble_sort, insertion_sort, selection_sort, quick_sort):
        _, metricas = fn(itens, chave=chave, reverso=reverso)
        resultados.append(metricas)
    return resultados

