"""Допоміжні функції для виведення таблиць у консоль."""


def print_table(headers, rows):
    """Вивести таблицю з вирівнюванням стовпців за найдовшим значенням."""
    table = [[str(cell) for cell in row] for row in rows]
    widths = [len(str(header)) for header in headers]
    for row in table:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    line = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def fmt(cells):
        parts = (
            f" {cell:<{width}} "
            for cell, width in zip(cells, widths, strict=True)
        )
        return "|" + "|".join(parts) + "|"

    print(line)
    print(fmt(headers))
    print(line)
    for row in table:
        print(fmt(row))
    print(line)
