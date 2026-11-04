"""Deterministic and non-production pytest configuration.

Never replaces a JWT secret configured by CI or the developer. Tests that need
PostgreSQL must use a disposable database; see TESTING.md.
"""
import os

os.environ.setdefault('JWT_SECRET', 'pytest-only-secret-not-for-production-123456789')
os.environ.setdefault('ENVIRONMENT', 'test')
