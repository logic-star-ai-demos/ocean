import time
import threading
import asyncio
import pytest
from port_ocean.log.handlers import HTTPMemoryHandler


def test_clear_thread_pool_skips_dead_threads():
    # Setup handler with dummy ocean and delayed send_logs
    handler = HTTPMemoryHandler(capacity=1)
    # Monkey-patch ocean property to always return a dummy object
    setattr(HTTPMemoryHandler, 'ocean', property(lambda self: object()))
    # Override send_logs to sleep so threads overlap
    def dummy_send_logs(ocean, logs):
        async def _inner():
            await asyncio.sleep(0.05)
        return _inner()
    handler.send_logs = lambda ocean, logs: dummy_send_logs(ocean, logs)

    # Rapidly trigger multiple flushes
    for i in range(10):
        handler.buffer.append(f"record{i}")
        handler._serialized_buffer.append({"msg": f"record{i}"})
        handler.flush()
        # Small pause to allow threads to start and then skip
        time.sleep(0.01)

    # Allow all threads time to finish
    time.sleep(0.5)

    # Due to the bug, clear_thread_pool logic skips some dead threads
    pool_size = len(handler._thread_pool)
    # Assert empty pool - this will fail if the bug is present
    assert pool_size == 0, f"Expected thread pool to be empty, but got size {pool_size}"
