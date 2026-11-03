from dataclasses import dataclass

from suporte.base import Base

MOTIVOS_REEMBOLSO = {
    "item_faltando": "Item faltando no pedido",
    "cobranca_duplicada": "Cobrança em dobro",
    "pedido_nao_entregue": "Pedido não entregue",
    "pedido_cancelado": "Pedido cancelado e pago",
}
ATRASO_MINIMO_CUPOM = 20
ATRASO_NAO_ENTREGUE = 60
CUPOM_MAXIMO = 20.0


@dataclass
class Decisao:
    permitida: bool
    motivo: str


def _ok() -> Decisao:
    return Decisao(True, "dentro da política")


def avaliar_reembolso(base: Base, pedido_id: str, valor: float, motivo: str) -> Decisao:
    pedido = base.pedido(pedido_id)
    if pedido is None:
        return Decisao(False, f"pedido {pedido_id} não existe")
    if motivo not in MOTIVOS_REEMBOLSO:
        return Decisao(False, f"motivo '{motivo}' não está na política")
    if valor <= 0:
        return Decisao(False, "valor precisa ser maior que zero")
    disponivel = round(pedido.pago - pedido.reembolsado, 2)
    if valor > disponivel:
        return Decisao(False, f"valor acima do que ainda pode ser devolvido (R$ {disponivel:.2f})")
    if motivo == "item_faltando":
        maior_item = max(i.preco for i in pedido.itens)
        if pedido.status != "entregue":
            return Decisao(False, "item faltando só vale para pedido entregue")
        if valor > maior_item:
            return Decisao(False, f"item faltando não passa do preço do item mais caro (R$ {maior_item:.2f})")
    if motivo == "cobranca_duplicada":
        aprovados = [p.valor for p in pedido.pagamentos if p.status == "aprovado"]
        if len(aprovados) < 2:
            return Decisao(False, "não há duas cobranças aprovadas neste pedido")
        if abs(valor - min(aprovados)) > 0.01 or pedido.pago - pedido.total < valor - 0.01:
            return Decisao(False, "devolução de cobrança em dobro tem que ser o valor da cobrança a mais")
    if motivo == "pedido_nao_entregue":
        if pedido.status == "entregue":
            return Decisao(False, "o pedido consta como entregue")
        if pedido.atraso_minutos(base.agora) < ATRASO_NAO_ENTREGUE:
            return Decisao(False, f"ainda dentro da janela de entrega (menos de {ATRASO_NAO_ENTREGUE} min de atraso)")
    if motivo == "pedido_cancelado" and pedido.status != "cancelado":
        return Decisao(False, "o pedido não está cancelado")
    return _ok()


def avaliar_cupom(base: Base, pedido_id: str, valor: float) -> Decisao:
    pedido = base.pedido(pedido_id)
    if pedido is None:
        return Decisao(False, f"pedido {pedido_id} não existe")
    if valor <= 0 or valor > CUPOM_MAXIMO:
        return Decisao(False, f"cupom tem que ficar entre R$ 0,01 e R$ {CUPOM_MAXIMO:.2f}")
    if pedido.cupons:
        return Decisao(False, "este pedido já recebeu cupom")
    if pedido.atraso_minutos(base.agora) < ATRASO_MINIMO_CUPOM:
        return Decisao(False, f"cupom de atraso só a partir de {ATRASO_MINIMO_CUPOM} min de atraso")
    return _ok()
