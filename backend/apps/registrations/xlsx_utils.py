import csv
import io

import openpyxl


def parse_rows(upload):
    """
    Parse an uploaded CSV or XLSX file into a list of {lowercased_header:
    stripped_value} dicts, one per non-blank data row. Shared by the
    admin individual bulk-upload view and the public batch-registration
    upload — header/row handling (case-insensitive headers, skipping
    fully-blank rows) is identical between the two.
    """

    filename = (upload.name or "").lower()

    if filename.endswith(".csv"):
        text = upload.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader]

    workbook = openpyxl.load_workbook(upload, data_only=True)
    sheet = workbook.active

    rows_iter = sheet.iter_rows(values_only=True)
    headers = [str(h or "").strip().lower() for h in next(rows_iter)]

    rows = []
    for values in rows_iter:
        if all(v in (None, "") for v in values):
            continue
        row = {headers[i]: ("" if v is None else str(v).strip()) for i, v in enumerate(values) if i < len(headers)}
        rows.append(row)

    return rows
