# Agenda Kids SP

Atividades para crianças nos shoppings de São Paulo, reunidas em um só lugar. Um crawler visita os
sites oficiais dos shoppings duas vezes por dia, separa o que é atividade infantil (oficinas, teatro,
Papai Noel, parquinhos, exposições...) de promoções e avisos, e publica tudo num site estático com
filtros por período, Natal, "precisa agendar", gratuito, região e shopping.

## Como funciona

```
crawler/fontes.py       lista de shoppings monitorados (URL da agenda + tipo de site)
crawler/adaptadores.py  um leitor por tipo de site:
                          multiplan   JSON embutido (datas, inscrição, categoria "Infantil")
                          detalhes    segue os links da agenda e lê cada página de evento
                          cards       eventos listados como cards na própria página
                          besistemas  plataforma de inscrições Be Sistemas
crawler/util.py         HTTP educado (robots.txt, 1 req/s por site), datas em português,
                        classificadores (infantil, Natal, agendamento, gratuito, faixa etária)
crawler/agente.py       agente opcional com Claude que relê cada evento e refina o veredito
site/index.html         o site (HTML + JS puro, lê site/dados/eventos.json)
```

O crawler usa só a biblioteca padrão do Python. Linhas que se repetem em várias páginas do mesmo
site (menu, rodapé, barra lateral) são descartadas antes da classificação, para que um "Papai Noel"
no menu não marque todos os eventos como de Natal. Se um site cair numa coleta, os eventos que já
tínhamos dele são mantidos até a próxima.

## Rodar localmente

```bash
python3 -m crawler              # coleta tudo e grava site/dados/eventos.json
python3 -m crawler Morumbi      # só as fontes cujo nome contém "Morumbi"
python3 -m unittest             # testes
python3 -m http.server -d site  # abre o site em http://localhost:8000
```

### Agente com Claude (opcional, melhora a precisão)

Sem chave, a classificação é só heurística (palavras-chave + datas). Com chave, o Claude lê cada
publicação e decide se é para crianças, extrai datas, horário, faixa etária e explica como agendar.

```bash
pip install -r requirements-agente.txt
export ANTHROPIC_API_KEY=...
python3 -m crawler
```

O modelo padrão é `claude-opus-5-5`; troque com `AGENDA_MODELO`. As respostas ficam em
`crawler/cache_agente.json`, então cada evento só é analisado de novo quando o texto muda.

## Publicar (GitHub Pages)

1. Suba este diretório para um repositório no GitHub.
2. Em *Settings → Pages*, escolha **GitHub Actions** como fonte.
3. (Opcional) Em *Settings → Secrets and variables → Actions*, crie o secret `ANTHROPIC_API_KEY`.
4. O workflow `.github/workflows/atualizar.yml` roda às 6h e às 18h, grava os dados no repositório
   e publica o site. Para rodar na hora: aba *Actions → Atualizar agenda → Run workflow*.

## Adicionar um shopping

Inclua um item em `crawler/fontes.py`. Na maioria dos casos basta o tipo `detalhes` com a URL da
página de eventos e uma regex para os links de cada evento, por exemplo:

```python
{"shopping": "Shopping X", "bairro": "Bairro", "regiao": "Zona Sul",
 "tipo": "detalhes", "url": "https://shoppingx.com.br/eventos",
 "padrao_link": r"shoppingx\.com\.br/evento/[a-z0-9-]+/?$"},
```

Teste com `python3 -m crawler "Shopping X"`.

### Ainda não cobertos

- **Bloqueiam robôs (HTTP 403):** Eldorado, Villa-Lobos, Tamboré, Mooca Plaza, Metrópole, Campo Limpo.
- **Agenda montada por JavaScript:** Butantã, SP Market, Santana Parque, Continental, Center Norte,
  Morumbi Town, Aricanduva, Raposo, West Plaza, Interlagos. Dá para cobri-los descobrindo a API
  que a página chama ou com um navegador headless.
- **Sem página de eventos ativa no momento:** Shopping Vila Olímpia.
