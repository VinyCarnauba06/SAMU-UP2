import pytest
from backend.estruturas import (
    Deque,
    DequeVazioError,
    Fila,
    FilaVaziaError,
    ListaEncadeada,
    Pilha,
    PilhaVaziaError,
    Vetor,
)


def test_vetor_redimensionamento_e_operacoes() -> None:
    v: Vetor[int] = Vetor(capacidade_inicial=2)
    assert v.esta_vazio()
    for n in (10, 20, 30, 40, 50):
        v.adicionar(n)
    assert len(v) == 5
    assert v.capacidade >= 5
    assert v.obter(2) == 30
    v.definir(2, 35)
    assert v.obter(2) == 35
    removido = v.remover_em(1)
    assert removido == 20
    assert v.para_lista() == [10, 35, 40, 50]
    assert v.encontrar(lambda x: x > 36) == 40
    pares = v.filtrar(lambda x: x % 10 == 0)
    assert pares.para_lista() == [10, 40, 50]


def test_lista_encadeada_insercao_e_remocao() -> None:
    lista: ListaEncadeada[str] = ListaEncadeada()
    assert lista.esta_vazia()
    lista.inserir_no_fim('B')
    lista.inserir_no_inicio('A')
    lista.inserir_no_fim('C')
    assert lista.para_lista() == ['A', 'B', 'C']
    removido = lista.remover_onde(lambda x: x == 'B')
    assert removido == 'B'
    assert lista.para_lista() == ['A', 'C']
    assert lista.encontrar(lambda x: x == 'C') == 'C'


def test_pilha_lifo() -> None:
    pilha: Pilha[str] = Pilha()
    with pytest.raises(PilhaVaziaError):
        pilha.desempilhar()
    pilha.empilhar('op-1')
    pilha.empilhar('op-2')
    pilha.empilhar('op-3')
    assert pilha.topo_valor() == 'op-3'
    assert pilha.desempilhar() == 'op-3'
    assert pilha.desempilhar() == 'op-2'
    assert len(pilha) == 1


def test_fila_fifo() -> None:
    fila: Fila[int] = Fila()
    with pytest.raises(FilaVaziaError):
        fila.desenfileirar()
    fila.enfileirar(1)
    fila.enfileirar(2)
    fila.enfileirar(3)
    assert fila.frente_valor() == 1
    assert fila.desenfileirar() == 1
    assert fila.desenfileirar() == 2
    assert fila.para_lista() == [3]


def test_deque_insercao_e_remocao_dupla() -> None:
    d: Deque[str] = Deque()
    with pytest.raises(DequeVazioError):
        d.remover_inicio()
    d.inserir_fim('moderado-1')
    d.inserir_inicio('critico-1')
    d.inserir_fim('baixo-1')
    d.inserir_inicio('critico-2')
    assert d.para_lista() == ['critico-2', 'critico-1', 'moderado-1', 'baixo-1']
    assert d.frente_valor() == 'critico-2'
    assert d.fim_valor() == 'baixo-1'
    assert d.remover_inicio() == 'critico-2'
    assert d.remover_fim() == 'baixo-1'
    assert d.para_lista() == ['critico-1', 'moderado-1']
    removido_meio = d.remover_onde(lambda x: x == 'moderado-1')
    assert removido_meio == 'moderado-1'
    assert d.para_lista() == ['critico-1']

