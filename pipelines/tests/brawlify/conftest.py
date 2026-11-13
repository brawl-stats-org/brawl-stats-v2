import pytest

from brawlify.core import paths
from brawlify.core.dump import Dump


@pytest.fixture(scope="session")
def dump() -> Dump:
    if not (paths.CSV / "csv_logic" / "cards.json").exists():
        pytest.skip("data/raw/brawlify/ is empty: run `uv run brawlify fetch` first")
    return Dump()
