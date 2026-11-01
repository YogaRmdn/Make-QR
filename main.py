#!/usr/bin/env python3
"""QR Maker - generator QR code berwarna untuk terminal.

Dibuat oleh Bangyog - github.com/YogaRmdn

Contoh pemakaian:
    python main.py                                  # mode interaktif
    python main.py example.com                      # -> example.com.png
    python main.py https://example.com -o kode.png  # nama file manual
    python main.py example.com --fill "#00E5FF" --back "#0B0F19"
    python main.py --help
"""

from __future__ import annotations

import argparse
import colorsys
import os
import re
import shutil
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlsplit

import qrcode
from qrcode.constants import (
    ERROR_CORRECT_H,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
)
from qrcode.exceptions import DataOverflowError

__version__ = "2.0.0"

# --------------------------------------------------------------------------
# ANSI
# --------------------------------------------------------------------------
RESET = "\x1b[0m"
BOLD = "\x1b[1m"
CLEAR_LINE = "\x1b[2K"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
CURSOR_UP = "\x1b[{}A"

RGB = tuple[int, int, int]
BANNER_PALETTE: tuple[RGB, ...] = ((0, 229, 255), (108, 92, 231), (255, 77, 166))
SPINNER_PALETTE: tuple[RGB, ...] = ((57, 255, 136), (0, 229, 255), (124, 92, 255))
ACCENT: RGB = (0, 229, 255)
SUCCESS: RGB = (57, 255, 136)
WARNING: RGB = (255, 196, 0)
DANGER: RGB = (255, 92, 92)
MUTED: RGB = (120, 132, 156)

# Banner asli dipertahankan apa adanya.
BANNER_ART: tuple[str, ...] = (
    "⡏⣭⡍⡇⢖⠃⣘⠇⢸⢩⣭⢹",
    "⠧⠭⠥⠇⡏⡯⢳⡳⠸⠬⠭⠼ Tools for make QR",
    "⢟⠬⠶⢍⣐⡐⡛⠘⣞⡩⠈⠵ By Bangyog",
    "⣠⢾⡽⣡⢥⠙⠝⣨⣙⣣⣓⠝ github.com/YogaRmdn",
    "⡖⣒⡒⡆⢳⣫⡣⢿⣐⣸⡧⠞",
    "⣇⣛⣃⡇⡭⠬⠞⣢⢆⡛⠝⣐",
)

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
ERROR_LEVELS = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


# --------------------------------------------------------------------------
# Utilitas warna & terminal
# --------------------------------------------------------------------------
def _mix(first: RGB, second: RGB, ratio: float) -> RGB:
    """Campur dua warna RGB berdasarkan rasio 0..1."""
    ratio = min(max(ratio, 0.0), 1.0)
    return (
        round(first[0] + (second[0] - first[0]) * ratio),
        round(first[1] + (second[1] - first[1]) * ratio),
        round(first[2] + (second[2] - first[2]) * ratio),
    )


def _sample(palette: Sequence[RGB], position: float) -> RGB:
    """Ambil warna dari palette pada posisi 0..1."""
    position = min(max(position, 0.0), 1.0)
    if len(palette) == 1:
        return palette[0]
    scaled = position * (len(palette) - 1)
    index = min(int(scaled), len(palette) - 2)
    return _mix(palette[index], palette[index + 1], scaled - index)


def _hue(hue: float, saturation: float = 1.0, value: float = 1.0) -> RGB:
    red, green, blue = colorsys.hsv_to_rgb((hue % 360.0) / 360.0, saturation, value)
    return (round(red * 255), round(green * 255), round(blue * 255))


def _is_tty() -> bool:
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def _enable_windows_vt() -> None:
    """Aktifkan dukungan ANSI escape di Windows 10+."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("TERM", "") == "dumb":
        return False
    _enable_windows_vt()
    return _is_tty()


def _configure_stdout() -> None:
    """Paksa UTF-8 agar karakter braille tampil benar."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def clear_screen() -> None:
    """Bersihkan layar hanya saat output menuju terminal sungguhan."""
    if not _is_tty():
        return
    if os.name == "nt":
        os.system("cls")
    else:
        sys.stdout.write("\x1b[2J\x1b[H")
        sys.stdout.flush()


class Console:
    """Pembungkus output berwarna + animasi."""

    def __init__(self, *, color: bool, animate: bool) -> None:
        self.color = color
        self.animate = animate and _is_tty()
        self.width = shutil.get_terminal_size((80, 24)).columns
        self._banner_width = max(len(line) for line in BANNER_ART)
        self._banner_anim = (
            self.animate
            and self.color
            and self.width >= self._banner_width + 2
        )

    # -- primitives --------------------------------------------------------
    def paint(self, text: str, rgb: RGB, *, bold: bool = False) -> str:
        if not self.color or not text:
            return text
        prefix = f"\x1b[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"
        return (BOLD if bold else "") + prefix + text + RESET

    def _banner_line(self, line: str, line_index: int, phase: float | None) -> str:
        """Satu baris banner, dengan sapuan cahaya bila phase diisi."""
        if not self.color:
            return line
        span = max(len(line) - 1, 1)
        band = (phase * 1.6 - 0.3 + line_index * 0.03) if phase is not None else -1.0
        parts: list[str] = []
        for index, char in enumerate(line):
            if char == " ":
                parts.append(char)
                continue
            unit = index / span
            rgb = _sample(BANNER_PALETTE, min(unit + line_index * 0.06, 1.0))
            if phase is not None:
                glow = max(0.0, 1.0 - abs(unit - band) / 0.18)
                if glow > 0:
                    rgb = _mix(rgb, (255, 255, 255), glow * 0.85)
            parts.append(self.paint(char, rgb, bold=True))
        return "".join(parts)

    # -- komponen tampilan -------------------------------------------------
    def banner(self, *, animate: bool = True) -> None:
        lines = [line.ljust(self._banner_width) for line in BANNER_ART]
        frames = 16 if (animate and self._banner_anim) else 0

        if frames:
            sys.stdout.write(HIDE_CURSOR)
            try:
                for frame in range(frames):
                    if frame:
                        sys.stdout.write(CURSOR_UP.format(len(lines)))
                    phase = frame / frames
                    for line_index, line in enumerate(lines):
                        sys.stdout.write(self._banner_line(line, line_index, phase) + "\n")
                    sys.stdout.flush()
                    time.sleep(0.032)
            finally:
                sys.stdout.write(SHOW_CURSOR)
            sys.stdout.write(CURSOR_UP.format(len(lines)))

        for line_index, line in enumerate(lines):
            sys.stdout.write(
                self._banner_line(line, line_index, None)
                if self.color
                else line.rstrip()
            )
            sys.stdout.write("\n")
        sys.stdout.write("\n")
        sys.stdout.flush()

    def spinner(self, label: str = "Membuat QR code", *, duration: float = 1.15) -> None:
        """Animasi spinner braille dengan progress bar bergradasi."""
        if not self.animate:
            return

        if self.width < 60:
            label = "Membuat QR"
        bar_width = max(8, min(24, self.width - len(label) - 16))

        start = time.perf_counter()
        index = 0
        sys.stdout.write(HIDE_CURSOR)
        try:
            while True:
                elapsed = time.perf_counter() - start
                progress = min(elapsed / duration, 1.0)
                eased = 1.0 - (1.0 - progress) ** 2  # ease-out
                filled = int(round(eased * bar_width))
                hue = (elapsed * 420.0) % 360.0

                cells: list[str] = []
                for cell in range(bar_width):
                    if cell < filled:
                        rgb = _sample(SPINNER_PALETTE, cell / max(bar_width - 1, 1))
                        if cell == filled - 1:
                            rgb = _mix(rgb, (255, 255, 255), 0.65)
                        cells.append(self.paint("█", rgb, bold=True))
                    else:
                        cells.append(self.paint("░", MUTED))

                frame = SPINNER_FRAMES[index % len(SPINNER_FRAMES)]
                percent = f"{int(round(eased * 100)):3d}%"
                line = (
                    f"  {self.paint(frame, _hue(hue), bold=True)}  {label}  "
                    f"[{''.join(cells)}]  {self.paint(percent, _hue(hue), bold=True)}"
                )
                sys.stdout.write(CLEAR_LINE + "\r" + line)
                sys.stdout.flush()

                if progress >= 1.0:
                    break
                index += 1
                time.sleep(0.04)
        finally:
            sys.stdout.write(SHOW_CURSOR)

        sys.stdout.write(CLEAR_LINE + "\r")
        sys.stdout.flush()

    def success(self, path: Path, modules: int, size_bytes: int) -> None:
        size_kb = max(size_bytes / 1024.0, 0.1)
        icon = self.paint("✔", SUCCESS, bold=True)
        message = self.paint("QR code berhasil dibuat", SUCCESS, bold=True)
        target = self.paint(str(path), ACCENT, bold=True)
        meta = self.paint(f"({modules}×{modules} modul, {size_kb:.1f} KB)", MUTED)
        print(f"  {icon} {message} → {target} {meta}")

    def info(self, message: str) -> None:
        print(f"  {self.paint('›', ACCENT, bold=True)} {message}")

    def warn(self, message: str) -> None:
        text = self.paint(message, WARNING)
        print(f"  {self.paint('!', WARNING, bold=True)} {text}", file=sys.stderr)

    def error(self, message: str) -> None:
        text = self.paint(message, DANGER)
        print(f"  {self.paint('✖', DANGER, bold=True)} {text}", file=sys.stderr)

    def prompt(self, label: str, *, default: str = "") -> str:
        prefix = self.paint("?", ACCENT, bold=True)
        suffix = self.paint(f" [{default}]", MUTED) if default else ""
        return input(f"  {prefix} {label}{suffix}: ").strip()


# --------------------------------------------------------------------------
# Validasi & pembuatan QR
# --------------------------------------------------------------------------
HEX_COLOR_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*)://")
INVALID_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def normalize_url(raw: str) -> str:
    """Tambahkan skema https:// bila belum ada dan validasi host."""
    value = raw.strip()
    if not value:
        raise ValueError("URL tidak boleh kosong.")

    match = SCHEME_RE.match(value)
    if match is None:
        value = "https://" + value
        match = SCHEME_RE.match(value)
    if match is not None and match.group(1).lower() not in {"http", "https"}:
        raise ValueError("hanya URL http:// atau https:// yang didukung.")

    authority = value.split("://", 1)[1].split("/", 1)[0]
    if not authority or authority[:1] in {"?", "#"}:
        raise ValueError("URL tidak memiliki host yang valid.")
    return value


def normalize_hex(value: str, field: str) -> str:
    match = HEX_COLOR_RE.match(value.strip())
    if match is None:
        raise ValueError(
            f"{field} harus warna hex 6 digit (contoh: #00E5FF), bukan {value!r}."
        )
    return "#" + match.group(1).upper()


def output_name_for_url(url: str) -> str:
    """Nama file default berdasarkan domain, mis. https://example.com/x -> example.com.png."""
    host = urlsplit(url).hostname or "qr"
    name = INVALID_FILENAME_RE.sub("_", host).strip(" .")
    return f"{name or 'qr'}.png"


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255.0 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    """Rasio kontras WCAG antara dua warna hex."""
    a, b = _relative_luminance(first), _relative_luminance(second)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def generate_qr(
    target: str,
    output: str | Path,
    *,
    fill: str,
    back: str,
    box_size: int,
    border: int,
    error_level: str,
) -> tuple[Path, int]:
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_LEVELS[error_level],
        box_size=box_size,
        border=border,
    )
    qr.add_data(target)
    qr.make(fit=True)
    image = qr.make_image(fill_color=fill, back_color=back)

    path = Path(output).expanduser()
    if not path.suffix:
        path = path.with_suffix(".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path.resolve(), int(qr.modules_count)


def process_target(console: Console, args: argparse.Namespace, raw_url: str) -> None:
    target = normalize_url(raw_url)
    if target != raw_url.strip():
        console.info(f"URL dinormalisasi → {console.paint(target, ACCENT, bold=True)}")
    if contrast_ratio(args.fill, args.back) < 3.0:
        console.warn("kontras warna QR rendah - hasil mungkin sulit dipindai.")

    output = args.output or output_name_for_url(target)
    path, modules = generate_qr(
        target,
        output,
        fill=args.fill,
        back=args.back,
        box_size=args.box_size,
        border=args.border,
        error_level=args.ec,
    )
    console.spinner(f"Membuat QR code {modules}×{modules}")
    console.success(path, modules, path.stat().st_size)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrmaker",
        description="Generator QR code berwarna untuk terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "contoh:\n"
            "  python main.py\n"
            "  python main.py example.com\n"
            '  python main.py example.com --fill "#00E5FF" --back "#0B0F19"\n'
        ),
    )
    parser.add_argument("url", nargs="?", help="URL tujuan; kosongkan untuk mode interaktif")
    parser.add_argument(
        "-o", "--output", default=None,
        help="path file hasil (default: <domain>.png, mis. example.com.png)",
    )
    parser.add_argument(
        "-f", "--fill", default="#000000", metavar="HEX",
        help="warna modul QR (default: #000000)",
    )
    parser.add_argument(
        "-b", "--back", default="#FFFFFF", metavar="HEX",
        help="warna latar QR (default: #FFFFFF)",
    )
    parser.add_argument(
        "-s", "--box-size", type=int, default=12,
        help="ukuran tiap modul dalam piksel (default: 12)",
    )
    parser.add_argument(
        "--border", type=int, default=2,
        help="lebar quiet zone dalam modul (default: 2)",
    )
    parser.add_argument(
        "--ec", choices=tuple(ERROR_LEVELS), default="H",
        help="level error correction (default: H)",
    )
    parser.add_argument("--no-color", action="store_true", help="matikan warna ANSI")
    parser.add_argument(
        "--no-animation", action="store_true",
        help="matikan animasi banner & spinner",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.box_size <= 40:
        parser.error("--box-size harus di antara 1 dan 40")
    if not 0 <= args.border <= 16:
        parser.error("--border harus di antara 0 dan 16")
    return args


def _interactive(console: Console, args: argparse.Namespace) -> int:
    clear_screen()
    first_round = True
    while True:
        console.banner(animate=first_round)
        first_round = False

        try:
            raw_url = console.prompt("Target url")
        except EOFError:
            sys.stdout.write("\n")
            return 0

        if not raw_url:
            console.warn("URL tidak boleh kosong.")
        else:
            try:
                process_target(console, args, raw_url)
            except (ValueError, OSError, DataOverflowError) as exc:
                console.error(str(exc))

        try:
            again = console.prompt("Ulangi? (y/n)", default="n").lower()
        except EOFError:
            sys.stdout.write("\n")
            return 0
        if again not in {"y", "ya", "yes"}:
            return 0
        clear_screen()


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdout()
    args = parse_args(argv)

    console = Console(
        color=not args.no_color and _supports_color(),
        animate=not args.no_animation,
    )

    try:
        args.fill = normalize_hex(args.fill, "warna QR")
        args.back = normalize_hex(args.back, "warna latar")
    except ValueError as exc:
        console.error(str(exc))
        return 2

    try:
        if args.url:
            console.banner()
            process_target(console, args, args.url)
            return 0
        return _interactive(console, args)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        console.warn("dibatalkan oleh pengguna")
        return 130
    except (ValueError, OSError, DataOverflowError) as exc:
        console.error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
