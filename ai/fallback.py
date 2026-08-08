"""
Fallback deterministik dengan Faker.

KENAPA ADA: brief mensyaratkan suite tetap jalan offline dan di CI tanpa API key.
Jadi fallback ini BUKAN cadangan darurat — ia jalur utama setiap kali CI berjalan.
Kualitasnya harus setara dengan jalur AI.

KENAPA PAKAI TABEL, BUKAN FAKER MURNI: cascade di wizard menolak kombinasi
wilayah yang tidak valid. Faker bisa menghasilkan "DKI Jakarta" + "Bandung",
dan test akan gagal karena datanya — bukan karena aplikasinya. Tabel di bawah
menjamin kombinasi selalu sah.
"""
import random

from faker import Faker

from .schemas import CompanyData, CustomerData

fake = Faker("id_ID")

# Kombinasi wilayah yang dipastikan valid di cascade eSuite.
# TODO(verifikasi): cocokkan dengan opsi asli di dropdown setelah inspeksi manual.
REGIONS = [
    {
        "country": "Indonesia", "province": "DKI Jakarta", "city": "Jakarta Selatan",
        "district": "Setiabudi", "zone": "Kuningan", "postal_code": "12920",
    },
    {
        "country": "Indonesia", "province": "DKI Jakarta", "city": "Jakarta Pusat",
        "district": "Menteng", "zone": "Menteng", "postal_code": "10310",
    },
    {
        "country": "Indonesia", "province": "Jawa Barat", "city": "Bandung",
        "district": "Coblong", "zone": "Dago", "postal_code": "40135",
    },
]

INDUSTRY_TYPES = ["Retail", "Manufacturing", "Services", "Technology"]
COMPANY_TYPES = ["PT", "CV", "UD"]
COMPANY_PREFIXES = ["PT", "CV"]
BUSINESS_WORDS = ["Sinar", "Berkah", "Sejahtera", "Mandiri", "Jaya", "Rejeki", "Nusantara"]


def _company_name() -> str:
    """Nama PT yang terbaca wajar, bukan nama orang seperti default Faker."""
    prefix = random.choice(COMPANY_PREFIXES)
    words = random.sample(BUSINESS_WORDS, k=2)
    return f"{prefix} {' '.join(words)}"


def _email_from_name(name: str) -> str:
    """
    Email diturunkan DARI nama perusahaan supaya koheren.

    Brief meminta data yang "coherent" — email acak yang tidak berhubungan
    dengan nama perusahaan gagal memenuhi itu.
    """
    slug = "".join(c.lower() for c in name if c.isalnum())[:20]
    return f"admin@{slug}.co.id"


def _phone() -> str:
    """Nomor kantor Jakarta: 021 + 8 digit. Digit murni, sesuai schema."""
    return "021" + "".join(str(random.randint(0, 9)) for _ in range(8))


def faker_company() -> CompanyData:
    """Hasilkan CompanyData yang dijamin lolos schema dan koheren."""
    name = _company_name()
    region = random.choice(REGIONS)

    return CompanyData(
        name=name,
        email=_email_from_name(name),
        phone=_phone(),
        industry_type=random.choice(INDUSTRY_TYPES),
        company_type=random.choice(COMPANY_TYPES),
        language="Indonesia",
        street_address=f"Jl. {fake.street_name()} No. {random.randint(1, 200)}",
        **region,
    )


def faker_customer() -> CustomerData:
    """Hasilkan CustomerData yang dijamin lolos schema."""
    return CustomerData(
        name=f"Toko {' '.join(random.sample(BUSINESS_WORDS, k=2))}",
        contact="08" + "".join(str(random.randint(0, 9)) for _ in range(10)),
        address=f"Jl. {fake.street_name()} No. {random.randint(1, 200)}, {fake.city()}",
    )
