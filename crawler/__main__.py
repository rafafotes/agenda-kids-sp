"""Roda todas as fontes e gera site/dados/eventos.json.

Uso:  python3 -m crawler            # todas as fontes
      python3 -m crawler Morumbi    # só fontes cujo nome contém o texto
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import util
from .adaptadores import ADAPTADORES, Candidato
from .agente import MODELO, Agente
from .fontes import FONTES

SAIDA = Path(__file__).resolve().parent.parent / "site" / "dados" / "eventos.json"
LIMIAR_INFANTIL = 2  # pontuação mínima da heurística para entrar como atividade infantil
LIMIAR_SEM_DATA = 4  # sem nenhuma data, só entra quem é claramente infantil


def normalizar(fonte: dict, c: Candidato, agente: Agente) -> dict | None:
    titulo, texto = c["titulo"].strip(), (c.get("texto") or "").strip()
    tudo = f"{titulo}\n{texto}"

    inicio, fim = util.data_iso(c.get("inicio")), util.data_iso(c.get("fim"))
    if not (inicio or fim):
        inicio, fim = util.periodo_do_texto(tudo)
    if not (inicio or fim) and c.get("publicado"):
        # notícia sem data explícita ("neste sábado"): vale pelas duas semanas seguintes à publicação
        fim = util.data_iso(c["publicado"]) + timedelta(days=14)

    pontos = util.pontuacao_infantil(titulo, texto) + (6 if c.get("infantil_fonte") else 0)
    evento = {
        "titulo": titulo,
        "resumo": util.resumo(texto),
        "inicio": util.iso(inicio),
        "fim": util.iso(fim),
        "horario": util.horario(texto),
        "faixa_etaria": c.get("faixa_etaria") or util.faixa_etaria(tudo),
        "gratuito": c["gratuito"] if c.get("gratuito") is not None else util.gratuito(tudo),
        "agendamento": bool(c.get("agendamento")) or util.precisa_agendar(tudo),
        "como_agendar": None,
        "link_inscricao": c.get("link_inscricao"),
        "natal": util.eh_natal(tudo),
        "categorias": c.get("categorias") or [],
        "inscricoes_abrem": c.get("inscricoes_abrem"),
        "esgotado": bool(c.get("esgotado")),
        "analisado_por": "heuristica",
    }
    para_criancas = pontos >= LIMIAR_INFANTIL

    # o agente só olha o que tem alguma chance de ser infantil, para não gastar à toa
    if pontos >= 0 or c.get("infantil_fonte"):
        v = agente.analisar(fonte["shopping"], titulo, texto)
        if v:
            para_criancas = v["para_criancas"]
            evento.update(
                titulo=v["titulo"] or titulo,
                resumo=v["resumo"] or evento["resumo"],
                inicio=c.get("inicio") or v["inicio"] or evento["inicio"],
                fim=c.get("fim") or v["fim"] or evento["fim"],
                horario=v["horario"] or evento["horario"],
                faixa_etaria=evento["faixa_etaria"] or v["faixa_etaria"],
                gratuito=evento["gratuito"] if c.get("gratuito") is not None else v["gratuito"],
                agendamento=bool(c.get("agendamento")) or v["precisa_agendar"],
                como_agendar=v["como_agendar"],
                natal=v["natal"] or evento["natal"],
                analisado_por="agente",
            )

    if not para_criancas:
        return None
    hoje = util.hoje()
    fim_d, inicio_d = util.data_iso(evento["fim"]), util.data_iso(evento["inicio"])
    if (fim_d or inicio_d) and (fim_d or inicio_d) < hoje:
        return None  # já acabou
    if not (fim_d or inicio_d) and evento["analisado_por"] == "heuristica" and pontos < LIMIAR_SEM_DATA:
        return None

    evento.update(
        id=hashlib.sha1(c["url"].encode()).hexdigest()[:12],
        shopping=fonte["shopping"],
        bairro=fonte["bairro"],
        regiao=fonte["regiao"],
        url=c["url"],
        imagem=c.get("imagem"),
    )
    return evento


def principal(filtro: str | None = None) -> None:
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {"eventos": []}
    agente = Agente()
    print(f"Agente LLM: {f'ativo ({MODELO})' if agente.ativo else 'desligado (só heurística)'}")

    eventos: dict[str, dict] = {}
    relatorio = []
    for fonte in FONTES:
        if filtro and filtro.lower() not in fonte["shopping"].lower():
            continue
        print(f"→ {fonte['shopping']} ({fonte['tipo']})")
        t0 = time.monotonic()
        try:
            candidatos = list(ADAPTADORES[fonte["tipo"]](fonte))
            achados = [e for c in candidatos if (e := normalizar(fonte, c, agente))]
            for e in achados:
                eventos[e["id"]] = e
            status = "ok"
            print(f"   {len(candidatos)} publicações lidas, {len(achados)} atividades infantis ({time.monotonic() - t0:.0f}s)")
        except Exception as erro:
            # mantém o que já tínhamos dessa fonte para o site não esvaziar por uma falha passageira
            status = f"erro: {type(erro).__name__}: {erro}"
            print(f"   ! {status}")
            antigos = [e for e in anterior["eventos"] if e["shopping"] == fonte["shopping"]]
            hoje = util.hoje().isoformat()
            for e in antigos:
                if (e.get("fim") or e.get("inicio") or hoje) >= hoje:
                    eventos[e["id"]] = e
        # um shopping pode ter mais de uma fonte (site + feed): uma linha só no relatório
        anterior_rel = next((r for r in relatorio if r["shopping"] == fonte["shopping"]), None)
        if anterior_rel is None:
            relatorio.append({"shopping": fonte["shopping"], "url": fonte.get("pagina") or fonte["url"],
                              "status": status, "eventos": 0})
            anterior_rel = relatorio[-1]
        elif status != "ok":
            anterior_rel["status"] = status
        anterior_rel["eventos"] = sum(1 for e in eventos.values() if e["shopping"] == fonte["shopping"])

    if filtro:  # rodada parcial: preserva as demais fontes
        rodadas = {r["shopping"] for r in relatorio}
        for e in anterior["eventos"]:
            if e["shopping"] not in rodadas:
                eventos.setdefault(e["id"], e)
        relatorio += [r for r in anterior.get("fontes", []) if r["shopping"] not in rodadas]

    ordenados = sorted(eventos.values(), key=lambda e: (e.get("inicio") or e.get("fim") or "9999", e["titulo"]))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "gerado_em": datetime.now(util.FUSO).isoformat(timespec="minutes"),
        "fontes": relatorio,
        "eventos": ordenados,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    agente.salvar()
    print(f"\n{len(ordenados)} atividades gravadas em {SAIDA} (chamadas ao agente: {agente.chamadas})")


if __name__ == "__main__":
    principal(sys.argv[1] if len(sys.argv) > 1 else None)
