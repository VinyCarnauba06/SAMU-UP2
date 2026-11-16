from typing import Callable, Generic, Iterator, Optional, TypeVar

T = TypeVar('T')


class _No(Generic[T]):
    __slots__ = ('valor', 'proximo')

    def __init__(self, valor: T) -> None:
        self.valor: T = valor
        self.proximo: Optional['_No[T]'] = None


class ListaEncadeada(Generic[T]):

    def __init__(self) -> None:
        self._cabeca: Optional[_No[T]] = None
        self._tamanho: int = 0

    def __len__(self) -> int:
        return self._tamanho

    def esta_vazia(self) -> bool:
        return self._cabeca is None

    def inserir_no_inicio(self, valor: T) -> None:
        no = _No(valor)
        no.proximo = self._cabeca
        self._cabeca = no
        self._tamanho += 1

    def inserir_no_fim(self, valor: T) -> None:
        no = _No(valor)
        if self._cabeca is None:
            self._cabeca = no
        else:
            atual = self._cabeca
            while atual.proximo is not None:
                atual = atual.proximo
            atual.proximo = no
        self._tamanho += 1

    def remover_onde(self, predicado: Callable[[T], bool]) -> Optional[T]:
        anterior: Optional[_No[T]] = None
        atual = self._cabeca
        while atual is not None:
            if predicado(atual.valor):
                if anterior is None:
                    self._cabeca = atual.proximo
                else:
                    anterior.proximo = atual.proximo
                self._tamanho -= 1
                return atual.valor
            anterior = atual
            atual = atual.proximo
        return None

    def encontrar(self, predicado: Callable[[T], bool]) -> Optional[T]:
        atual = self._cabeca
        while atual is not None:
            if predicado(atual.valor):
                return atual.valor
            atual = atual.proximo
        return None

    def para_lista(self) -> list[T]:
        saida: list[T] = []
        atual = self._cabeca
        while atual is not None:
            saida.append(atual.valor)
            atual = atual.proximo
        return saida

    def __iter__(self) -> Iterator[T]:
        atual = self._cabeca
        while atual is not None:
            yield atual.valor
            atual = atual.proximo

    def __repr__(self) -> str:
        return f'ListaEncadeada({self.para_lista()!r})'

