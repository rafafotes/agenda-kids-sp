"""Utilitários compartilhados: HTTP educado, extração de texto, datas em pt-BR e classificadores."""

from __future__ import annotations

import gzip
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130 Safari/537.36 AgendaKidsSP/1.0 (+agenda de eventos infantis)"
)
INTERVALO_POR_DOMINIO = 1.0  # segundos entre requisições ao mesmo site

_ultimo_acesso: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def hoje() -> date:
    return datetime.now(FUSO).date()


# ---------------------------------------------------------------- HTTP

def _permitido(url: str) -> bool:
    partes = urllib.parse.urlsplit(url)
    base = f"{partes.scheme}://{partes.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as r:
                rp.parse(r.read().decode("utf-8", "ignore").splitlines())
            _robots[base] = rp
        except Exception:
            _robots[base] = None  # sem robots.txt acessível: liberado
    rp = _robots[base]
    return rp is None or rp.can_fetch(USER_AGENT, url)


def baixar(url: str, timeout: int = 25) -> str:
    """Baixa uma página respeitando robots.txt e um intervalo mínimo por domínio."""
    if not _permitido(url):
        raise PermissionError(f"robots.txt não permite {url}")
    dominio = urllib.parse.urlsplit(url).netloc
    espera = INTERVALO_POR_DOMINIO - (time.monotonic() - _ultimo_acesso.get(dominio, 0))
    if espera > 0:
        time.sleep(espera)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Accept-Encoding": "gzip",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            corpo = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                corpo = gzip.decompress(corpo)
            charset = r.headers.get_content_charset() or "utf-8"
    finally:
        _ultimo_acesso[dominio] = time.monotonic()
    return corpo.decode(charset, "ignore")


# ---------------------------------------------------------------- HTML

def texto_de_html(trecho: str) -> str:
    trecho = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", trecho)
    trecho = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", trecho)
    trecho = re.sub(r"<[^>]+>", " ", trecho)
    trecho = html.unescape(trecho)
    linhas = [re.sub(r"[ \t ]+", " ", l).strip() for l in trecho.splitlines()]
    return "\n".join(l for l in linhas if l)


def meta(pagina: str, nome: str) -> str | None:
    """Lê <meta property|name="nome" content="..."> em qualquer ordem de atributos."""
    for tag in re.findall(r"<meta\b[^>]*>", pagina, re.I):
        if re.search(rf'(?:property|name)\s*=\s*["\']{re.escape(nome)}["\']', tag, re.I):
            m = re.search(r'content\s*=\s*"([^"]*)"', tag, re.I) or re.search(
                r"content\s*=\s*'([^']*)'", tag, re.I
            )
            if m:
                return html.unescape(m.group(1)).strip() or None
    return None


def titulo_da_pagina(pagina: str) -> str | None:
    t = meta(pagina, "og:title")
    if not t:
        m = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", pagina) or re.search(r"(?is)<title>(.*?)</title>", pagina)
        t = texto_de_html(m.group(1)) if m else None
    return t


def json_ld(pagina: str) -> list[dict]:
    blocos = []
    for bruto in re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', pagina):
        try:
            dado = json.loads(bruto)
        except ValueError:
            continue
        itens = dado if isinstance(dado, list) else dado.get("@graph", [dado]) if isinstance(dado, dict) else []
        blocos.extend(i for i in itens if isinstance(i, dict))
    return blocos


def limpar_titulo(titulo: str, shopping: str) -> str:
    """Tira sufixos como " | Tietê Plaza" ou " - Shopping X" que os sites colam no og:title."""
    nomes = {p for p in sem_acento(shopping).split() if len(p) > 3} | {"shopping"}
    titulo = re.sub(r"(?i)\s+no iguatemi:\s*sua pr[oó]xima experi[eê]ncia\s*$", "", titulo)
    partes = re.split(r"\s+[|–—-]\s+", titulo.strip())
    uteis = [p for p in partes if not (set(sem_acento(p).split()) & nomes)]
    limpo = " - ".join(uteis) if uteis and len(uteis) < len(partes) else titulo.strip()
    return limpo.title() if limpo.isupper() and len(limpo) > 4 else limpo


def absoluta(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, html.unescape(href)).split("#")[0]


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------- Datas

MESES = {
    "janeiro": 1, "jan": 1, "fevereiro": 2, "fev": 2, "marco": 3, "mar": 3, "abril": 4, "abr": 4,
    "maio": 5, "mai": 5, "junho": 6, "jun": 6, "julho": 7, "jul": 7, "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9, "outubro": 10, "out": 10, "novembro": 11, "nov": 11,
    "dezembro": 12, "dez": 12,
}
_MES_RE = "|".join(sorted(MESES, key=len, reverse=True))
_DATA_RE = re.compile(
    rf"(?P<d1>\d{{1,2}})/(?P<m1>\d{{1,2}})(?:/(?P<a1>\d{{2,4}}))?"
    rf"|(?P<d2>\d{{1,2}})(?:º|o)?\s+de\s+(?P<m2>{_MES_RE})\b\.?(?:\s+de\s+(?P<a2>\d{{4}}))?"
)
# "de 27 a 30 de outubro" / "27 e 28 de novembro": o primeiro dia herda o mês do segundo
_INTERVALO_MESMO_MES = re.compile(rf"\b(\d{{1,2}})\s+(?:a|e|até|-|–)\s+(\d{{1,2}})\s+de\s+({_MES_RE})\b")


def _inferir_ano(dia: int, mes: int, ref: date) -> date | None:
    """Sem ano explícito, escolhe o ano que deixa a data mais perto do presente (até ~10 meses à frente)."""
    for ano in (ref.year, ref.year + 1, ref.year - 1):
        try:
            d = date(ano, mes, dia)
        except ValueError:
            return None
        if ref - timedelta(days=60) <= d <= ref + timedelta(days=300):
            return d
    try:
        return date(ref.year, mes, dia)
    except ValueError:
        return None


def datas_no_texto(texto: str, ref: date | None = None) -> list[date]:
    ref = ref or hoje()
    t = sem_acento(texto)
    achadas: list[date] = []
    for m in _INTERVALO_MESMO_MES.finditer(t):
        mes = MESES[m.group(3)]
        d = _inferir_ano(int(m.group(1)), mes, ref)
        if d:
            achadas.append(d)
    for m in _DATA_RE.finditer(t):
        if m.group("d1"):
            dia, mes, ano = int(m.group("d1")), int(m.group("m1")), m.group("a1")
        else:
            dia, mes, ano = int(m.group("d2")), MESES[m.group("m2")], m.group("a2")
        if not (1 <= mes <= 12 and 1 <= dia <= 31):
            continue
        if ano:
            ano_i = int(ano) + (2000 if len(ano) == 2 else 0)
            try:
                d = date(ano_i, mes, dia)
            except ValueError:
                continue
        else:
            d = _inferir_ano(dia, mes, ref)
        if d and abs((d - ref).days) < 800:
            achadas.append(d)
    return achadas


def periodo_do_texto(texto: str, ref: date | None = None) -> tuple[date | None, date | None]:
    """Devolve (início, fim). "Até 09/11" vira (None, 09/11)."""
    datas = datas_no_texto(texto, ref)
    if not datas:
        return None, None
    if len(set(datas)) == 1 and re.search(r"\bat[eé]\s+(o\s+dia\s+)?\d", texto, re.I):
        return None, datas[0]
    return min(datas), max(datas)


def iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def data_iso(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00")).astimezone(FUSO).date() if "T" in valor else date.fromisoformat(valor[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------- Classificadores

_INFANTIL_FORTE = [
    "crianca", "infantil", "kids", "kid ", "baby", "bebe", "bebes", "pequenos", "criancada", "meninada",
    "papai noel", "noel", "oficina", "parquinho", "brinquedo", "brincadeira", "recreacao", "pula-pula",
    "trampolim", "lego", "contacao", "historinha", "teatro infantil", "espetaculo infantil", "fantoche",
    "princesa", "personagem", "personagens", "bailinho", "monitores", "playground", "gira-gira",
    "carrossel", "dinossauro", "pintura de rosto", "caca ao", "familia", "toda a familia", "para os pequenos",
    "a partir de 2 anos", "a partir de 3 anos", "a partir de 4 anos", "a partir de 5 anos", "anos de idade",
    "cinema infantil", "cinematerna", "patinacao", "roda gigante", "minecraft", "mini ",
]
_INFANTIL_FRACO = [
    "exposicao", "ciencia", "halloween", "maquiagem", "fantasia", "parada", "musical", "teatro", "cinema",
    "ferias", "pascoa", "arraia", "circo", "magica", "show", "aventura", "diversao",
]
# negativos fortes: valem no texto inteiro (indicam promoção, campanha ou evento adulto)
_NEGATIVO = [
    "doacao de sangue", "sorteio", "numero da sorte", "numeros da sorte", "notas fiscais", "cadastre suas notas",
    "ganhador", "ganhadora", "resultado da promocao", "black friday", "vagas de emprego", "cashback",
    "nubank parque", "vias alternativas", "happy hour", "degustacao de vinho",
]
# negativos de contexto: só no título, porque aparecem como rodapé dentro de eventos legítimos
_NEGATIVO_TITULO = [
    "estacionamento", "horario", "feriado", "nova loja", "chegou", "inauguracao da loja", "% off", "desconto",
    "beneficio", "coworking", "clube do livro", "bloqueio", "tiktok", "live ", "promocao", "corrida", "run ",
    "outubro rosa", "novembro azul", "adocao", "campanha", " pet ", "pet friendly", "investidores",
]
_NATAL = ["natal", "noel", "natalin", "presepio", "renas", "duende", "cartinha", "arvore de natal", "christmas"]
_AGENDAR = [
    "agendamento", "agende", "agendar", "inscricao", "inscricoes", "inscreva", "garanta sua vaga", "garanta seu",
    "vagas limitadas", "sujeito a lotacao", "ingresso", "sympla", "bileto", "reserve", "reserva", "retirada de senha",
    "retire sua senha", "senhas", "resgate", "resgatar", "pelo app", "no app", "pelo aplicativo", "no aplicativo",
    "link na bio", "cadastro previo",
]
_GRATIS = ["gratuito", "gratuita", "gratis", "entrada franca", "sem custo", "free"]
_PAGO = [r"r\$\s*\d", "ingressos a partir", "valor:", "valores:", "por crianca", "meia-entrada", "meia entrada"]


def _conta(t: str, termos: list[str]) -> int:
    return sum(1 for termo in termos if termo in t)


def pontuacao_infantil(titulo: str, texto: str = "") -> int:
    t = " " + sem_acento(f"{titulo}\n{texto}") + " "
    tt = " " + sem_acento(titulo) + " "
    return (2 * _conta(t, _INFANTIL_FORTE) + _conta(t, _INFANTIL_FRACO)
            - 3 * _conta(t, _NEGATIVO) - 4 * _conta(tt, _NEGATIVO_TITULO))


def eh_natal(texto: str) -> bool:
    return _conta(sem_acento(texto), _NATAL) > 0


def precisa_agendar(texto: str) -> bool:
    return _conta(sem_acento(texto), _AGENDAR) > 0


def gratuito(texto: str) -> bool | None:
    t = sem_acento(texto)
    if _conta(t, _GRATIS):
        return True
    if any(re.search(p, t) for p in _PAGO):
        return False
    return None


def faixa_etaria(texto: str) -> str | None:
    t = sem_acento(texto)
    m = re.search(r"(?:de|dos?)\s+(\d{1,2})\s+(?:a|aos?|ate)\s+(\d{1,2})\s+anos", t) or re.search(
        r"(\d{1,2})\s*(?:a|-|–)\s*(\d{1,2})\s+anos", t
    )
    if m:
        return f"{m.group(1)} a {m.group(2)} anos"
    m = re.search(r"a partir de\s+(\d{1,2})\s+anos", t) or re.search(r"maiores de\s+(\d{1,2})\s+anos", t)
    if m:
        return f"a partir de {m.group(1)} anos"
    m = re.search(r"(?:ate|menores de)\s+(\d{1,2})\s+anos", t)
    if m:
        return f"até {m.group(1)} anos"
    return None


def horario(texto: str) -> str | None:
    t = sem_acento(texto)
    m = re.search(r"\b(?:das?\s+)?(\d{1,2}h\d{0,2})\s*(?:as|a|ate|-|–)\s*(\d{1,2}h\d{0,2})", t)
    if m:
        return f"das {m.group(1)} às {m.group(2)}"
    horas = list(dict.fromkeys(re.findall(r"\b(\d{1,2}h\d{0,2})\b", t)))
    return ", ".join(horas) if 0 < len(horas) <= 3 else None


def resumo(texto: str, limite: int = 320) -> str:
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) <= limite:
        return texto
    corte = texto[:limite].rsplit(" ", 1)[0]
    return corte.rstrip(",.;:") + "…"
