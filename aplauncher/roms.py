"""ROM checks: byte order normalisation and SHA-1 identification."""
import hashlib
from pathlib import Path

SM64_HASHES = {
    "9bef1128717f958171a4afac3ed78ee2bb4e86ce": ("us", "USA"),
    "8a20a5c83d6ceb0f0506cfc9fa20d8f438cafe51": ("jp", "Japan"),
}

# From Shipwright docs/supportedHashes.json. Master Quest is not supported by SoH Archipelago.
OOT_HASHES = {
    "328a1f1beba30ce5e178f031662019eb32c5f3b5": "PAL 1.0",
    "cfbb98d392e4a9d39da8285d10cbef3974c2f012": "PAL 1.1",
    "0227d7c0074f2d0ac935631990da8ec5914597b4": "PAL GC",
    "cee6bc3c2a634b41728f2af8da54d9bf8cc14099": "PAL GC (Debug)",
    "ad69c91157f6705e8ab06c79fe08aad47bb57ba7": "NTSC 1.0 (US)",
    "d3ecb253776cd847a5aa63d859d8c89a2f37b364": "NTSC 1.1 (US)",
    "41b3bdc48d98c48529219919015a1af22f5057c2": "NTSC 1.2 (US)",
    "c892bbda3993e66bd0d56a10ecd30b1ee612210f": "NTSC 1.0 (JP)",
    "dbfc81f655187dc6fefd93fa6798face770d579d": "NTSC 1.1 (JP)",
    "fa5f5942b27480d60243c2d52c0e93e26b9e6b86": "NTSC 1.2 (JP)",
    "b82710ba2bd3b4c6ee8aa1a7e9acf787dfc72e9b": "NTSC GC (US)",
    "0769c84615422d60f16925cd859593cdfa597f84": "NTSC GC (JP)",
    "2ce2d1a9f0534c9cd9fa04ea5317b80da21e5e73": "NTSC GC (JP) (Collector's Edition)",
}
OOT_MQ_HASHES = {
    "f46239439f59a2a594ef83cf68ef65043b1bffe2", "079b855b943d6ad8bd1eb026c0ed169ecbdac7da",
    "50bebedad9e0f10746a52b07239e47fa6c284d03", "cfecfdc58d650e71a200c81f033de4e6d617a9f6",
    "8b5d13aac69bfbf989861cfdc50b1d840945fc1d", "dd14e143c4275861fe93ea79d0c02e36ae8c6c2f",
}


class RomError(Exception):
    pass


def to_z64(data: bytes) -> bytes:
    """Convert .v64 (16-bit swapped) or .n64 (32-bit little endian) dumps to big endian .z64."""
    head = data[:4]
    if head == b"\x80\x37\x12\x40":
        return data
    if head == b"\x37\x80\x40\x12":
        b = bytearray(data)
        b[0::2], b[1::2] = data[1::2], data[0::2]
        return bytes(b)
    if head == b"\x40\x12\x37\x80":
        b = bytearray(len(data))
        b[0::4], b[1::4], b[2::4], b[3::4] = data[3::4], data[2::4], data[1::4], data[0::4]
        return bytes(b)
    raise RomError("Das ist keine N64-ROM (unbekannter Dateianfang). ISO/ZIP-Dateien gehen nicht, "
                   "es muss eine entpackte .z64/.n64/.v64 sein.")


def _read(path: str) -> bytes:
    p = Path(path)
    if not path or not p.is_file():
        raise RomError("ROM-Datei nicht gefunden.")
    if p.suffix.lower() in (".zip", ".7z", ".rar"):
        raise RomError("Bitte die ROM erst entpacken (.z64/.n64/.v64).")
    if p.stat().st_size > 128 * 1024 * 1024:
        raise RomError("Datei ist zu groß für eine N64-ROM.")
    return to_z64(p.read_bytes())


def check_sm64(path: str) -> tuple[str, str, bytes]:
    """Returns (region, label, z64 bytes) or raises RomError."""
    data = _read(path)
    sha = hashlib.sha1(data).hexdigest()
    if sha in SM64_HASHES:
        region, label = SM64_HASHES[sha]
        return region, f"Super Mario 64 ({label})", data
    if b"SUPER MARIO 64" in data[0x20:0x34]:
        raise RomError("Super Mario 64 erkannt, aber falsche Version. Nur USA oder Japan "
                       "(nicht Europa/Shindou) werden unterstützt.")
    raise RomError("Keine passende Super-Mario-64-ROM (USA oder Japan nötig).")


def check_oot(path: str) -> tuple[str, bytes]:
    """Returns (label, z64 bytes) or raises RomError."""
    data = _read(path)
    sha = hashlib.sha1(data).hexdigest()
    if sha in OOT_HASHES:
        return f"Ocarina of Time {OOT_HASHES[sha]}", data
    if sha in OOT_MQ_HASHES:
        raise RomError("Das ist Master Quest. SoH-Archipelago braucht die normale (nicht-MQ) Version.")
    if b"ZELDA" in data[0x20:0x34] or b"THE LEGEND OF ZELDA" in data[0x20:0x34]:
        raise RomError("Zelda-ROM erkannt, aber keine von SoH unterstützte Version "
                       "(evtl. verändert/gepatcht oder Majora's Mask).")
    raise RomError("Keine passende Ocarina-of-Time-ROM.")


def describe(game: str, path: str) -> tuple[bool, str]:
    try:
        if game == "sm64":
            return True, check_sm64(path)[1]
        if game == "soh":
            return True, check_oot(path)[0]
    except RomError as e:
        return False, str(e)
    except OSError as e:
        return False, f"ROM nicht lesbar: {e}"
    return True, ""
