import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SPRINTS = RAIZ / "sprints"

# Permite importar los módulos de src/ desde las pruebas
sys.path.insert(0, str(RAIZ / "src"))


@pytest.fixture(scope="session")
def flujo_local():
    """Datos de los sprints 2 a 6 construidos UNA vez desde los CSV locales (sin red, resultado determinista)."""
    import flujo
    return flujo.cargar_y_construir("local")
