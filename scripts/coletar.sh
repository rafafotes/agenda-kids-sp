#!/usr/bin/env bash
# Coleta a agenda neste computador e envia os dados ao GitHub, que publica o site.
#
# Roda aqui, e não no GitHub Actions, porque Sesc SP, Jardim Sul e Itaquera recusam (HTTP 403)
# acessos vindos de servidores de nuvem. Agendado pelo Agendador de Tarefas do Windows às 6h e 18h
# (veja scripts/agendar-windows.ps1). Pode ser rodado à mão a qualquer momento.
#
# Chave opcional do agente com Claude: ANTHROPIC_API_KEY=... em ~/.config/agenda-kids/env

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
ESTADO="${XDG_STATE_HOME:-$HOME/.local/state}/agenda-kids"
mkdir -p "$ESTADO"
exec >>"$ESTADO/coleta.log" 2>&1

# uma coleta por vez (o horário perdido e o agendado podem cair juntos)
exec 9>"$ESTADO/coleta.lock"
flock -n 9 || { echo "$(date -Is) outra coleta em andamento, saindo"; exit 0; }

echo "== $(date -Is) início"
cd "$REPO"

if [ -f "$HOME/.config/agenda-kids/env" ]; then
  set -a; . "$HOME/.config/agenda-kids/env"; set +a
fi

git pull --rebase --autostash -q origin main
python3 -m unittest -q
python3 -m crawler

git add site/dados/eventos.json crawler/cache_agente.json
if git diff --cached --quiet; then
  echo "sem mudanças nos dados"
else
  git -c user.name="agenda-bot" -c user.email="agenda-bot@users.noreply.github.com" \
    commit -q -m "Atualiza agenda ($(date '+%d/%m %H:%M'))"
  git push -q origin main
  echo "dados enviados"
fi
echo "== $(date -Is) fim"
