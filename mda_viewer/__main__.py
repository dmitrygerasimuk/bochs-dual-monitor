 
# softice_mda_fixascii.py
#
# Reads SoftICE MDA named pipe (full-screen text dump) and prints it to a terminal.
# Additionally fixes the "ASCII tail" in SoftICE memory dump lines:
# SoftICE renders '.' for all non-ASCII bytes; we rebuild the tail from the HEX bytes
# and decode it as CP866 (so Cyrillic/extended chars become visible).
#
# Supported:
#  - Byte view: 0000:0000  8A 10 ...  ..../....
#  - Word view: 0000:0500  0000 2020 ...  .... ....
#
# Notes:
#  - We only replace the trailing ASCII column on matching lines.
#  - Control chars (<0x20 and 0x7F) stay as '.' to keep layout readable.

import os
import re
import select
import sys

from cp866 import cp866_to_utf8

ANSI_CURSOR_HOME = "\33[0;0H"
ANSI_ATTR_RESET  = "\33[0m"

# show control bytes as '.' (recommended for stable layout)
def render_byte_cp866(b: int) -> str:
    if b < 0x20 or b == 0x7F:
        return "."
    # decode single byte as CP866
    return cp866_to_utf8(bytes([b]))

# --- line fixers -------------------------------------------------------------

_ADDR_RE = re.compile(r"^([0-9A-Fa-f]{4}:[0-9A-Fa-f]{4})(.*)$")
_BYTE_TOK_RE = re.compile(r"\b([0-9A-Fa-f]{2})\b")
_WORD_TOK_RE = re.compile(r"\b([0-9A-Fa-f]{4})\b")

def try_fix_byte_view_line(line: str) -> str | None:
    """
    If line is a SoftICE byte-view hexdump line, return fixed version.
    Else return None.
    """
    m = _ADDR_RE.match(line)
    if not m:
        return None

    addr = m.group(1)
    rest = m.group(2)

    # find first 16 byte tokens after the address
    it = list(_BYTE_TOK_RE.finditer(rest))
    if len(it) < 16:
        return None

    # byte view has 16 bytes per line (we take first 16)
    bytes16 = []
    for tok in it[:16]:
        bytes16.append(int(tok.group(1), 16))

    # position in the original line where the 16th byte token ends
    end_in_rest = it[15].end()
    split_pos = len(addr) + end_in_rest  # addr + rest slice end

    # everything after split_pos is "spaces + old ascii tail"
    tail = line[split_pos:]
    # keep original left padding before ascii column
    pad = len(tail) - len(tail.lstrip(" "))
    if pad < 1:
        pad = 2  # typical SoftICE layout

    ascii_fixed = "".join(render_byte_cp866(b) for b in bytes16)

    return line[:split_pos] + (" " * pad) + ascii_fixed

def try_fix_word_view_line(line: str) -> str | None:
    """
    If line is a SoftICE word-view hexdump line, return fixed version.
    Else return None.
    """
    m = _ADDR_RE.match(line)
    if not m:
        return None

    addr = m.group(1)
    rest = m.group(2)

    it = list(_WORD_TOK_RE.finditer(rest))
    if len(it) < 8:
        return None

    # word view: 8 words == 16 bytes, shown as 4-hex groups.
    # SoftICE words are little-endian in memory -> bytes are (lo, hi).
    bytes16 = []
    for tok in it[:8]:
        w = int(tok.group(1), 16)
        lo = w & 0xFF
        hi = (w >> 8) & 0xFF
        bytes16.extend([lo, hi])

    end_in_rest = it[7].end()
    split_pos = len(addr) + end_in_rest

    tail = line[split_pos:]
    pad = len(tail) - len(tail.lstrip(" "))
    if pad < 1:
        pad = 2

    ascii_fixed = "".join(render_byte_cp866(b) for b in bytes16)
    return line[:split_pos] + (" " * pad) + ascii_fixed

def fix_screen_text(screen_text: str) -> str:
    out_lines = []
    for line in screen_text.splitlines(True):  # keep '\n'
        # strip only newline for matching, but keep it to append back
        nl = ""
        core = line
        if core.endswith("\r\n"):
            core, nl = core[:-2], "\r\n"
        elif core.endswith("\n"):
            core, nl = core[:-1], "\n"

        fixed = (
            try_fix_byte_view_line(core)
            or try_fix_word_view_line(core)
            or core
        )
        out_lines.append(fixed + nl)
    return "".join(out_lines)

# --- main loop ---------------------------------------------------------------

def main() -> int:
    mda_pipe = os.getenv("MDA_PIPE")
    if not mda_pipe:
        print("Environment variable MDA_PIPE must contain path to named pipe. Aborting.")
        return 1

    fifo = os.open(mda_pipe, os.O_RDONLY | os.O_NONBLOCK)
    poll = select.poll()
    poll.register(fifo, select.POLLIN)

    try:
        while True:
            if (fifo, select.POLLIN) in poll.poll(1000 // 12):
                data = os.read(fifo, 49_152)
                # decode whole screen as cp866 (as you already do)
                screen = cp866_to_utf8(data)
                # patch only dump-line tails
                screen = fix_screen_text(screen)
                print(ANSI_CURSOR_HOME + screen, end="")
    except KeyboardInterrupt:
        print(ANSI_ATTR_RESET)
        return 0

if __name__ == "__main__":
    sys.exit(main())