"""Re-encode the site's videos for the web, and generate a poster frame for each.

MP4 is only a container -- it says nothing about how hard the video was
compressed. The screen recordings here were exported at roughly 22 Mbit/s, which
is broadcast-master territory and about ten times what a screen recording needs.
Re-encoding with H.264 at a sane quality target cuts them by ~95% with no
visible difference at the size they are played back at.

Originals stay in ``static/video`` as the source of truth. Web copies are written
to ``static/video-web`` along with a ``.webp`` poster frame, and that is what the
templates point at.

Requires ffmpeg on PATH (``winget install Gyan.FFmpeg``).

Usage::

    uv run python scripts/compress_videos.py --dry-run
    uv run python scripts/compress_videos.py
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "static" / "video"
DEFAULT_OUTPUT = REPO_ROOT / "static" / "video-web"

SOURCE_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".avi"}

# 26 is visually transparent for screen recordings and UI animations, which have
# large flat areas. Drop it towards 20 for camera footage if it ever looks soft.
DEFAULT_CRF = 26
DEFAULT_MAX_WIDTH = 1280
DEFAULT_PRESET = "slow"


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB"):
        if abs(size) < 1024 or unit == "MB":
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")


def source_videos(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
    )


def has_audio(source: Path) -> bool:
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index",
            "-of", "json",
            str(source),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(json.loads(probe.stdout).get("streams"))


def encode(source: Path, destination: Path, crf: int, preset: str, max_width: int) -> None:
    command = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(source),
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        # Never upscale: only shrink sources wider than the cap.
        "-vf", f"scale='min({max_width},iw)':-2",
        # Safari and older Android decoders reject anything but 4:2:0.
        "-pix_fmt", "yuv420p",
        # Moves the index to the front so playback can start before the whole
        # file has downloaded.
        "-movflags", "+faststart",
    ]
    command += ["-c:a", "aac", "-b:a", "128k"] if has_audio(source) else ["-an"]
    command.append(str(destination))
    subprocess.run(command, check=True)


def make_poster(source: Path, destination: Path, max_width: int) -> None:
    """Grab a frame to show before playback starts.

    With a poster the browser has something to render without fetching any video
    data, which is what makes ``preload="none"`` free rather than ugly.
    """
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            # One second in: the very first frame of a screen recording is often
            # blank or mid-fade.
            "-ss", "1",
            "-i", str(source),
            "-frames:v", "1",
            "-vf", f"scale='min({max_width},iw)':-2",
            "-quality", "80",
            str(destination),
        ],
        check=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"directory of originals to walk (default: {DEFAULT_SOURCE.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"where web copies are written (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=DEFAULT_CRF,
        help=f"H.264 quality, lower is better and bigger, 18-28 is useful (default: {DEFAULT_CRF})",
    )
    parser.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        help=f"x264 preset: slower means smaller files (default: {DEFAULT_PRESET})",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=DEFAULT_MAX_WIDTH,
        help=f"shrink anything wider than this (default: {DEFAULT_MAX_WIDTH})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-encode even when an up-to-date copy already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list what would be re-encoded without writing anything",
    )
    args = parser.parse_args(argv)

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        parser.error("ffmpeg and ffprobe must be on PATH (winget install Gyan.FFmpeg)")

    source_root: Path = args.source
    output_root: Path = args.output
    if not source_root.is_dir():
        parser.error(f"not a directory: {source_root}")

    videos = source_videos(source_root)
    if not videos:
        print(f"No videos found in {source_root}")
        return 0

    total_before = 0
    total_after = 0
    converted = 0
    skipped = 0

    for source in videos:
        relative = source.relative_to(source_root)
        destination = (output_root / relative).with_suffix(".mp4")
        poster = destination.with_suffix(".webp")
        before = source.stat().st_size

        if (
            destination.exists()
            and not args.force
            and destination.stat().st_mtime >= source.stat().st_mtime
        ):
            print(f"  skip  {source.name}  (up-to-date; --force to redo)")
            skipped += 1
            continue

        if args.dry_run:
            # Encoding is far too slow to run speculatively, so unlike the image
            # script this only reports what it would touch.
            print(f"  would re-encode  {source.name:<36} {human_size(before):>10}")
            converted += 1
            total_before += before
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        print(f"  encoding  {source.name} ...", flush=True)
        encode(source, destination, args.crf, args.preset, args.max_width)
        make_poster(source, poster, args.max_width)

        after = destination.stat().st_size
        total_before += before
        total_after += after
        converted += 1
        reduction = (1 - after / before) * 100 if before else 0
        print(
            f"  {'encoded':>13}  {source.name:<36} "
            f"{human_size(before):>10} -> {human_size(after):>10} "
            f"({reduction:5.1f}% smaller, poster {poster.name})"
        )

    print()
    print(f"{converted} video(s) {'to re-encode' if args.dry_run else 'encoded'}, {skipped} skipped")
    if converted and not args.dry_run:
        saved = total_before - total_after
        reduction = (1 - total_after / total_before) * 100 if total_before else 0
        print(
            f"Total: {human_size(total_before)} -> {human_size(total_after)} "
            f"({human_size(saved)} saved, {reduction:.1f}% smaller)"
        )
        print(f"\nWritten to {output_root}. Originals left untouched in {source_root}.")
    elif args.dry_run:
        print("\nDry run: nothing was written. Re-run without --dry-run to apply.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
