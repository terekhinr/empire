#!/usr/bin/env python3
"""Сборка раздаточных HTML для user01–20 + общая инструкция Hiddify.

Выход:
  /root/empire-secrets/profiles/dist/userNN.html  (один файл на человека)
  /root/empire-secrets/profiles/dist/guide/       (инструкция с картинками)
  /var/www/vpn-dl/dist/                          (копия для выдачи по HTTPS)
"""
from __future__ import annotations

import base64
import html
import io
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/root/projects/empire")
PROFILES = Path("/root/empire-secrets/profiles")
SECRETS_CDN = Path("/root/empire-secrets/cdn-kalitka")
DIST = PROFILES / "dist"
GUIDE = DIST / "guide"
WWW = Path("/var/www/vpn-dl/dist")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def qr_data_uri(text: str, box: int = 6) -> str:
    img = qrcode.make(text, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def make_step_image(step: int, title: str, lines: list[str], accent: str = "#C45C26") -> Image.Image:
    """Простая иллюстрация шага (телефон + карточка), без чужих скриншотов."""
    w, h = 900, 560
    img = Image.new("RGB", (w, h), "#1A1512")
    d = ImageDraw.Draw(img)

    # soft panel
    d.rounded_rectangle((40, 40, w - 40, h - 40), radius=28, fill="#241E1A")
    # phone frame
    d.rounded_rectangle((70, 70, 340, 490), radius=36, fill="#0E0C0B", outline="#3A322C", width=3)
    d.rounded_rectangle((95, 110, 315, 450), radius=18, fill="#2A2320")
    d.ellipse((185, 82, 225, 92), fill="#3A322C")  # speaker

    # accent bar on phone
    d.rounded_rectangle((110, 140, 300, 190), radius=12, fill=accent)
    d.text((125, 152), "Hiddify", font=_font(22, True), fill="#FFF8F2")

    # fake list rows
    y = 210
    for i, label in enumerate(["Авто (urltest)", "CDN", "VDSina", "Aeza", "STO1"]):
        fill = accent if i == 0 else "#3A322C"
        row_h = 36
        d.rounded_rectangle((110, y, 300, y + row_h), radius=9, fill=fill)
        d.text((124, y + 8), label, font=_font(15, i == 0), fill="#FFF8F2")
        y += row_h + 8

    # step badge + text
    d.ellipse((400, 80, 470, 150), fill=accent)
    d.text((418, 98), str(step), font=_font(36, True), fill="#FFF8F2")
    d.text((490, 95), title, font=_font(32, True), fill="#FFF8F2")

    ty = 170
    for line in lines:
        d.text((400, ty), line, font=_font(22), fill="#E8DCD2")
        ty += 36

    d.text((400, 480), "kalitkuprikroy · Empire VPN", font=_font(16), fill="#8A7A70")
    return img


def build_guide_images() -> dict[str, str]:
    """Рисует шаги и возвращает {name: relative path}."""
    GUIDE.mkdir(parents=True, exist_ok=True)
    specs = [
        (
            1,
            "Установите Hiddify",
            [
                "App Store или Google Play:",
                "найдите «Hiddify».",
                "Откройте приложение.",
            ],
        ),
        (
            2,
            "Добавьте подписку",
            [
                "Скопируйте свою ссылку",
                "из персонального файла.",
                "В Hiddify: «+» → из буфера.",
            ],
        ),
        (
            3,
            "Режим Авто",
            [
                "Выберите группу Авто / urltest.",
                "Не переключайте ноды руками —",
                "клиент сам уйдёт на живую.",
            ],
        ),
        (
            4,
            "Включите VPN",
            [
                "IPv6 → Disable.",
                "DNS → https://1.1.1.1/dns-query",
                "Режим VPN/TUN, не только Proxy.",
                "Перезапустите Telegram.",
            ],
        ),
    ]
    rel: dict[str, str] = {}
    for step, title, lines in specs:
        name = f"step-{step}.png"
        save_png(make_step_image(step, title, lines), GUIDE / name)
        rel[f"step{step}"] = name
    return rel


GUIDE_CSS = """
:root {
  --bg: #14110f;
  --panel: #1f1a17;
  --text: #f3ebe4;
  --muted: #b5a79c;
  --accent: #c45c26;
  --line: #3a322c;
  --ok: #3d8b6e;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  background:
    radial-gradient(900px 500px at 10% -10%, #3a2218 0%, transparent 55%),
    radial-gradient(700px 400px at 100% 0%, #1c2a28 0%, transparent 50%),
    var(--bg);
  color: var(--text);
  line-height: 1.55;
}
.wrap { max-width: 820px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
header h1 {
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  margin: 0 0 .4rem;
  letter-spacing: -0.02em;
}
header p { color: var(--muted); margin: 0 0 1.5rem; max-width: 40rem; }
.badge {
  display: inline-block;
  background: color-mix(in srgb, var(--accent) 22%, transparent);
  color: #ffd7c2;
  border: 1px solid color-mix(in srgb, var(--accent) 55%, transparent);
  border-radius: 999px;
  padding: .2rem .75rem;
  font-size: .85rem;
  margin-bottom: 1rem;
}
.step {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 1.25rem;
  margin: 1.25rem 0;
}
.step img {
  width: 100%;
  height: auto;
  border-radius: 14px;
  margin-top: .85rem;
  display: block;
}
.step h2 { margin: 0 0 .35rem; font-size: 1.25rem; }
.step .n {
  color: var(--accent);
  font-weight: 700;
  margin-right: .35rem;
}
ol.tips { color: var(--muted); padding-left: 1.2rem; }
code, .mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .92em;
}
footer { margin-top: 2.5rem; color: var(--muted); font-size: .9rem; }
a { color: #ffb089; }
"""


def write_guide(images: dict[str, str]) -> None:
    body = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Как включить VPN на телефоне</title>
<style>{GUIDE_CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="badge">Hiddify · iPhone / Android</div>
    <h1>Как настроить VPN за 4 шага</h1>
    <p>Одна подписка = несколько серверов. Клиент сам выбирает живой.
       Вам не нужно ничего переключать вручную.</p>
  </header>

  <section class="step">
    <h2><span class="n">1.</span> Установите Hiddify</h2>
    <p>В App Store или Google Play найдите <strong>Hiddify</strong> и установите.
       Это приложение, которое умеет автоматически переключаться между серверами.</p>
    <img src="{html.escape(images['step1'])}" alt="Шаг 1: установка Hiddify"/>
  </section>

  <section class="step">
    <h2><span class="n">2.</span> Добавьте свою подписку</h2>
    <p>Откройте персональный файл (или ссылку), которую вам прислали.
       Скопируйте <strong>ссылку подписки</strong> → в Hiddify нажмите <strong>+</strong> →
       «Добавить из буфера» / Subscribe.</p>
    <p>Либо отсканируйте QR-код из вашего файла — так ещё проще.</p>
    <img src="{html.escape(images['step2'])}" alt="Шаг 2: добавить подписку"/>
  </section>

  <section class="step">
    <h2><span class="n">3.</span> Режим «Авто»</h2>
    <p>Выберите профиль / группу <strong>Авто</strong> (urltest). Не выбирайте отдельные
       серверы вручную: внутри уже CDN + несколько Reality-нод.</p>
    <img src="{html.escape(images['step3'])}" alt="Шаг 3: режим Авто"/>
  </section>

  <section class="step">
    <h2><span class="n">4.</span> Включите VPN и проверьте</h2>
    <ol class="tips">
      <li>Настройки Hiddify: <strong>IPv6 → Disable</strong></li>
      <li>DNS: Remote = <span class="mono">https://1.1.1.1/dns-query</span></li>
      <li>Режим <strong>VPN / TUN</strong> (не только Proxy)</li>
      <li>Включите тумблер VPN</li>
      <li>Полностью закройте Telegram и откройте снова</li>
      <li>Откройте YouTube — должно работать</li>
    </ol>
    <img src="{html.escape(images['step4'])}" alt="Шаг 4: включить VPN"/>
  </section>

  <section class="step">
    <h2>Если не подключается</h2>
    <ol class="tips">
      <li>Обновите подписку в Hiddify (pull-to-refresh / обновить)</li>
      <li>Переключите Wi‑Fi ↔ мобильный интернет</li>
      <li>Напишите тому, кто выдал доступ — укажите свой номер user (например user07)</li>
    </ol>
  </section>

  <footer>
    Инструкция общая. Персональная ссылка — только в вашем файле userNN.html.
    Обновлено {datetime.now(timezone.utc).strftime("%Y-%m-%d")} UTC.
  </footer>
</div>
</body>
</html>
"""
    (GUIDE / "index.html").write_text(body, encoding="utf-8")


USER_CSS = """
:root {
  --bg: #14110f; --panel: #1f1a17; --text: #f3ebe4; --muted: #b5a79c;
  --accent: #c45c26; --line: #3a322c; --card: #2a2320;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.5;
}
.wrap { max-width: 720px; margin: 0 auto; padding: 1.5rem 1rem 3rem; }
h1 { font-size: 1.75rem; margin: 0 0 .25rem; }
.sub { color: var(--muted); margin: 0 0 1.25rem; }
.card {
  background: var(--panel); border: 1px solid var(--line);
  border-radius: 16px; padding: 1.1rem 1.2rem; margin: 1rem 0;
}
.card h2 { margin: 0 0 .6rem; font-size: 1.1rem; }
.qr { display: block; width: min(240px, 70vw); height: auto; margin: .75rem auto;
  background: #fff; padding: 10px; border-radius: 12px; }
.btn {
  display: inline-block; margin: .35rem .35rem .35rem 0; padding: .65rem 1rem;
  background: var(--accent); color: #fff8f2; text-decoration: none;
  border-radius: 10px; font-weight: 600;
}
.btn.secondary { background: transparent; border: 1px solid var(--line); color: var(--text); }
.linkbox {
  word-break: break-all; background: var(--card); border-radius: 10px;
  padding: .75rem; font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: .8rem; color: #ffd7c2;
}
ol { color: var(--muted); }
.nodes { list-style: none; padding: 0; margin: 0; }
.nodes li {
  background: var(--card); border-radius: 10px; padding: .65rem .8rem; margin: .4rem 0;
  font-size: .92rem;
}
.nodes .tag { color: var(--accent); font-weight: 700; margin-right: .4rem; }
.nodes code { font-size: .75rem; color: var(--muted); word-break: break-all; }
.warning { color: #e8b4a0; font-size: .9rem; }
"""


def node_label(name: str) -> str:
    n = name.lower()
    if "cf" in n or "cdn" in n:
        return "CDN (Cloudflare) — если режут IP серверов"
    if "vdsina" in n:
        return "VDSina — быстрый Reality"
    if "aeza" in n:
        return "Aeza — быстрый Reality"
    if "sto1" in n or "justhost" in n:
        return "JustHost Stockholm — быстрый Reality"
    return name


def build_user_html(user: str, sub_url: str, json_url: str, links: list[str], guide_href: str) -> str:
    qr_sub = qr_data_uri(sub_url)
    nodes_html = []
    for i, link in enumerate(links, 1):
        name = link.split("#")[-1] if "#" in link else f"node{i}"
        host = link.split("@", 1)[1].split("?", 1)[0] if "@" in link else ""
        nodes_html.append(
            f'<li><span class="tag">{i}.</span>{html.escape(node_label(name))}'
            f'<br/><code>{html.escape(host)}</code></li>'
        )
    links_block = "\n".join(html.escape(l) for l in links)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>VPN {html.escape(user)}</title>
<style>{USER_CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>Ваш доступ · {html.escape(user)}</h1>
  <p class="sub">Одна подписка содержит все серверы. В Hiddify включите режим Авто — переключать ничего не нужно.</p>

  <div class="card">
    <h2>1. Отсканируйте QR в Hiddify</h2>
    <img class="qr" src="{qr_sub}" alt="QR подписки {html.escape(user)}"/>
    <p style="text-align:center;color:var(--muted);font-size:.9rem">или нажмите кнопку ниже</p>
    <p style="text-align:center">
      <a class="btn" href="{html.escape(sub_url)}">Открыть подписку</a>
      <a class="btn secondary" href="{html.escape(json_url)}">JSON (urltest)</a>
    </p>
    <div class="linkbox">{html.escape(sub_url)}</div>
  </div>

  <div class="card">
    <h2>2. Что внутри (не надо выбирать вручную)</h2>
    <ul class="nodes">
      {''.join(nodes_html)}
    </ul>
  </div>

  <div class="card">
    <h2>3. Короткая настройка</h2>
    <ol>
      <li>Установите <strong>Hiddify</strong></li>
      <li>Импортируйте подписку (QR или ссылка)</li>
      <li>Режим <strong>Авто</strong> → включите VPN/TUN</li>
      <li>IPv6 Disable · DNS <code>https://1.1.1.1/dns-query</code></li>
      <li>Перезапустите Telegram · проверьте YouTube</li>
    </ol>
    <p><a class="btn secondary" href="{html.escape(guide_href)}">Полная инструкция с картинками</a></p>
  </div>

  <div class="card">
    <h2>Запасной вариант — все ссылки текстом</h2>
    <p class="warning">Нужен только если подписка не импортируется. Обычно хватает QR выше.</p>
    <div class="linkbox">{links_block}</div>
  </div>
</div>
</body>
</html>
"""


def main() -> None:
    meta = json.loads((SECRETS_CDN / "sub-meta.json").read_text(encoding="utf-8"))
    base = meta["base"].rstrip("/")
    DIST.mkdir(parents=True, exist_ok=True)
    images = build_guide_images()
    write_guide(images)

    index_rows = []
    for i in range(1, 21):
        user = f"user{i:02d}"
        txt = PROFILES / f"{user}.txt"
        links = [l.strip() for l in txt.read_text(encoding="utf-8").splitlines() if l.startswith("vless://")]
        if len(links) < 2:
            raise SystemExit(f"{user}: мало ссылок ({len(links)})")
        sub_url = f"{base}/{user}"
        json_url = f"{base}/{user}.json"
        # relative guide from dist/userNN.html -> guide/index.html
        page = build_user_html(user, sub_url, json_url, links, guide_href="guide/index.html")
        out = DIST / f"{user}.html"
        out.write_text(page, encoding="utf-8")
        out.chmod(0o600)
        index_rows.append(f'<li><a href="{user}.html">{user}</a> — {len(links)} сервера</li>')

    index = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Раздача VPN user01–20</title><style>{USER_CSS}</style></head>
<body><div class="wrap">
<h1>Раздача · 20 пользователей</h1>
<p class="sub">Каждый файл — один человек. Шлите только его HTML (или ссылку на него).</p>
<div class="card"><p><a class="btn" href="guide/index.html">Общая инструкция с картинками</a></p>
<ul>{''.join(index_rows)}</ul></div>
</div></body></html>
"""
    (DIST / "index.html").write_text(index, encoding="utf-8")
    (DIST / "index.html").chmod(0o600)

    # publish to www
    if WWW.exists():
        shutil.rmtree(WWW)
    shutil.copytree(DIST, WWW)
    for p in WWW.rglob("*"):
        if p.is_file():
            p.chmod(0o644)
    print(f"built {DIST}")
    print(f"published {WWW}")
    print(f"users 20 · guide steps {sorted(images)}")


if __name__ == "__main__":
    main()
