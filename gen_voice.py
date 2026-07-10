#!/usr/bin/env python3
"""Генерация живой озвучки для игры (Microsoft Edge TTS, нейроголос).

Создаёт snd/<md5>.mp3 для каждой фразы и snd/voice_map.json (фраза → файл).
Файлы генерируются инкрементально: существующие не перегенерируются.
Смена голоса: python3 gen_voice.py --voice ru-RU-SvetlanaNeural (и удалить snd/*.mp3)
"""
import asyncio
import hashlib
import json
import pathlib
import re
import sys

import edge_tts

VOICE = "ru-RU-DmitryNeural"
RATE = "-8%"
if "--voice" in sys.argv:
    VOICE = sys.argv[sys.argv.index("--voice") + 1]

HERE = pathlib.Path(__file__).parent
OUT = HERE / "snd"
OUT.mkdir(exist_ok=True)

# --- данные из игры (держать в синхроне с game_template.html!) ---
NAMES = ["Ам", "Жу", "Зуб", "Ино", "Квак", "КряКря", "Нос", "Ося", "Уна", "Чупа"]
LET = list("АБВГДЕЖЗИКЛМНОПРСТУ")
WORDS3 = ["ДОМ", "СОК", "КОТ", "НОС", "ЖУК", "ЛУК", "МАК", "КИТ", "СЫР", "СОН", "ЛЕС", "РАК", "ДЫМ", "БОК"]
WORDS4 = ["РЫБА", "ЛУНА", "РОЗА", "ГОРА", "КАША", "ЗИМА", "НЕБО", "ЛАПА"]
PRAISE = ["Молодец!", "Умница!", "Правильно!", "Здорово!", "Супер!", "Отлично!"]

# фраза-ключ (ровно как в коде игры) -> текст для синтеза (None = совпадает)
phrases: dict[str, str | None] = {}


def add(key, tts=None):
    phrases[key] = tts


for p in PRAISE:
    add(p)
add("Ура! Ты победил! Ты настоящий молодец!")
add("Привет! Я Бо́до Бородо́! Поиграем?")

# инструкции игр
add("Найди одинаковые карточки. Где спрятались пары?")
add("Посмотри внимательно. Три морфика одинаковые, а один — другой. Кто лишний?")
add("Посмотри на тёмную тень. Кто из морфиков там спрятался?")
add("Посмотри на ряд. Морфики чередуются. Кто должен стоять следующим?")
add("Нажми на имя, а потом на морфика, которого так зовут!")
add("Расставь морфиков так, чтобы в каждой строке и каждом столбике никто не повторялся! Сначала выбери морфика внизу.")
add("Веди Бо́до пальцем по дорожкам лабиринта к морфику!")
add("Посмотри внимательно и запомни, кто стоит на полянке!")
add("Запомни, кто на полянке!")
add("Кто-то спрятался! Кого не хватает на полянке?")
add("Кого не хватает?")
add("Перетаскивай кусочки на картинку, чтобы собрать её целиком!")
add("Ой! Не тот морфик. Смотри ещё раз и повторяй!")
add("Ой! Смотри ещё раз!")
add("Смотри внимательно, кто прыгает, и запоминай порядок!")
add("Теперь ты! Нажимай на морфиков в том же порядке!")
add("Теперь ты!")
add("Посчитай! На какой полянке морфиков больше? Нажми на неё!")
add("Посчитай! На какой полянке морфиков меньше? Нажми на неё!")
add("Где морфиков больше?")
add("Где морфиков меньше?")
add("Разложи стрелки по порядку, а потом нажми Пуск! Бодо пойдёт по твоей программе к морфику!")
add("Разложи стрелки и нажми Пуск! Помоги Бодо дойти до морфика!")
add("Сначала разложи стрелки!")
add("Почти! Попробуй ещё!")
add("Ой! Там не пройти!")
add("Ой! Там край поля!")

# имена морфиков
for n in NAMES:
    add(n, n + "!")

# буквы
for ch in LET:
    add("Лови букву " + ch + "!")
    add("Лови букву " + ch + "! Двигай Бо́до пальцем!")
    add("Собери слово! Лови букву " + ch + "!")

# слова (капс в ключе, Тайтл в синтезе — иначе читается по буквам)
for w in WORDS3 + WORDS4:
    add(w + "! Молодец!", w.title() + "! Молодец!")
    add("Лови буквы по порядку и собери слово " + w + "!",
        "Лови буквы по порядку и собери слово " + w.title() + "!")

# числа для «Кого больше?» (пары с разницей 1..3 в пределах 2..8)
for a in range(2, 9):
    for b in range(2, 9):
        if a != b and abs(a - b) <= 3:
            add(f"{a} и {b}!")


def tts_input(key, custom):
    t = custom if custom is not None else key
    t = re.sub(r"([Мм])орфик", "\\1о́рфик", t)
    t = t.replace("Бодо Бородо", "Бо́до Бородо́")
    t = re.sub(r"(?<!о́)(?<!о)Бодо", "Бо́до", t)
    t = t.replace("полянк", "поля́нк")
    return t


async def gen():
    mapping = {}
    todo = []
    for key, custom in phrases.items():
        h = hashlib.md5((VOICE + "|" + tts_input(key, custom)).encode()).hexdigest()[:12]
        fn = f"{h}.mp3"
        mapping[key] = "snd/" + fn
        path = OUT / fn
        if not path.exists():
            todo.append((key, custom, path))
    print(f"фраз: {len(phrases)}, генерировать: {len(todo)}")

    sem = asyncio.Semaphore(4)

    async def one(key, custom, path):
        async with sem:
            text = tts_input(key, custom)
            for attempt in range(3):
                try:
                    tts = edge_tts.Communicate(text, VOICE, rate=RATE)
                    await tts.save(str(path))
                    return
                except Exception as e:
                    if attempt == 2:
                        print("FAIL:", key, e)
                    await asyncio.sleep(1 + attempt)

    await asyncio.gather(*(one(*t) for t in todo))
    (OUT / "voice_map.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=0), encoding="utf-8")
    total = sum(f.stat().st_size for f in OUT.glob("*.mp3"))
    print(f"OK: {len(list(OUT.glob('*.mp3')))} файлов, {total//1024} KB")


asyncio.run(gen())
