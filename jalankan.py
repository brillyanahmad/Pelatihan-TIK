"""Jalankan analisis lalu buka dashboard di browser."""
import webbrowser
from pathlib import Path

import analisis

analisis.build()
webbrowser.open((Path(__file__).parent / "index.html").resolve().as_uri())
