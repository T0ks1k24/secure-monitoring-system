"""
conftest.py — pytest configuration.

Adds project root to sys.path so that `frame_extractor_service` can be imported.
"""
import sys
import os

# add parent folder (where frame_extractor_service package is located)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
