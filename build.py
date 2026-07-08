#!/usr/bin/env python3
"""Сборка index.html: подставляет base64-картинки и WAV-звуки в game_template.html.

Использование: python3 build.py [--artifact]
  по умолчанию — полный standalone HTML (для GitHub Pages)
  --artifact   — без обёртки <!doctype html> (для публикации как Claude Artifact)

WAV-звуки нужны для iPadOS: WebAudio там глохнет после синтеза речи,
а HTMLAudioElement играет через тот же тракт, что и голос.
"""
import base64
import io
import math
import pathlib
import struct
import sys
import wave

HERE = pathlib.Path(__file__).parent
IMG_DIR = HERE / "img"

MAPPING = {
    "bodo": "bodo_t.png",
    "am": "m_am.png", "zhu": "m_zhu.png", "zub": "m_zub.png",
    "ino": "m_ino.png", "kvak": "m_kvak.png", "krya": "m_kryakrya.png",
    "nos": "m_nos.png", "osya": "m_osya.png", "una": "m_una.png",
    "chupa": "m_chupa.png",
}

SR = 16000


def tone_samples(freq, dur, vol=0.5, shape="tri"):
    """Одна нота с быстрой атакой и экспоненциальным затуханием."""
    n = int(dur * SR)
    for i in range(n):
        t = i / SR
        env = min(1.0, t / 0.012) * math.exp(-3.2 * t / dur)
        if shape == "tri":
            v = 2 * abs(2 * ((t * freq) % 1) - 1) - 1
        else:
            v = math.sin(2 * math.pi * freq * t)
        yield vol * env * v


def silence_samples(dur):
    for _ in range(int(dur * SR)):
        yield 0.0


def make_wav(samples):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
            for s in samples
        )
        w.writeframes(frames)
    return "data:audio/wav;base64," + base64.b64encode(buf.getvalue()).decode()


def seq(*notes):
    """Последовательность нот (freq, dur) подряд."""
    out = []
    for freq, dur in notes:
        out.extend(tone_samples(freq, dur, vol=0.5))
    return out


SOUNDS = {
    "silence": list(silence_samples(0.05)),
    "tap": list(tone_samples(520, 0.1, vol=0.3)),
    "no": list(tone_samples(220, 0.25, vol=0.35, shape="sine")),
    "good": seq((523, 0.14), (659, 0.14), (784, 0.3)),
    "win": seq((523, 0.14), (659, 0.14), (784, 0.14), (1047, 0.18), (784, 0.14), (1047, 0.3)),
    "n0": list(tone_samples(262, 0.35)),
    "n1": list(tone_samples(330, 0.35)),
    "n2": list(tone_samples(392, 0.35)),
    "n3": list(tone_samples(494, 0.35)),
}

html = (HERE / "game_template.html").read_text()
for key, fn in MAPPING.items():
    data = base64.b64encode((IMG_DIR / fn).read_bytes()).decode()
    html = html.replace(f"__IMG_{key}__", f"data:image/png;base64,{data}")
for key, samples in SOUNDS.items():
    html = html.replace(f"__SND_{key}__", make_wav(samples))
assert "__IMG_" not in html, "остался незаменённый плейсхолдер картинки"
assert "__SND_" not in html, "остался незаменённый плейсхолдер звука"

if "--artifact" not in sys.argv:
    html = ('<!DOCTYPE html>\n<html lang="ru">\n<head>\n'
            + html.replace("</style>\n", "</style>\n</head>\n<body>\n", 1)
            + "\n</body>\n</html>\n")

out = HERE / ("artifact.html" if "--artifact" in sys.argv else "index.html")
out.write_text(html)
print(f"OK {out.name}: {len(html)//1024} KB")
