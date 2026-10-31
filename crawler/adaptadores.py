"""Adaptadores: cada um sabe ler um tipo de site e devolve candidatos a evento.

Um candidato é um dict com as chaves de `Candidato` abaixo; campos desconhecidos ficam None e são
preenchidos depois pela heurística (util.py) ou pelo agente LLM (agente.py).
"""

from __future__ import annotations

import html
import json
import re
from typing import Iterator, TypedDict

from . import util


class Candidato(TypedDict, total=False):
    titulo: str
    texto: str  # descrição completa em texto puro, base para classificação
    url: str
    imagem: str | None
    inicio: str | None  # ISO yyyy-mm-dd
    fim: str | None
    gratuito: bool | None
    agendamento: bool | None
    link_inscricao: str | None
    faixa_etaria: str | None
    categorias: list[str]
    infantil_fonte: bool  # a própria fonte marcou como infantil
    publicado: str | None  # data de publicação do post, quando a fonte é um blog/notícia


# ---------------------------------------------------------------- Multiplan

def multiplan(fonte: dict) -> Iterator[Candidato]:
    """Sites Multiplan (MorumbiShopping, Anália Franco...) embutem os eventos em JSON no atributo
    data-props de <div class="event_grid">, com datas, tipo de entrada e link de inscrição."""
    pagina = util.baixar(fonte["url"])
    vistos = set()
    for bruto in re.findall(r'class="event_grid"\s+data-props="([^"]*)"', pagina):
        for e in json.loads(html.unescape(bruto)).get("events", []):
            if e.get("id") in vistos or e.get("active") is False:
                continue
            vistos.add(e.get("id"))
            cats = [c["name"] for c in e.get("categories") or []]
            texto = util.texto_de_html(e.get("description") or "")
            extras = " ".join(filter(None, [e.get("duration"), e.get("location"), e.get("information"),
                                           e.get("guarantee_your_ticket"), e.get("observation")]))
            tipo = e.get("event_type") or ""
            imagens = e.get("event_image_sizes") or {}
            yield Candidato(
                titulo=e["title"].strip(),
                texto=(texto + "\n" + util.texto_de_html(extras)).strip(),
                url=util.absoluta(fonte["url"], e.get("get_absolute_url") or ""),
                imagem=imagens.get("x650") or e.get("get_image_url") or e.get("get_default_image_url"),
                inicio=util.iso(util.data_iso(e.get("start_date"))),
                fim=util.iso(util.data_iso(e.get("end_date"))),
                gratuito=True if tipo.startswith("free") else (False if tipo == "paid" else None),
                agendamento=bool(e.get("limited_seats") or e.get("link") or tipo == "freeWithLink") or None,
                link_inscricao=e.get("link"),
                faixa_etaria=(e.get("age_range") or None),
                categorias=cats,
                infantil_fonte="Infantil" in cats,
            )


# ---------------------------------------------------------------- Páginas de detalhe

def paginas_de_detalhe(fonte: dict) -> Iterator[Candidato]:
    """Lista genérica: pega os links da página de agenda que casam com `padrao_link` e lê cada
    página de detalhe (og:title, og:description, og:image, JSON-LD Event e o texto principal)."""
    listagem = util.baixar(fonte["url"])
    padrao = re.compile(fonte["padrao_link"])
    links = []
    for href in re.findall(r'href\s*=\s*["\']([^"\']+)["\']', listagem):
        url = util.absoluta(fonte["url"], href)
        if padrao.search(url) and url.rstrip("/") != fonte["url"].rstrip("/") and url not in links:
            links.append(url)
    titulo_listagem = util.titulo_da_pagina(listagem)
    paginas = {}
    for url in links[: fonte.get("max_links", 30)]:
        try:
            paginas[url] = util.baixar(url)
        except Exception as erro:  # um detalhe quebrado não derruba a fonte inteira
            print(f"    ! {url}: {erro}")

    corpos = {url: _corpo_principal(p) for url, p in paginas.items()}
    repetidas = _linhas_repetidas(corpos.values())
    for url, pagina in paginas.items():
        titulo = util.titulo_da_pagina(pagina) or url
        if titulo == titulo_listagem or re.search(r"(?i)\bhome\b|p[aá]gina n[aã]o encontrada|404", titulo):
            continue  # link quebrado que caiu na home ou numa página de erro
        corpo = "\n".join(l for l in corpos[url].splitlines() if l not in repetidas)[:4000]
        descricao = util.meta(pagina, "og:description") or util.meta(pagina, "description") or ""
        if descricao in repetidas:
            descricao = ""
        texto = descricao if descricao and descricao in corpo else (descricao + "\n" + corpo)
        exigir = fonte.get("exigir_texto")
        if exigir and not re.search(exigir, util.sem_acento(texto + " " + url)):
            continue
        c = Candidato(
            titulo=util.limpar_titulo(titulo, fonte["shopping"]),
            texto=texto.strip(),
            url=url,
            imagem=util.meta(pagina, "og:image"),
            categorias=[],
            infantil_fonte=False,
            publicado=util.iso(util.data_iso(util.meta(pagina, "article:published_time"))),
        )
        for ld in util.json_ld(pagina):
            if "Event" in str(ld.get("@type")):
                c["inicio"] = util.iso(util.data_iso(ld.get("startDate")))
                c["fim"] = util.iso(util.data_iso(ld.get("endDate")))
        yield c


def _corpo_principal(pagina: str) -> str:
    m = re.search(r"(?is)<(main|article)\b.*?</\1>", pagina)
    trecho = m.group(0) if m else pagina
    trecho = re.sub(r"(?is)<(header|footer|nav|aside|form)\b.*?</\1>", " ", trecho)
    return util.texto_de_html(trecho)


def _linhas_repetidas(corpos) -> set[str]:
    """Linhas presentes em boa parte das páginas de um mesmo site são menu, rodapé ou barra lateral
    (que costumam citar outros eventos e datas) e não podem contaminar a leitura de cada evento."""
    corpos = list(corpos)
    if len(corpos) < 3:
        return set()
    contagem: dict[str, int] = {}
    for corpo in corpos:
        for linha in set(corpo.splitlines()):
            contagem[linha] = contagem.get(linha, 0) + 1
    minimo = max(2, int(len(corpos) * 0.4))
    return {linha for linha, n in contagem.items() if n >= minimo}


# ---------------------------------------------------------------- Cards na própria página

def cards(fonte: dict) -> Iterator[Candidato]:
    """Páginas que listam eventos como cards (<h2>título</h2><p>descrição</p>) sem página de
    detalhe própria, como o 'Acontece no CJ' do Shopping Cidade Jardim."""
    pagina = util.baixar(fonte["url"])
    padrao = re.compile(
        r'(?is)(?:<img[^>]+src="(?P<img>[^"]+)"[^>]*>(?:(?!<h2).){0,600})?'
        r"<h2[^>]*>(?P<titulo>.*?)</h2>\s*<p[^>]*>(?P<texto>.*?)</p>"
    )
    for i, m in enumerate(padrao.finditer(pagina)):
        titulo = util.texto_de_html(m.group("titulo"))
        if not titulo:
            continue
        yield Candidato(
            titulo=titulo.title() if titulo.isupper() else titulo,
            texto=util.texto_de_html(m.group("texto")),
            url=f'{fonte["url"]}#{re.sub(r"[^a-z0-9]+", "-", util.sem_acento(titulo)).strip("-")}',
            imagem=m.group("img"),
            categorias=[],
            infantil_fonte=False,
        )


# ---------------------------------------------------------------- Be Sistemas

def besistemas(fonte: dict) -> Iterator[Candidato]:
    """Plataforma de inscrições Be Sistemas (eventos.besistemas.com.br/<shopping>), usada por
    shoppings como Penha. Os eventos vêm no __NEXT_DATA__; quando há evento ali, há inscrição."""
    pagina = util.baixar(fonte["url"])
    m = re.search(r'(?s)<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', pagina)
    if not m:
        return
    eventos = json.loads(m.group(1))["props"]["pageProps"].get("events") or []
    for e in eventos:
        titulo = e.get("title") or e.get("name") or e.get("nome")
        if not titulo:
            continue
        descricao = util.texto_de_html(e.get("description") or e.get("descricao") or "")
        slug = e.get("slug") or e.get("id") or ""
        yield Candidato(
            titulo=titulo,
            texto=descricao,
            url=f'{fonte["url"].rstrip("/")}/{slug}' if slug else fonte["url"],
            imagem=e.get("image") or e.get("banner") or e.get("cover"),
            inicio=util.iso(util.data_iso(e.get("start_date") or e.get("startDate") or e.get("data_inicio"))),
            fim=util.iso(util.data_iso(e.get("end_date") or e.get("endDate") or e.get("data_fim"))),
            agendamento=True,
            link_inscricao=fonte["url"],
            categorias=[],
            infantil_fonte=False,
        )


ADAPTADORES = {
    "multiplan": multiplan,
    "detalhes": paginas_de_detalhe,
    "cards": cards,
    "besistemas": besistemas,
}
