"""Release smoke check: run inside the production container BEFORE shipping.

Imports all application modules, so missing modules and broken imports stop deployment.
Does not connect to the database or trigger AI model downloads.
"""
import importlib
import pkgutil
import sys

def verify() -> None:
    import app
    failures: list[str] = []
    for module in pkgutil.walk_packages(app.__path__, prefix='app.'):
        if '.__pycache__' in module.name:
            continue
        try:
            importlib.import_module(module.name)
        except Exception as exc:
            failures.append(f'{module.name}: {type(exc).__name__}: {exc}')
    if failures:
        raise RuntimeError('Invalid application release; missing/broken modules:\n' + '\n'.join(failures))
    from app.main import app as fastapi_app
    assert any(route.path == '/api/v1/listings' for route in fastapi_app.routes), 'Listings router is not registered'
    print('RELEASE_SMOKE_OK: application imports and listings router registered')

if __name__ == '__main__':
    verify()
