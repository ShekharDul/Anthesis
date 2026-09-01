"""Command-line entry point for Anthesis."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile

import uvicorn

from anthesis import __version__
from anthesis.audio.errors import AudioProcessingError
from anthesis.processing import ProcessingConfig, analyze_file, generate_file
from anthesis.rendering import RenderConfig


def _dimension(value: str) -> int:
    dimension = int(value)
    if not 256 <= dimension <= 2_048:
        raise argparse.ArgumentTypeError("expected an integer from 256 through 2048")
    return dimension


def _supersampling(value: str) -> int:
    amount = int(value)
    if not 1 <= amount <= 3:
        raise argparse.ArgumentTypeError("expected an integer from 1 through 3")
    return amount


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anthesis",
        description="Turn the mathematics of a music recording into one deterministic flower.",
    )
    parser.add_argument("--version", action="version", version=f"Anthesis {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="write a MusicGenome and flower blueprint")
    analyze.add_argument("input", type=Path, help="source audio file")
    analyze.add_argument("--output", "-o", type=Path, help="analysis JSON path")

    generate = commands.add_parser("generate", help="render a flower PNG and analysis JSON")
    generate.add_argument("input", type=Path, help="source audio file")
    generate.add_argument("--output", "-o", type=Path, help="flower PNG path")
    analysis_output = generate.add_mutually_exclusive_group()
    analysis_output.add_argument("--analysis", type=Path, help="generation manifest JSON path")
    analysis_output.add_argument(
        "--no-analysis", action="store_true", help="do not write sidecar JSON"
    )
    generate.add_argument("--width", type=_dimension, default=900, metavar="PIXELS")
    generate.add_argument("--height", type=_dimension, default=1_200, metavar="PIXELS")
    generate.add_argument("--supersampling", type=_supersampling, default=2, metavar="1-3")

    serve = commands.add_parser("serve", help="run the local Anthesis API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    return parser


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _analyze(arguments: argparse.Namespace) -> int:
    input_path: Path = arguments.input
    output: Path = arguments.output or input_path.with_suffix(".anthesis.json")
    document = analyze_file(input_path)
    _atomic_write(output, document.model_dump_json(indent=2).encode("utf-8"))
    print(f"Analysis: {output.resolve()}")
    print(f"Genome:   {document.genome.digest}")
    return 0


def _generate(arguments: argparse.Namespace) -> int:
    input_path: Path = arguments.input
    output: Path = arguments.output or input_path.with_suffix(".anthesis.png")
    analysis_path: Path = arguments.analysis or input_path.with_suffix(".anthesis.json")
    render = RenderConfig(
        width=arguments.width,
        height=arguments.height,
        supersampling=arguments.supersampling,
    )
    generated = generate_file(input_path, ProcessingConfig(render=render))
    _atomic_write(output, generated.png)
    if not arguments.no_analysis:
        manifest = generated.manifest.model_dump_json(indent=2).encode("utf-8")
        _atomic_write(analysis_path, manifest)
    print(f"Flower:  {output.resolve()}")
    if not arguments.no_analysis:
        print(f"Analysis: {analysis_path.resolve()}")
    print(f"Genome:   {generated.manifest.analysis.genome.digest}")
    return 0


def _serve(arguments: argparse.Namespace) -> int:
    if not 1 <= arguments.port <= 65_535:
        raise ValueError("port must be between 1 and 65535")
    uvicorn.run(
        "anthesis.api:app",
        host=arguments.host,
        port=arguments.port,
        reload=arguments.reload,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse a command, report domain errors cleanly, and return an exit code."""

    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "analyze":
            return _analyze(arguments)
        if arguments.command == "generate":
            return _generate(arguments)
        return _serve(arguments)
    except (AudioProcessingError, OSError, ValueError) as error:
        print(f"anthesis: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
