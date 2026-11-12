# NURMADOG — пять пробных 2D-мультфильмов

Одна история в пяти вариантах: герою звонит полиция, полицейская машина приезжает к дому, полицейские подходят и задерживают героя. Каждый ролик — 10 секунд, MP4 (H.264 + AAC), 1280 × 720, 25 кадров/с.

| № | Стиль | Видео |
|---|---|---|
| 1 | Солнечный мульт | [01_sunny_cartoon.mp4](videos/01_sunny_cartoon.mp4) |
| 2 | Комикс-детектив | [02_detective_comic.mp4](videos/02_detective_comic.mp4) |
| 3 | Неоновая ночь | [03_neon_night.mp4](videos/03_neon_night.mp4) |
| 4 | Бумажный театр | [04_paper_theater.mp4](videos/04_paper_theater.mp4) |
| 5 | Пиксельное приключение | [05_pixel_adventure.mp4](videos/05_pixel_adventure.mp4) |

Для удобства сравнения есть [страница с плеерами](index.html) и [архив со всеми видео](videos/five_styles.zip). В роликах — музыка и звуковые эффекты, без речевой озвучки.

## Как сделано

Это **упрощённая векторная 2D-анимация**, нарисованная кодом и отрендеренная средствами Pygame/SDL; фотографии или AI-картинки не используются. Персонажи собраны из отдельных подвижных частей: анимированы ноги, руки, телефон в руке, глаза и рот. У машины вращаются колёса и мигают огни, дверь открывается, полицейский подходит и надевает наручники. Варианты используют общий сюжет и одинаковую узнаваемую внешность героя, но различаются графической обработкой, цветом, текстурами и музыкой.

## Повторный рендер

Нужен Python 3.11+ и шрифты DejaVu в `/usr/share/fonts/truetype/dejavu/` (в Debian/Ubuntu — пакет `fonts-dejavu-core`). FFmpeg поставляется через пакет `imageio-ffmpeg`.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r animation/requirements.txt
python animation/render.py                 # все пять файлов
python animation/render.py --style pixel   # один стиль
python -m unittest discover -s animation  # проверки движения и звука
python -m http.server 8000                # страница сравнения
```
