#!/usr/bin/env python3
"""Сборка index.html: подставляет base64-картинки в game_template.html.

Использование: python3 build.py [--artifact]
  по умолчанию — полный standalone HTML (для GitHub Pages)
  --artifact   — без обёртки <!doctype html> (для публикации как Claude Artifact)
"""
import base64
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
IMG_DIR = HERE / "img"

MAPPING = {
    "bodo": "bodo_t.png",
    "am": "m_am.png", "zhu": "m_zhu.png", "zub": "m_zub.png",
    "ino": "m_ino.png", "kvak": "m_kvak.png", "krya": "m_kryakrya.png",
    "nos": "m_nos.png", "osya": "m_osya.png", "una": "m_una.png",
    "chupa": "m_chupa.png",
}

html = (HERE / "game_template.html").read_text()
for key, fn in MAPPING.items():
    data = base64.b64encode((IMG_DIR / fn).read_bytes()).decode()
    html = html.replace(f"__IMG_{key}__", f"data:image/png;base64,{data}")
assert "__IMG_" not in html, "остался незаменённый плейсхолдер"

if "--artifact" not in sys.argv:
    html = ('<!DOCTYPE html>\n<html lang="ru">\n<head>\n'
            + html.replace("</style>\n", "</style>\n</head>\n<body>\n", 1)
            + "\n</body>\n</html>\n")

out = HERE / ("artifact.html" if "--artifact" in sys.argv else "index.html")
out.write_text(html)
print(f"OK {out.name}: {len(html)//1024} KB")
