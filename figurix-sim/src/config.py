"""Carregador de configuração de regras (config/regras_v1.json + variantes).

Toda regra numérica do jogo deve ser lida daqui. O motor nunca deve ter
um número de regra escrito diretamente no código-fonte.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PADRAO = ROOT / "config" / "regras_v1.json"


def carregar_config(caminho: str | Path = CONFIG_PADRAO, overrides: dict | None = None) -> dict:
    """Carrega o JSON de regras. Se `overrides` for passado, faz merge raso
    por cima (usado para variantes de experimento)."""
    with open(caminho, encoding="utf-8") as f:
        config = json.load(f)
    if overrides:
        config = merge_config(config, overrides)
    return config


def carregar_variante(nome_variante: str, base: str | Path = CONFIG_PADRAO) -> dict:
    """Carrega regras_v1.json e aplica os overrides de config/variantes/<nome>.json"""
    config = carregar_config(base)
    caminho_variante = ROOT / "config" / "variantes" / f"{nome_variante}.json"
    with open(caminho_variante, encoding="utf-8") as f:
        overrides = json.load(f)
    return merge_config(config, overrides)


def merge_config(config: dict, overrides: dict) -> dict:
    resultado = copy.deepcopy(config)
    for chave, valor in overrides.items():
        if isinstance(valor, dict) and isinstance(resultado.get(chave), dict):
            resultado[chave] = merge_config(resultado[chave], valor)
        else:
            resultado[chave] = valor
    return resultado
