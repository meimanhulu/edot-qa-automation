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


def _maestro_command(flow_path: Path, env_vars: dict) -> list[str]:
    """
    Susun perintah maestro beserta variabel yang diteruskan ke flow.

    Sejak Maestro 1.39.9 CLI-nya berjalan NATIVE di Windows, sehingga WSL tidak
    lagi dibutuhkan dan tidak ada penerjemahan path.

    Variabel dilewatkan lewat flag `-e`, BUKAN lewat environment proses.
    Diverifikasi: dengan environment proses saja, `appId: ${EWORK_APP_ID}`
    terbaca sebagai "undefined" dan flow gagal dengan
    "Package undefined is not installed". Flag `-e` diteruskan sampai ke
    sub-flow yang dipanggil runFlow.
    """
    cmd = ["maestro", "test"]
    for key, value in env_vars.items():
        cmd += ["-e", f"{key}={value}"]
    cmd.append(str(flow_path))
    return cmd


def maestro_available() -> bool:
    """Cek Maestro terpasang. Dipakai untuk skip test dengan alasan jelas."""
    if platform.system() == "Windows":
        return shutil.which("wsl") is not None
    return shutil.which("maestro") is not None


def run_flow(flow_name: str, extra_env: dict | None = None, timeout: int = 300):
    """
    Jalankan satu flow Maestro.

    Kredensial dan data test dilewatkan lewat flag `-e` ke Maestro —
    brief melarang hardcode di YAML.

    Mengembalikan CompletedProcess apa adanya. Output selalu dilampirkan
    ke Allure, baik berhasil maupun gagal, supaya reviewer bisa melihat
    apa yang benar-benar terjadi di device.
    """
    flow_path = FLOWS_DIR / flow_name

    passthrough = {k: str(v) for k, v in (extra_env or {}).items() if v}
    cmd = _maestro_command(flow_path, passthrough)

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, shell=True
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