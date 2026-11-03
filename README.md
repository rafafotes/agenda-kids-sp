# Agenda Kids SP

Atividades para crianças nos shoppings e nas unidades do Sesc em São Paulo, reunidas em um só lugar. Um crawler visita os
sites oficiais dos shoppings duas vezes por dia, separa o que é atividade infantil (oficinas, teatro,
Papai Noel, parquinhos, exposições...) de promoções e avisos, e publica tudo num site estático com
filtros por período, Natal, "precisa agendar", gratuito, região e shopping.

## Como funciona

```
crawler/fontes.py       lista de shoppings monitorados (URL da agenda + tipo de site)
crawler/adaptadores.py  um leitor por tipo de site:
                          multiplan        JSON embutido (datas, inscrição, categoria "Infantil")
                          detalhes         segue os links da agenda e lê cada página de evento
                          cards            eventos listados como cards na própria página
                          besistemas       plataforma de inscrições (vagas, esgotado, abertura)
                          madnezz/api_json API pública que o próprio site consulta no navegador
                          eventos_manager  agenda WordPress com aba "Para crianças"
                          feed_instagram   legendas do Instagram que o site embute na home
                          noticias         releases publicados em sites de notícias (WordPress)
                          sesc             API pública do Sesc SP, unidades da cidade, público "Crianças"
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

## Publicar

O site fica em https://rafafotes.github.io/agenda-kids-sp/ (GitHub Pages).

A **coleta roda no computador do mantenedor**, não no GitHub Actions: Sesc SP, Jardim Sul e
Itaquera respondem HTTP 403 a acessos vindos de servidores de nuvem, e o crawler não se disfarça
para contornar isso. `scripts/coletar.sh` atualiza o repositório, roda os testes, coleta e faz
push só dos dados; cada push dispara `.github/workflows/atualizar.yml`, que testa e publica.

O agendamento é uma tarefa do Agendador de Tarefas do Windows ("Agenda Kids SP - coleta"), às 6h
e às 18h, que chama o script dentro do WSL. Se o computador estiver desligado no horário, a coleta
roda assim que ele voltar. Para recriar a tarefa:

```bash
powershell.exe -ExecutionPolicy Bypass -File "$(wslpath -w scripts/agendar-windows.ps1)" \
  -Distro "$WSL_DISTRO_NAME" -Script "$PWD/scripts/coletar.sh"
```

- Rodar uma coleta agora: `scripts/coletar.sh` (log em `~/.local/state/agenda-kids/coleta.log`).
- Agente com Claude (opcional): `ANTHROPIC_API_KEY=...` em `~/.config/agenda-kids/env`, mais
  `pip install -r requirements-agente.txt`.

## Adicionar um shopping

Inclua um item em `crawler/fontes.py`. Na maioria dos casos basta o tipo `detalhes` com a URL da
página de eventos e uma regex para os links de cada evento, por exemplo:

```python
{"shopping": "Shopping X", "bairro": "Bairro", "regiao": "Zona Sul",
 "tipo": "detalhes", "url": "https://shoppingx.com.br/eventos",
 "padrao_link": r"shoppingx\.com\.br/evento/[a-z0-9-]+/?$"},
```

Teste com `python3 -m crawler "Shopping X"`.

### Shoppings que bloqueiam robôs

Eldorado e Tamboré respondem HTTP 403 a qualquer acesso automatizado. O crawler não se disfarça de
navegador para contornar isso: busca os eventos deles em sites de notícias que publicam os releases
(`SITES_NOTICIAS` em `adaptadores.py`), usando só o trecho que fala do shopping. A cobertura é menor
que a do site oficial; o caminho completo seria pedir ao shopping acesso ou um feed.

### Ainda não cobertos

- **Bloqueiam robôs (HTTP 403):** Villa-Lobos, Mooca Plaza, Metrópole, Campo Limpo.
- **Agenda montada por JavaScript:** Morumbi Town, SP Market, Butantã, Santana Parque, Aricanduva,
  Raposo, Interlagos. Em geral dá para achar a API que a página chama (veja `madnezz` e `api_json`).
