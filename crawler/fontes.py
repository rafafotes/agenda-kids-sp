"""Fontes monitoradas. Para incluir um shopping novo, adicione um item aqui.

Campos:
  shopping, bairro, regiao  -> exibidos no site e usados nos filtros
  tipo                      -> adaptador em adaptadores.ADAPTADORES
  url                       -> página de agenda/eventos do shopping
  padrao_link (detalhes)    -> regex dos links que levam a páginas de evento
  exigir_texto (opcional)   -> regex (sem acento, minúsculo) que o texto precisa conter;
                               útil quando a página mistura vários shoppings da rede
  agente (opcional)         -> True para pedir ao agente LLM que reextraia esta fonte página a página
"""

FONTES = [
    # --- Multiplan: eventos estruturados em JSON (datas, inscrição, categoria "Infantil")
    {"shopping": "MorumbiShopping", "bairro": "Morumbi", "regiao": "Zona Sul",
     "tipo": "multiplan", "url": "https://www.morumbishopping.com.br/eventos/"},
    {"shopping": "Shopping Anália Franco", "bairro": "Anália Franco", "regiao": "Zona Leste",
     "tipo": "multiplan", "url": "https://www.shoppinganaliafranco.com.br/eventos/"},

    # --- Iguatemi
    {"shopping": "JK Iguatemi", "bairro": "Vila Olímpia", "regiao": "Zona Sul",
     "tipo": "detalhes", "url": "https://iguatemi.com.br/jkiguatemi/eventos",
     "padrao_link": r"/jkiguatemi/eventos/[a-z0-9-]+/?$"},
    {"shopping": "Iguatemi São Paulo", "bairro": "Jardim Paulistano", "regiao": "Zona Oeste",
     "tipo": "detalhes", "url": "https://iguatemi.com.br/saopaulo/eventos",
     "padrao_link": r"/saopaulo/eventos/[a-z0-9-]+/?$"},
    {"shopping": "Shopping Pátio Higienópolis", "bairro": "Higienópolis", "regiao": "Centro",
     "tipo": "detalhes", "url": "https://iguatemi.com.br/patiohigienopolis/eventos",
     "padrao_link": r"/patiohigienopolis/eventos/[a-z0-9-]+/?$"},

    # --- Sites próprios com página por evento
    {"shopping": "Shopping Jardim Sul", "bairro": "Morumbi / Vila Andrade", "regiao": "Zona Sul",
     "tipo": "detalhes", "url": "https://www.shoppingjardimsul.com.br/eventos",
     "padrao_link": r"/evento/[a-z0-9-]+$"},
    {"shopping": "Shopping Ibirapuera", "bairro": "Moema", "regiao": "Zona Sul",
     "tipo": "detalhes", "url": "https://ibirapuera.com.br/acontece-2025/",
     "padrao_link": r"ibirapuera\.com\.br/novidades/[a-z0-9-]+/?$"},
    {"shopping": "Bourbon Shopping São Paulo", "bairro": "Pompeia", "regiao": "Zona Oeste",
     "tipo": "detalhes", "url": "https://www.bourbonshopping.com.br/novidades",
     "padrao_link": r"bourbonshopping\.com\.br/novidades/[a-z0-9-]+/?$",
     "exigir_texto": r"bourbon sao paulo|pompeia|sp\b|sao paulo"},

    {"shopping": "Shopping Pátio Paulista", "bairro": "Bela Vista", "regiao": "Centro",
     "tipo": "detalhes", "url": "https://iguatemi.com.br/shoppingpatiopaulista/eventos",
     "padrao_link": r"/shoppingpatiopaulista/eventos/[a-z0-9-]+/?$"},
    {"shopping": "Tietê Plaza Shopping", "bairro": "Jardim Íris / Pirituba", "regiao": "Zona Oeste",
     "tipo": "detalhes", "url": "https://tieteplaza.com.br/eventos/",
     "padrao_link": r"tieteplaza\.com\.br/evento/[a-z0-9-]+/?$"},
    {"shopping": "Shopping Cidade São Paulo", "bairro": "Bela Vista (Av. Paulista)", "regiao": "Centro",
     "tipo": "detalhes", "url": "https://shoppingcidadesp.com.br/eventos/",
     "padrao_link": r"shoppingcidadesp\.com\.br/evento/[a-z0-9-]+/?$"},
    {"shopping": "Villa Romana Shopping", "bairro": "Vila Romana", "regiao": "Zona Oeste",
     "tipo": "detalhes", "url": "https://villaromanashopping.com.br/novidades/",
     "padrao_link": r"villaromanashopping\.com\.br/novidades/[a-z0-9-]+/?$"},
    {"shopping": "Shopping Itaquera", "bairro": "Itaquera", "regiao": "Zona Leste",
     "tipo": "detalhes", "url": "https://www.shoppingitaquera.com.br/novidades",
     "padrao_link": r"shoppingitaquera\.com\.br/novidade/[a-z0-9-]+$"},
    {"shopping": "Shopping D", "bairro": "Canindé", "regiao": "Centro",
     "tipo": "detalhes", "url": "https://www.shoppingd.com.br/acontece",
     "padrao_link": r"shoppingd\.com\.br/acontece/[a-z0-9-]+$"},

    # --- Cards na própria página
    {"shopping": "Shopping Cidade Jardim", "bairro": "Cidade Jardim", "regiao": "Zona Oeste",
     "tipo": "cards", "url": "https://www.shoppingcidadejardim.com/acontece-no-cj"},

    # --- Plataforma de inscrições Be Sistemas
    {"shopping": "Shopping Penha", "bairro": "Penha", "regiao": "Zona Leste",
     "tipo": "besistemas", "url": "https://eventos.besistemas.com.br/penha"},
]
