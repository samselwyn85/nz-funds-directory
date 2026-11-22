"""Wraps site/app.html into a full site/index.html for hosting.

app.html holds the page body (also used for the Claude preview). This adds the
doctype, head, install-as-app tags (manifest, icons, offline support) and an
optional config line, e.g. the Buttondown username:
    BUTTONDOWN_USER=punaputea python3 scripts/build_site.py
"""
import json, os, pathlib

root = pathlib.Path(__file__).resolve().parent.parent / "site"
body = (root / "app.html").read_text()
cfg = {"buttondownUser": os.environ.get("BUTTONDOWN_USER", "")}

# Paddle checkout (Apple Pay, PayPal and cards in one overlay). Set these as
# GitHub repo variables once the Paddle account is approved:
#   PADDLE_CLIENT_TOKEN  client-side token (starts live_ or test_)
#   PADDLE_PRICES        JSON, e.g. {"alerts-m":"pri_...","alerts-y":"pri_...","writer-m":"pri_...","writer-y":"pri_..."}
paddle_token = os.environ.get("PADDLE_CLIENT_TOKEN", "")
paddle_prices = os.environ.get("PADDLE_PRICES", "{}")
paddle = ""
if paddle_token:
    env = "sandbox" if paddle_token.startswith("test_") else "production"
    paddle = f"""<script src="https://cdn.paddle.com/paddle/v2/paddle.js"></script>
<script>
(function(){{
  var prices = {paddle_prices};
  if ("{env}" === "sandbox") Paddle.Environment.set("sandbox");
  Paddle.Initialize({{ token: "{paddle_token}" }});
  window.PUNA_CONFIG.checkout = function(plan, yearly){{
    var id = prices[plan + (yearly ? "-y" : "-m")];
    if (!id) return;
    Paddle.Checkout.open({{ items: [{{ priceId: id, quantity: 1 }}], settings: {{ displayMode: "overlay", locale: "en", successUrl: location.origin + location.pathname + "#alerts" }} }});
  }};
}})();
</script>
"""
head = f"""<!doctype html>
<html lang="en-NZ">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d6b57">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Puna Pūtea">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<script>window.PUNA_CONFIG={json.dumps(cfg)};
if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {{}}));</script>
{paddle}</head>
<body>
"""
(root / "index.html").write_text(head + body + "\n</body>\n</html>\n")
print("wrote", root / "index.html")
