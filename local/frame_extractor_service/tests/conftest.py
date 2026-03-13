"""
conftest.py — налаштування pytest.

Додає корінь проєкту до sys.path щоб `frame_extractor_service` був імпортований.
"""
import sys
import os

# /home/.../frame_extractor_service/tests/conftest.py
# додаємо батьківську папку (де знаходиться сам пакет frame_extractor_service)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
