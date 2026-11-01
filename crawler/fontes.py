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
    {"shopping": "Shopping Vila Olímpia", "bairro": "Vila Olímpia", "regiao": "Zona Sul",
     "tipo": "multiplan", "url": "https://www.shoppingvilaolimpia.com.br/eventos/"},

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

    {"shopping": "Shopping West Plaza", "bairro": "Água Branca", "regiao": "Zona Oeste",
     "tipo": "detalhes", "url": "https://www.westplaza.com.br/",
     "padrao_link": r"westplaza\.com\.br/evento/\?evento=[a-z0-9-]+$"},
    {"shopping": "Shopping União", "bairro": "Osasco", "regiao": "Grande SP",
     "tipo": "detalhes", "url": "https://www.shoppinguniao.com.br/",
     "padrao_link": r"shoppinguniao\.com\.br/evento_\d{4}_[a-z0-9_-]+\.php$"},
    {"shopping": "Shopping União", "bairro": "Osasco", "regiao": "Grande SP",
     "tipo": "feed_instagram", "url": "https://www.shoppinguniao.com.br/"},
    {"shopping": "Open Mall The Square", "bairro": "Granja Viana (Cotia)", "regiao": "Grande SP",
     "tipo": "eventos_manager", "url": "https://openmallthesquare.com.br/eventos-nova/"},

    # --- Cards na própria página
    {"shopping": "Shopping Cidade Jardim", "bairro": "Cidade Jardim", "regiao": "Zona Oeste",
     "tipo": "cards", "url": "https://www.shoppingcidadejardim.com/acontece-no-cj"},

    # --- Plataforma de inscrições Be Sistemas: lê a página "Acontece" do shopping e cada evento
    {"shopping": "Shopping Penha", "bairro": "Penha", "regiao": "Zona Leste",
     "tipo": "besistemas", "url": "https://www.shoppingpenha.com.br/pt-BR/acontece"},
    {"shopping": "Shopping Frei Caneca", "bairro": "Consolação", "regiao": "Centro",
     "tipo": "besistemas", "url": "https://freicanecashopping.com.br/pt-BR/acontece"},

    # --- Sites que carregam a agenda por script, lidos pela mesma API pública que a página usa
    {"shopping": "Shopping Partage Santana", "bairro": "Santana", "regiao": "Zona Norte",
     "tipo": "madnezz", "empreendimento_id": 11, "pagina": "https://www.partagesantana.com.br/eventos"},
    {"shopping": "Shopping Center Norte", "bairro": "Vila Guilherme", "regiao": "Zona Norte",
     "tipo": "api_json", "url": "https://apisite.cidadecenternorte.com.br/v1/site/scn/news",
     "pagina": "https://www.centernorte.com.br/novidades"},

    # --- Shoppings que recusam acesso automatizado (HTTP 403): eventos buscados nas notícias
    {"shopping": "Shopping Eldorado", "bairro": "Pinheiros", "regiao": "Zona Oeste",
     "tipo": "noticias", "url": "https://www.shoppingeldorado.com.br/", "termos": ["Shopping Eldorado"]},
    {"shopping": "Shopping Tamboré", "bairro": "Barueri", "regiao": "Grande SP",
     "tipo": "noticias", "url": "https://shoppingtambore.com.br", "termos": ["Shopping Tamboré"]},

    # --- Sesc SP: programação de todas as unidades da cidade pela API pública do site
    {"shopping": "Sesc SP", "bairro": "", "regiao": "", "tipo": "sesc", "tipo_local": "Sesc",
     "url": "https://www.sescsp.org.br/programacao/",
     "unidades": {  # slug na API: (bairro, região)
         "14-bis": ("Bela Vista", "Centro"),
         "24-de-maio": ("República", "Centro"),
         "avenida-paulista": ("Bela Vista", "Centro"),
         "belenzinho": ("Belenzinho", "Zona Leste"),
         "bom-retiro": ("Bom Retiro", "Centro"),
         "campo-limpo": ("Campo Limpo", "Zona Sul"),
         "carmo": ("Sé", "Centro"),
         "casa-verde": ("Casa Verde", "Zona Norte"),
         "cinesesc": ("Cerqueira César", "Centro"),
         "consolacao": ("Consolação", "Centro"),
         "interlagos": ("Interlagos", "Zona Sul"),
         "ipiranga": ("Ipiranga", "Zona Sul"),
         "itaquera": ("Itaquera", "Zona Leste"),
         "pinheiros": ("Pinheiros", "Zona Oeste"),
         "pompeia": ("Pompeia", "Zona Oeste"),
         "santana": ("Santana", "Zona Norte"),
         "santo-amaro": ("Santo Amaro", "Zona Sul"),
         "sao-bento": ("Centro", "Centro"),
         "vila-mariana": ("Vila Mariana", "Zona Sul"),
     }},
]
