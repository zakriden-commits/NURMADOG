# NURMADOG — пробные 2D-мультфильмы

## «Вмешаться» — серия 1, переработка

[**Открыть переработанную серию**](videos/vmeshat_sya_episode_01_reworked.mp4) — вертикальный ролик 9:16, 1080 × 1920, 24 кадра/с, 60 секунд, MP4 (H.264 + AAC). История содержит неграфическую сцену домашнего насилия. [Первоначальная версия](videos/vmeshat_sya_episode_01.mp4) сохранена для сравнения.

Это рисованная векторная 2D-анимация: персонажи и окружение составлены из созданных вручную контуров, ключевые позы и монтаж расставлены вручную, промежуточные кадры рассчитываются программно. Это **не** анимация фотографий, слайд-шоу или использование готовых 3D-моделей. Герой показан в полный рост; добавлены профиль и три четверти, новые жесты и реакции, световые переходы и звук. Движения остаются стилизованными, а не снятыми с живых актёров.

Герой, мужчина и женщина озвучены разными выбранными голосами. Для атмосферы и событий добавлены ночной двор, шаги, скрип качелей, стук, хлопок и разбивающаяся дверь; есть русские субтитры. Образ героя: [в полный рост](characters/hero_full_body.png) и [портрет](characters/hero_golden_hair.png). Доступны [сценарий и таймкоды](series/vmeshat_sya/script_reworked.md), [первый набор реплик](series/vmeshat_sya/voices/) и [новые дубли](series/vmeshat_sya/voices_v2/). ID голосов и примеры сохранены в [voices.json](series/vmeshat_sya/voices.json); возможность применения ID в другом сеансе зависит от системы озвучки.

Звуки ночи и города: “Oculus Audio Pack 01” by Oculus VR, LLC ([источник](https://developers.meta.com/vr/downloads/package/oculus-audio-pack-1/)), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); файлы переименованы и перекодированы источником, затем обрезаны, сведены и изменены по громкости для ролика. Другие звуковые эффекты: [Kenney](https://kenney.nl), CC0. Подробности — [ATTRIBUTION.txt](series/vmeshat_sya/sounds/ATTRIBUTION.txt).

## Предыдущий вариант: современный комикс для Shorts

[**Открыть видео 06_modern_comic_shorts.mp4**](videos/06_modern_comic_shorts.mp4) — вертикальный ролик 9:16, 1080 × 1920, 30 кадров/с, 10 секунд, MP4 (H.264 + AAC).

История прежняя: герою звонит полиция, машина подъезжает к дому, герой выходит на порог и полицейские его задерживают. Добавлены крупный план, мимика, повороты головы и корпуса, движения рук и ног, открывание двери, вращение колёс и свет мигалок. Есть музыка, звуковые эффекты и титры; **голосовой озвучки нет**.

Это стилизованная, вручную составленная из векторных элементов 2D-анимация, а не фотореалистичный motion capture. Каждый кадр рассчитывается заново: фотографии и готовые изображения не анимируются. В новой версии векторные сцены рендерит движок [resvg](https://github.com/linebender/resvg).

## Первые пять вариантов

| № | Стиль | Видео |
|---|---|---|
| 1 | Солнечный мульт | [01_sunny_cartoon.mp4](videos/01_sunny_cartoon.mp4) |
| 2 | Комикс-детектив | [02_detective_comic.mp4](videos/02_detective_comic.mp4) |
| 3 | Неоновая ночь | [03_neon_night.mp4](videos/03_neon_night.mp4) |
| 4 | Бумажный театр | [04_paper_theater.mp4](videos/04_paper_theater.mp4) |
| 5 | Пиксельное приключение | [05_pixel_adventure.mp4](videos/05_pixel_adventure.mp4) |

Ранние варианты — по 10 секунд, 1280 × 720, 25 кадров/с, созданы в Pygame/SDL. Для сравнения есть [страница с плеерами](index.html); [архив](videos/five_styles.zip) содержит именно первые пять роликов.

Звуки шагов, двери и металла в новом ролике: [Kenney](https://kenney.nl), лицензия CC0 1.0. Подробнее — [animation/sounds/ATTRIBUTION.txt](animation/sounds/ATTRIBUTION.txt). Остальная музыка и эффекты созданы программно.

## Повторный рендер

Нужен Python 3.11+ и шрифты DejaVu в `/usr/share/fonts/truetype/dejavu/` (в Debian/Ubuntu — пакет `fonts-dejavu-core`). FFmpeg поставляется через пакет `imageio-ffmpeg`.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r animation/requirements.txt
python series/vmeshat_sya/episode_01_reworked.py  # переработка, нативный рендер 1080 × 1920
python series/vmeshat_sya/episode_01.py            # первоначальная версия (рендер 720p, вывод 1080p)
python animation/modern_shorts.py                  # предыдущий вертикальный ролик
python animation/render.py                # все пять первых вариантов
python animation/render.py --style comic  # один ранний стиль
python -m unittest discover -s animation  # проверки ранних роликов
python -m unittest discover -s series/vmeshat_sya  # проверки серии
python -m http.server 8000                # страница сравнения
```
