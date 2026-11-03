import json

from mcp import Client

from suporte.acoes import Fila
from suporte.base import Base
from suporte.servidor import criar_servidor


async def test_ferramentas_expostas_nao_executam_dinheiro():
    async with Client(criar_servidor(Fila(Base()))) as cliente:
        nomes = {t.name for t in (await cliente.list_tools()).tools}
    assert nomes == {"consultar_pedido", "consultar_pagamentos", "consultar_rastreio", "propor_reembolso", "propor_cupom", "responder_cliente"}


async def test_consulta_e_proposta_pelo_mcp():
    fila = Fila(Base())
    async with Client(criar_servidor(fila)) as cliente:
        pedido = json.loads((await cliente.call_tool("consultar_pedido", {"pedido_id": "p1004"})).content[0].text)
        assert pedido["status"] == "em_rota" and pedido["atraso_minutos"] == 70
        proposta = json.loads((await cliente.call_tool("propor_reembolso", {"pedido_id": "P1004", "valor": 500, "motivo": "pedido_nao_entregue", "justificativa": "x"})).content[0].text)
    assert proposta["status"] == "recusada_pela_politica"
    assert fila.pendentes() == []


async def test_servidor_de_verdade_por_stdio(tmp_path):
    import os
    import sys
    from pathlib import Path

    from mcp import StdioServerParameters

    raiz = str(Path(__file__).resolve().parent.parent)
    parametros = StdioServerParameters(command=sys.executable, args=["-m", "suporte.servidor"], cwd=str(tmp_path), env={**os.environ, "PYTHONPATH": raiz})
    async with Client(parametros) as cliente:
        resposta = await cliente.call_tool("propor_cupom", {"pedido_id": "P1001", "valor": 15, "justificativa": "55 min de atraso"})
    assert json.loads(resposta.content[0].text)["status"] == "aguardando_aprovacao"
    assert (tmp_path / "estado" / "acoes.json").exists()
    assert "acao_proposta" in (tmp_path / "estado" / "auditoria.jsonl").read_text()
