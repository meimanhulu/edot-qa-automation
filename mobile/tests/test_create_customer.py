"""TC-MOB-004 + TC-MOB-009 — create customer dan verifikasi datanya."""
import allure
import pytest

from mobile.runner import maestro_available, run_flow

pytestmark = pytest.mark.skipif(
    not maestro_available(),
    reason="Maestro CLI tidak terpasang — lihat docs/MAESTRO_SETUP_WINDOWS.md",
)


@pytest.mark.mobile
@pytest.mark.tier2
@allure.title("TC-MOB-004 Create customer and verify data")
def test_create_customer(env, customer_data):
    """
    Catatan untuk reviewer: assertion Tier 2 untuk mobile berada di dalam
    YAML (assertVisible dengan text persis dari data input), bukan di Python.
    Alasannya Maestro yang memegang kendali device; Python hanya pemanggil.

    Data dilewatkan sebagai env var — brief melarang hardcode di YAML.
    """
    result = run_flow(
        "create_customer.yaml",
        extra_env={
            "EWORK_APP_ID": env["ework_app_id"],
            "EWORK_COMPANY_ID": env["ework_company_id"],
            "EWORK_USERNAME": env["ework_username"],
            "EWORK_PASSWORD": env["ework_password"],
            "CUSTOMER_NAME": customer_data.name,
            "CUSTOMER_PHONE": customer_data.contact,
            "CUSTOMER_ADDRESS": customer_data.address,
        },
    )

    allure.attach(
        f"name: {customer_data.name}\ncontact: {customer_data.contact}\naddress: {customer_data.address}",
        name="data customer yang dipakai",
        attachment_type=allure.attachment_type.TEXT,
    )

    # Tier 2: flow gagal berarti salah satu assertVisible di YAML tidak cocok,
    # yaitu nilai yang tersimpan berbeda dari yang diinput.
    assert result.returncode == 0, (
        f"Flow create customer gagal (exit {result.returncode}):\n{result.stdout[-2000:]}"
    )
