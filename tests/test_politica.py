from suporte.base import Base
from suporte.politica import avaliar_cupom, avaliar_reembolso


def test_cobranca_em_dobro_devolve_so_a_cobranca_a_mais():
    base = Base()
    assert avaliar_reembolso(base, "P1002", 62.0, "cobranca_duplicada").permitida
    assert not avaliar_reembolso(base, "P1002", 124.0, "cobranca_duplicada").permitida
    assert not avaliar_reembolso(base, "P1001", 75.0, "cobranca_duplicada").permitida


def test_reembolso_nunca_passa_do_que_foi_pago():
    base = Base()
    assert not avaliar_reembolso(base, "P1006", 500.0, "pedido_cancelado").permitida
    assert avaliar_reembolso(base, "P1006", 73.0, "pedido_cancelado").permitida


def test_pedido_entregue_nao_vira_nao_entregue():
    base = Base()
    assert not avaliar_reembolso(base, "P1001", 75.0, "pedido_nao_entregue").permitida
    assert avaliar_reembolso(base, "P1004", 58.0, "pedido_nao_entregue").permitida


def test_item_faltando_limitado_ao_item():
    base = Base()
    assert avaliar_reembolso(base, "P1003", 34.9, "item_faltando").permitida
    assert not avaliar_reembolso(base, "P1003", 114.8, "item_faltando").permitida


def test_motivo_fora_da_politica():
    assert not avaliar_reembolso(Base(), "P1005", 27.0, "nao_gostou").permitida


def test_cupom_so_com_atraso_e_ate_vinte_reais():
    base = Base()
    assert avaliar_cupom(base, "P1001", 20.0).permitida
    assert not avaliar_cupom(base, "P1001", 25.0).permitida
    assert not avaliar_cupom(base, "P1005", 10.0).permitida


def test_pedido_inexistente():
    assert not avaliar_reembolso(Base(), "P9999", 10.0, "pedido_cancelado").permitida
