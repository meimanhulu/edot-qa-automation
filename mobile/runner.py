"""
Wrapper Pytest yang memanggil Maestro.

Brief: "Flows are YAML; a Pytest wrapper invokes them so web and mobile
report into the same Allure run."

Tugas modul ini: susun env var, jalankan maestro sebagai subprocess,
lampirkan outputnya ke Allure, kembalikan hasil apa adanya.

Kegagalan TIDAK ditelan di sini — test yang memutuskan lulus atau gagal.
"""
import os
import platform
import shutil
import subprocess
from pathlib import Path

import allure

FLOWS_DIR = Path(__file__).parent / "flows"


def _maestro_command(flow_path: Path) -> list[str]:
    """
    Susun perintah sesuai sistem operasi.

    Windows: Maestro tidak jalan native, harus lewat WSL. Path Windows
    (C:\\Users\\...) juga harus diterjemahkan ke path WSL (/mnt/c/Users/...).
    Detail setup ada di docs/MAESTRO_SETUP_WINDOWS.md.
    """
    if platform.system() == "Windows":
        wsl_path = str(flow_path).replace("\\", "/")
        if len(wsl_path) > 1 and wsl_path[1] == ":":
            drive = wsl_path[0].lower()
            wsl_path = f"/mnt/{drive}{wsl_path[2:]}"
        return ["wsl", "maestro", "test", wsl_path]

    return ["maestro", "test", str(flow_path)]


def maestro_available() -> bool:
    """Cek Maestro terpasang. Dipakai untuk skip test dengan alasan jelas."""
    if platform.system() == "Windows":
        return shutil.which("wsl") is not None
    return shutil.which("maestro") is not None


def run_flow(flow_name: str, extra_env: dict | None = None, timeout: int = 300):
    """
    Jalankan satu flow Maestro.

    Kredensial dan data test dilewatkan sebagai environment variable —
    brief melarang hardcode di YAML.

    Mengembalikan CompletedProcess apa adanya. Output selalu dilampirkan
    ke Allure, baik berhasil maupun gagal, supaya reviewer bisa melihat
    apa yang benar-benar terjadi di device.
    """
    flow_path = FLOWS_DIR / flow_name

    env = os.environ.copy()
    if extra_env:
        env.update({k: str(v) for k, v in extra_env.items()})

    cmd = _maestro_command(flow_path)

    result = subprocess.run(
        cmd, env=env, capture_output=True, text=True, timeout=timeout
    )

    allure.attach(
        result.stdout or "(kosong)",
        name=f"maestro stdout — {flow_name}",
        attachment_type=allure.attachment_type.TEXT,
    )
    if result.stderr.strip():
        allure.attach(
            result.stderr,
            name=f"maestro stderr — {flow_name}",
            attachment_type=allure.attachment_type.TEXT,
        )

    return result
