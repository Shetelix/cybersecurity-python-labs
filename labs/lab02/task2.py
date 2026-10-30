"""Завдання 2 (варіант 8): фільтр та аналізатор журналів DNS-запитів.

Утиліта читає CSV-журнал DNS-транзакцій (Timestamp, ClientIP, Domain,
QueryType), рахує запити за типами, шукає домени з чорного списку,
підозрілі TLD, надто довгі домени/мітки (ознака DNS-тунелювання) та
мітки, схожі на згенеровані алгоритмом (DGA). Підозрілі записи
зберігаються в CSV.
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("lab02.dns")

LAB_DIR = Path(__file__).resolve().parent
DATA_DIR = LAB_DIR / "data" / "data_v08"
DEFAULT_LOG = DATA_DIR / "dns_queries.csv"
DEFAULT_BLACKLIST = DATA_DIR / "blacklist.txt"
DEFAULT_OUT = LAB_DIR / "reports" / "dns_alerts.csv"
DEFAULT_MIN_DOMAIN_LEN = 50

REQUIRED_COLUMNS = ("Timestamp", "ClientIP", "Domain", "QueryType")
QUERY_TYPES = ("A", "AAAA", "TXT", "MX", "CNAME", "NS", "PTR", "SRV")

# Синтаксис доменного імені: мітки з [a-z0-9_-], не починаються і не
# закінчуються дефісом, TLD — лише літери. Довжина міток перевіряється
# окремо, щоб надто довгу мітку показати як аномалію, а не як «сміття».
DOMAIN_RE = re.compile(r"(?:[a-z0-9_](?:[a-z0-9_-]*[a-z0-9])?\.)+[a-z]{2,63}")
IPV4_RE = re.compile(
    r"(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)"
)
# TLD, які часто використовують для фішингу та шкідливих доменів.
SUSPICIOUS_TLD_RE = re.compile(r"\.(zip|mov|top|xyz|tk|ml|gq|cf|click)$")
# Мітка з 25+ символів — типова ознака передачі даних через DNS.
LONG_LABEL_RE = re.compile(r"[a-z0-9_-]{25,}")
# Кандидат у DGA: 12+ символів лише з літер і цифр, серед них 3+ цифри.
DGA_LABEL_RE = re.compile(r"(?=(?:[a-z]*\d){3})[a-z0-9]{12,}")
DGA_ENTROPY_THRESHOLD = 3.5
MAX_LABEL_LEN = 63  # обмеження RFC 1035


@dataclass(frozen=True)
class DnsRecord:
    """Один розібраний запис журналу DNS."""

    line_no: int
    timestamp: datetime
    client_ip: str
    domain: str
    query_type: str


@dataclass
class Finding:
    """Підозрілий запис і перелік причин."""

    record: DnsRecord
    reasons: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Підсумок аналізу журналу."""

    total: int = 0
    skipped: int = 0
    first: datetime | None = None
    last: datetime | None = None
    types: Counter[str] = field(default_factory=Counter)
    findings: list[Finding] = field(default_factory=list)


def shannon_entropy(text: str) -> float:
    """Обчислити ентропію Шеннона рядка (біт на символ)."""
    if not text:
        return 0.0
    counts = Counter(text)
    size = len(text)
    return -sum(n / size * math.log2(n / size) for n in counts.values())


def load_blacklist(path: Path) -> set[str]:
    """Прочитати чорний список доменів (порожні рядки та # пропускаються)."""
    with path.open(encoding="utf-8") as file:
        return {
            line.strip().lower().rstrip(".")
            for line in file
            if line.strip() and not line.lstrip().startswith("#")
        }


def parse_row(line_no: int, row: dict[str, str]) -> DnsRecord:
    """Перетворити рядок CSV на DnsRecord або підняти ValueError."""
    timestamp = datetime.fromisoformat(row["Timestamp"].strip())
    client_ip = row["ClientIP"].strip()
    if not IPV4_RE.fullmatch(client_ip):
        raise ValueError(f"некоректна IP-адреса {client_ip!r}")
    domain = row["Domain"].strip().lower().rstrip(".")
    if len(domain) > 253 or not DOMAIN_RE.fullmatch(domain):
        raise ValueError(f"некоректне доменне ім'я {domain!r}")
    query_type = row["QueryType"].strip().upper()
    if query_type not in QUERY_TYPES:
        raise ValueError(f"невідомий тип запиту {query_type!r}")
    return DnsRecord(line_no, timestamp, client_ip, domain, query_type)


def iter_records(path: Path, result: AnalysisResult) -> Iterator[DnsRecord]:
    """Генератор записів журналу; пошкоджені рядки логуються й пропускаються.

    Генератор читає файл порядково, тому великі журнали не завантажуються
    в пам'ять повністю.
    """
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"у файлі бракує стовпців: {', '.join(sorted(missing))}"
            )
        # Рядок 1 — заголовок, тому записи нумеруються з 2.
        for line_no, row in enumerate(reader, start=2):
            try:
                yield parse_row(line_no, row)
            except (ValueError, KeyError, AttributeError) as exc:
                result.skipped += 1
                logger.warning("Line %d skipped: %s", line_no, exc)


def is_blacklisted(domain: str, blacklist: set[str]) -> bool:
    """Перевірити домен і всі його батьківські домени за чорним списком."""
    labels = domain.split(".")
    return any(
        ".".join(labels[i:]) in blacklist for i in range(len(labels) - 1)
    )


def check_record(
    record: DnsRecord, blacklist: set[str], min_domain_len: int
) -> list[str]:
    """Повернути перелік причин підозрілості запису (порожній — норма)."""
    reasons: list[str] = []
    domain = record.domain
    labels = domain.split(".")

    if is_blacklisted(domain, blacklist):
        reasons.append("BLACKLIST")
    tld = SUSPICIOUS_TLD_RE.search(domain)
    if tld:
        reasons.append(f"SUSPICIOUS_TLD .{tld.group(1)}")
    if len(domain) >= min_domain_len:
        reasons.append(f"LONG_DOMAIN {len(domain)} chars")

    longest = max(labels[:-1], key=len)  # TLD не враховуємо
    if LONG_LABEL_RE.fullmatch(longest):
        reasons.append(f"LONG_LABEL {len(longest)} chars")
    if len(longest) > MAX_LABEL_LEN:
        reasons.append("LABEL_OVER_63 (RFC 1035)")
    for label in labels[:-1]:
        if DGA_LABEL_RE.fullmatch(label):
            entropy = shannon_entropy(label)
            if entropy >= DGA_ENTROPY_THRESHOLD:
                reasons.append(f"DGA entropy={entropy:.2f}")
                break
    return reasons


def analyze(
    log_path: Path, blacklist: set[str], min_domain_len: int
) -> AnalysisResult:
    """Проаналізувати журнал і повернути підсумок."""
    result = AnalysisResult()
    for record in iter_records(log_path, result):
        result.total += 1
        result.types[record.query_type] += 1
        if result.first is None or record.timestamp < result.first:
            result.first = record.timestamp
        if result.last is None or record.timestamp > result.last:
            result.last = record.timestamp
        reasons = check_record(record, blacklist, min_domain_len)
        if reasons:
            result.findings.append(Finding(record, reasons))
    return result


def write_csv(findings: list[Finding], path: Path) -> None:
    """Записати підозрілі запити у CSV (каталог створюється за потреби)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Line",
                "Timestamp",
                "ClientIP",
                "Domain",
                "QueryType",
                "Length",
                "Reasons",
            ]
        )
        for item in findings:
            rec = item.record
            writer.writerow(
                [
                    rec.line_no,
                    rec.timestamp.isoformat(),
                    rec.client_ip,
                    rec.domain,
                    rec.query_type,
                    len(rec.domain),
                    "; ".join(item.reasons),
                ]
            )


def alert_line(item: Finding) -> str:
    """Сформувати рядок тривоги з головним тегом за пріоритетом."""
    rec, reasons = item.record, item.reasons
    joined = ", ".join(reasons)
    if "BLACKLIST" in reasons:
        tag = "[BLACKMATCH]"
        text = f"Client {rec.client_ip} queried blacklisted domain"
    elif any(r.startswith("DGA") for r in reasons):
        tag = "[DGA-DETECT]"
        text = f"High entropy subdomain (Client: {rec.client_ip})"
    elif any(r.startswith(("LONG", "LABEL")) for r in reasons):
        tag = "[TUNNEL]"
        text = (
            f"Abnormally long {rec.query_type} query (Client: {rec.client_ip})"
        )
    else:
        tag = "[SUSP-TLD]"
        text = f"Suspicious TLD (Client: {rec.client_ip})"
    return f"{tag} {text}: {rec.domain}\n    reasons: {joined}"


def display_path(path: Path) -> str:
    """Показати шлях відносно поточного каталогу, якщо це можливо."""
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def print_report(result: AnalysisResult) -> None:
    """Вивести статистику типів і тривоги в консоль."""
    print("\n=== Query Type Breakdown ===")
    for qtype, count in result.types.most_common():
        share = count / result.total * 100
        print(f"{qtype:<5}: {count:>3} ({share:.1f}%)")

    print("\n=== Suspicious DNS Activity ===")
    if not result.findings:
        print("No suspicious queries found.")
    for item in result.findings:
        print(alert_line(item))
    print()


def positive_int(value: str) -> int:
    """Тип argparse: ціле число більше нуля."""
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("значення має бути > 0")
    return number


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Додати аргументи варіанта 8 до парсера."""
    parser.add_argument(
        "--dns-log",
        type=Path,
        default=DEFAULT_LOG,
        help="CSV-журнал DNS-запитів (Timestamp,ClientIP,Domain,QueryType)",
    )
    parser.add_argument(
        "--blacklist",
        type=Path,
        default=DEFAULT_BLACKLIST,
        help="текстовий файл із доменами чорного списку",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=DEFAULT_OUT,
        help="CSV-файл для підозрілих записів",
    )
    parser.add_argument(
        "--min-domain-len",
        type=positive_int,
        default=DEFAULT_MIN_DOMAIN_LEN,
        help="довжина домену, з якої запит вважається підозрілим "
        f"(типово {DEFAULT_MIN_DOMAIN_LEN})",
    )


def run(args: argparse.Namespace) -> int:
    """Запустити аналіз; повернути код завершення (0 — успіх)."""
    for label, path in (
        ("DNS log", args.dns_log),
        ("Blacklist", args.blacklist),
    ):
        if not path.is_file():
            logger.error("%s file not found: %s", label, path)
            return 2
    try:
        blacklist = load_blacklist(args.blacklist)
        logger.info(
            "Loaded %d blacklisted domains from %s",
            len(blacklist),
            display_path(args.blacklist),
        )
        logger.info("Parsing DNS log file %s...", display_path(args.dns_log))
        result = analyze(args.dns_log, blacklist, args.min_domain_len)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        logger.error("Cannot analyze log: %s", exc)
        return 1

    if result.total == 0:
        logger.error("No valid DNS records found")
        return 1
    logger.info(
        "Processed %d DNS query records (%d skipped), %s - %s",
        result.total,
        result.skipped,
        f"{result.first:%Y-%m-%d %H:%M:%S}",
        f"{result.last:%H:%M:%S}",
    )
    print_report(result)

    try:
        write_csv(result.findings, args.out_csv)
    except OSError as exc:
        logger.error("Cannot write report: %s", exc)
        return 1
    if result.findings:
        logger.warning(
            "%d suspicious DNS queries detected", len(result.findings)
        )
    logger.info(
        "Suspicious records exported to %s", display_path(args.out_csv)
    )
    return 0
