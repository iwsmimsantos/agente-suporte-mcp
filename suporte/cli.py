import argparse
import asyncio
import json
import os
import sys

from suporte.servidor import ESTADO, fila_persistente


def imprimir_acao(acao) -> None:
    linha = f"[{acao.id}] {acao.tipo} de R$ {acao.valor:.2f} no pedido {acao.pedido_id} ({acao.motivo}) · {acao.status}"
    print(linha)
    print(f"    justificativa do agente: {acao.justificativa}")
    if acao.observacao:
        print(f"    observação: {acao.observacao}")


async def comando_atender(texto: str) -> None:
    import anthropic
    from mcp import Client, StdioServerParameters

    from suporte.agente import atender

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        sys.exit("Defina ANTHROPIC_API_KEY para rodar o agente.")
    parametros = StdioServerParameters(command=sys.executable, args=["-m", "suporte.servidor"])
    async with Client(parametros) as cliente_mcp:
        resultado = await atender(texto, cliente_mcp, anthropic.Anthropic())
    for passo in resultado.passos:
        marca = "erro" if passo.erro else "ok"
        print(f"- {passo.ferramenta}({json.dumps(passo.entrada, ensure_ascii=False)}) -> {marca}")
    print(f"\nResposta ao cliente: {resultado.resposta or '(sem resposta)'}")
    pendentes = fila_persistente().pendentes()
    if pendentes:
        print("\nAguardando aprovação humana:")
        for acao in pendentes:
            imprimir_acao(acao)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m suporte.cli")
    sub = parser.add_subparsers(dest="comando", required=True)
    atender = sub.add_parser("atender", help="o agente atende um chamado")
    atender.add_argument("texto")
    sub.add_parser("pendentes", help="lista as propostas aguardando aprovação")
    aprovar = sub.add_parser("aprovar", help="aprova e executa uma proposta")
    aprovar.add_argument("acao_id")
    aprovar.add_argument("--por", required=True)
    recusar = sub.add_parser("recusar", help="recusa uma proposta")
    recusar.add_argument("acao_id")
    recusar.add_argument("--por", required=True)
    recusar.add_argument("--motivo", required=True)
    sub.add_parser("auditoria", help="mostra a trilha de auditoria")
    args = parser.parse_args()

    if args.comando == "atender":
        asyncio.run(comando_atender(args.texto))
        return
    fila = fila_persistente()
    if args.comando == "pendentes":
        pendentes = fila.pendentes()
        if not pendentes:
            print("Nada aguardando aprovação.")
        for acao in pendentes:
            imprimir_acao(acao)
    elif args.comando == "aprovar":
        imprimir_acao(fila.aprovar(args.acao_id, args.por))
    elif args.comando == "recusar":
        imprimir_acao(fila.recusar(args.acao_id, args.por, args.motivo))
    elif args.comando == "auditoria":
        arquivo = ESTADO / "auditoria.jsonl"
        print(arquivo.read_text(encoding="utf-8") if arquivo.exists() else "Trilha vazia.")


if __name__ == "__main__":
    main()
