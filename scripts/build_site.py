"""Wraps site/app.html into a full site/index.html for hosting.

app.html holds the page body (also used for the Claude preview). This adds the
doctype, head and an optional config line, e.g. the Buttondown username:
    BUTTONDOWN_USER=punaputea python3 scripts/build_site.py
"""
import json, os, pathlib

root = pathlib.Path(__file__).resolve().parent.parent / "site"
body = (root / "app.html").read_text()
cfg = {"buttondownUser": os.environ.get("BUTTONDOWN_USER", "")}
html = (
    "<!doctype html>\n<html lang=\"en-NZ\">\n<head>\n<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
    f"<script>window.PUNA_CONFIG={json.dumps(cfg)};</script>\n</head>\n<body>\n"
    + body + "\n</body>\n</html>\n"
)
(root / "index.html").write_text(html)
print("wrote", root / "index.html")
