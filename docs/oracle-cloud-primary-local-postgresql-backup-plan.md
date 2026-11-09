# Рекомендация: Oracle Cloud как основной сервер, локальный PostgreSQL как резервная копия

С учётом твоих трёх целей я предлагаю **пересмотреть первоначальную рекомендацию и рассматривать Oracle Cloud Always Free как основную инфраструктуру проекта**, включая PostgreSQL 17.

Это будет гораздо интереснее для твоего обучения и технического портфолио, чем размещение только FastAPI на облачной VM.

Ты сможешь продемонстрировать не просто умение запустить приложение в облаке, но и полноценную работу с Cloud Infrastructure: Linux, Docker, PostgreSQL, сетью, безопасностью, миграциями, резервным копированием и восстановлением после сбоев.

При этом я предлагаю разделить две задачи:

- **Основная PostgreSQL на Oracle Cloud** — настоящее рабочее хранилище Wishlist.
- **Локальная PostgreSQL + локальные backup-файлы** — независимый контур восстановления и экспериментирования.

Это реалистичная архитектура для учебного проекта с 411 картами и одним пользователем.

Главное условие: не переносить существующую базу в облако до того, как мы проверим возможность восстановить её из резервной копии.

## 1. Предлагаемая архитектура

**Статус: Proposed — Cloud-primary architecture**

```text
Existing Frontend
www.nadadeneg.com/wishlist/
Static HTML / JavaScript
           |
           | HTTPS REST API
           v
+--------------------------------------+
| Oracle Cloud Always Free             |
| Ampere A1 VM / Linux ARM64           |
|                                      |
|   Caddy (HTTPS reverse proxy)        |
|           |                          |
|           v                          |
|   FastAPI                            |
|   Authentication / Wishlist REST API |
|           |                          |
|           v                          |
|   PostgreSQL 17 — PRIMARY            |
|   Persistent Docker volume           |
+--------------------------------------+
           |
           | Encrypted VPN / Replication / Backup
           v
+--------------------------------------+
| Local Environment                    |
|                                      |
|   PostgreSQL 17                      |
|   Replica / Restore target           |
|                                      |
|   Backup files                       |
|   pg_dump / Retention                |
+--------------------------------------+
```

В этой модели frontend остаётся на существующем хостинге. Переносим только backend и основную базу.

Такой подход также исключает задержку между API и PostgreSQL: оба компонента будут внутри одной Docker-сети на OCI VM.

## 2. Твоя идея синхронизации Oracle → Local вполне реализуема

PostgreSQL 17 поддерживает несколько механизмов, позволяющих поддерживать локальную базу в актуальном состоянии.

Но здесь важно различать **копию базы, реплику базы и резервную копию**. Это три разные вещи.

| Механизм | Что делает | Подходит нам |
|---|---|---|
| `pg_dump` + `pg_restore` | Периодически создаёт полный переносимый снимок | **Да, начать с этого** |
| Logical Replication | Передаёт изменения строк из Oracle в локальную PostgreSQL | **Да, второй этап** |
| Physical Streaming Replication | Поддерживает физическую standby-копию PostgreSQL | Возможно, но сложнее |
| WAL Archiving + PITR | Позволяет восстановиться на определённый момент времени | Позже, для углублённого обучения |

Официальная документация PostgreSQL подтверждает, что logical replication может сначала скопировать существующие таблицы, а затем автоматически передавать изменения практически в реальном времени.

Иными словами, можно сделать именно то, что ты предлагаешь:

```text
Oracle PostgreSQL (Primary)
        |
        | INSERT / UPDATE / DELETE
        v
Local PostgreSQL (Subscriber)
```

Но моя рекомендация — **сначала автоматизированные backups, затем репликация**. Это даст два самостоятельных и проверяемых навыка, не смешивая их в один рискованный эксперимент.

## 3. Как организовать синхронизацию и backup

Я предлагаю двигаться в три этапа, постепенно увеличивая сложность.

### Этап A — Cloud PostgreSQL + локальный backup

Разворачиваем PostgreSQL 17 в OCI, переносим копию данных через `pg_dump` / `pg_restore`, проверяем работу FastAPI и выполняем регулярный `pg_dump` облачной базы на локальный компьютер. Раз в некоторое время восстанавливаем его в отдельную локальную тестовую базу.

**Рекомендую для начала.**

### Этап B — Oracle → Local Logical Replication

Настраиваем `PUBLICATION` на Oracle и `SUBSCRIPTION` локально. Изменения в таблицах автоматически поступают в локальную копию. Локальную базу используем только для чтения и проверки.

Дополнительно изучаем replication lag, replication slots, WAL retention и recovery после обрыва VPN.

### Этап C — Disaster Recovery Exercise

Имитируем отказ Oracle VM, разворачиваем новую PostgreSQL из локального backup и временно подключаем FastAPI к восстановленной базе. Проверяем целостность каталога, `wishlist_items`, количество записей и сохранность notes/quantity.

Это уже полноценное доказательство навыка восстановления сервиса после сбоя.

Есть нюанс: **репликация не заменяет backup**.

Если случайно удалить записи из Oracle PostgreSQL, удаление может автоматически попасть в локальную реплику. Поэтому нужны исторические backup-файлы, которые не перезаписываются при очередной синхронизации.

Для начала я бы выбрал ежедневный `pg_dump -Fc`, хранение 7 ежедневных и 4 еженедельных копий, плюс проверяемый restore. `pg_dump` создаёт согласованный снимок, не останавливая обычные чтения и записи.

При logical replication понадобятся дополнительные меры: DDL и изменения структуры таблиц автоматически не реплицируются, а значения последовательностей `IDENTITY` нужно отдельно учитывать при failover. Если локальный subscriber долго недоступен, replication slot может удерживать WAL на Oracle и переполнить диск.

Также стоит учитывать, что твоя текущая локальная PostgreSQL содержит не только `wishlist_items`, но и полноценную модель импорта, аудита и Cardmarket. Поэтому локальный subscriber лучше создавать как **отдельную базу или отдельный Docker Compose deployment**, не превращая существующую рабочую DB автоматически в target синхронизации.

## 4. А что будет, если Oracle удалит VM?

Здесь важно различать Compute instance и хранилище.

Oracle позволяет сохранять boot volume при обычном завершении VM, а отдельные Block Volumes могут существовать независимо от Compute. Но это не гарантия сохранности данных во всех сценариях reclaim, удаления ресурсов или потери доступа к tenancy.

Для учебного проекта с cloud-primary PostgreSQL я бы использовал отдельный persistent Block Volume под PostgreSQL, если позволяет storage quota.

Например:

| Ресурс | Предлагаемая конфигурация |
|---|---|
| A1 Compute | 2 OCPU, 8 GB RAM |
| Boot volume | 50 GB |
| PostgreSQL block volume | 50 GB |
| Reserved free quota | 100 GB |
| Database | PostgreSQL 17, Docker Compose |
| API | FastAPI + Caddy |

Такой вариант укладывается в опубликованные лимиты **2 OCPU / 12 GB RAM / 200 GB Block Volume** для Always Free tenancy.

Это лишь предложенное распределение ресурсов, а не уже проверенная OCI-конфигурация.

Для дополнительной защиты можно использовать OCI Block Volume Backups: Always Free включает до пяти volume backups, но snapshot работающего диска не заменяет согласованный PostgreSQL backup.

Восстановление должно работать даже в случае, когда исходная Oracle tenancy полностью недоступна.

## 5. Чему ты научишься

Для портфолио эта конфигурация будет особенно полезна тем, что позволит показать работу сразу с несколькими самостоятельными направлениями.

| Направление | Практический результат |
|---|---|
| Oracle OCI | Compute, VCN, Security Lists/NSG, IAM, Block Volumes |
| Linux | SSH, users, permissions, system services |
| Docker | ARM64 images, Docker Compose, persistent volumes |
| PostgreSQL | Remote administration, roles, migrations, backups |
| Backend | FastAPI, authentication, CRUD, REST |
| Networking | HTTPS, DNS, Caddy, private VPN |
| Data Engineering | Logical replication, replication monitoring |
| Recovery | Cloud-to-local restore, failover exercise |
| Documentation | ADR, architecture diagram, evidence, runbook |

И это не искусственное усложнение ради количества технологий. Каждый компонент решает конкретную задачу.

## 6. Что я предлагаю зафиксировать в проекте

Архитектурное решение пока остаётся `Proposed`. Для GitHub Project я бы использовал следующий рабочий блок:

**Issue:** `Evaluate Oracle Cloud Always Free for Wishlist API hosting` / `Evaluate Oracle Cloud Always Free for Primary Application and Database Hosting`

`Type: Research` · `Area: Infrastructure` · `Priority: P0` · `Project phase: M2` · `Risk: High` · `Effort: M` · `Status: In progress`

Критериями завершения будут подтверждённые бесплатные лимиты, проверенный deployment OCI, успешное восстановление облачной копии PostgreSQL локально, отсутствие публичного доступа к `5432`, документированный recovery plan и подтверждение архитектурного решения.

Сам переход с локального PostgreSQL на облачный нужно отслеживать отдельной implementation issue после утверждения архитектуры. Это также потребует пересмотра ранее предложенного Raspberry Pi deployment, а не молчаливой замены уже задокументированного направления.

## Мой итог

- **Oracle Cloud — основной backend и PostgreSQL.**
- **Локально — независимые backups и тестовая PostgreSQL.**
- **Позже — однонаправленная репликация Oracle → Local.**
- **Переход только после успешного восстановления тестовой копии.**

Следующее практическое действие — начать с отдельного, полностью обратимого OCI infrastructure experiment. Мы можем создать VM и пустую PostgreSQL 17, проверить доступ к ней из DBeaver через SSH tunnel или VPN, изучить Block Volumes и выполнить тестовый backup/restore. Только после этого переносить копию существующей базы и переключать API на Oracle.

**Таким образом, Oracle Free Tier станет полноценной учебной облачной площадкой, а не просто бесплатным хостингом.**

---

> **Примечание:** сохранён план из обсуждения от 9 ноября 2026 года. Это предложение архитектуры, а не отчёт о выполненной настройке. Лимиты и условия Oracle Always Free необходимо подтвердить перед развёртыванием. Визуальная схема из чата представлена текстовой диаграммой для удобства чтения в Markdown.
