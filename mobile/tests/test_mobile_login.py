"""TC-MOB-001 — login eWork SFA."""
import allure
import pytest

from mobile.runner import maestro_available, run_flow

pytestmark = pytest.mark.skipif(
    not maestro_available(),
    reason="Maestro CLI tidak terpasang — lihat docs/MAESTRO_SETUP_WINDOWS.md",
)


@pytest.mark.mobile
@pytest.mark.tier1
@allure.title("TC-MOB-001 Login to eWork SFA")
def test_mobile_login(env):
    result = run_flow(
        "login.yaml",
        extra_env={
            "EWORK_APP_ID": env["ework_app_id"],
            "EWORK_COMPANY_ID": env["ework_company_id"],
            "EWORK_USERNAME": env["ework_username"],
            "EWORK_PASSWORD": env["ework_password"],
        },
    )

    # stdout disertakan di pesan assert supaya kegagalan langsung terbaca
    # di terminal tanpa harus membuka laporan Allure lebih dulu.
    assert result.returncode == 0, (
        f"Flow login gagal (exit {result.returncode}):\n{result.stdout[-2000:]}"
    )
