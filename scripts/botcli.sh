#!/bin/bash
# Интерактивный CLI бота. Работает с реальной локальной БД, Redis, OpenRouter.
# Использование:
#   bash scripts/botcli.sh
#
# Внутри терминала:
#   /start, /help, /support, /rebuild, /profile     — команды
#   @role:guest:student                              — клик по кнопке (любой callback_data)
#   любой текст                                      — сообщение боту
#   !state, !data                                    — посмотреть FSM
#   !quit                                            — выход
exec docker compose exec -it botcli python scripts/cli_bot.py
