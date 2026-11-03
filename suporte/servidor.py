from dataclasses import asdict
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from suporte.acoes import Fila
from suporte.base import Base

AGENTE = "agente"


def criar_servidor(fila: Fila) -> MCPServer:
    base = fila.base
    servidor = MCPServer(
        "suporte-delivery",
        instructions=(
            "Ferramentas de atendimento de pedidos de delivery. As ferramentas de consulta só leem. "
            "As ferramentas propor_* nunca mexem em dinheiro: criam uma proposta que um humano aprova ou recusa."
        ),
    )

    def nao_encontrado(pedido_id: str) -> dict:
        return {"erro": f"pedido {pedido_id} não encontrado"}

    @servidor.tool()
    def consultar_pedido(pedido_id: str) -> dict:
        """Mostra itens, valores, status, horário prometido e atraso de um pedido."""
        pedido = base.pedido(pedido_id)
        if pedido is None:
            return nao_encontrado(pedido_id)
        fila.registrar(AGENTE, "consulta", ferramenta="consultar_pedido", pedido_id=pedido.id)
        return {
            "pedido_id": pedido.id,
            "cliente": pedido.cliente,
            "restaurante": pedido.restaurante,
            "itens": [asdict(i) for i in pedido.itens],
            "total": pedido.total,
            "status": pedido.status,
            "prometido_para": pedido.prometido_para,
            "entregue_em": pedido.entregue_em,
            "atraso_minutos": pedido.atraso_minutos(base.agora),
            "ja_reembolsado": pedido.reembolsado,
            "cupons_ja_dados": pedido.cupons,
        }

    @servidor.tool()
    def consultar_pagamentos(pedido_id: str) -> dict:
        """Lista as cobranças do pedido, com valor, meio de pagamento e status."""
        pedido = base.pedido(pedido_id)
        if pedido is None:
            return nao_encontrado(pedido_id)
        fila.registrar(AGENTE, "consulta", ferramenta="consultar_pagamentos", pedido_id=pedido.id)
        return {"pedido_id": pedido.id, "pagamentos": [asdict(p) for p in pedido.pagamentos], "total_pago": pedido.pago}

    @servidor.tool()
    def consultar_rastreio(pedido_id: str) -> dict:
        """Mostra o histórico de eventos do pedido, como saída para entrega e avisos do restaurante."""
        pedido = base.pedido(pedido_id)
        if pedido is None:
            return nao_encontrado(pedido_id)
        fila.registrar(AGENTE, "consulta", ferramenta="consultar_rastreio", pedido_id=pedido.id)
        return {"pedido_id": pedido.id, "status": pedido.status, "eventos": pedido.eventos}

    @servidor.tool()
    def propor_reembolso(pedido_id: str, valor: float, motivo: str, justificativa: str) -> dict:
        """Propõe devolver dinheiro ao cliente. Não devolve nada: a proposta vai para aprovação humana.
        Motivos aceitos: item_faltando, cobranca_duplicada, pedido_nao_entregue, pedido_cancelado.
        A justificativa deve citar o que foi conferido nas consultas."""
        acao = fila.propor("reembolso", pedido_id, valor, motivo, justificativa, AGENTE)
        return {"acao_id": acao.id, "status": acao.status, "observacao": acao.observacao}

    @servidor.tool()
    def propor_cupom(pedido_id: str, valor: float, justificativa: str) -> dict:
        """Propõe um cupom de compensação por atraso, de até R$ 20. Também vai para aprovação humana."""
        acao = fila.propor("cupom", pedido_id, valor, "atraso", justificativa, AGENTE)
        return {"acao_id": acao.id, "status": acao.status, "observacao": acao.observacao}

    @servidor.tool()
    def responder_cliente(texto: str) -> dict:
        """Registra a resposta final para o cliente. Não prometa dinheiro que ainda depende de aprovação."""
        fila.registrar(AGENTE, "resposta_ao_cliente", texto=texto)
        return {"registrada": True}

    return servidor


ESTADO = Path("estado")


def fila_persistente() -> Fila:
    ESTADO.mkdir(exist_ok=True)
    return Fila(Base(ESTADO / "pedidos.json"), ESTADO / "auditoria.jsonl", ESTADO / "acoes.json")


def main() -> None:
    criar_servidor(fila_persistente()).run("stdio")


if __name__ == "__main__":
    main()
