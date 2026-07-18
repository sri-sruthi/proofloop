from __future__ import annotations

from datetime import timedelta

import pytest

from .conftest import START
from proofloop.infrastructure.memory import VirtualClock


def test_virtual_clock_set_cannot_move_time_backwards() -> None:
    clock = VirtualClock(START)

    with pytest.raises(ValueError, match="backwards"):
        clock.set(START - timedelta(seconds=1))

    assert clock.now() == START
