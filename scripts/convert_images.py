"""Convert the site's images to WebP.

The photos in ``static/images`` came straight off a camera, so several are
multi-megabyte files being scaled down to a few hundred pixels in the browser.
This re-encodes them as WebP and caps their longest edge, which is the single
biggest win available for page load time.

Originals stay put in ``static/images`` as the editable source of truth. The
WebP copies are written to ``static/images-webp``, and that is the folder the
templates point at. Re-running the script regenerates the whole folder, so the
originals are the only thing that ever needs editing by hand.

Usage::

    uv run --group images python scripts/convert_images.py --dry-run
    uv run --group images python scripts/convert_images.py
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from PIL import Image, ImageOps

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "static" / "images"
DEFAULT_OUTPUT = REPO_ROOT / "static" / "images-webp"

# Formats worth re-encoding. WebP beats all of them at comparable quality.
SOURCE_SUFFIXES = {".jpg", ".jpeg", ".png"}

DEFAULT_QUALITY = 82
DEFAULT_MAX_EDGE = 2000


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB"):
        if abs(size) < 1024 or unit == "MB":
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")


def source_images(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
    )


def encode(source: Path, quality: int, max_edge: int) -> tuple[bytes, tuple[int, int]]:
    """Return ``source`` re-encoded as WebP, plus the dimensions it ended up at.

    Encoding to memory means ``--dry-run`` reports real byte counts rather than
    an estimate, and the write path stays a single ``Path.write_bytes``.
    """
    with Image.open(source) as image:
        # Phone photos carry their rotation in EXIF rather than in the pixel
        # data, and WebP has no equivalent tag -- bake it in or they come out
        # sideways.
        image = ImageOps.exif_transpose(image)

        if max_edge and max(image.size) > max_edge:
            image.thumbnail((max_edge, max_edge), Image.LANCZOS)

        # Paletted and greyscale sources have to be promoted before WebP will
        # take them. Palette PNGs keep transparency in a separate info key
        # rather than in an alpha band, so check both or the logos lose their
        # transparent backgrounds.
        if image.mode not in ("RGB", "RGBA"):
            has_alpha = "A" in image.getbands() or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")

        buffer = io.BytesIO()
        image.save(buffer, "WEBP", quality=quality, method=6)
        return buffer.getvalue(), image.size


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
        help=f"where the .webp copies are written (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=DEFAULT_QUALITY,
        help=f"WebP quality, 0-100 (default: {DEFAULT_QUALITY})",
    )
    parser.add_argument(
        "--max-edge",
        type=int,
        default=DEFAULT_MAX_EDGE,
        help=(
            "shrink images whose longest edge exceeds this many pixels; "
            f"0 disables resizing (default: {DEFAULT_MAX_EDGE})"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-encode even when an up-to-date .webp already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing anything",
    )
    args = parser.parse_args(argv)

    source_root: Path = args.source
    output_root: Path = args.output
    if not source_root.is_dir():
        parser.error(f"not a directory: {source_root}")

    images = source_images(source_root)
    if not images:
        print(f"No convertible images found in {source_root}")
        return 0

    total_before = 0
    total_after = 0
    converted = 0
    skipped = 0

    for source in images:
        # Mirror any subdirectories so the two trees stay parallel.
        destination = (output_root / source.relative_to(source_root)).with_suffix(".webp")
        before = source.stat().st_size

        if (
            destination.exists()
            and not args.force
            and destination.stat().st_mtime >= source.stat().st_mtime
        ):
            print(f"  skip  {source.name}  (up-to-date {destination.name}; --force to redo)")
            skipped += 1
            continue

        encoded, dimensions = encode(source, args.quality, args.max_edge)
        after = len(encoded)

        if args.dry_run:
            action = "would convert"
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(encoded)
            action = "converted"

        total_before += before
        total_after += after
        converted += 1
        reduction = (1 - after / before) * 100 if before else 0
        print(
            f"  {action:>13}  {source.name:<32} "
            f"{human_size(before):>10} -> {human_size(after):>10} "
            f"({reduction:5.1f}% smaller, {dimensions[0]}x{dimensions[1]})"
        )

    print()
    print(f"{converted} image(s) {'to convert' if args.dry_run else 'converted'}, {skipped} skipped")
    if converted:
        saved = total_before - total_after
        reduction = (1 - total_after / total_before) * 100 if total_before else 0
        print(
            f"Total: {human_size(total_before)} -> {human_size(total_after)} "
            f"({human_size(saved)} saved, {reduction:.1f}% smaller)"
        )
    if args.dry_run:
        print("\nDry run: nothing was written. Re-run without --dry-run to apply.")
    elif converted:
        print(f"\nWritten to {output_root}. Originals left untouched in {source_root}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
