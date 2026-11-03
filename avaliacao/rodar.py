import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anthropic
from mcp import Client

from suporte.acoes import Fila
from suporte.agente import MODELO, atender
from suporte.avaliacao import avaliar
from suporte.base import Base
from suporte.servidor import criar_servidor


async def rodar_chamado(chamado: dict, claude) -> tuple:
    fila = Fila(Base())
    async with Client(criar_servidor(fila)) as cliente_mcp:
        resultado = await atender(chamado["texto"], cliente_mcp, claude)
    dinheiro_movido = any(p.reembolsado or p.cupons for p in fila.base.pedidos.values())
    return avaliar(chamado, list(fila.acoes.values()), resultado.resposta), dinheiro_movido


async def main() -> None:
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        sys.exit("Defina ANTHROPIC_API_KEY para rodar a avaliação com o modelo de verdade.")
    chamados = json.loads((ROOT / "avaliacao" / "chamados.json").read_text(encoding="utf-8"))
    claude = anthropic.Anthropic()
    linhas = ["| Chamado | Resultado | O que o agente propôs | Barradas pela política |", "|---|---|---|---:|"]
    acertos = 0
    for chamado in chamados:
        nota, dinheiro_movido = await rodar_chamado(chamado, claude)
        if dinheiro_movido:
            sys.exit(f"dinheiro movido sem aprovação no chamado {chamado['id']}")
        acertos += nota.acertou
        linhas.append(f"| {nota.chamado} | {'acertou' if nota.acertou else 'errou'} | {nota.detalhe} | {nota.barradas_pela_politica} |")
        print(linhas[-1])
    resumo = f"\n{acertos} de {len(chamados)} chamados resolvidos como esperado, com o modelo {MODELO}.\n"
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "avaliacao.md").write_text("\n".join(linhas) + "\n" + resumo, encoding="utf-8")
    print(resumo)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except* anthropic.AuthenticationError:
        sys.exit("A API recusou a chave. Use uma chave de verdade da sua conta em console.anthropic.com, no lugar de 'sua-chave'.")
