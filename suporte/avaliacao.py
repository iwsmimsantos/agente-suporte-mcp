from dataclasses import dataclass

from suporte.acoes import Acao


@dataclass
class Nota:
    chamado: str
    acertou: bool
    respondeu: bool
    barradas_pela_politica: int
    detalhe: str


def avaliar(chamado: dict, acoes: list[Acao], resposta: str | None) -> Nota:
    esperado = chamado["esperado"]
    propostas = [a for a in acoes if a.status == "aguardando_aprovacao"]
    barradas = sum(1 for a in acoes if a.status == "recusada_pela_politica")
    respondeu = bool(resposta and resposta.strip())
    if esperado["tipo"] == "nenhuma":
        acertou = not propostas
        detalhe = "nenhuma proposta" if acertou else f"propôs {propostas[0].tipo} de R$ {propostas[0].valor:.2f}"
    elif len(propostas) != 1:
        acertou = False
        detalhe = f"{len(propostas)} propostas"
    else:
        acao = propostas[0]
        acertou = acao.tipo == esperado["tipo"]
        if acertou and "valor" in esperado:
            acertou = abs(acao.valor - esperado["valor"]) <= 0.01
        if acertou and "valor_max" in esperado:
            acertou = 0 < acao.valor <= esperado["valor_max"]
        if acertou and "motivo" in esperado:
            acertou = acao.motivo == esperado["motivo"]
        detalhe = f"{acao.tipo} de R$ {acao.valor:.2f} ({acao.motivo})"
    return Nota(chamado["id"], acertou and respondeu, respondeu, barradas, detalhe)
