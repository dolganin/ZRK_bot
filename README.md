# ZRK_bot

## VPN mode via TalosClaudeVPN

Если Telegram доступен только через VPN-контейнер `TalosClaudeVPN` из соседнего `../TalosPrinciple`, бот можно запускать без изменения основной схемы так:

```bash
docker compose -f docker-compose.yml -f docker-compose.vpn.yml up -d --build
```

Что делает `docker-compose.vpn.yml`:
- переводит сервис `bot` в `network_mode: "container:TalosClaudeVPN"`
- отправляет весь Telegram-трафик через VPN namespace контейнера `TalosClaudeVPN`
- оставляет доступ к Postgres и Redis через `host.docker.internal`

По умолчанию в VPN-режиме используются:
- `DATABASE_URL_VPN=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/career_quest`
- `REDIS_URL_VPN=redis://host.docker.internal:6379/0`

Если у тебя другие адреса БД/Redis, просто переопредели `DATABASE_URL_VPN` и `REDIS_URL_VPN`.

Дополнительно бот поддерживает опциональный `TELEGRAM_PROXY_URL`. Это запасной режим на случай, если позже ты поднимешь HTTP/SOCKS proxy поверх VPN-контейнера.
