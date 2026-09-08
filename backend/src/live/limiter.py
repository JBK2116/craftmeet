import time


class WebsocketRateLimiter:
    """
    A token bucket rate limiter for handling inbound websocket messages from the frontend.
    """

    def __init__(self, rate: int, capacity: int) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def allow_request(self) -> bool:
        """
        Checks if a request is allowed based on the token bucket algorithm.
        """

        now = time.monotonic()
        # add tokens based on elapsed time
        elapsed = now - self.last_refill
        self.tokens += elapsed * self.rate

        # do not exceed bucket capacity
        self.tokens = min(self.tokens, self.capacity)
        self.last_refill = now

        # allow a request if it is within the capacity
        if self.tokens >= 1:
            self.tokens -= 1
            return True

        return False
