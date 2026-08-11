"""TC-MOB-002 - Create customer di eWork SFA."""
import allure
import pytest

from ai.fallback import (
    CHANNEL_TYPE,
    contact_person_name,
    customer_email,
    random_address_type,
    random_customer_type,
    random_indonesian_address,
    random_nik,
)
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
    field terisi dan verifikasi mencakup lebih banyak permukaan. Domainnya
    gmail.com - domain kustom berisiko ditolak validasi aplikasi.

    Seluruh nilai acak per run: nama outlet, nomor telepon, email, dan nama
    contact person. Test yang selalu memakai nilai sama bisa lolos karena
    record lama, bukan karena input baru benar-benar diterima.
    """
    # Seluruh nilai dibuat ACAK per run supaya tidak bentrok dengan data
    # sebelumnya di shared environment, dan supaya test tidak diam-diam
    # bergantung pada satu nilai tetap.
    email = customer_email(customer_data.name)
    contact = contact_person_name()
    customer_type = random_customer_type()
    address_type = random_address_type()
    address = random_indonesian_address()
    ktp = random_nik()

    result = run_flow(
        "create_customer.yaml",
        extra_env={
            "EWORK_APP_ID": env["ework_app_id"],
            "EWORK_COMPANY_ID": env["ework_company_id"],
            "EWORK_USERNAME": env["ework_username"],
            "EWORK_PASSWORD": env["ework_password"],
            "CUSTOMER_NAME": customer_data.name,
            "CUSTOMER_PHONE": customer_data.contact.lstrip("0"),
            "CUSTOMER_EMAIL": email,
            "CUSTOMER_CONTACT_PERSON": contact,
            "CHANNEL_TYPE": CHANNEL_TYPE,
            "CUSTOMER_TYPE": customer_type,
            "ADDRESS_TYPE": address_type,
            "CUSTOMER_ADDRESS": address,
            "KTP_NUMBER": ktp,
        },
    )

    allure.attach(
        f"outlet name    : {customer_data.name}\n"
        f"phone          : {customer_data.contact.lstrip('0')}\n"
        f"email          : {email}\n"
        f"contact person : {contact}\n"
        f"channel type   : {CHANNEL_TYPE}\n"
        f"customer type  : {customer_type}\n"
        f"address type   : {address_type}\n"
        f"address        : {address}\n"
        f"ktp            : {ktp}",
        name="data customer yang dipakai",
        attachment_type=allure.attachment_type.TEXT,
    )

    # Tier 2: flow gagal berarti salah satu assertVisible di YAML tidak cocok,
    # yaitu nilai yang tersimpan di field berbeda dari yang diinput.
    assert result.returncode == 0, (
        f"Flow create customer gagal (exit {result.returncode}):\n{result.stdout[-2000:]}"
    )