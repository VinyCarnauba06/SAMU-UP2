from typing import Callable, Generic, Iterator, Optional, TypeVar

T = TypeVar('T')
CAPACIDADE_INICIAL = 4
FATOR_CRESCIMENTO = 2


class Vetor(Generic[T]):

    def __init__(self, capacidade_inicial: int = CAPACIDADE_INICIAL) -> None:
        if capacidade_inicial < 1:
            capacidade_inicial = 1
        self._dados: list[Optional[T]] = [None] * capacidade_inicial
        self._tamanho: int = 0
        self._capacidade: int = capacidade_inicial

    def __len__(self) -> int:
        return self._tamanho

    @property
    def capacidade(self) -> int:
        return self._capacidade

    def esta_vazio(self) -> bool:
        return self._tamanho == 0

    def _redimensionar(self, nova_capacidade: int) -> None:
        novo_bloco: list[Optional[T]] = [None] * nova_capacidade
        for i in range(self._tamanho):
            novo_bloco[i] = self._dados[i]
        self._dados = novo_bloco
        self._capacidade = nova_capacidade

    def adicionar(self, item: T) -> None:
        if self._tamanho == self._capacidade:
            self._redimensionar(self._capacidade * FATOR_CRESCIMENTO)
        self._dados[self._tamanho] = item
        self._tamanho += 1

    def obter(self, indice: int) -> T:
        self._validar_indice(indice)
        valor = self._dados[indice]
        assert valor is not None
        return valor

    def definir(self, indice: int, item: T) -> None:
        self._validar_indice(indice)
        self._dados[indice] = item

    def remover_em(self, indice: int) -> T:
        self._validar_indice(indice)
        item = self._dados[indice]
        for i in range(indice, self._tamanho - 1):
            self._dados[i] = self._dados[i + 1]
        self._dados[self._tamanho - 1] = None
        self._tamanho -= 1
        assert item is not None
        return item

    def indice_de(self, predicado: Callable[[T], bool]) -> int:
        for i in range(self._tamanho):
            item = self._dados[i]
            if item is not None and predicado(item):
                return i
        return -1

    def encontrar(self, predicado: Callable[[T], bool]) -> Optional[T]:
        indice = self.indice_de(predicado)
        return self._dados[indice] if indice != -1 else None

    def filtrar(self, predicado: Callable[[T], bool]) -> 'Vetor[T]':
        resultado: Vetor[T] = Vetor()
        for i in range(self._tamanho):
            item = self._dados[i]
            if item is not None and predicado(item):
                resultado.adicionar(item)
        return resultado

    def __iter__(self) -> Iterator[T]:
        for i in range(self._tamanho):
            item = self._dados[i]
            if item is not None:
                yield item

    def para_lista(self) -> list[T]:
        saida: list[T] = []
        for i in range(self._tamanho):
            item = self._dados[i]
            if item is not None:
                saida.append(item)
        return saida

    def _validar_indice(self, indice: int) -> None:
        if indice < 0 or indice >= self._tamanho:
            raise IndexError(f'indice {indice} fora do intervalo [0, {self._tamanho})')

    def __repr__(self) -> str:
        return f'Vetor({self.para_lista()!r}, capacidade={self._capacidade})'

