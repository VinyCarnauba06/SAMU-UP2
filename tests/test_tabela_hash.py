from backend.estruturas import (
    COLISAO_ENCADEAMENTO,
    COLISAO_SONDAGEM_LINEAR,
    COLISAO_SONDAGEM_QUADRATICA,
    METODO_DIVISAO_HORNER,
    METODO_DOBRA,
    METODO_HASH_HMAC_SHA256,
    METODO_MULTIPLICACAO,
    TabelaHash,
)


def test_hash_horner_encadeamento_separado() -> None:
    tabela: TabelaHash[str, str] = TabelaHash(
        capacidade_inicial=7,
        metodo_hash=METODO_DIVISAO_HORNER,
        metodo_colisao=COLISAO_ENCADEAMENTO,
        justificativa_aplicacao='Teste Horner',
    )
    for i in range(20):
        cpf = f'10482937{i:03d}'
        tabela.inserir(cpf, f'Paciente {i}')
    assert len(tabela) == 20
    assert tabela.obter('10482937005') == 'Paciente 5'
    tabela.inserir('10482937005', 'Paciente Cinco Atualizado')
    assert tabela.obter('10482937005') == 'Paciente Cinco Atualizado'
    removido = tabela.remover('10482937005')
    assert removido == 'Paciente Cinco Atualizado'
    assert tabela.obter('10482937005') is None
    est = tabela.estatisticas()
    assert est.metodo_hash == METODO_DIVISAO_HORNER
    assert est.metodo_colisao == COLISAO_ENCADEAMENTO


def test_hash_multiplicacao_sondagem_quadratica() -> None:
    tabela: TabelaHash[str, float] = TabelaHash(
        capacidade_inicial=11,
        metodo_hash=METODO_MULTIPLICACAO,
        metodo_colisao=COLISAO_SONDAGEM_QUADRATICA,
        justificativa_aplicacao='Cache de rotas',
    )
    chaves = [f'v-{i}->v-{i+1}' for i in range(15)]
    for idx, ch in enumerate(chaves):
        tabela.inserir(ch, float(idx) * 1.5)
    assert len(tabela) == 15
    for idx, ch in enumerate(chaves):
        assert tabela.obter(ch) == float(idx) * 1.5
    assert tabela.remover(chaves[3]) == 4.5
    assert not tabela.contem(chaves[3])
    tabela.inserir(chaves[3], 99.0)
    assert tabela.obter(chaves[3]) == 99.0


def test_hash_dobra_sondagem_linear() -> None:
    tabela: TabelaHash[str, str] = TabelaHash(
        capacidade_inicial=11,
        metodo_hash=METODO_DOBRA,
        metodo_colisao=COLISAO_SONDAGEM_LINEAR,
        justificativa_aplicacao='CEPs de Maceio',
    )
    ceps = ['57010300', '57020600', '57052405', '57025580', '57084025', '57072290']
    for cep in ceps:
        tabela.inserir(cep, f'Unidade {cep}')
    for cep in ceps:
        assert tabela.obter(cep) == f'Unidade {cep}'
    est = tabela.estatisticas()
    assert est.tamanho == len(ceps)
    assert sum(est.ocupacao_por_posicao) == len(ceps)


def test_hash_criptografico_hmac_sha256() -> None:
    tabela: TabelaHash[str, str] = TabelaHash(
        capacidade_inicial=19,
        metodo_hash=METODO_HASH_HMAC_SHA256,
        metodo_colisao=COLISAO_ENCADEAMENTO,
        justificativa_aplicacao='Prontuario Criptografico LGPD',
    )
    tabela.inserir('10482937401', 'Carlos Eduardo')
    tabela.inserir('10482937402', 'Maria Jose')
    assert tabela.obter('10482937401') == 'Carlos Eduardo'
    assert tabela.obter('10482937402') == 'Maria Jose'
    token = tabela.gerar_token_lgpd('10482937401')
    assert token.startswith('lgpd-')
    assert len(token) > 10


def test_simulacao_efeito_avalanche() -> None:
    resultado = TabelaHash.simular_efeito_avalanche('10482937401', '10482937402')
    assert resultado['bits_alterados_hmac'] > 80
    assert resultado['taxa_avalanche_hmac_pct'] > 35.0
    assert 'conclusao_teorica' in resultado

