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


# Jenis usaha untuk nama outlet, supaya variasinya tidak selalu "Toko".
OUTLET_PREFIXES = ["Toko", "Warung", "Kios", "UD", "Agen", "Grosir", "Depot"]


def faker_customer() -> CustomerData:
    """
    Hasilkan CustomerData acak yang dijamin lolos schema.

    Setiap pemanggilan menghasilkan nama, nomor, dan alamat berbeda supaya
    run berulang tidak bentrok dengan data sebelumnya di shared environment.
    """
    prefix = random.choice(OUTLET_PREFIXES)
    words = random.sample(BUSINESS_WORDS, k=2)

    return CustomerData(
        name=f"{prefix} {' '.join(words)}",
        contact="08" + "".join(str(random.randint(0, 9)) for _ in range(10)),
        address=f"Jl. {fake.street_name()} No. {random.randint(1, 200)}, {fake.city()}",
    )


# --- Opsi dropdown form New Customer di eWork SFA ---
#
# Disalin dari daftar yang benar-benar muncul di aplikasi, bukan dikarang.
#
# CATATAN: opsi Customer Type BERGANTUNG pada Channel Type yang dipilih.
# Daftar di bawah diverifikasi saat Channel Type = "Modern Trade (MT)".
# Bila Channel Type diacak juga, kombinasi bisa tidak sah dan flow gagal
# dengan "Element not found" yang menyesatkan - jadi Channel Type sengaja
# ditetapkan sampai daftar untuk General Trade ikut diverifikasi.
CHANNEL_TYPE = "Modern Trade (MT)"

CUSTOMER_TYPES = [
    "Semi Grosir",
    "Grosir",
    "Retailer Small",
    "Retailer Medium",
    "Retailer Large",
    "Big Grosir",
]


def random_customer_type() -> str:
    """Pilih Customer Type acak dari daftar yang sah untuk Modern Trade (MT)."""
    return random.choice(CUSTOMER_TYPES)


# Address Type di step Locations. "Others" sengaja tidak dipakai - dua nilai
# lain lebih mewakili pemakaian nyata dan keduanya sah untuk semua customer.
ADDRESS_TYPES = ["Delivery Address", "Invoice Address"]


def random_address_type() -> str:
    """Pilih Address Type acak antara Delivery dan Invoice."""
    return random.choice(ADDRESS_TYPES)


def random_indonesian_address() -> str:
    """
    Alamat jalan Indonesia acak untuk field Address di step Locations.

    Hanya nama jalan dan nomor - provinsi sampai kode pos dipilih terpisah
    lewat cascade, dan nilainya ditentukan aplikasi saat runtime.
    """
    return f"Jl. {fake.street_name()} No. {random.randint(1, 250)}"


# Kode wilayah untuk NIK - dua digit provinsi + dua digit kab/kota.
# Contoh nyata, bukan angka acak, supaya NIK terbaca wajar.
NIK_REGION_CODES = ["3271", "3173", "3578", "3374", "1275", "6471", "5171"]


def random_nik() -> str:
    """
    NIK 16 digit dengan struktur yang benar.

        PP KK KC DDMMYY NNNN
        |  |  |  |      +- nomor urut 4 digit
        |  |  |  +-------- tanggal lahir
        |  |  +----------- kode kecamatan
        |  +-------------- kode kabupaten/kota
        +----------------- kode provinsi

    Untuk perempuan, tanggal lahir DITAMBAH 40 - aturan asli NIK. Di sini
    selalu dibuat sebagai laki-laki (tanggal 1-28) agar nilainya selalu sah
    dan tidak bergantung pada asumsi gender data test.

    Nomornya fiktif: kombinasi kode wilayah dan tanggal memang valid secara
    format, tetapi tidak merujuk pada orang nyata.
    """
    region = random.choice(NIK_REGION_CODES)
    kecamatan = f"{random.randint(1, 30):02d}"
    day = f"{random.randint(1, 28):02d}"
    month = f"{random.randint(1, 12):02d}"
    year = f"{random.randint(70, 99):02d}"
    serial = f"{random.randint(1, 9999):04d}"
    return f"{region}{kecamatan}{day}{month}{year}{serial}"


def customer_email(name: str) -> str:
    """
    Email diturunkan dari nama outlet, berdomain gmail.com.

    Domain gmail dipakai karena form eWork SFA menerima email umum, dan
    domain kustom berisiko ditolak validasi. Sufiks angka acak mencegah
    bentrok bila nama outlet kebetulan sama pada run berbeda.
    """
    slug = "".join(c.lower() for c in name if c.isalnum())[:20]
    return f"{slug}{random.randint(100, 999)}@gmail.com"


def contact_person_name() -> str:
    """Nama orang acak untuk field Contact Person."""
    return fake.name()