# Built-in wallpapers

Original vector illustrations (Nature, Abstract, Minimal, IT), each in a light and a dark version,
made for this project and released with it under the same license. They are rendered as 2560 × 1440 WebP
images, with 480 × 270 thumbnails.

To regenerate them (Python 3.13):

```bash
python3 -m venv /tmp/wp && /tmp/wp/bin/pip install resvg-py pillow numpy && /tmp/wp/bin/python scripts/wallpapers/generate.py frontend/src/assets/wallpapers
```

Rendering is deterministic (fixed seeds): change a color or a shape in `generate.py`, then run it again.
