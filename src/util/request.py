import json
from odoo.http import Response


def json_response(payload, status=200):
    return Response(
        json.dumps(payload, ensure_ascii=False),
        status=status,
        content_type="application/json; charset=utf-8",
    )


def csv_response(content, filename, status=200):
    if isinstance(content, str):
        content = content.encode("utf-8-sig")

    return Response(
        content,
        status=status,
        headers=[
            ("Content-Type", "text/csv; charset=utf-8"),
            ("Content-Disposition", f'attachment; filename="{filename}"'),
        ],
    )
