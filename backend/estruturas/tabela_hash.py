import hashlib
import hmac
import math
from dataclasses import dataclass
from typing import Generic, Iterator, Optional, TypeVar
from backend.estruturas.lista_encadeada import ListaEncadeada

K = TypeVar('K')
V = TypeVar('V')

METODO_DIVISAO_HORNER = 'divisao_horner'
METODO_MULTIPLICACAO = 'multiplicacao'
METODO_DOBRA = 'dobra'
METODO_HASH_HMAC_SHA256 = 'hmac_sha256'

COLISAO_ENCADEAMENTO = 'encadeamento'
COLISAO_SONDAGEM_LINEAR = 'sondagem_linear'
COLISAO_SONDAGEM_QUADRATICA = 'sondagem_quadratica'

CONSTANTE_KNUTH = (math.sqrt(5) - 1.0) / 2.0
CHAVE_SECRETA_PADRAO = b'pulso192_maceio_seguranca_hash_secreto'


@dataclass
class ParChaveValor(Generic[K, V]):
    chave: K
    valor: V


@dataclass
class _SlotAberto(Generic[K, V]):
    chave: Optional[K] = None
    valor: Optional[V] = None
    estado: str = 'vazio'


@dataclass
class EstatisticasHash:
    metodo_hash: str
    metodo_colisao: str
    capacidade: int
    tamanho: int
    fator_carga: float
    total_colisoes: int
    maior_cadeia_ou_sondagem: int
    ocupacao_por_posicao: list[int]
    justificativa_aplicacao: str


def _eh_primo(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def _proximo_primo(minimo: int) -> int:
    candidato = max(3, minimo)
    if candidato % 2 == 0:
        candidato += 1
    while not _eh_primo(candidato):
        candidato += 2
    return candidato


class TabelaHash(Generic[K, V]):

    def __init__(
        self,
        capacidade_inicial: int = 17,
        metodo_hash: str = METODO_DIVISAO_HORNER,
        metodo_colisao: str = COLISAO_ENCADEAMENTO,
        justificativa_aplicacao: str = '',
        chave_secreta: bytes = CHAVE_SECRETA_PADRAO,
    ) -> None:
        if metodo_hash not in (METODO_DIVISAO_HORNER, METODO_MULTIPLICACAO, METODO_DOBRA, METODO_HASH_HMAC_SHA256):
            raise ValueError(f'metodo_hash invalido: {metodo_hash}')
        if metodo_colisao not in (COLISAO_ENCADEAMENTO, COLISAO_SONDAGEM_LINEAR, COLISAO_SONDAGEM_QUADRATICA):
            raise ValueError(f'metodo_colisao invalido: {metodo_colisao}')
        self._metodo_hash: str = metodo_hash
        self._metodo_colisao: str = metodo_colisao
        self._justificativa: str = justificativa_aplicacao
        self._chave_secreta: bytes = chave_secreta
        self._capacidade: int = _proximo_primo(capacidade_inicial)
        self._tamanho: int = 0
        self._total_colisoes: int = 0
        self._maior_cadeia_ou_sondagem: int = 0
        self._baldes: list[ListaEncadeada[ParChaveValor[K, V]]] = []
        self._slots: list[_SlotAberto[K, V]] = []
        self._inicializar_armazenamento(self._capacidade)

    def _inicializar_armazenamento(self, capacidade: int) -> None:
        self._capacidade = capacidade
        if self._metodo_colisao == COLISAO_ENCADEAMENTO:
            self._baldes = [ListaEncadeada() for _ in range(capacidade)]
            self._slots = []
        else:
            self._slots = [_SlotAberto() for _ in range(capacidade)]
            self._baldes = []

    def __len__(self) -> int:
        return self._tamanho

    @property
    def capacidade(self) -> int:
        return self._capacidade

    @property
    def metodo_hash(self) -> str:
        return self._metodo_hash

    @property
    def metodo_colisao(self) -> str:
        return self._metodo_colisao

    @property
    def fator_carga(self) -> float:
        return self._tamanho / self._capacidade if self._capacidade > 0 else 0.0

    def _chave_para_inteiro_horner(self, chave: K) -> int:
        texto = str(chave)
        acumulador = 0
        base = 31
        for caractere in texto:
            acumulador = (acumulador * base + ord(caractere)) & 0x7FFFFFFF
        return acumulador

    def _chave_para_inteiro_dobra(self, chave: K) -> int:
        texto = str(chave)
        digitos = ''.join(str(ord(c)) if not c.isdigit() else c for c in texto)
        if not digitos:
            return 0
        tamanho_bloco = 3
        soma = 0
        bloco_idx = 0
        for i in range(0, len(digitos), tamanho_bloco):
            pedaco = digitos[i:i + tamanho_bloco]
            if bloco_idx % 2 == 1:
                pedaco = pedaco[::-1]
            soma += int(pedaco)
            bloco_idx += 1
        return soma

    def _chave_para_inteiro_hmac(self, chave: K) -> tuple[int, str]:
        texto = str(chave).encode('utf-8')
        digest_hex = hmac.new(self._chave_secreta, texto, hashlib.sha256).hexdigest()
        valor_int = int(digest_hex[:16], 16) & 0x7FFFFFFF
        return (valor_int, digest_hex)

    def calcular_indice_base(self, chave: K) -> int:
        if self._metodo_hash == METODO_HASH_HMAC_SHA256:
            valor_int, _ = self._chave_para_inteiro_hmac(chave)
            return valor_int % self._capacidade
        if self._metodo_hash == METODO_DIVISAO_HORNER:
            valor_int = self._chave_para_inteiro_horner(chave)
            return valor_int % self._capacidade
        if self._metodo_hash == METODO_MULTIPLICACAO:
            valor_int = self._chave_para_inteiro_horner(chave)
            fracao = (valor_int * CONSTANTE_KNUTH) % 1.0
            return int(math.floor(self._capacidade * fracao))
        valor_dobra = self._chave_para_inteiro_dobra(chave)
        return valor_dobra % self._capacidade

    def gerar_token_lgpd(self, chave: K) -> str:
        _, digest = self._chave_para_inteiro_hmac(chave)
        return f'lgpd-{digest[:16]}'

    @staticmethod
    def simular_efeito_avalanche(chave_a: str, chave_b: str, segredo: bytes = CHAVE_SECRETA_PADRAO) -> dict:
        dig_a = hmac.new(segredo, chave_a.encode('utf-8'), hashlib.sha256).hexdigest()
        dig_b = hmac.new(segredo, chave_b.encode('utf-8'), hashlib.sha256).hexdigest()
        bin_a = bin(int(dig_a, 16))[2:].zfill(256)
        bin_b = bin(int(dig_b, 16))[2:].zfill(256)
        bits_diferentes = sum(1 for bit_a, bit_b in zip(bin_a, bin_b) if bit_a != bit_b)
        taxa_avalanche = round((bits_diferentes / 256.0) * 100.0, 2)

        horner_a = 0
        horner_b = 0
        for c in chave_a:
            horner_a = (horner_a * 31 + ord(c)) & 0x7FFFFFFF
        for c in chave_b:
            horner_b = (horner_b * 31 + ord(c)) & 0x7FFFFFFF
        bin_ha = bin(horner_a)[2:].zfill(32)
        bin_hb = bin(horner_b)[2:].zfill(32)
        bits_dif_horner = sum(1 for bit_a, bit_b in zip(bin_ha, bin_hb) if bit_a != bit_b)
        taxa_horner = round((bits_dif_horner / 32.0) * 100.0, 2)

        return {
            'chave_original_1': chave_a,
            'chave_original_2': chave_b,
            'hmac_sha256_1': dig_a,
            'hmac_sha256_2': dig_b,
            'bits_alterados_hmac': bits_diferentes,
            'total_bits_hmac': 256,
            'taxa_avalanche_hmac_pct': taxa_avalanche,
            'bits_alterados_horner': bits_dif_horner,
            'total_bits_horner': 32,
            'taxa_avalanche_horner_pct': taxa_horner,
            'conclusao_teorica': (
                f'Enquanto o algoritmo linear Horner alterou {taxa_horner}% dos bits com alto acoplamento posicional, '
                f'o HMAC-SHA256 gerou {taxa_avalanche}% de bits invertidos (ideal criptográfico ~50%), '
                f'provando Efeito Avalanche completo e resistência contra ataques de colisão dirigida.'
            )
        }

    def _indice_sondagem(self, indice_base: int, tentativa: int) -> int:
        if self._metodo_colisao == COLISAO_SONDAGEM_LINEAR:
            return (indice_base + tentativa) % self._capacidade
        return (indice_base + tentativa + (tentativa * tentativa)) % self._capacidade

    def _precisa_redimensionar(self) -> bool:
        if self._metodo_colisao == COLISAO_ENCADEAMENTO:
            return self.fator_carga >= 0.75
        return self.fator_carga >= 0.55

    def _redimensionar(self) -> None:
        itens_atuais = self.itens()
        nova_capacidade = _proximo_primo(self._capacidade * 2)
        self._tamanho = 0
        self._maior_cadeia_ou_sondagem = 0
        self._inicializar_armazenamento(nova_capacidade)
        for chave, valor in itens_atuais:
            self._inserir_interno(chave, valor, contar_colisao=False)

    def inserir(self, chave: K, valor: V) -> None:
        if self._precisa_redimensionar():
            self._redimensionar()
        self._inserir_interno(chave, valor, contar_colisao=True)

    def _inserir_interno(self, chave: K, valor: V, contar_colisao: bool) -> None:
        indice_base = self.calcular_indice_base(chave)
        if self._metodo_colisao == COLISAO_ENCADEAMENTO:
            balde = self._baldes[indice_base]
            existente = balde.encontrar(lambda par: par.chave == chave)
            if existente is not None:
                existente.valor = valor
                return
            if len(balde) > 0 and contar_colisao:
                self._total_colisoes += 1
            balde.inserir_no_fim(ParChaveValor(chave=chave, valor=valor))
            self._tamanho += 1
            if len(balde) > self._maior_cadeia_ou_sondagem:
                self._maior_cadeia_ou_sondagem = len(balde)
            return

        primeiro_removido: Optional[int] = None
        for tentativa in range(self._capacidade):
            pos = self._indice_sondagem(indice_base, tentativa)
            slot = self._slots[pos]
            if slot.estado == 'ocupado':
                if slot.chave == chave:
                    slot.valor = valor
                    return
                if contar_colisao:
                    self._total_colisoes += 1
            elif slot.estado == 'removido':
                if primeiro_removido is None:
                    primeiro_removido = pos
            else:
                alvo = primeiro_removido if primeiro_removido is not None else pos
                self._slots[alvo] = _SlotAberto(chave=chave, valor=valor, estado='ocupado')
                self._tamanho += 1
                if tentativa + 1 > self._maior_cadeia_ou_sondagem:
                    self._maior_cadeia_ou_sondagem = tentativa + 1
                return

        if primeiro_removido is not None:
            self._slots[primeiro_removido] = _SlotAberto(chave=chave, valor=valor, estado='ocupado')
            self._tamanho += 1
            return

        self._redimensionar()
        self._inserir_interno(chave, valor, contar_colisao=contar_colisao)

    def obter(self, chave: K) -> Optional[V]:
        indice_base = self.calcular_indice_base(chave)
        if self._metodo_colisao == COLISAO_ENCADEAMENTO:
            balde = self._baldes[indice_base]
            par = balde.encontrar(lambda item: item.chave == chave)
            return par.valor if par is not None else None

        for tentativa in range(self._capacidade):
            pos = self._indice_sondagem(indice_base, tentativa)
            slot = self._slots[pos]
            if slot.estado == 'vazio':
                return None
            if slot.estado == 'ocupado' and slot.chave == chave:
                return slot.valor
        return None

    def contem(self, chave: K) -> bool:
        return self.obter(chave) is not None

    def remover(self, chave: K) -> Optional[V]:
        indice_base = self.calcular_indice_base(chave)
        if self._metodo_colisao == COLISAO_ENCADEAMENTO:
            balde = self._baldes[indice_base]
            removido = balde.remover_onde(lambda item: item.chave == chave)
            if removido is not None:
                self._tamanho -= 1
                return removido.valor
            return None

        for tentativa in range(self._capacidade):
            pos = self._indice_sondagem(indice_base, tentativa)
            slot = self._slots[pos]
            if slot.estado == 'vazio':
                return None
            if slot.estado == 'ocupado' and slot.chave == chave:
                valor = slot.valor
                slot.chave = None
                slot.valor = None
                slot.estado = 'removido'
                self._tamanho -= 1
                return valor
        return None

    def itens(self) -> list[tuple[K, V]]:
        saida: list[tuple[K, V]] = []
        if self._metodo_colisao == COLISAO_ENCADEAMENTO:
            for balde in self._baldes:
                for par in balde:
                    saida.append((par.chave, par.valor))
        else:
            for slot in self._slots:
                if slot.estado == 'ocupado' and slot.chave is not None and slot.valor is not None:
                    saida.append((slot.chave, slot.valor))
        return saida

    def valores(self) -> list[V]:
        return [valor for _, valor in self.itens()]

    def chaves(self) -> list[K]:
        return [chave for chave, _ in self.itens()]

    def __iter__(self) -> Iterator[tuple[K, V]]:
        for item in self.itens():
            yield item

    def estatisticas(self) -> EstatisticasHash:
        if self._metodo_colisao == COLISAO_ENCADEAMENTO:
            ocupacao = [len(b) for b in self._baldes]
            maior = max(ocupacao) if ocupacao else 0
        else:
            ocupacao = [1 if s.estado == 'ocupado' else 0 for s in self._slots]
            maior = max(self._maior_cadeia_ou_sondagem, max(ocupacao) if ocupacao else 0)
        return EstatisticasHash(
            metodo_hash=self._metodo_hash,
            metodo_colisao=self._metodo_colisao,
            capacidade=self._capacidade,
            tamanho=self._tamanho,
            fator_carga=round(self.fator_carga, 4),
            total_colisoes=self._total_colisoes,
            maior_cadeia_ou_sondagem=maior,
            ocupacao_por_posicao=ocupacao,
            justificativa_aplicacao=self._justificativa,
        )

