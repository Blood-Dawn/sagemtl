# Blood-Dawn — CLI tests
import os
import subprocess
import sys
from pathlib import Path


def run_cli(args, stdin="", env: dict[str, str] | None = None):
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    p = subprocess.run(
        [sys.executable, "-m", "sagemtl", *args],
        input=stdin.encode(),
        capture_output=True,
        check=True,
        env=proc_env,
    )
    return p.stdout.decode()


def test_clean_stdin_stdout(tmp_path: Path):
    out = run_cli(["clean"], "A—B  \r\n\r\n\r\nC")
    assert out == "A-B\n\nC\n"


def test_clean_file(tmp_path: Path):
    f = tmp_path / "x.txt"
    f.write_text("“Yo—yo”\r\n", encoding="utf-8", newline="\r\n")
    out = run_cli(["clean", "--in", str(f)])
    assert out == '"Yo-yo"\n'


def test_clean_uses_config_defaults(tmp_path: Path):
    cfg_path = tmp_path / "config.toml"
    input_file = tmp_path / "input.txt"
    input_file.write_text("A—B", encoding="utf-8")

    from sagemtl.config import Settings, clear_config_cache, save_config

    settings = Settings(
        clean_input_path=str(input_file),
        clean_output_path=str(tmp_path / "out.txt"),
        newline_mode="crlf",
    )
    save_config(settings, cfg_path)
    clear_config_cache()

    run_cli(["clean"], env={"SAGEMTL_CONFIG": str(cfg_path)})

    output = (tmp_path / "out.txt").read_bytes()
    assert output == b"A-B\r\n"
