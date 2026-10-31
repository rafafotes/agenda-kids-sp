"""Adaptadores: cada um sabe ler um tipo de site e devolve candidatos a evento.

Um candidato é um dict com as chaves de `Candidato` abaixo; campos desconhecidos ficam None e são
preenchidos depois pela heurística (util.py) ou pelo agente LLM (agente.py).
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
from datetime import datetime, timedelta
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
    inscricoes_abrem: str | None  # ISO; quando as inscrições ainda não abriram
    esgotado: bool | None  # todas as sessões sem vaga


# ---------------------------------------------------------------- Multiplan

def multiplan(fonte: dict) -> Iterator[Candidato]:
    """Sites Multiplan (MorumbiShopping, Anália Franco...) embutem os eventos em JSON no atributo
    data-props de <div class="event_grid">, com datas, tipo de entrada e link de inscrição."""
    pagina = util.baixar(fonte["url"], timeout=fonte.get("timeout", 60))
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
    links = _links(fonte["url"], listagem, fonte["padrao_link"])
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
        if titulo == titulo_listagem:
            if abs(len(pagina) - len(listagem)) < 0.05 * len(listagem):
                continue  # link quebrado que caiu na própria listagem/home
            # site com o mesmo <title> em todas as páginas: o nome do evento está no cabeçalho
            m = re.search(r"(?is)<h[12][^>]*>(.*?)</h[12]>", _sem_cabecalho(pagina))
            titulo = util.texto_de_html(m.group(1)) if m else titulo
        if re.search(r"(?i)\bhome\b|p[aá]gina n[aã]o encontrada|404|^\s*(acontece|eventos?|novidades?|agenda)\s*$", titulo):
            continue
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


def _links(base: str, pagina: str, padrao: str) -> list[str]:
    """Links da página que casam com o padrão: em href e também dentro de JSON embutido
    (banners e carrosséis montados por script, com barras escapadas como "\\/evento.php")."""
    regex = re.compile(padrao)
    bruto = pagina.replace("\\/", "/")
    achados = re.findall(r'href\s*=\s*["\']([^"\']+)["\']|"(?:link|url|href)"\s*:\s*"([^"]+)"', bruto)
    links: list[str] = []
    for href in (a or b for a, b in achados):
        url = util.absoluta(base, href)
        if regex.search(url) and url.rstrip("/") != base.rstrip("/") and url not in links:
            links.append(url)
    return links


def _sem_cabecalho(pagina: str) -> str:
    m = re.search(r"(?is)<(main|article)\b.*?</\1>", pagina)
    trecho = m.group(0) if m else pagina
    return re.sub(r"(?is)<(header|footer|nav|aside|form)\b.*?</\1>", " ", trecho)


def _corpo_principal(pagina: str) -> str:
    return util.texto_de_html(_sem_cabecalho(pagina))


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

BESISTEMAS = "https://eventos.besistemas.com.br"


def besistemas(fonte: dict) -> Iterator[Candidato]:
    """Plataforma de inscrições Be Sistemas, usada por Frei Caneca, Penha e outros. A página
    "Acontece" do shopping linka cada evento (eventos.besistemas.com.br/<cliente>/event/<id>/...);
    a página do evento traz no __NEXT_DATA__ datas, sessões, vagas e quando abrem as inscrições."""
    listagem = util.baixar(fonte["url"])
    links = _links(fonte["url"], listagem, r"eventos\.besistemas\.com\.br/[a-z0-9-]+/event/[a-z0-9]+")
    agora = datetime.now(util.FUSO)
    for url in links[: fonte.get("max_links", 30)]:
        try:
            pagina = util.baixar(url)
        except Exception as erro:
            print(f"    ! {url}: {erro}")
            continue
        m = re.search(r'(?s)<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', pagina)
        e = json.loads(m.group(1))["props"]["pageProps"].get("event") if m else None
        if not e or e.get("status") not in (None, "active"):
            continue
        sessoes = [s for dia in e.get("event_times") or [] for s in dia.get("available_datetimes") or []]
        horarios = list(dict.fromkeys(
            f'{s["starts_at_hour"]}–{s["ends_at_hour"]}' for s in sessoes if s.get("starts_at_hour")))
        idades = {_texto_idade(t.get("age_group")) for s in sessoes for t in s.get("available_tickets") or []} - {None}
        abre = e.get("online_sales_start_at")
        abre_dt = datetime.fromisoformat(abre) if abre else None
        texto = util.texto_de_html(e.get("description") or "")
        if horarios:
            texto += "\nSessões: " + ", ".join(horarios[:6])
        yield Candidato(
            titulo=e["title"].strip(),
            texto=texto,
            url=url,
            imagem=BESISTEMAS + e["banner_src"] if e.get("banner_src") else None,
            inicio=util.iso(util.data_iso(e.get("start_at"))),
            fim=util.iso(util.data_iso(e.get("finish_at"))),
            gratuito=(e.get("highest_price") == 0) if e.get("highest_price") is not None else None,
            agendamento=True,
            link_inscricao=url,
            faixa_etaria=", ".join(sorted(idades)) or None,
            categorias=[],
            infantil_fonte=False,
            inscricoes_abrem=util.iso(abre_dt.date()) if abre_dt and abre_dt > agora else None,
            esgotado=bool(sessoes) and all(s.get("status") == "sold_out" for s in sessoes),
        )


def _texto_idade(valor) -> str | None:
    if isinstance(valor, dict):
        valor = valor.get("name") or valor.get("title") or valor.get("description")
    return str(valor).strip() if valor else None


# ---------------------------------------------------------------- Madnezz

MADNEZZ = "https://api-public.madnezz.com.br/api/v1/public/sites"


def madnezz(fonte: dict) -> Iterator[Candidato]:
    """Sites feitos na plataforma Madnezz (Partage Santana) carregam os eventos de uma API pública:
    /novidade?empreendimento_id=<id>&tp=1, o mesmo pedido que a página faz no navegador."""
    url = f'{MADNEZZ}/novidade?empreendimento_id={fonte["empreendimento_id"]}&tp=1'
    for e in json.loads(util.baixar(url)) or []:
        if str(e.get("novidade_ativo")) != "1":
            continue
        texto = util.texto_de_html(e.get("novidade_texto") or "")
        extras = [e.get("novidade_horario") and f'Horário: {e["novidade_horario"]}',
                  e.get("novidade_local") and f'Local: {e["novidade_local"]}',
                  e.get("novidade_valor") and f'Valor: {e["novidade_valor"]}']
        imagem = e.get("novidade_imagem_1_url")
        yield Candidato(
            titulo=e["novidade_nome"].strip(),
            texto="\n".join([texto, *filter(None, extras)]),
            url=f'{fonte["pagina"]}?novidade_id={e["novidade_id"]}',
            imagem=imagem if imagem and imagem != "None" else None,
            inicio=_data_br(e.get("novidade_entrada")),
            fim=_data_br(e.get("novidade_saida")),
            faixa_etaria=e.get("novidade_idade") or None,
            categorias=[],
            infantil_fonte=False,
        )


def _data_br(valor: str | None) -> str | None:
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", valor or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


# ---------------------------------------------------------------- API JSON genérica

def api_json(fonte: dict) -> Iterator[Candidato]:
    """Lista JSON pública que o próprio site consulta (ex.: Center Norte). Mapeia os nomes de campo
    mais comuns; o que não vier é preenchido pela heurística."""
    dados = json.loads(util.baixar(fonte["url"]))
    itens = dados if isinstance(dados, list) else dados.get("data") or dados.get("items") or []
    pega = lambda e, *ks: next((e[k] for k in ks if e.get(k)), None)  # noqa: E731
    for e in itens:
        titulo = pega(e, "title", "titulo", "name", "nome")
        if not titulo:
            continue
        slug = pega(e, "slug", "url", "id")
        yield Candidato(
            titulo=str(titulo).strip(),
            texto=util.texto_de_html(str(pega(e, "content", "description", "descricao", "texto", "resumo") or "")),
            url=util.absoluta(fonte["pagina"] + "/", str(slug)) if slug else fonte["pagina"],
            imagem=pega(e, "image", "imagem", "thumbnail", "cover", "banner"),
            inicio=util.iso(util.data_iso(pega(e, "startDate", "start_date", "data_inicio", "dataInicio"))),
            fim=util.iso(util.data_iso(pega(e, "endDate", "end_date", "data_fim", "dataFim"))),
            categorias=[],
            infantil_fonte=False,
            publicado=util.iso(util.data_iso(pega(e, "publishedAt", "created_at", "date", "data"))),
        )


# ---------------------------------------------------------------- Notícias

# Sites de notícias e guias que publicam os releases dos shoppings e expõem a busca pela API
# pública do WordPress. Usados para shoppings cujo site recusa acesso automatizado.
SITES_NOTICIAS = [
    "https://saopauloparacriancas.com.br",
    "https://www.abcdacomunicacao.com.br",
]


def noticias(fonte: dict) -> Iterator[Candidato]:
    """Busca posts recentes que citam o shopping e usa só o trecho que fala dele: em matérias do
    tipo "Halloween em SP: 20 programas", cada shopping vira um candidato separado."""
    desde = (util.hoje() - timedelta(days=fonte.get("dias", 75))).isoformat()
    termos = fonte["termos"]
    vistos = set()
    for site in SITES_NOTICIAS:
        for termo in termos:
            url = (f"{site}/wp-json/wp/v2/posts?search={urllib.parse.quote(termo)}&after={desde}T00:00:00"
                   f"&per_page=20&_fields=date,link,title,content,yoast_head_json")
            try:
                posts = json.loads(util.baixar(url))
            except Exception as erro:
                print(f"    ! {site}: {erro}")
                continue
            for post in posts:
                if post["link"] in vistos:
                    continue
                vistos.add(post["link"])
                titulo_post = util.texto_de_html(post["title"]["rendered"])
                trecho, subtitulo = _trecho_sobre(post["content"]["rendered"], termos)
                if not trecho:
                    continue
                cita_no_titulo = any(util.sem_acento(t) in util.sem_acento(titulo_post) for t in termos)
                imagens = (post.get("yoast_head_json") or {}).get("og_image") or [{}]
                yield Candidato(
                    titulo=(titulo_post if cita_no_titulo or not _materia_lista(post["content"]["rendered"])
                            else subtitulo if subtitulo and not _generico(subtitulo)
                            else f'{titulo_post.split(":")[0].strip()} — {fonte["shopping"]}'),
                    texto=trecho,
                    url=post["link"],
                    imagem=imagens[0].get("url") if cita_no_titulo else None,
                    categorias=[],
                    infantil_fonte="paracriancas" in site,  # guia dedicado a programas infantis
                    publicado=post["date"][:10],
                )


def _materia_lista(conteudo: str) -> bool:
    """Matéria do tipo "20 programas de Halloween": cita três ou mais shoppings diferentes."""
    nomes = re.findall(r"\b(?:Shopping|Mall|Plaza)\s+[A-ZÀ-Ú][\wÀ-ú]+", util.texto_de_html(conteudo))
    return len(set(nomes)) >= 3


def _generico(subtitulo: str) -> bool:
    return bool(re.match(r"(?i)\s*(como chegar|servi[cç]o|onde|quando|endere[cç]o|informa[cç][oõ]es|"
                         r"ingressos?|programa[cç][aã]o|hor[aá]rios?|saiba mais|leia tamb[eé]m)\b", subtitulo))


def _trecho_sobre(conteudo: str, termos: list[str]) -> tuple[str, str | None]:
    """Parágrafos que citam o shopping (e o seguinte, se ainda for sobre ele) e o subtítulo da
    seção quando o próprio subtítulo nomeia o shopping. Em matérias-lista cada parágrafo fala de
    um shopping diferente, então um parágrafo que cita outro shopping encerra o trecho."""
    blocos = re.findall(r"(?is)<(h[2-4]|p|li)\b[^>]*>(.*?)</\1>", conteudo)
    alvo = [util.sem_acento(t) for t in termos]
    cita = lambda texto: any(a in util.sem_acento(texto) for a in alvo)  # noqa: E731
    outro_shopping = re.compile(r"(?i)\b(shopping|mall|plaza)\b")
    partes, subtitulo, ultimo_titulo = [], None, None
    for i, (tag, corpo) in enumerate(blocos):
        texto = util.texto_de_html(corpo)
        if tag.lower().startswith("h"):
            ultimo_titulo = texto
            continue
        if not cita(texto):
            continue
        if ultimo_titulo and cita(ultimo_titulo):
            subtitulo = subtitulo or ultimo_titulo
        partes.append(texto)
        if i + 1 < len(blocos) and not blocos[i + 1][0].lower().startswith("h"):
            seguinte = util.texto_de_html(blocos[i + 1][1])
            if cita(seguinte) or not outro_shopping.search(seguinte):
                partes.append(seguinte)
    return "\n".join(dict.fromkeys(partes))[:3000], subtitulo


# ---------------------------------------------------------------- Eventos Manager (WordPress)

def eventos_manager(fonte: dict) -> Iterator[Candidato]:
    """Agenda do plugin WordPress "eventos-manager" (Open Mall The Square): um <section data-date>
    por dia e um <article class="event-card" data-audience="infantil|adulto"> por atração. Lê só as
    infantis e junta a mesma atração repetida em vários dias num evento só."""
    pagina = util.baixar(fonte["url"])
    agrupados: dict[str, dict] = {}
    for dia, corpo in re.findall(r'(?s)<section\s[^>]*?data-date="([\d-]+)"[^>]*>(.*?)</section>', pagina):
        for card in re.findall(r'(?s)<article\s+class="event-card[^"]*"([^>]*)>(.*?)</article>', corpo):
            atributos, conteudo = card
            if 'data-audience="infantil"' not in atributos:
                continue
            campo = lambda classe: (m := re.search(rf'(?s)class="{classe}"[^>]*>(.*?)</', conteudo)) and util.texto_de_html(m.group(1))  # noqa: E731
            titulo = campo("card-title") or ""
            chave = f"{titulo}|{campo('card-venue')}"
            hora = (re.search(r"(\d{1,2}H\d*)$", campo("card-date") or "") or [None, None])[1]
            g = agrupados.setdefault(chave, {"titulo": titulo, "dias": [], "horas": [], "card": conteudo,
                                             "extras": [campo("card-kicker"), campo("card-subtitle"),
                                                        campo("card-venue"), campo("card-badge-main")]})
            g["dias"].append(dia)
            if hora:
                g["horas"].append(hora.lower())
    for g in agrupados.values():
        imagem = re.search(r'class="media-image" src="([^"]+)"', g["card"])
        texto = "\n".join(filter(None, g["extras"]))
        if g["horas"]:
            texto += "\nHorários: " + ", ".join(dict.fromkeys(g["horas"]))
        yield Candidato(
            titulo=g["titulo"],
            texto=texto + "\nAtividade infantil",
            url=f'{fonte["url"]}#{re.sub(r"[^a-z0-9]+", "-", util.sem_acento(g["titulo"])).strip("-")}',
            imagem=imagem.group(1) if imagem else None,
            inicio=min(g["dias"]),
            fim=max(g["dias"]),
            gratuito=True if "gratuito" in util.sem_acento(texto) else None,
            categorias=["Infantil"],
            infantil_fonte=True,
        )


# ---------------------------------------------------------------- Feed do Instagram embutido

def feed_instagram(fonte: dict) -> Iterator[Candidato]:
    """Alguns shoppings publicam a agenda só como arte (imagem) e descrevem o evento nas legendas
    do Instagram, que o próprio site embute na home numa variável JS (ex.: `var instagram_feed`).
    Cada legenda recente vira um candidato; as datas vêm do texto ("Até 02/11", "dia 07/11")."""
    pagina = util.baixar(fonte["url"])
    m = re.search(rf'var {fonte.get("variavel", "instagram_feed")}\s*=\s*', pagina)
    if not m:
        return
    posts, _ = json.JSONDecoder().raw_decode(pagina[m.end():])
    posts = posts if isinstance(posts, list) else posts.get("data") or []
    for post in posts[: fonte.get("max_posts", 15)]:
        legenda = (post.get("caption") or "").strip()
        if not legenda:
            continue
        sem_tags = re.sub(r"(?m)^\s*(#\S+\s*)+$", "", legenda).strip()
        primeira = re.split(r"(?<=[.!?…])\s|\n", sem_tags, maxsplit=1)[0]
        titulo = re.sub(r"[^\w\s,.!?…:'’\-–()/ºª%&]", "", primeira).strip(" .")
        yield Candidato(
            titulo=titulo[:90] + ("…" if len(titulo) > 90 else ""),
            texto=sem_tags,
            url=post.get("permalink") or fonte["url"],
            imagem=post.get("thumbnail_url") or post.get("media_url") if post.get("media_type") != "VIDEO"
            else post.get("thumbnail_url"),
            categorias=[],
            infantil_fonte=False,
        )


ADAPTADORES = {
    "multiplan": multiplan,
    "detalhes": paginas_de_detalhe,
    "cards": cards,
    "besistemas": besistemas,
    "madnezz": madnezz,
    "api_json": api_json,
    "noticias": noticias,
    "eventos_manager": eventos_manager,
    "feed_instagram": feed_instagram,
}
