# ZRK_bot

## VPN mode via TalosClaudeVPN

Если Telegram доступен только через VPN-контейнер `TalosClaudeVPN` из соседнего `../TalosPrinciple`, бот можно запускать без изменения основной схемы так:

```bash
export DATABASE_URL_VPN='postgresql+asyncpg://postgres:postgres@<HOST_GATEWAY_IP>:5432/career_quest'
export REDIS_URL_VPN='redis://<HOST_GATEWAY_IP>:6379/0'
docker compose -f docker-compose.yml -f docker-compose.vpn.yml up -d --build
```

Что делает `docker-compose.vpn.yml`:
- переводит сервис `bot` в `network_mode: "container:TalosClaudeVPN"`
- отправляет весь Telegram-трафик через VPN namespace контейнера `TalosClaudeVPN`
- оставляет доступ к Postgres и Redis через адрес хоста, который нужно передать явно

Важно:
- в этом режиме имена `db` и `redis` больше не работают, потому что бот использует сетевой namespace контейнера `TalosClaudeVPN`
- поэтому `DATABASE_URL_VPN` и `REDIS_URL_VPN` нужно задавать явно

Узнать IP хост-шлюза из `TalosClaudeVPN` можно так:

```bash
docker exec TalosClaudeVPN sh -lc "ip route | awk '/default/ {print \$3}'"
```

После этого можно быстро проверить доступность портов с точки зрения VPN-контейнера:

```bash
docker exec TalosClaudeVPN bash -lc 'GW=$(ip route | awk "/default/ {print \$3}"); timeout 2 bash -lc "</dev/tcp/$GW/5432" && echo POSTGRES_OK'
docker exec TalosClaudeVPN bash -lc 'GW=$(ip route | awk "/default/ {print \$3}"); timeout 2 bash -lc "</dev/tcp/$GW/6379" && echo REDIS_OK'
```

Для продового переключения безопаснее запускать только сервис бота:

```bash
docker compose -f docker-compose.yml -f docker-compose.vpn.yml up -d --no-deps --build bot
```

Это пересоздаст только `bot`, не трогая `db` и `redis`. Параллельно второй экземпляр с тем же `BOT_TOKEN` запускать нельзя, потому что используется long polling.

Дополнительно бот поддерживает опциональный `TELEGRAM_PROXY_URL`. Это запасной режим на случай, если позже ты поднимешь HTTP/SOCKS proxy поверх VPN-контейнера.
