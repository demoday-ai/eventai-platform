#!/bin/bash
# Drive the live bot via chat.py inside the `botcli` compose service.
#
# Each session keeps its own state under /tmp/eventai_<session>/ inside the
# container. State persists across calls within a session; different sessions
# are isolated (different user_id, FSM, /tmp dir).
#
# Usage:
#   scripts/botchat.sh <session> '<message>'
#   scripts/botchat.sh <session> '@<callback_data>'    # button click
#   scripts/botchat.sh <session> '!state'              # show FSM state
#   scripts/botchat.sh <session> '!data'               # show FSM data
#   scripts/botchat.sh <session> '!reset'              # wipe session
#
# Example flow (guest path):
#   scripts/botchat.sh g1 '/start'
#   scripts/botchat.sh g1 '@role:guest:student'
#   scripts/botchat.sh g1 'Меня интересуют NLP проекты'
#   scripts/botchat.sh g1 '@profile:confirm'
set -euo pipefail
if [ $# -lt 2 ]; then
  echo "usage: $0 <session> '<message_or_callback>'" >&2
  exit 2
fi
SESSION="$1"
shift
# Default to local dev compose. Override with COMPOSE_FILE=docker-compose.prod.yml
# when running on the prod host (e.g. via SSH from CD).
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SERVICE="${SERVICE:-botcli}"
exec docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
  python scripts/chat.py --session="$SESSION" "$@"
