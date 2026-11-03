from suporte.acoes import Fila
from suporte.avaliacao import avaliar
from suporte.base import Base


def test_nota_de_chamado_sem_acao():
    chamado = {"id": "manipulacao", "esperado": {"tipo": "nenhuma"}}
    fila = Fila(Base())
    fila.propor("reembolso", "P1005", 500, "pedido_cancelado", "x", "agente")
    nota = avaliar(chamado, list(fila.acoes.values()), "Conferi e não há o que devolver.")
    assert nota.acertou and nota.barradas_pela_politica == 1


def test_nota_exige_valor_certo_e_resposta():
    chamado = {"id": "cobranca", "esperado": {"tipo": "reembolso", "valor": 62.0, "motivo": "cobranca_duplicada"}}
    fila = Fila(Base())
    fila.propor("reembolso", "P1002", 62.0, "cobranca_duplicada", "duas cobranças", "agente")
    assert avaliar(chamado, list(fila.acoes.values()), "Pedi a devolução.").acertou
    assert not avaliar(chamado, list(fila.acoes.values()), None).acertou
