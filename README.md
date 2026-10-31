# Portable OpenCode workbench

Переносимая конфигурация OpenCode V2 и `oh-my-opencode-slim` без секретов,
сессий, истории, логов и кэшей.

## Текущая конфигурация

- Slim закреплён на версии `3.0.6`; `autoUpdate` отключён.
- Основной доступ: официальный вход OpenAI через ChatGPT Plus/Pro.
- Orchestrator и Fixer: `openai/gpt-6.1-sol`.
- Explorer и Designer: `openai/gpt-6-luna`.
- Oracle: `openai/gpt-6.1-sol`, вызывается по риску, а не после каждой правки.
- Не более двух одновременно работающих фоновых задач.
- `wallClockTimeoutMs=1800000` ограничивает отдельного фонового исполнителя,
  а не всю сессию и не расходы.
- Автоматический fallback, Council injection, Marketplace tools, Interview,
  Companion и multiplexer отключены.
- Shell-команды требуют подтверждения OpenCode.

## Запуск

Из каталога нужного проекта:

```sh
~/ai-workbench/bin/oc
```

Wrapper не меняет текущий каталог и передаёт все аргументы OpenCode.
Web search по умолчанию выключен. Для явного включения Exa на один запуск:

```sh
~/ai-workbench/bin/oc --web
```

## Вход и проверка

Авторизация хранится отдельно и не переносится. При необходимости запустите
OpenCode и выполните `/connect`, выберите OpenAI и официальный вход ChatGPT.
Не помещайте токены в этот репозиторий.

Проверка без модельных запросов:

```sh
opencode plugin list
opencode models
npx oh-my-opencode-slim@3.0.6 doctor
```

`ping all agents` обращается к моделям и расходует квоту; запускайте его только
осознанно. На OpenCode V2 команды `opencode models --refresh` нет.

## Перенос на вторую машину

1. Установите версии из `versions.txt` или совместимые актуальные версии
   OpenCode V2 и Node.js/npm. Bun не обязателен.
2. Клонируйте приватный репозиторий как `~/ai-workbench`.
3. Сохраните существующие пользовательские конфиги с датой:

   ```sh
   stamp=$(date +%Y%m%d-%H%M%S)
   cp -a ~/.config/opencode/opencode.jsonc ~/.config/opencode/opencode.jsonc.bak.$stamp
   cp -a ~/.config/opencode/oh-my-opencode-slim.jsonc ~/.config/opencode/oh-my-opencode-slim.jsonc.bak.$stamp
   ```

   Выполняйте только для реально существующих файлов. Если одновременно есть
   JSON и JSONC, сначала разберите конфликт; JSONC Slim имеет приоритет.
4. Подключите только управляемые файлы, не заменяя весь каталог:

   ```sh
   mkdir -p ~/.config/opencode
   ln -s ../../ai-workbench/config/opencode.jsonc ~/.config/opencode/opencode.jsonc
   ln -s ../../ai-workbench/config/oh-my-opencode-slim.jsonc ~/.config/opencode/oh-my-opencode-slim.jsonc
   ```

5. Убедитесь, что pinned-плагин `oh-my-opencode-slim@3.0.6` загрузился.
   Один перенос JSON не переносит установленный пакет или кэш.
6. Авторизуйте OpenAI заново через `/connect` на второй машине.
7. Выполните `opencode plugin list`, `opencode models` и doctor.
8. Запускайте `~/ai-workbench/bin/oc` из нужного проекта.

## OpenRouter как независимый резерв

Резерв намеренно не активирован и баланс не пополнялся. Для подключения
запустите `/connect`, выберите OpenRouter и введите ключ локально, затем
получите реальные модели через `/models` или `opencode models`. Только после
этого добавляйте отдельный preset с фактическими ID. Сначала задайте лимит
расходов на стороне провайдера; concurrency и timeout денежным лимитом не
являются.

## Обновление

1. Проверьте release notes и схему новой версии.
2. Создайте датированные копии двух конфигов.
3. Замените точную версию одновременно в `config/opencode.jsonc`, `$schema`
   Slim и `versions.txt`.
4. Выполните reload и doctor, затем минимальный smoke test.
5. Проверьте, что ссылки не заменены обычными файлами:

   ```sh
   test -L ~/.config/opencode/opencode.jsonc
   test -L ~/.config/opencode/oh-my-opencode-slim.jsonc
   ```

Не используйте `--reset` без отдельного решения. Изменение preset по умолчанию
не меняет уже привязанную V2-сессию; примените `/preset <name>` к текущей
сессии или начните новую.

## Откат

Удалите только две управляемые ссылки и восстановите датированные копии, если
они были созданы. Затем выполните `opencode reload`. Если сервис неисправен,
а не просто перечитывает конфиг, используйте `opencode service restart`.

Синхронизация этих файлов не переносит авторизацию, активные сессии, историю,
логи, базы данных или кэши.

## Git

Перед staging всегда проверьте `git status` и `git diff --cached`, а также
отсутствие секретов. `.gitignore` — только дополнительная защита. Инициализация,
commit, создание private remote и push выполняются отдельно и только явно.
