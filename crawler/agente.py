"""Agente de extração com Claude (opcional).

Sem credencial da Anthropic o crawler funciona só com a heurística de util.py. Com ANTHROPIC_API_KEY
definida (e o pacote `anthropic` instalado), cada candidato passa pelo Claude, que lê o texto como
uma pessoa leria e devolve um veredito estruturado. As respostas ficam em cache por conteúdo, então
um evento só é analisado de novo quando o texto dele muda.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from . import util

MODELO = os.environ.get("AGENDA_MODELO") or "claude-opus-5-5"
CACHE = Path(__file__).with_name("cache_agente.json")

INSTRUCOES = """Você ajuda pais a encontrar atividades para crianças em shoppings de São Paulo.
Recebe o texto de uma publicação do site de um shopping e decide se é uma atividade para crianças
(oficina, teatro, espetáculo, parquinho, encontro com Papai Noel, exposição interativa, cinema infantil,
brinquedos, etc.). Promoções de compra, sorteios, liquidações, horários de funcionamento, lojas novas,
doação de sangue e eventos só para adultos NÃO são atividades para crianças.

Regras:
- Datas no formato AAAA-MM-DD. Hoje é {hoje}; quando o ano não aparecer, use o ano que deixa a data
  mais próxima de hoje. Se só houver data final ("até 22/12"), deixe inicio nulo.
- Não invente: campo sem informação no texto fica nulo.
- precisa_agendar = true quando houver inscrição, agendamento, retirada de senha, ingresso,
  reserva ou resgate pelo app. Em como_agendar, diga como fazer em uma frase curta.
- resumo: até 2 frases, em português, dizendo o que a criança vai fazer.
"""

ESQUEMA = {
    "type": "object",
    "properties": {
        "para_criancas": {"type": "boolean"},
        "titulo": {"type": "string"},
        "resumo": {"type": "string"},
        "inicio": {"type": ["string", "null"]},
        "fim": {"type": ["string", "null"]},
        "horario": {"type": ["string", "null"]},
        "faixa_etaria": {"type": ["string", "null"]},
        "gratuito": {"type": ["boolean", "null"]},
        "precisa_agendar": {"type": "boolean"},
        "como_agendar": {"type": ["string", "null"]},
        "natal": {"type": "boolean"},
    },
    "required": ["para_criancas", "titulo", "resumo", "inicio", "fim", "horario", "faixa_etaria",
                 "gratuito", "precisa_agendar", "como_agendar", "natal"],
    "additionalProperties": False,
}


class Agente:
    def __init__(self) -> None:
        self.cliente = None
        self.cache: dict[str, dict] = {}
        self.chamadas = 0
        if CACHE.exists():
            self.cache = json.loads(CACHE.read_text(encoding="utf-8"))
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return
        try:
            import anthropic
        except ImportError:
            print("! ANTHROPIC_API_KEY definida, mas o pacote 'anthropic' não está instalado; usando só heurística.")
            return
        self.anthropic = anthropic
        self.cliente = anthropic.Anthropic()

    @property
    def ativo(self) -> bool:
        return self.cliente is not None

    def analisar(self, shopping: str, titulo: str, texto: str) -> dict | None:
        chave = hashlib.sha256(f"{MODELO}\n{shopping}\n{titulo}\n{texto}".encode()).hexdigest()[:24]
        if chave in self.cache:
            return self.cache[chave]
        if not self.ativo:
            return None
        try:
            resposta = self.cliente.beta.messages.create(
                model=MODELO,
                max_tokens=4000,
                betas=["server-side-fallback-2026-07-01"],
                # se o modelo recusar, a própria API refaz a chamada num modelo alternativo
                extra_body={"fallbacks": "default"},
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}},
                system=INSTRUCOES.format(hoje=util.hoje().isoformat()),
                messages=[{"role": "user", "content": f"Shopping: {shopping}\nTítulo: {titulo}\n\n{texto[:6000]}"}],
            )
        except self.anthropic.RateLimitError:
            print("    ! agente: limite de requisições atingido; seguindo com heurística")
            return None
        except self.anthropic.APIStatusError as erro:
            print(f"    ! agente: erro {erro.status_code}: {erro.message}")
            return None
        except self.anthropic.APIConnectionError:
            print("    ! agente: falha de conexão")
            return None
        self.chamadas += 1
        if resposta.stop_reason == "refusal":
            return None
        bloco = next((b for b in resposta.content if b.type == "text"), None)
        if bloco is None:
            return None
        veredito = json.loads(bloco.text)
        self.cache[chave] = veredito
        return veredito

    def salvar(self) -> None:
        CACHE.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
