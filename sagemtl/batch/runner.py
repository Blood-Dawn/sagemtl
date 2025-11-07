"""Threaded batch runner with deduplication and JSONL streaming."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

BatchInput = Any


class BatchRunner:
    """Iterator that processes inputs in parallel and writes JSONL output."""

    def __init__(
        self,
        op,
        inputs: Iterable[BatchInput],
        out_path: str | Path | None,
        *,
        workers: int = 4,
    ) -> None:
        if workers < 1:
            raise ValueError("workers must be >= 1")
        self._op = op
        self._inputs = iter(inputs)
        self._out_path = Path(out_path) if out_path is not None else None
        if self._out_path is not None:
            self._out_path.parent.mkdir(parents=True, exist_ok=True)
        self._workers = workers
        self._cancelled = False
        self._iterator = self._run()
        self._cancel_requested = False
        self.stats: dict[str, Any] = {
            "processed": 0,
            "unique": 0,
            "duplicates": 0,
            "jsonl": str(self._out_path) if self._out_path else None,
            "cancelled": False,
        }

    def __iter__(self) -> "BatchRunner":
        return self

    def __next__(self) -> dict[str, Any]:
        return next(self._iterator)

    def close(self) -> None:
        """Stop processing further inputs."""
        self._cancel_requested = True
        try:
            self._iterator.close()
        finally:
            if not self._cancelled:
                self._cancel_requested = False

    cancel = close

    @property
    def cancelled(self) -> bool:
        return self.stats.get("cancelled", False)

    def _run(self) -> Iterator[dict[str, Any]]:
        executor = ThreadPoolExecutor(max_workers=self._workers)
        fh = self._out_path.open("w", encoding="utf-8", newline="\n") if self._out_path else None
        pending_sources: dict[str, list[str]] = {}
        futures: dict[Future[str], str] = {}
        seen: dict[str, str] = {}
        inputs = self._inputs
        exhausted = False

        def emit(record: dict[str, Any]) -> dict[str, Any]:
            self.stats["processed"] += 1
            if record.get("duplicate"):
                self.stats["duplicates"] += 1
            else:
                self.stats["unique"] += 1
            if fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                fh.flush()
            return record

        try:
            while True:
                while not exhausted and len(futures) < self._workers:
                    try:
                        item = next(inputs)
                    except StopIteration:
                        exhausted = True
                        break
                    source, payload = _coerce_input(item)
                    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                    if digest in seen:
                        yield emit(
                            {
                                "source": source,
                                "text": seen[digest],
                                "sha256": digest,
                                "duplicate": True,
                            }
                        )
                        continue
                    if digest in pending_sources:
                        pending_sources[digest].append(source)
                        continue
                    future = executor.submit(self._op, payload)
                    futures[future] = digest
                    pending_sources[digest] = [source]
                if not futures:
                    if exhausted:
                        break
                    continue
                done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                for fut in done:
                    digest = futures.pop(fut)
                    sources = pending_sources.pop(digest)
                    text = fut.result()
                    seen[digest] = text
                    first = True
                    for src in sources:
                        yield emit(
                            {
                                "source": src,
                                "text": text,
                                "sha256": digest,
                                "duplicate": not first,
                            }
                        )
                        first = False
                if exhausted and not futures:
                    break
        except GeneratorExit:
            if self._cancel_requested:
                self._cancelled = True
            for fut in futures:
                fut.cancel()
            raise
        except KeyboardInterrupt:
            self._cancelled = True
            for fut in futures:
                fut.cancel()
            raise
        except BaseException:
            for fut in futures:
                fut.cancel()
            raise
        finally:
            for fut in futures:
                fut.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            if fh:
                fh.flush()
                fh.close()
            self.stats["cancelled"] = self._cancelled


def _coerce_input(item: BatchInput) -> tuple[str, str]:
    if isinstance(item, tuple) and len(item) == 2:
        source, payload = item
        source = _stringify_source(source)
        payload = _materialize_payload(payload)
        return source, payload
    if isinstance(item, Mapping):
        if "source" not in item or "text" not in item:
            raise ValueError("mapping inputs must contain 'source' and 'text'")
        source = _stringify_source(item["source"])
        payload = _materialize_payload(item["text"])
        return source, payload
    if isinstance(item, (str, Path)):
        path = Path(item)
        text = path.read_text(encoding="utf-8", errors="ignore")
        return str(path), text
    raise TypeError(f"Unsupported batch input: {type(item)!r}")


def _stringify_source(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _materialize_payload(value: Any) -> str:
    if callable(value):
        value = value()
    if isinstance(value, Path):
        return value.read_text(encoding="utf-8", errors="ignore")
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def run_batch(
    op,
    inputs: Iterable[BatchInput],
    out_path: str | Path | None,
    *,
    workers: int = 4,
) -> BatchRunner:
    """Run *op* over *inputs* with optional JSONL logging."""
    return BatchRunner(op, inputs, out_path, workers=workers)
