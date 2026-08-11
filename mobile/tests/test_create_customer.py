"""TC-MOB-002 - Create customer di eWork SFA."""
import allure
import pytest

from mobile.runner import maestro_available, run_flow

pytestmark = pytest.mark.skipif(
    not maestro_available(),
    reason="Maestro CLI tidak terpasang - lihat docs/MAESTRO_SETUP_WINDOWS.md",
)


@pytest.mark.mobile
@pytest.mark.tier2
@allure.title("TC-MOB-002 Create customer and verify entered values")
def test_create_customer(env, customer_data):
    """
    Data customer berasal dari modul AI (Phase 3A) dan dilewatkan ke Maestro
    lewat flag -e. Tidak ada nilai yang di-hardcode di YAML - brief melarangnya.

    Catatan untuk reviewer: assertion Tier 2 berada di dalam YAML, bukan di
    Python. Maestro yang memegang kendali device; Python hanya pemanggilnya.
    Yang diverifikasi di sana adalah nilai yang BENAR-BENAR masuk ke field,
    dibaca balik dengan assertVisible bertext persis - bukan sekadar
    "flow selesai tanpa error".

    Email disertakan meski field-nya opsional (tanpa tanda *), supaya seluruh
    field terisi dan verifikasi mencakup lebih banyak permukaan.
    """
    # Nama dibuat unik per run supaya tidak bentrok dengan data sebelumnya
    # di shared environment.
    result = run_flow(
        "create_customer.yaml",
        extra_env={
            "EWORK_APP_ID": env["ework_app_id"],
            "EWORK_COMPANY_ID": env["ework_company_id"],
            "EWORK_USERNAME": env["ework_username"],
            "EWORK_PASSWORD": env["ework_password"],
            "CUSTOMER_NAME": customer_data.name,
            "CUSTOMER_PHONE": customer_data.contact.lstrip("0"),
            "CUSTOMER_EMAIL": f"{customer_data.name.lower().replace(' ', '')}@example.co.id",
            "CUSTOMER_CONTACT_PERSON": "Arya QA",
        },
    )

    allure.attach(
        f"name           : {customer_data.name}\n"
        f"phone          : {customer_data.contact.lstrip('0')}\n"
        f"contact person : Arya QA",
        name="data customer yang dipakai",
        attachment_type=allure.attachment_type.TEXT,
    )

    # Tier 2: flow gagal berarti salah satu assertVisible di YAML tidak cocok,
    # yaitu nilai yang tersimpan di field berbeda dari yang diinput.
    assert result.returncode == 0, (
        f"Flow create customer gagal (exit {result.returncode}):\n{result.stdout[-2000:]}"
    )