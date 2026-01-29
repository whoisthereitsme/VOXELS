import time
import urllib.request
import urllib.error
import json


class Request:
    def __init__(self, url: str = None, timeout: int = 600, retries: int = 3, data=None, method: str = None) -> None:
        self.timeout = timeout
        self.retries = retries
        self.url = url
        self.data = data
        self.method = method

        self.init()

    def init(self) -> None:
        self.request = urllib.request.Request(url=self.url, data=self.data, method=self.method)

    def header(self, key: str = None, value: str = None) -> None:
        self.request.add_header(key, value)

    def open(self) -> dict:
        try:
            with urllib.request.urlopen(self.request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw else {}

        except urllib.error.HTTPError as e:
            # Retry on 429 + 5xx, fail fast on other 4xx
            raw = e.read().decode("utf-8", errors="replace")
            retryable = (e.code == 429) or (500 <= e.code <= 599)

            if retryable and self.retries > 0:
                self.retries -= 1
                time.sleep(0.5)  # tiny backoff; keep simple
                return self.open()

            raise RuntimeError(f"[ERROR] {e.code} for {self.url}\n{raw}") from e

        except (urllib.error.URLError, TimeoutError) as e:
            if self.retries > 0:
                self.retries -= 1
                time.sleep(0.5)
                return self.open()
            raise RuntimeError(f"[ERROR] request failed for {self.url}\n{e!r}") from e
        
        except json.JSONDecodeError as e:
            raise RuntimeError(f"[ERROR] invalid JSON response for {self.url}\n{e!r}") from e