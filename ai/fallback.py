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

# Kombinasi wilayah yang DIVERIFIKASI valid di cascade eSuite.
#
# Rantai ini disalin dari hasil pemilihan manual di aplikasi, bukan dikarang.
#
# Pelajaran: rantai "KOTA TENGAH > TAPA" sempat dipakai dan SALAH — TAPA
# berada di bawah SIPATANA. Kesalahan seperti ini muncul sebagai timeout,
# bukan pesan error, sehingga terlihat seperti aplikasi yang rusak.
# Jangan menambah entri tanpa memverifikasinya langsung di aplikasi.
# Cascade menolak kombinasi yang tidak sah, dan kegagalannya berupa timeout
# tanpa pesan — jadi data yang salah terlihat seperti aplikasi yang rusak.
#
# postal_code TIDAK disertakan: aplikasi mengisinya OTOMATIS setelah
# Sub District dipilih. Nilainya dibaca dari form, bukan ditentukan di sini.
#
# province/city/district/sub_district juga tidak lagi dipakai untuk mengisi
# form — suite memilih opsi pertama yang disediakan aplikasi. Nilai di sini
# dipertahankan sebagai dokumentasi rantai yang terverifikasi sah.
#
# country TETAP dipakai: memilih "Philippines" (opsi pertama) mengubah
# struktur cascade menjadi Region > Province > City > Barangay dan prefix
# telepon jadi +63. Suite ini fokus pada Indonesia.
REGIONS = [
    {
        "country": "Indonesia",
        "province": "GORONTALO",
        "city": "KOTA GORONTALO",
        "district": "SIPATANA",
        "sub_district": "MOLOSIFAT U",
    },
    {
        "country": "Indonesia",
        "province": "GORONTALO",
        "city": "KOTA GORONTALO",
        "district": "SIPATANA",
        "sub_district": "TAPA",
    },
    {
        "country": "Indonesia",
        "province": "GORONTALO",
        "city": "KOTA GORONTALO",
        "district": "KOTA TENGAH",
        "sub_district": "DULALOWO TIMUR",
    },
]

INDUSTRY_TYPES = [
    "Retail",
    "Real Estate",
    "Manufacturing",
    "Hospitality",
    "Food & Beverage",
    "Finance and Banking",
    "Transportation and Logistics",
    "Telecommunications",
    "Technology",
    "Construction",
    "Automotive",
    "Entertainment and Media",
    "Energy",
    "Agriculture",
    "Healthcare",
    "Education",
]

# Company Type BUKAN bentuk badan hukum (PT/CV/UD) seperti dugaan awal,
# melainkan peran bisnis dalam rantai pasok.
COMPANY_TYPES = [
    "Importer/Exporter",
    "Consignor/Consignee",
    "Marketplace",
    "Retailer",
    "Service Aggregator",
    "Third-Party Logistics (3PL) Provider",
    "Holding Company",
    "Cooperative (Co-op)",
    "Franchisee/Franchisor",
    "Manufacturer",
    "Principal",
    "Agent",
    "Dropshipper",
    "Freight Forwarder",
    "Distributor",
    "Service",
    "Service Provider",
]

# Hanya dua bahasa tersedia.
LANGUAGES = ["Indonesia", "English"]
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
    """
    Nomor telepon TANPA kode negara: diawali 8, total 11 digit.

    Form eSuite menampilkan +62 sebagai prefix terpisah, sehingga field
    input hanya menerima nomor lokal tanpa 0 di depan. Contoh yang diterima
    aplikasi: 81982913977.

    Diverifikasi lewat pengisian manual — nomor berformat 021xxxxxxxx
    membuat tombol Next tetap terkunci tanpa pesan error apa pun.
    """
    return "8" + "".join(str(random.randint(0, 9)) for _ in range(10))


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
        language=random.choice(LANGUAGES),
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