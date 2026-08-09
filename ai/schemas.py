"""
Schema validasi untuk data test.

KENAPA ADA: brief mensyaratkan output model divalidasi SEBELUM dikonsumsi test.
Tanpa ini, model bisa mengembalikan `"postal_code": "12920 (Kuningan)"` — lolos
sebagai string, tapi merusak test dengan cara yang membingungkan. Schema adalah
gerbangnya: data yang tidak lolos tidak pernah sampai ke test.
"""
from pydantic import BaseModel, Field, field_validator


class CompanyData(BaseModel):
    """Data untuk wizard Register Company di eSuite."""

    name: str = Field(min_length=1, max_length=100)
    email: str
    phone: str
    industry_type: str = Field(min_length=1)
    company_type: str = Field(min_length=1)
    language: str = Field(min_length=1)
    street_address: str = Field(min_length=1)

    # Cascade — urutannya penting, tiap nilai harus konsisten dengan induknya
    country: str = Field(min_length=1)
    province: str = Field(min_length=1)
    city: str = Field(min_length=1)
    district: str = Field(min_length=1)
    sub_district: str = Field(min_length=1)

    # postal_code diisi OTOMATIS oleh aplikasi setelah Sub District dipilih,
    # jadi tidak perlu disediakan sebagai data input. Disimpan opsional agar
    # nilai hasil pembacaan form bisa ditaruh di sini saat verifikasi.
    postal_code: str = ""

    @field_validator("name", "street_address", "city", "province")
    @classmethod
    def not_blank(cls, v: str) -> str:
        """Tolak string yang isinya hanya spasi — lolos min_length tapi tidak berguna."""
        if not v.strip():
            raise ValueError("nilai tidak boleh hanya berisi spasi")
        return v

    @field_validator("email")
    @classmethod
    def email_shape(cls, v: str) -> str:
        """
        Validasi bentuk email seadanya, sengaja tidak memakai EmailStr.

        Alasan: EmailStr menolak domain yang tidak resolve (mis. .co.id dummy),
        padahal data test memang tidak perlu domain nyata.
        """
        if v.count("@") != 1 or "." not in v.split("@")[1]:
            raise ValueError(f"format email tidak valid: {v!r}")
        return v

    @field_validator("phone")
    @classmethod
    def phone_digits_only(cls, v: str) -> str:
        """
        Nomor telepon harus digit murni.

        Form eSuite menampilkan +62 sebagai prefix terpisah, sehingga field
        hanya menerima nomor lokal yang diawali 8 (mis. 81982913977).

        Model sering mengembalikan '021-5099-8877' atau '+62 21 5099 8877'.
        Aplikasi menolaknya secara SENYAP — tombol Next tetap terkunci tanpa
        pesan error. Ditangkap di sini supaya kegagalan menyebut penyebab
        sebenarnya, bukan berupa timeout yang membingungkan.
        """
        if not v.isdigit():
            raise ValueError(f"phone harus digit saja, dapat: {v!r}")
        if not v.startswith("8"):
            raise ValueError(
                f"phone harus diawali 8 (tanpa 0 maupun +62), dapat: {v!r}. "
                "Form eSuite menampilkan +62 sebagai prefix terpisah."
            )
        if not 10 <= len(v) <= 13:
            raise ValueError(f"panjang phone tidak wajar: {len(v)} digit")
        return v

    @field_validator("postal_code")
    @classmethod
    def postal_five_digits(cls, v: str) -> str:
        """
        Kode pos Indonesia selalu 5 digit.

        Boleh kosong: aplikasi mengisinya otomatis, jadi data input tidak
        perlu menyediakannya. Validasi tetap berlaku bila nilainya ada.
        """
        if v and not (v.isdigit() and len(v) == 5):
            raise ValueError(f"postal_code harus 5 digit, dapat: {v!r}")
        return v


class CustomerData(BaseModel):
    """Data untuk form Create Customer di eWork SFA."""

    name: str = Field(min_length=1, max_length=100)
    contact: str
    address: str = Field(min_length=1)

    @field_validator("name", "address")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("nilai tidak boleh hanya berisi spasi")
        return v

    @field_validator("contact")
    @classmethod
    def contact_digits_only(cls, v: str) -> str:
        """Nomor HP Indonesia: digit saja, diawali 08, panjang 10–13."""
        if not v.isdigit():
            raise ValueError(f"contact harus digit saja, dapat: {v!r}")
        if not v.startswith("08"):
            raise ValueError(f"contact harus diawali 08, dapat: {v!r}")
        if not 10 <= len(v) <= 13:
            raise ValueError(f"panjang contact tidak wajar: {len(v)} digit")
        return v