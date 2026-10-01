"""Downloads and installs Archipelago, Ship of Harkinian and the SM64 build toolchain."""
import os
import shutil
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path

from . import config, roms
from .config import Paths

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class InstallError(Exception):
    pass


class Installer:
    def __init__(self, paths: Paths, log, progress):
        self.p = paths
        self.log = log            # log(str)
        self.progress = progress  # progress(fraction or None, text)

    # ---------- helpers ----------
    def download(self, url: str, name: str) -> Path:
        """Fetch url into the downloads folder, or take it from the bundled payload."""
        bundled = config.payload_dir() / name
        if bundled.is_file():
            self.log(f"Nutze mitgelieferte Datei {name}")
            return bundled
        self.p.downloads.mkdir(parents=True, exist_ok=True)
        dest = self.p.downloads / name
        if dest.is_file() and dest.stat().st_size > 0:
            return dest
        tmp = dest.with_suffix(dest.suffix + ".part")
        self.log(f"Lade {name} herunter ...")
        req = urllib.request.Request(url, headers={"User-Agent": "APLauncher"})
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while chunk := r.read(1 << 16):
                f.write(chunk)
                done += len(chunk)
                if total:
                    self.progress(done / total, f"{name}: {done >> 20} / {total >> 20} MB")
        tmp.replace(dest)
        self.progress(None, "")
        return dest

    def run(self, args, cwd=None, env=None, check=True) -> int:
        """Run a process and stream its output into the log."""
        proc = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, creationflags=NO_WINDOW,
                                text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                self.log(line)
        code = proc.wait()
        if check and code != 0:
            raise InstallError(f"Befehl fehlgeschlagen ({code}): {args if isinstance(args, str) else args[0]}")
        return code

    # ---------- Archipelago ----------
    def archipelago_ok(self) -> bool:
        return self.p.ap_generate.is_file() and (self.p.ap / "custom_worlds" / "oot_soh.apworld").is_file()

    def install_archipelago(self):
        if not self.p.ap_generate.is_file():
            setup = self.download(config.AP_URL, f"Setup.Archipelago.{config.AP_VERSION}.exe")
            self.log(f"Installiere Archipelago {config.AP_VERSION} nach {self.p.ap} ...")
            self.progress(None, "Archipelago wird installiert ...")
            self.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
                      "/NOICONS", "/TASKS=", f"/DIR={self.p.ap}"])
            if not self.p.ap_generate.is_file():
                raise InstallError("Archipelago-Installation fehlgeschlagen.")
        # The SoH world is a custom world; the host needs it to generate, so everyone gets it.
        world = self.download(config.SOH_APWORLD_URL, f"oot_soh-{config.SOH_VERSION}.apworld")
        (self.p.ap / "custom_worlds").mkdir(exist_ok=True)
        shutil.copyfile(world, self.p.ap / "custom_worlds" / "oot_soh.apworld")
        self.log("Archipelago ist bereit.")

    def ensure_templates(self):
        """Archipelago writes one option template per game; copy ours as the player's YAMLs."""
        tdir = self.p.ap / "Players" / "Templates"
        if not (tdir / "Super Mario 64.yaml").is_file() or not (tdir / "Ship of Harkinian.yaml").is_file():
            self.log("Erzeuge Options-Vorlagen ...")
            self.run([str(self.p.ap / "ArchipelagoLauncher.exe"), "Generate Template Options"],
                     cwd=self.p.ap, check=False)
        self.p.yamls.mkdir(parents=True, exist_ok=True)
        for key, g in config.GAMES.items():
            dest = self.p.yaml_for(key)
            src = tdir / f"{g['ap_game']}.yaml"
            if not dest.is_file() and src.is_file():
                shutil.copyfile(src, dest)

    # ---------- Ship of Harkinian ----------
    def soh_ok(self) -> bool:
        return self.p.soh_exe.is_file() and (self.p.soh / "oot.o2r").is_file()

    def install_soh(self, rom_path: str):
        label, data = roms.check_oot(rom_path)
        self.log(f"ROM erkannt: {label}")
        if not self.p.soh_exe.is_file():
            z = self.download(config.SOH_ZIP_URL, f"SoH_Archipelago_{config.SOH_VERSION}_Windows.zip")
            self.log("Entpacke Ship of Harkinian ...")
            self.progress(None, "SoH wird entpackt ...")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(self.p.soh)
        if not (self.p.soh / "oot.o2r").is_file():
            self.extract_soh_assets(data)
        self.log("Ship of Harkinian ist bereit.")

    def extract_soh_assets(self, rom: bytes):
        """SoH builds oot.o2r from a ROM placed next to soh.exe on first start; do that once, then close it."""
        rom_copy = self.p.soh / "oot.z64"
        rom_copy.write_bytes(rom)
        o2r = self.p.soh / "oot.o2r"
        self.log("Erzeuge Spieldaten aus der ROM (SoH startet kurz, 1-5 Minuten) ...")
        self.progress(None, "OoT-Daten werden erzeugt ...")
        proc = subprocess.Popen([str(self.p.soh_exe)], cwd=self.p.soh)
        try:
            last, stable = -1, 0
            deadline = time.time() + 600
            while time.time() < deadline:
                time.sleep(2)
                size = o2r.stat().st_size if o2r.is_file() else -1
                stable = stable + 1 if size == last and size > 1_000_000 else 0
                last = size
                if stable >= 3:
                    break
                if proc.poll() is not None and size < 0:
                    raise InstallError("SoH hat sich beendet, ohne oot.o2r zu erzeugen.")
            else:
                raise InstallError("Zeitüberschreitung beim Erzeugen von oot.o2r.")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            rom_copy.unlink(missing_ok=True)
        self.log("oot.o2r erzeugt.")

    # ---------- Super Mario 64 (sm64ex Archipelago build) ----------
    def sm64_ok(self, region="us") -> bool:
        return self.p.sm64_exe_for(region).is_file() and self.sm64_patches_applied()

    def _patch_marker(self) -> Path:
        return self.p.sm64 / ".aplauncher_patches"

    def sm64_patches_applied(self) -> bool:
        try:
            return self._patch_marker().read_text().split() == config.SM64_PATCHES
        except OSError:
            return False

    def apply_sm64_patches(self, src: str):
        if self.sm64_patches_applied():
            return
        # Start from a clean tree so a changed patch list never stacks on old patches.
        self.bash(f"cd '{src}' && git checkout -- . && git clean -fdq -e 'baserom.*' -e build")
        for patch in config.SM64_PATCHES:
            self.log(f"Wende Patch an: {patch}")
            self.bash(f"cd '{src}' && git apply '{patch}'")
        self._patch_marker().write_text("\n".join(config.SM64_PATCHES))

    def msys_env(self) -> dict:
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        env["MSYSTEM"] = "MINGW64"
        env["CHERE_INVOKING"] = "1"
        return env

    def bash(self, cmd: str, check=True) -> int:
        return self.run([str(self.p.msys / "usr" / "bin" / "bash.exe"), "--login", "-c", cmd],
                        cwd=self.p.root, env=self.msys_env(), check=check)

    @staticmethod
    def posix(path: Path) -> str:
        s = str(path.resolve())
        return "/" + s[0].lower() + s[2:].replace("\\", "/")

    def install_msys(self):
        bash = self.p.msys / "usr" / "bin" / "bash.exe"
        if not bash.is_file():
            sfx = self.download(config.MSYS2_URL, "msys2-x86_64-latest.sfx.exe")
            self.log("Entpacke MSYS2 (Compiler-Umgebung) ...")
            self.progress(None, "MSYS2 wird entpackt ...")
            self.run([str(sfx), "-y", f"-o{self.p.root}"])
            self.log("MSYS2 Ersteinrichtung ...")
            self.bash("true", check=False)
        if self.bash("pacman -Q " + " ".join(config.MSYS2_PACKAGES) + " >/dev/null 2>&1", check=False) == 0:
            return
        self.log("Aktualisiere MSYS2 und installiere Compiler (einige Minuten) ...")
        self.progress(None, "Compiler werden installiert ...")
        # MSYS2 updates its core first and may exit; the second run finishes the update.
        self.bash("pacman -Syu --noconfirm", check=False)
        self.bash("pacman -Syu --noconfirm", check=False)
        self.bash("pacman -S --needed --noconfirm " + " ".join(config.MSYS2_PACKAGES))

    def install_sm64(self, rom_path: str):
        if " " in str(self.p.root):
            raise InstallError("Der Installationsordner darf keine Leerzeichen enthalten (MSYS2/make).")
        region, label, data = roms.check_sm64(rom_path)
        self.log(f"ROM erkannt: {label}")
        if self.sm64_ok(region):
            self.log("Super Mario 64 ist schon gebaut.")
            return
        self.install_msys()
        src = self.posix(self.p.sm64)
        if not (self.p.sm64 / "Makefile").is_file():
            self.log("Lade sm64ex (Archipelago) Quellcode ...")
            self.progress(None, "Quellcode wird geladen ...")
            shutil.rmtree(self.p.sm64, ignore_errors=True)
            self.bash(f"git clone --recursive --depth=1 -b {config.SM64_BRANCH} {config.SM64_REPO} '{src}'")
        self.apply_sm64_patches(src)
        (self.p.sm64 / f"baserom.{region}.z64").write_bytes(data)
        jobs = max(1, (os.cpu_count() or 4))
        self.log(f"Kompiliere Super Mario 64 ({jobs} Kerne, ca. 5-10 Minuten) ...")
        self.progress(None, "Super Mario 64 wird kompiliert ...")
        self.bash(f"cd '{src}' && export CC=/mingw64/bin/gcc CXX=/mingw64/bin/g++ && make -j{jobs} VERSION={region}")
        if not self.sm64_ok(region):
            raise InstallError("Build fertig, aber die sm64-exe fehlt. Siehe Log.")
        self.log("Super Mario 64 ist bereit.")

    def sm64_region_built(self) -> str | None:
        for region in ("us", "jp"):
            if self.sm64_ok(region):
                return region
        return None
