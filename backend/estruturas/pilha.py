from typing import Generic, Optional, TypeVar

T = TypeVar('T')


class _No(Generic[T]):
    __slots__ = ('valor', 'proximo')

    def __init__(self, valor: T) -> None:
        self.valor: T = valor
        self.proximo: Optional['_No[T]'] = None


class PilhaVaziaError(Exception):
    pass


class Pilha(Generic[T]):

    def __init__(self) -> None:
        self._topo: Optional[_No[T]] = None
        self._tamanho: int = 0

    def __len__(self) -> int:
        return self._tamanho

    def esta_vazia(self) -> bool:
        return self._topo is None

    def empilhar(self, valor: T) -> None:
        no = _No(valor)
        no.proximo = self._topo
        self._topo = no
        self._tamanho += 1

    def desempilhar(self) -> T:
        if self._topo is None:
            raise PilhaVaziaError('pilha vazia')
        no = self._topo
        self._topo = no.proximo
        self._tamanho -= 1
        return no.valor

    def topo_valor(self) -> T:
        if self._topo is None:
            raise PilhaVaziaError('pilha vazia')
        return self._topo.valor

    def para_lista(self) -> list[T]:
        saida: list[T] = []
        atual = self._topo
        while atual is not None:
            saida.append(atual.valor)
            atual = atual.proximo
        return saida

    def __repr__(self) -> str:
        return f'Pilha(topo->base={self.para_lista()!r})'

