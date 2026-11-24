"""Wraps site/app.html into a full site/index.html for hosting.

app.html holds the page body (also used for the Claude preview). This adds the
doctype, head and install-as-app tags (manifest, icons, offline support).
Run: python3 scripts/build_site.py
"""
import pathlib

root = pathlib.Path(__file__).resolve().parent.parent / "site"
body = (root / "app.html").read_text()
head = """<!doctype html>
<html lang="en-NZ">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0b5d4b">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icon-192.png">
<link rel="alternate" type="application/rss+xml" title="Puna Pūtea: what's changed" href="feed.xml">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Puna Pūtea">
<script>if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));</script>
</head>
<body>
"""
(root / "index.html").write_text(head + body + "\n</body>\n</html>\n")
print("wrote", root / "index.html")
