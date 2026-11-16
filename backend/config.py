import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfiguracaoApp:
    host: str
    porta: int
    debug: bool


def carregar_configuracao() -> ConfiguracaoApp:
    host = os.environ.get('PULSO_HOST', '127.0.0.1').strip() or '127.0.0.1'
    porta_str = os.environ.get('PULSO_PORT', '5000').strip()
    try:
        porta = int(porta_str)
    except ValueError:
        porta = 5000
    debug_flag = os.environ.get('PULSO_DEBUG', '0').strip() in ('1', 'true', 'True')
    debug_seguro = debug_flag and host in ('127.0.0.1', 'localhost')
    return ConfiguracaoApp(host=host, porta=porta, debug=debug_seguro)

