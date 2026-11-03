import pytest

from suporte.acoes import Fila
from suporte.base import Base


def test_proposta_nao_move_dinheiro_ate_aprovar():
    fila = Fila(Base())
    acao = fila.propor("reembolso", "P1003", 34.9, "item_faltando", "rastreio confirma falta do temaki", "agente")
    assert acao.status == "aguardando_aprovacao"
    assert fila.base.pedido("P1003").reembolsado == 0
    fila.aprovar(acao.id, "ana.operacao")
    assert fila.base.pedido("P1003").reembolsado == 34.9


def test_nao_executa_duas_vezes():
    fila = Fila(Base())
    acao = fila.propor("cupom", "P1001", 15.0, "atraso", "55 min de atraso", "agente")
    fila.aprovar(acao.id, "ana.operacao")
    with pytest.raises(ValueError):
        fila.aprovar(acao.id, "ana.operacao")
    assert fila.base.pedido("P1001").cupons == [15.0]


def test_reconfere_a_politica_na_hora_de_aprovar():
    fila = Fila(Base())
    primeira = fila.propor("reembolso", "P1006", 73.0, "pedido_cancelado", "cancelado e pago", "agente")
    segunda = fila.propor("reembolso", "P1006", 73.0, "pedido_cancelado", "cancelado e pago", "agente")
    fila.aprovar(primeira.id, "ana.operacao")
    barrada = fila.aprovar(segunda.id, "ana.operacao")
    assert barrada.status == "recusada_pela_politica"
    assert fila.base.pedido("P1006").reembolsado == 73.0


def test_recusa_humana_e_trilha_de_auditoria():
    fila = Fila(Base())
    acao = fila.propor("cupom", "P1001", 10.0, "atraso", "55 min de atraso", "agente")
    fila.recusar(acao.id, "ana.operacao", "cliente já recebeu cupom por telefone")
    eventos = [r.evento for r in fila.registros]
    assert eventos == ["acao_proposta", "acao_recusada"]
    assert fila.registros[-1].quem == "ana.operacao"


def test_persistencia_entre_processos(tmp_path):
    fila = Fila(Base(tmp_path / "pedidos.json"), tmp_path / "auditoria.jsonl", tmp_path / "acoes.json")
    acao = fila.propor("cupom", "P1001", 10.0, "atraso", "55 min de atraso", "agente")
    outra = Fila(Base(tmp_path / "pedidos.json"), tmp_path / "auditoria.jsonl", tmp_path / "acoes.json")
    outra.aprovar(acao.id, "ana.operacao")
    terceira = Fila(Base(tmp_path / "pedidos.json"), None, tmp_path / "acoes.json")
    assert terceira.base.pedido("P1001").cupons == [10.0]
    assert terceira.acoes[acao.id].status == "executada"
    assert len((tmp_path / "auditoria.jsonl").read_text().splitlines()) == 2
