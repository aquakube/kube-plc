import threading
import queue
from typing import List
import logging

_lock = threading.Lock()
_queues = {}

logger = logging.getLogger()

def publish_event(name: str, value: int | List[int] | None, timestamp: int):
    """
    Publish an event to all subscribers. This function is thread-safe.
    """
    global _queues, _lock

    with _lock:
        for thread_id, queue in _queues.items():
            try:
                queue.put((name, value, timestamp))
            except queue.Full:
                logger.warning(f"Queue for thread {thread_id} is full. Dropping event.")


def subscribe(thread_id: int, timeout=1) -> tuple[str, int | List[int] | None] | None:
    """
    Subscribes to the events if not already subscribed and listens for events.
    This function is thread-safe during subscription.
    """
    global _queues, _lock

    with _lock:
        if thread_id not in _queues:
            _queues[thread_id] = queue.Queue(maxsize=100)

    try:
        return _queues[thread_id].get(timeout=timeout)
    except queue.Empty:
        # normal if no events are available
        pass


def unsubscribe(thread_id: int):
    """
    Unsibscribes from the events. This function is thread-safe.
    """
    global _queues, _lock

    with _lock:
        if thread_id in _queues:
            del _queues[thread_id]