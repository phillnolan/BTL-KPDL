from __future__ import annotations

import csv
from pathlib import Path


STRING_COLUMNS = {"dataset", "split", "video_id", "cube_id"}
NOMINAL_COLUMNS = {"cell_id"}


def convert_csv_to_arff(input_csv: str | Path, output_arff: str | Path, relation: str | None = None) -> Path:
    input_path = Path(input_csv)
    output_path = Path(output_arff)
    if relation is None:
        relation = _safe_relation_name(input_path.stem)

    nominal_values = _collect_nominal_values(input_path)

    with input_path.open("r", newline="", encoding="utf-8") as src:
        reader = csv.DictReader(src)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {input_path}")
        fieldnames = reader.fieldnames

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as dst:
            dst.write(f"@RELATION {_quote_arff(relation)}\n\n")
            for column in fieldnames:
                if column in STRING_COLUMNS:
                    dst.write(f"@ATTRIBUTE {_quote_arff(column)} STRING\n")
                elif column in NOMINAL_COLUMNS:
                    values = nominal_values.get(column) or ["unknown"]
                    joined = ",".join(_quote_arff(value) for value in values)
                    dst.write(f"@ATTRIBUTE {_quote_arff(column)} {{{joined}}}\n")
                else:
                    dst.write(f"@ATTRIBUTE {_quote_arff(column)} NUMERIC\n")

            dst.write("\n@DATA\n")
            for row in reader:
                values = [_format_value(column, row.get(column, "")) for column in fieldnames]
                dst.write(",".join(values) + "\n")

    return output_path


def _collect_nominal_values(input_path: Path) -> dict[str, list[str]]:
    values: dict[str, set[str]] = {column: set() for column in NOMINAL_COLUMNS}
    with input_path.open("r", newline="", encoding="utf-8") as src:
        reader = csv.DictReader(src)
        for row in reader:
            for column in NOMINAL_COLUMNS:
                value = row.get(column)
                if value:
                    values[column].add(value)
    return {column: sorted(items) for column, items in values.items()}


def _format_value(column: str, value: str) -> str:
    if value == "" or value is None:
        return "?"
    if column in STRING_COLUMNS or column in NOMINAL_COLUMNS:
        return _quote_arff(value)
    try:
        float(value)
    except ValueError:
        return "?"
    return value


def _quote_arff(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{text}'"


def _safe_relation_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)
