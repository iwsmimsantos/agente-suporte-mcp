import copy
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Item:
    nome: str
    preco: float


@dataclass
class Pagamento:
    id: str
    valor: float
    metodo: str
    status: str


@dataclass
class Pedido:
    id: str
    cliente: str
    restaurante: str
    itens: list[Item]
    status: str
    pedido_em: str
    prometido_para: str
    entregue_em: str | None
    pagamentos: list[Pagamento]
    eventos: list[str] = field(default_factory=list)
    reembolsado: float = 0.0
    cupons: list[float] = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(sum(i.preco for i in self.itens), 2)

    @property
    def pago(self) -> float:
        return round(sum(p.valor for p in self.pagamentos if p.status == "aprovado"), 2)

    def atraso_minutos(self, agora: str) -> int:
        prometido = datetime.fromisoformat(self.prometido_para)
        fim = datetime.fromisoformat(self.entregue_em or agora)
        return max(0, int((fim - prometido).total_seconds() // 60))


AGORA = "2026-11-03T21:30:00"

PEDIDOS_INICIAIS = [
    Pedido(
        "P1001", "Lucas", "Burger Lab",
        [Item("Smash duplo com bacon", 41.0), Item("Batata frita com cheddar", 26.0), Item("Refrigerante", 8.0)],
        "entregue", "2026-11-03T20:00:00", "2026-11-03T20:45:00", "2026-11-03T21:40:00",
        [Pagamento("PG1", 75.0, "pix", "aprovado")],
        ["saiu para entrega 21:05", "entregue 21:40"],
    ),
    Pedido(
        "P1002", "Mariana", "Forno Bravo",
        [Item("Pizza margherita", 54.0), Item("Refrigerante", 8.0)],
        "entregue", "2026-11-03T19:30:00", "2026-11-03T20:15:00", "2026-11-03T20:10:00",
        [Pagamento("PG2", 62.0, "cartao", "aprovado"), Pagamento("PG3", 62.0, "cartao", "aprovado")],
        ["entregue 20:10"],
    ),
    Pedido(
        "P1003", "Ana", "Sushi Kaze",
        [Item("Combinado de salmão (20 peças)", 79.9), Item("Temaki de salmão grelhado", 34.9)],
        "entregue", "2026-11-03T19:00:00", "2026-11-03T19:50:00", "2026-11-03T19:45:00",
        [Pagamento("PG4", 114.8, "pix", "aprovado")],
        ["entregue 19:45", "restaurante informou falta do temaki"],
    ),
    Pedido(
        "P1004", "Bruno", "Cedro",
        [Item("Falafel com homus", 34.0), Item("Tabule", 24.0)],
        "em_rota", "2026-11-03T19:40:00", "2026-11-03T20:20:00", None,
        [Pagamento("PG5", 58.0, "pix", "aprovado")],
        ["saiu para entrega 20:05", "entregador sem atualização desde 20:30"],
    ),
    Pedido(
        "P1005", "Carla", "Doce Lar",
        [Item("Petit gâteau", 27.0)],
        "entregue", "2026-11-03T21:00:00", "2026-11-03T21:35:00", "2026-11-03T21:20:00",
        [Pagamento("PG6", 27.0, "cartao", "aprovado")],
        ["entregue 21:20"],
    ),
    Pedido(
        "P1006", "Diego", "La Calaca",
        [Item("Burrito de carne", 42.0), Item("Nachos com guacamole", 31.0)],
        "cancelado", "2026-11-03T20:50:00", "2026-11-03T21:35:00", None,
        [Pagamento("PG7", 73.0, "pix", "aprovado")],
        ["cancelado pelo restaurante antes do preparo 20:55"],
    ),
]


class Base:
    def __init__(self, caminho: Path | None = None, agora: str = AGORA):
        self.caminho = caminho
        self.agora = agora
        self.pedidos: dict[str, Pedido] = {p.id: copy.deepcopy(p) for p in PEDIDOS_INICIAIS}
        if caminho and caminho.exists():
            self._carregar()

    def pedido(self, pedido_id: str) -> Pedido | None:
        return self.pedidos.get(pedido_id.strip().upper())

    def salvar(self) -> None:
        if not self.caminho:
            return
        dados = {pid: asdict(p) for pid, p in self.pedidos.items()}
        self.caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    def _carregar(self) -> None:
        dados = json.loads(self.caminho.read_text(encoding="utf-8"))
        for pid, d in dados.items():
            d["itens"] = [Item(**i) for i in d["itens"]]
            d["pagamentos"] = [Pagamento(**p) for p in d["pagamentos"]]
            self.pedidos[pid] = Pedido(**d)
