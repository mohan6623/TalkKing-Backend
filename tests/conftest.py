"""Pytest configuration and shared fixtures."""
import sys
import os

# Ensure the Backend directory is on sys.path so `app` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
