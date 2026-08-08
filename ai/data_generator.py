"""
Phase 3A — generator data test berbasis AI.

ALUR (sesuai brief):

    ada API key? ── tidak ──> fallback Faker
        │ ya
        ▼
    panggil model ──> validasi schema ──┬── valid ──> pakai
                                        └── invalid ──> retry SEKALI
                                                        └── masih invalid ──> fallback

Data yang BENAR-BENAR dipakai dilampirkan ke Allure, beserta jalurnya
(ai / fallback) — supaya reviewer bisa melihat mekanismenya bekerja.
"""
import json
import logging
import os

import allure
from pydantic import ValidationError

from .fallback import faker_company, faker_customer
from .schemas import CompanyData, CustomerData

log = logging.getLogger(__name__)

MAX_RETRY = 1  # sengaja 1: hemat token, dan fallback sudah tersedia

# ---------------------------------------------------------------------------
# Prompt PERSIS yang dikirim. Salin blok ini apa adanya ke AI_USAGE.md —
# brief meminta "the exact prompts you send".
# ---------------------------------------------------------------------------

COMPANY_PROMPT = """Generate ONE fictional Indonesian company for software testing.

Return ONLY a JSON object. No markdown fences, no explanation, no extra text.

Required keys and constraints:
  name            PT or CV company name, max 100 chars
  email           lowercase, derived from the company name, domain .co.id
  phone           DIGITS ONLY, no spaces or dashes, Jakarta landline format (021 + 8 digits)
  industry_type   one of: Retail, Manufacturing, Services, Technology
  company_type    one of: PT, CV, UD
  language        "Indonesia"
  street_address  Indonesian street address with a house number
  country         "Indonesia"
  province        a real Indonesian province
  city            a real city INSIDE that province
  district        a real district INSIDE that city
  zone            a real zone/kelurahan INSIDE that district
  postal_code     EXACTLY 5 digits, and it must be the real postal code for that zone

The geographic chain must be internally consistent: city belongs to province,
district belongs to city, zone belongs to district, postal_code belongs to zone.
An inconsistent chain is rejected by the form under test."""

CUSTOMER_PROMPT = """Generate ONE fictional Indonesian retail customer for software testing.

Return ONLY a JSON object. No markdown fences, no explanation, no extra text.

Required keys and constraints:
  name      shop or business name, Indonesian style, max 100 chars
  contact   DIGITS ONLY, Indonesian mobile number starting with 08, 10-13 digits
  address   Indonesian street address including the city"""


def _call_model(prompt: str) -> dict:
    """
    Kirim prompt ke model, kembalikan dict hasil parse.

    API key dibaca dari environment variable — tidak pernah hardcode,
    tidak pernah di-commit (brief: non-negotiable).

    Ganti isi fungsi ini kalau memakai provider lain. Yang penting kontraknya
    tetap: terima prompt string, kembalikan dict, lempar exception saat gagal.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["AI_API_KEY"])
    response = client.messages.create(
        model=os.environ.get("AI_MODEL", "claude-sonnet-4-6"),
        max_tokens=512,          # dibatasi: kita hanya butuh satu objek JSON kecil
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Model kadang tetap membungkus dengan ```json meski diminta tidak.
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


def _generate(prompt: str, model_cls, fallback_fn, label: str):
    """
    Inti alur generate. Dipakai bersama oleh company dan customer.

    Mengembalikan (data, source) dengan source = "ai" atau "fallback".

    Kegagalan TIDAK ditelan diam-diam: tiap kali jatuh ke fallback, alasannya
    dicatat di log dan ikut dilampirkan ke Allure.
    """
    reason = None

    if not os.environ.get("AI_API_KEY"):
        reason = "AI_API_KEY tidak diisi"
    else:
        for attempt in range(MAX_RETRY + 1):
            try:
                raw = _call_model(prompt)
                data = model_cls(**raw)          # ← gerbang schema
                _attach(label, data, source="ai", note=f"percobaan ke-{attempt + 1}")
                return data, "ai"
            except ValidationError as e:
                reason = f"output tidak lolos schema (percobaan {attempt + 1}): {e.error_count()} error"
                log.warning("%s: %s", label, reason)
            except Exception as e:                # network, parse, auth
                reason = f"panggilan model gagal (percobaan {attempt + 1}): {type(e).__name__}: {e}"
                log.warning("%s: %s", label, reason)

    data = fallback_fn()
    _attach(label, data, source="fallback", note=reason)
    return data, "fallback"


def _attach(label: str, data, source: str, note: str | None = None):
    """
    Lampirkan data yang dipakai ke Allure (syarat brief).

    Yang dilampirkan bukan cuma datanya, tapi juga JALUR mana yang dipakai
    dan kenapa — itu yang membuktikan schema validation dan fallback bekerja.
    """
    payload = {
        "source": source,
        "reason": note,
        "data": data.model_dump(),
    }
    allure.attach(
        json.dumps(payload, indent=2, ensure_ascii=False),
        name=f"{label} ({source})",
        attachment_type=allure.attachment_type.JSON,
    )


def generate_company() -> tuple[CompanyData, str]:
    return _generate(COMPANY_PROMPT, CompanyData, faker_company, "company data")


def generate_customer() -> tuple[CustomerData, str]:
    return _generate(CUSTOMER_PROMPT, CustomerData, faker_customer, "customer data")
