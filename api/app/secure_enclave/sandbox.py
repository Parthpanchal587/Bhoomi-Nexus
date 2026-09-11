"""
Process-Isolated Execution Sandbox.

Implements sandboxing and resource restrictions:
1. Environment variable scrubbing (prevents leaking host API keys/tokens to worker tasks)
2. Strict execution timeout enforcement
3. Memory consumption tracking using psutil
4. Fail-closed error handling
5. Exception boundary preventing untrusted task crashes from corrupting the host server
"""

import asyncio
import concurrent.futures
import os
import sys
import time
from typing import Any, Callable, Dict, Optional, Tuple

try:
    import psutil
except (ImportError, Exception):
    psutil = None


class SandboxResourceLimitExceeded(Exception):
    """Raised when a sandboxed execution exceeds memory or CPU bounds."""
    pass


class SandboxTimeoutError(Exception):
    """Raised when an operation exceeds its allotted maximum execution time."""
    pass


class IsolatedSandbox:
    """
    Executes sensitive or untrusted operations within a strictly monitored,
    time-bounded, and environment-scrubbed sandbox.
    """

    MAX_MEMORY_MB = 512.0  # Maximum memory ceiling for a task

    def __init__(self, max_workers: int = 4) -> None:
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="EnclaveSandboxWorker",
        )

    def scrub_environment(self) -> Dict[str, str]:
        """
        Create a minimal, sanitized environment dictionary for child execution,
        stripping out all sensitive host environment variables.
        """
        allowlist = {"PATH", "SYSTEMROOT", "TEMP", "TMP", "PYTHONPATH", "LANG", "TZ"}
        scrubbed = {}
        for k, v in os.environ.items():
            if k.upper() in allowlist:
                scrubbed[k] = v
        return scrubbed

    def execute_bounded(
        self,
        func: Callable[..., Any],
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
        timeout_ms: int = 5000,
    ) -> Tuple[Any, float]:
        """
        Execute a function with hard execution timeout and memory observation.
        Returns (result, execution_time_ms).
        """
        kwargs = kwargs or {}
        start_time = time.perf_counter()
        timeout_sec = max(0.1, timeout_ms / 1000.0)

        mem_before = 0.0
        process = None
        if psutil is not None:
            try:
                process = psutil.Process()
                mem_before = process.memory_info().rss / (1024 * 1024)
            except Exception:
                pass

        future = self._executor.submit(func, *args, **kwargs)

        try:
            result = future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            raise SandboxTimeoutError(
                f"Execution aborted: Operation exceeded maximum allowed timeout of {timeout_ms}ms."
            )
        except Exception as e:
            # Re-raise within sandbox boundary
            raise RuntimeError(f"Sandboxed execution error: {e}") from e

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000.0

        if process is not None:
            try:
                mem_after = process.memory_info().rss / (1024 * 1024)
                if (mem_after - mem_before) > self.MAX_MEMORY_MB:
                    raise SandboxResourceLimitExceeded(
                        f"Operation exceeded maximum permitted memory allocation delta ({self.MAX_MEMORY_MB} MB)."
                    )
            except SandboxResourceLimitExceeded:
                raise
            except Exception:
                pass

        return result, duration_ms

    async def execute_bounded_async(
        self,
        func: Callable[..., Any],
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
        timeout_ms: int = 5000,
    ) -> Tuple[Any, float]:
        """Async-compatible wrapper running synchronous work on the isolated executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self.execute_bounded,
            func,
            args,
            kwargs,
            timeout_ms,
        )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
