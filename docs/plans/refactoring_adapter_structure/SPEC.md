# ТЗ: Рефакторинг структуры — адаптеры и кластер микросервисов

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Тезисное техническое задание на реализацию целевой структуры контейнеров и ролей клиентов/серверов на базе mcp-proxy-adapter.

---

## 1. Зачем нужны клиенты и серверы на базе адаптера

- **Единый кластерный подход ко всем микросервисам** — все сервисы (Redis, Model Workplace Server, рабочее место модели) участвуют в одном кластере через один и тот же протокол и прокси: регистрация, каталог команд, единая точка входа.
- **Автоматическая регистрация на прокси** — каждый сервер-адаптер при старте регистрируется на MCP Proxy; клиенты находят сервисы через прокси, без хардкода адресов.
- **Необходимый уровень безопасности** — mTLS, единая модель доверия (сертификаты), все взаимодействия через прокси; нет прямого доступа к портам Redis/Model Workplace Server снаружи.

---

## 2. Транспорт: WebSocket

- **Клиенты при общении с серверами обязаны использовать WebSocket** (не только HTTP). Соединение с сервером-адаптером (через прокси) — по WebSocket; команды и ответы передаются по этому каналу.

---

## 3. Режим тоннеля и воспроизведение API

- **Клиенты** работают в режиме **тоннеля**: принимают вызовы в формате API Redis или Model Workplace Server и передают их командами на соответствующий сервер через адаптер (по WebSocket).
- **Серверы** на базе адаптера принимают команды от клиентов, обращаются к **реальному** Redis или Model Workplace Server и возвращают ответ обратно по цепочке клиенту.
- Итог: с точки зрения вызывающего кода сохраняются привычные API Redis и Model Workplace Server, но трафик идёт через адаптер (WebSocket) и прокси.

**Redis:**

- **Клиент Redis на базе адаптера** — передаёт команды (GET, SET, LRANGE и т.д.) серверу через адаптер.
- **Сервер Redis на базе адаптера** — принимает команды от клиента, выполняет их через локальный клиент Redis (подключение к Redis в контейнере), возвращает ответ клиенту.

**Model Workplace Server:**

- **Клиент Model Workplace Server на базе адаптера** — передаёт запросы (chat, embed, list, pull и т.д.) серверу через адаптер.
- **Сервер Model Workplace Server на базе адаптера** — принимает команды от клиента, выполняет их через HTTP к локальному Model Workplace Server (127.0.0.1:11434), возвращает ответ клиенту.

---

## 4. Целевая структура контейнеров

| Контейнер           | Содержимое                                      | Роль |
|---------------------|--------------------------------------------------|------|
| **redis-adapter**   | Redis + сервер API на базе mcp-proxy-adapter     | Сервис хранилища; доступ только через адаптер. |
| **mwps-adapter**  | Model Workplace Server + сервер API на базе mcp-proxy-adapter    | Сервис моделей; доступ только через адаптер.   |
| **model-workspace-server** | Только приложение «рабочее место модели»   | Использует **клиенты провайдеров** (mwps_provider_client, redis_provider_client). Model Workplace Server для рабочего места — просто отдельный провайдер; внутри нет Redis и Model Workplace Server. |

- Контейнер **mwps** (только образ mwps/mwps) — удалить из использования.
- Контейнер **redis** (голый redis:7-alpine) — заменить на **redis-adapter** (Redis + адаптер-сервер).

---

## 5. Структура репозитория: серверы и клиенты на базе адаптера

В **корне репозитория** — подпроекты двух типов: **серверы** (сервис + адаптер) и **клиенты** (на базе клиента адаптера). Корень содержит только общее и сертификаты.

**Принцип клиентов:** Все клиенты должны быть **на базе клиента адаптера** (mcp-proxy-adapter: WebSocket, протокол команд). В клиенте **скрыта специфика и формат** работы с конкретным провайдером/сервисом: вызывающий код видит только единый API (Model Workplace Server-методы, Redis-команды, контракт provider_client_standard и т.д.), транспорт и сериализация — внутри клиента.

**Корень репозитория:**

- **Общие документы** — обзор подпроектов, сопряжение, правила, ссылки. См. [docs/SUBPROJECTS_OVERVIEW.md](../../SUBPROJECTS_OVERVIEW.md).
- **Сертификаты** — каталог `mtls_certificates`.
- Никакого кода приложений, зависимостей и конфигов подпроектов в корне.

**Шесть категорий подпроектов (каталоги в корне):**

| № | Категория | Подкаталог | Назначение |
|---|-----------|------------|------------|
| 1 | Model Workplace Server сервер + адаптер | **mwps_adapter** | Сервер: Model Workplace Server + API на базе mcp-proxy-adapter; регистрация на прокси; доступ к Model Workplace Server только через адаптер. |
| 2 | Redis сервер + адаптер | **redis_adapter** | Сервер: Redis + API на базе mcp-proxy-adapter; регистрация на прокси; доступ к Redis только через адаптер. |
| 3 | Рабочее место (сервер) | **model_workspace** | Приложение «рабочее место модели»: оркестрация чата, сессии, контекст, инструменты через MCP Proxy; использует клиенты провайдеров; внутри нет Redis и Model Workplace Server. |
| 4 | Клиент Model Workplace Server на базе клиента адаптера | **mwps_provider_client** | Клиент провайдера Model Workplace Server: единый API (chat, embed, healthcheck) для model_workspace; **на базе клиента адаптера**; внутри скрыты формат и транспорт к mwps-adapter. Для рабочего места Model Workplace Server — просто отдельный провайдер. |
| 5 | Клиент Redis на базе клиента адаптера | **redis_provider_client** | Клиент к redis-adapter: API хранилища (execute + обёртки get, set, …); **на базе клиента адаптера**; внутри скрыты формат и транспорт к redis-adapter. |
| 6 | Клиенты других провайдеров | **&lt;provider&gt;_provider_client** | Подкаталоги для клиентов иных провайдеров (например openai_provider_client, anthropic_provider_client): каждый на базе клиента адаптера, скрывает специфику и формат своего провайдера; контракт — docs/standards/provider_client_standard. |

Подпроекты изолированы: свои зависимости, конфиги, документация. Требования к каждому: структура под PyPI (`pyproject.toml`, `src/<package>/`, тесты, README, docs/).

Итог: монорепозиторий; корень — общие документы и `mtls_certificates`; серверы (1–3) и клиенты (4–6) в отдельных каталогах; все клиенты строятся на базе клиента адаптера и скрывают специфику провайдера.

---

## 6. Model Workplace Server: полный набор методов клиента

Model Workplace Server предоставляет **REST HTTP API** на порту 11434. **Клиент Model Workplace Server на базе адаптера должен повторять весь этот набор в виде методов клиента** (каждый эндпоинт — отдельный метод). Сервер mwps-adapter реализует те же операции, обращаясь к локальному Model Workplace Server.

**Классы протокола.**

- **Отдельный класс для запроса/ответа Model Workplace Server** — единая структура (request/response): имя метода/эндпоинта, параметры (model, messages, prompt и т.д.), тело ответа. Используется при сериализации запроса от клиента к серверу и при сериализации ответа от сервера к клиенту (например, JSON с полями `method`, `params`, `result` / `error`).
- **Отдельный класс для ошибок Model Workplace Server** — выделенный тип для ошибок (ответ HTTP 4xx/5xx, ошибка протокола, таймаут). Клиент и сервер используют его для передачи и обработки ошибок; на клиенте ошибки могут пробрасываться как исключение этого класса.

**Архитектура: один базовый метод + обёртки (клиент).**

- **Клиент Model Workplace Server на базе адаптера** реализует **один базовый метод**, например `execute(method_name: str, **params)` (или `(method_name, params)`). Он передаёт на сервер по WebSocket имя метода (tags, chat, generate, pull и т.д.) и набор параметров. Получает ответ, десериализует его и возвращает вызывающему коду **питоновские объекты** (dict, list, str и т.д., в соответствии с форматом ответа Model Workplace Server).
- **Все остальные методы** клиента Model Workplace Server (tags, chat, generate, embeddings, pull, …) — **обёртки** над этим одним методом: каждая обёртка формирует имя метода и аргументы и вызывает `execute(method_name, **params)`, возвращая результат без изменения. **Валидация параметров** (наличие обязательных, отсутствие лишних, типы) выполняется **в обёртках**, а не в базовом `execute()`.

**Сервер mwps-adapter.**

- Принимает запрос от клиента и **десериализует** его (имя метода + параметры).
- Вызывает **нативный HTTP-клиент** к локальному Model Workplace Server (соответствующий эндпоинт: /api/tags, /api/chat и т.д.).
- Получает ответ от Model Workplace Server, **сериализует в JSON** и отправляет клиенту Model Workplace Server-адаптера по WebSocket.

**Полный список методов API Model Workplace Server (и соответствующих методов клиента):**

| HTTP API | Метод клиента (пример имени) | Назначение |
|----------|------------------------------|------------|
| `GET /api/tags` | `tags()` / `list_models()` | Список локальных моделей |
| `POST /api/chat` | `chat(model, messages, …)` | Чат (messages, tools, stream) |
| `POST /api/generate` | `generate(model, prompt, …)` | Генерация по промпту |
| `POST /api/embeddings` | `embeddings(model, input)` | Эмбеддинги (офиц. док. — embeddings) |
| `POST /api/pull` | `pull(model)` | Скачивание модели |
| `POST /api/push` | `push(model)` | Выгрузка модели в реестр |
| `DELETE /api/delete` | `delete(model)` | Удаление модели |
| `POST /api/show` | `show(model)` | Информация о модели |
| `POST /api/copy` | `copy(source, dest)` | Копирование/переименование модели |
| `POST /api/create` | `create(name, modelfile, …)` | Создание модели из Modelfile |
| `GET /api/ps` | `ps()` / `running()` | Список запущенных моделей |
| `GET /api/version` | `version()` | Версия Model Workplace Server |

Клиент реализует **все** перечисленные методы как обёртки над `execute()`; вызов каждого уходит на сервер-адаптер по WebSocket и воспроизводит поведение соответствующего эндпоинта Model Workplace Server.

---

## 7. Redis: методы клиента

**Классы протокола.**

- **Отдельный класс для запроса/ответа Redis** — единая структура (request/response): имя команды, параметры, тело ответа. Используется при сериализации запроса от клиента к серверу и при сериализации ответа от сервера к клиенту (например, JSON с полями `command`, `params`, `result` / `error`).
- **Отдельный класс для ошибок Redis** — выделенный тип для ошибок (ответ Redis, исключение нативного клиента, ошибка протокола). Клиент и сервер используют его для передачи и обработки ошибок; на клиенте ошибки могут пробрасываться как исключение этого класса.

Клиент Redis на базе адаптера должен воспроизводить **полный набор команд/методов клиента Redis**. Эталон — протокол Redis (команды сервера) и/или API клиента **redis-py** (класс `Redis`, миксины `CoreCommands` и др.). Ссылки: [Redis Commands](https://redis.io/docs/latest/commands/), [redis-py Commands](https://redis.readthedocs.io/en/stable/commands.html).

**Категории команд Redis (кратко; полный список — по ссылкам выше):**

- **ACL:** `acl_cat`, `acl_deluser`, `acl_getuser`, `acl_list`, `acl_load`, `acl_save`, `acl_setuser`, `acl_users`, `acl_whoami`, …
- **Строки (String):** `get`, `set`, `setex`, `setnx`, `getex`, `getdel`, `append`, `getrange`, `setrange`, `incr`, `incrby`, `decr`, `decrby`, `incrbyfloat`, `mget`, `mset`, `msetnx`, `strlen`, …
- **Ключи (Generic):** `delete`, `exists`, `expire`, `expireat`, `pexpire`, `ttl`, `pttl`, `persist`, `keys`, `scan`, `rename`, `renamenx`, `type`, `dump`, `restore`, …
- **Хеши (Hash):** `hget`, `hset`, `hsetnx`, `hgetall`, `hmget`, `hmset`, `hdel`, `hlen`, `hkeys`, `hvals`, `hexists`, `hincrby`, `hincrbyfloat`, `hscan`, …
- **Списки (List):** `lpush`, `rpush`, `lpop`, `rpop`, `lrange`, `llen`, `lindex`, `lset`, `lrem`, `ltrim`, `linsert`, `blpop`, `brpop`, `rpoplpush`, `lmove`, `lmpop`, …
- **Множества (Set):** `sadd`, `srem`, `smembers`, `sismember`, `scard`, `spop`, `srandmember`, `sinter`, `sunion`, `sdiff`, `sinterstore`, `sunionstore`, `sdiffstore`, `sscan`, …
- **Упорядоченные множества (Sorted Set):** `zadd`, `zrem`, `zrange`, `zrevrange`, `zrangebyscore`, `zrank`, `zscore`, `zcard`, `zcount`, `zincrby`, `zpopmin`, `zpopmax`, `bzpopmin`, `bzpopmax`, …
- **Битовые операции (Bitmap):** `getbit`, `setbit`, `bitcount`, `bitop`, `bitpos`, `bitfield`, …
- **Pub/Sub:** `publish`, `subscribe`, `unsubscribe`, `psubscribe`, `punsubscribe`, `pubsub_channels`, `pubsub_numsub`, …
- **Транзакции и скрипты:** `multi`, `exec`, `discard`, `watch`, `unwatch`, `eval`, `evalsha`, `script_load`, `script_flush`, `script_exists`, …
- **Подключение и сервер:** `ping`, `echo`, `auth`, `select`, `quit`, `client_list`, `client_setname`, `config_get`, `config_set`, `info`, `dbsize`, `flushdb`, `flushall`, `save`, `bgsave`, `lastsave`, `shutdown`, …

**Архитектура: один базовый метод + обёртки (клиент).**

- **Клиент Redis на базе адаптера** реализует **один базовый метод**, например `execute(command_name: str, *args, **kwargs)` (или `(command_name, params)`). Он передаёт на сервер по WebSocket:
  - имя команды Redis;
  - набор параметров (аргументы команды).
  Получает ответ, десериализует его (по сути — сериализация/десериализация ответа нативного клиента Redis) и возвращает вызывающему коду **питоновские объекты** (str, int, list, dict, bytes и т.д., в зависимости от команды).
- **Все остальные методы** клиента Redis (get, set, hgetall, lrange, …) — **обёртки** над этим одним методом: каждая обёртка формирует имя команды и аргументы и вызывает `execute(command_name, *params)`, возвращая результат без изменения. **Валидация параметров** (наличие обязательных, отсутствие лишних, типы) выполняется **в обёртках**, а не в базовом `execute()`.

**Сервер redis-adapter.**

- Принимает запрос от клиента и **десериализует** его (имя команды + параметры).
- Вызывает **нативный клиент Redis** (например, redis-py) с этой командой и параметрами.
- Получает ответ от Redis, **сериализует в JSON** (или другой согласованный формат) и отправляет клиенту Redis-адаптера по WebSocket.

Итог: один протокол запрос/ответ (команда + параметры ↔ сериализованный результат), обёртки на клиенте повторяют API redis-py; на сервере — десериализация → нативный Redis → сериализация ответа в JSON → отправка клиенту.

---

## 8. Итог по ролям

- **Сервер redis-adapter:** Redis + mcp-proxy-adapter server; регистрация на прокси; команды — обёртки над Redis API.
- **Сервер mwps-adapter:** Model Workplace Server + mcp-proxy-adapter server; регистрация на прокси; команды — обёртки над Model Workplace Server HTTP API (tags, chat, embed, pull и др.).
- **redis_provider_client:** клиент к redis-adapter **на базе клиента адаптера**; скрывает формат и транспорт; для model_workspace — API хранилища (execute + обёртки).
- **mwps_provider_client:** клиент провайдера Model Workplace Server **на базе клиента адаптера**; скрывает формат и транспорт; для рабочего места **Model Workplace Server — просто отдельный провайдер**; контракт по docs/standards/provider_client_standard.
- **Клиенты других провайдеров:** отдельные подкаталоги (например openai_provider_client); каждый на базе клиента адаптера, скрывает специфику провайдера.
- **model-workspace-server:** только логика рабочего места; использует клиенты провайдеров (mwps, redis, при необходимости другие); тоннельный режим через эти клиенты.
