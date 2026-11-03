import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from suporte.base import Base
from suporte.politica import Decisao, avaliar_cupom, avaliar_reembolso


@dataclass
class Acao:
    id: str
    tipo: str
    pedido_id: str
    valor: float
    motivo: str
    justificativa: str
    proposta_por: str
    status: str
    decidida_por: str | None = None
    observacao: str | None = None


@dataclass
class Registro:
    quando: str
    quem: str
    evento: str
    dados: dict = field(default_factory=dict)


class Fila:
    def __init__(self, base: Base, auditoria: Path | None = None, arquivo_acoes: Path | None = None):
        self.base = base
        self.acoes: dict[str, Acao] = {}
        self.registros: list[Registro] = []
        self.auditoria = auditoria
        self.arquivo_acoes = arquivo_acoes
        if arquivo_acoes and arquivo_acoes.exists():
            dados = json.loads(arquivo_acoes.read_text(encoding="utf-8"))
            self.acoes = {d["id"]: Acao(**d) for d in dados}

    def _salvar_acoes(self) -> None:
        if self.arquivo_acoes:
            dados = [asdict(a) for a in self.acoes.values()]
            self.arquivo_acoes.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    def registrar(self, quem: str, evento: str, **dados) -> None:
        registro = Registro(datetime.now(timezone.utc).isoformat(timespec="seconds"), quem, evento, dados)
        self.registros.append(registro)
        if self.auditoria:
            with self.auditoria.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(registro), ensure_ascii=False) + "\n")

    def _avaliar(self, tipo: str, pedido_id: str, valor: float, motivo: str) -> Decisao:
        if tipo == "reembolso":
            return avaliar_reembolso(self.base, pedido_id, valor, motivo)
        if tipo == "cupom":
            return avaliar_cupom(self.base, pedido_id, valor)
        return Decisao(False, f"tipo de ação '{tipo}' não existe")

    def propor(self, tipo: str, pedido_id: str, valor: float, motivo: str, justificativa: str, agente: str) -> Acao:
        valor = round(float(valor), 2)
        decisao = self._avaliar(tipo, pedido_id, valor, motivo)
        acao = Acao(uuid.uuid4().hex[:8], tipo, pedido_id.strip().upper(), valor, motivo, justificativa, agente, "aguardando_aprovacao" if decisao.permitida else "recusada_pela_politica")
        if not decisao.permitida:
            acao.observacao = decisao.motivo
        self.acoes[acao.id] = acao
        self._salvar_acoes()
        self.registrar(agente, "acao_proposta", acao=asdict(acao), politica=decisao.motivo)
        return acao

    def pendentes(self) -> list[Acao]:
        return [a for a in self.acoes.values() if a.status == "aguardando_aprovacao"]

    def aprovar(self, acao_id: str, aprovador: str) -> Acao:
        acao = self._buscar(acao_id)
        if acao.status != "aguardando_aprovacao":
            raise ValueError(f"ação {acao_id} está '{acao.status}' e não pode ser aprovada")
        decisao = self._avaliar(acao.tipo, acao.pedido_id, acao.valor, acao.motivo)
        if not decisao.permitida:
            acao.status, acao.decidida_por, acao.observacao = "recusada_pela_politica", aprovador, decisao.motivo
            self._salvar_acoes()
            self.registrar(aprovador, "aprovacao_barrada", acao_id=acao_id, politica=decisao.motivo)
            return acao
        pedido = self.base.pedido(acao.pedido_id)
        if acao.tipo == "reembolso":
            pedido.reembolsado = round(pedido.reembolsado + acao.valor, 2)
        else:
            pedido.cupons.append(acao.valor)
        acao.status, acao.decidida_por = "executada", aprovador
        self.base.salvar()
        self._salvar_acoes()
        self.registrar(aprovador, "acao_executada", acao_id=acao_id, tipo=acao.tipo, valor=acao.valor, pedido_id=acao.pedido_id)
        return acao

    def recusar(self, acao_id: str, aprovador: str, observacao: str) -> Acao:
        acao = self._buscar(acao_id)
        if acao.status != "aguardando_aprovacao":
            raise ValueError(f"ação {acao_id} está '{acao.status}' e não pode ser recusada")
        acao.status, acao.decidida_por, acao.observacao = "recusada_por_humano", aprovador, observacao
        self._salvar_acoes()
        self.registrar(aprovador, "acao_recusada", acao_id=acao_id, observacao=observacao)
        return acao

    def _buscar(self, acao_id: str) -> Acao:
        if acao_id not in self.acoes:
            raise KeyError(f"ação {acao_id} não existe")
        return self.acoes[acao_id]
