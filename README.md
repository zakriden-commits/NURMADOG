# NURMADOG — пробные 2D-мультфильмы

## Новый вариант: современный комикс для Shorts

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
python animation/modern_shorts.py         # новый вертикальный ролик
python animation/render.py                # все пять первых вариантов
python animation/render.py --style comic  # один ранний стиль
python -m unittest discover -s animation  # проверки движения и звука
python -m http.server 8000                # страница сравнения
```
