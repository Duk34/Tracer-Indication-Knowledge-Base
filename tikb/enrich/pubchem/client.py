"""Calls to PubChem with a pause and one retry (shared by all PubChem steps)."""

import socket
import time

PAUSE = 0.25  # seconds between requests, PubChem allows 5 requests per second

# pubchempy sets no timeout, so a silent connection would hang forever.
# After 30 s the request fails and call_with_retry tries once more.
socket.setdefaulttimeout(30)


def call_with_retry(func, *args):
    """Call func(*args). PubChem sometimes answers with 502, so try once more after 1 s."""
    time.sleep(PAUSE)
    try:
        return func(*args)
    except Exception as error:
        print(f"Error for {args}: {error}. Retrying after 1 second...")
        time.sleep(1)
        try:
            return func(*args)
        except Exception as error:
            print(f"Retry failed for {args}: {error}")
            return None
