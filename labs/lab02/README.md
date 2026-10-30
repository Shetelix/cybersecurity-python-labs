# Лабораторна робота №2 — консольні утиліти для задач кібербезпеки

Студент: Шетеля Дмитро Максимович, група КБ-209, варіант 23.
У методичці 15 варіантів даних, тому номер береться циклічно:
`(23 - 1) % 15 + 1 = 8` (див. `shared/student.py`).

**Варіант 8 — фільтр та аналізатор журналів DNS-запитів.**

## Встановлення

З кореня репозиторію, в активованому віртуальному середовищі з ЛР №1:

```powershell
.venv\Scripts\Activate.ps1          # Windows PowerShell
python -m pip install -r requirements.txt
```

Сторонніх бібліотек програма не використовує (лише стандартна бібліотека
Python 3.10+); `ruff` потрібен для перевірки коду.

## Структура

```
labs/lab02/
├── __init__.py
├── main.py          # підкоманди demo та analyze
├── task1.py         # User, Admin, Session, AuditRecord, AuditLog, UserAccount
├── task2.py         # аналізатор DNS-журналів (варіант 8)
├── README.md
└── data/
    └── data_v08/            # каталог з lab2_data.zip без змін
        ├── dns_queries.csv  # журнал: Timestamp,ClientIP,Domain,QueryType
        └── blacklist.txt    # чорний список доменів, по одному в рядку
```

Звіт аналізатора записується в `labs/lab02/reports/dns_alerts.csv`
(каталог створюється автоматично і не потрапляє в Git).

## Запуск

Завдання 1 — демонстрація класів:

```powershell
python -m labs.lab02.main demo
```

Завдання 2 — аналіз журналу (усі аргументи мають типові значення):

```powershell
python -m labs.lab02.main analyze
python -m labs.lab02.main analyze `
    --dns-log labs/lab02/data/data_v08/dns_queries.csv `
    --blacklist labs/lab02/data/data_v08/blacklist.txt `
    --out-csv labs/lab02/reports/dns_alerts.csv `
    --min-domain-len 50
```

## Параметри CLI (`analyze`)

| Параметр | Типово | Опис |
|---|---|---|
| `--dns-log` | `data/data_v08/dns_queries.csv` | CSV-журнал DNS-запитів |
| `--blacklist` | `data/data_v08/blacklist.txt` | чорний список доменів |
| `--out-csv` | `reports/dns_alerts.csv` | файл для підозрілих записів |
| `--min-domain-len` | `50` | довжина домену, з якої запит підозрілий (ціле > 0) |

## Що вважається підозрілим

* `BLACKLIST` — домен або його батьківський домен є у чорному списку;
* `SUSPICIOUS_TLD` — зона `.zip`, `.mov`, `.top`, `.xyz`, `.tk` тощо;
* `LONG_DOMAIN` — довжина домену ≥ `--min-domain-len`;
* `LONG_LABEL` / `LABEL_OVER_63` — мітка з 25+ символів (ознака
  DNS-тунелювання) або довша за 63 символи (порушення RFC 1035);
* `DGA` — мітка з 12+ латинських літер і цифр (3+ цифри) з ентропією
  Шеннона ≥ 3,5 біт/символ.

## Поведінка при помилках

* файл журналу або чорного списку не знайдено — `[ERROR]`, код виходу 2;
* у CSV бракує стовпців або файл не читається — `[ERROR]`, код 1;
* окремий пошкоджений рядок (дата, IP, домен, тип запиту) — `[WARNING]`
  з номером рядка, рядок пропускається, аналіз триває;
* `--min-domain-len 0` або не число — помилка argparse, код 2.
