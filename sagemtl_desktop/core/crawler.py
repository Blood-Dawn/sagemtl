"""
Novel crawler using LNCrawl (Lightnovel Crawler) as subprocess.
"""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Callable, Optional


class Crawler:
    """Wrapper for Lightnovel Crawler (LNCrawl) subprocess"""

    def __init__(self):
        self.output_dir = Path(tempfile.mkdtemp(prefix="sagemtl_crawl_"))
        self._check_lncrawl_installed()

    def _check_lncrawl_installed(self) -> bool:
        """Check if LNCrawl is installed"""
        try:
            result = subprocess.run(
                ["lncrawl", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def is_available(self) -> bool:
        """Check if LNCrawl is available"""
        return self._check_lncrawl_installed()

    def crawl_novel(
        self,
        url: str,
        novel_name: str = "",
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        Crawl novel using LNCrawl subprocess.

        Args:
            url: Novel URL
            novel_name: Name for the novel (optional)
            start_chapter: Starting chapter (optional)
            end_chapter: Ending chapter (optional)
            progress_callback: Progress callback (0-100)
            log_callback: Log callback (level, message)

        Returns:
            Path to downloaded EPUB file

        Raises:
            RuntimeError: If LNCrawl is not installed or crawl fails
        """
        if log_callback:
            log_callback("info", f"Starting crawl: {url}")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Build LNCrawl command with multiprocessing context fix
        # Use force=True to avoid "context has already been set" error
        python_code = (
            "import multiprocessing as mp; "
            "mp.set_start_method('spawn', force=True); "
            "import lncrawl; "
            "lncrawl.main()"
        )

        # Base command with Python -c to set multiprocessing context
        # Use sys.executable to ensure subprocess uses same Python (virtualenv) as parent
        cmd = [
            sys.executable, "-c", python_code,
            "--suppress",  # Non-interactive mode
            "--format", "epub",
            "--output", str(self.output_dir),
            "--source", url
        ]

        if novel_name:
            cmd.extend(["--novel-name", novel_name])

        if start_chapter is not None:
            cmd.extend(["--first", str(start_chapter)])

        if end_chapter is not None:
            cmd.extend(["--last", str(end_chapter)])

        if log_callback:
            # Log only the meaningful parts (not the Python wrapper)
            meaningful_args = [arg for arg in cmd[3:] if arg != python_code]  # Skip python -c "code"
            log_callback("info", f"Running LNCrawl with: {' '.join(meaningful_args)}")

        # Retry logic: 2 attempts with backoff
        max_attempts = 2
        backoff_seconds = [0, 5]  # No delay on first attempt, 5s on retry

        last_error = None

        for attempt in range(max_attempts):
            if attempt > 0 and log_callback:
                log_callback("warn", f"Retrying crawl (attempt {attempt + 1}/{max_attempts})...")
                import time
                time.sleep(backoff_seconds[attempt])

            try:
                # Run subprocess
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Combine stderr with stdout
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # Stream output
                output_lines = []
                for line in iter(process.stdout.readline, ''):
                    line = line.strip()
                    if not line:
                        continue

                    output_lines.append(line)

                    if log_callback:
                        log_callback("info", f"[LNCrawl] {line}")

                    # Try to parse progress
                    if progress_callback:
                        progress = self._parse_progress(line)
                        if progress is not None:
                            progress_callback(progress)

                # Wait for completion
                returncode = process.wait(timeout=600)  # 10 minute timeout

                if returncode != 0:
                    error_msg = '\n'.join(output_lines[-20:])  # Last 20 lines
                    if log_callback:
                        log_callback("error", f"LNCrawl failed with code {returncode}")
                        log_callback("error", error_msg)
                    last_error = RuntimeError(f"LNCrawl exited with code {returncode}\n{error_msg}")
                    continue  # Retry

                # Find EPUB file
                epub_files = list(self.output_dir.glob("*.epub"))
                if not epub_files:
                    if log_callback:
                        log_callback("error", "No EPUB file generated")
                    last_error = RuntimeError("No EPUB file generated by LNCrawl")
                    continue  # Retry

                epub_path = epub_files[0]

                if log_callback:
                    log_callback("info", f"EPUB saved to: {epub_path}")

                if progress_callback:
                    progress_callback(100.0)

                return str(epub_path)

            except FileNotFoundError:
                error_msg = "Python or LNCrawl not found. Ensure both are in PATH."
                if log_callback:
                    log_callback("error", error_msg)
                last_error = RuntimeError(error_msg)
                break  # Don't retry for missing dependencies

            except subprocess.TimeoutExpired:
                process.kill()
                error_msg = "Crawl timed out after 10 minutes"
                if log_callback:
                    log_callback("error", error_msg)
                last_error = RuntimeError(error_msg)
                continue  # Retry timeout

            except Exception as e:
                if log_callback:
                    log_callback("error", f"Crawl error: {str(e)}")
                last_error = e
                continue  # Retry

        # If we exhausted all retries, raise the last error
        if log_callback:
            log_callback("error", f"Crawl failed after {max_attempts} attempts")
        raise last_error if last_error else RuntimeError("Crawl failed for unknown reason")

    def _parse_progress(self, line: str) -> Optional[float]:
        """
        Try to parse progress from LNCrawl output.

        LNCrawl might output progress like:
        - "Downloaded 10 of 100 chapters"
        - "Progress: 50%"

        Args:
            line: Output line from LNCrawl

        Returns:
            Progress percentage (0-100) or None
        """
        import re

        # Try to match percentage
        percent_match = re.search(r'(\d+)%', line)
        if percent_match:
            try:
                return float(percent_match.group(1))
            except ValueError:
                pass

        # Try to match "X of Y" pattern
        of_match = re.search(r'(\d+)\s+of\s+(\d+)', line)
        if of_match:
            try:
                current = float(of_match.group(1))
                total = float(of_match.group(2))
                if total > 0:
                    return (current / total) * 100
            except ValueError:
                pass

        return None

    def cleanup(self):
        """Clean up temp directory"""
        if self.output_dir.exists():
            try:
                shutil.rmtree(self.output_dir)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp directory: {e}")

    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()
