from typing import Callable, Generic, Iterator, Optional, TypeVar

T = TypeVar('T')


class _NoDuplo(Generic[T]):
    __slots__ = ('valor', 'anterior', 'proximo')

    def __init__(self, valor: T) -> None:
        self.valor: T = valor
        self.anterior: Optional['_NoDuplo[T]'] = None
        self.proximo: Optional['_NoDuplo[T]'] = None


class DequeVazioError(Exception):
    pass


class Deque(Generic[T]):

    def __init__(self) -> None:
        self._inicio: Optional[_NoDuplo[T]] = None
        self._fim: Optional[_NoDuplo[T]] = None
        self._tamanho: int = 0

    def __len__(self) -> int:
        return self._tamanho

    def esta_vazio(self) -> bool:
        return self._inicio is None

    def inserir_inicio(self, valor: T) -> None:
        no = _NoDuplo(valor)
        if self._inicio is None:
            self._inicio = no
            self._fim = no
        else:
            no.proximo = self._inicio
            self._inicio.anterior = no
            self._inicio = no
        self._tamanho += 1

    def inserir_fim(self, valor: T) -> None:
        no = _NoDuplo(valor)
        if self._fim is None:
            self._inicio = no
            self._fim = no
        else:
            no.anterior = self._fim
            self._fim.proximo = no
            self._fim = no
        self._tamanho += 1

    def remover_inicio(self) -> T:
        if self._inicio is None:
            raise DequeVazioError('deque vazio')
        no = self._inicio
        self._inicio = no.proximo
        if self._inicio is None:
            self._fim = None
        else:
            self._inicio.anterior = None
        self._tamanho -= 1
        return no.valor

    def remover_fim(self) -> T:
        if self._fim is None:
            raise DequeVazioError('deque vazio')
        no = self._fim
        self._fim = no.anterior
        if self._fim is None:
            self._inicio = None
        else:
            self._fim.proximo = None
        self._tamanho -= 1
        return no.valor

    def frente_valor(self) -> T:
        if self._inicio is None:
            raise DequeVazioError('deque vazio')
        return self._inicio.valor

    def fim_valor(self) -> T:
        if self._fim is None:
            raise DequeVazioError('deque vazio')
        return self._fim.valor

    def remover_onde(self, predicado: Callable[[T], bool]) -> Optional[T]:
        atual = self._inicio
        while atual is not None:
            if predicado(atual.valor):
                if atual.anterior is None:
                    self._inicio = atual.proximo
                else:
                    atual.anterior.proximo = atual.proximo
                if atual.proximo is None:
                    self._fim = atual.anterior
                else:
                    atual.proximo.anterior = atual.anterior
                self._tamanho -= 1
                return atual.valor
            atual = atual.proximo
        return None

    def para_lista(self) -> list[T]:
        saida: list[T] = []
        atual = self._inicio
        while atual is not None:
            saida.append(atual.valor)
            atual = atual.proximo
        return saida

    def __iter__(self) -> Iterator[T]:
        atual = self._inicio
        while atual is not None:
            yield atual.valor
            atual = atual.proximo

    def __repr__(self) -> str:
        return f'Deque(inicio->fim={self.para_lista()!r})'

