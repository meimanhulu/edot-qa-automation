"""
conftest.py (root) — fixture yang dipakai suite web DAN mobile.
"""
import os

import allure
import pytest
from dotenv import load_dotenv


def pytest_configure(config):
    """Muat .env sekali sebelum collection, supaya fixture bisa membacanya."""
    load_dotenv()


def _required(name: str) -> str:
    """
    Baca env wajib. Gagal CEPAT dengan pesan jelas bila kosong.

    Kenapa gagal cepat: env kosong yang lolos akan menyebabkan test gagal
    di tengah dengan pesan yang menyesatkan (mis. 'element not found'),
    dan triage akan salah memvonisnya sebagai cacat locator.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Env wajib '{name}' belum diisi. Salin .env.example jadi .env lalu isi nilainya."
        )
    return value


@pytest.fixture(scope="session")
def env() -> dict:
    """
    SATU-SATUNYA tempat os.environ dibaca.

    Modul lain menerima nilainya sebagai argumen. Kalau ada env baru,
    cukup ubah di sini — bukan menyisir banyak file.
    """
    return {
        "base_url": _required("ESUITE_BASE_URL"),
        "email": _required("ESUITE_EMAIL"),
        "password": _required("ESUITE_PASSWORD"),
        "headless": os.environ.get("HEADLESS", "true").lower() == "true",
        "timeout_ms": int(os.environ.get("DEFAULT_TIMEOUT_MS", "30000")),
        # mobile — opsional, hanya wajib saat suite mobile dijalankan
        "ework_app_id": os.environ.get("EWORK_APP_ID", ""),
        "ework_company_id": os.environ.get("EWORK_COMPANY_ID", ""),
        "ework_username": os.environ.get("EWORK_USERNAME", ""),
        "ework_password": os.environ.get("EWORK_PASSWORD", ""),
    }


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """
    Simpan hasil tiap fase ke item, supaya fixture teardown bisa tahu
    apakah test barusan gagal. Dipakai oleh fixture screenshot.
    """
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture
def company_data():
    """
    Data company dari modul AI, dengan fallback otomatis.

    Sumber (ai / fallback) ikut dilampirkan ke Allure oleh generator-nya.
    """
    from ai.data_generator import generate_company

    data, source = generate_company()
    allure.dynamic.parameter("data_source", source)
    return data


@pytest.fixture
def customer_data():
    """Data customer dari modul AI, dengan fallback otomatis."""
    from ai.data_generator import generate_customer

    data, source = generate_customer()
    allure.dynamic.parameter("data_source", source)
    return data