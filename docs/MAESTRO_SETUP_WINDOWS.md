# Setup Maestro di Windows (VS Code + WSL)

Maestro **tidak jalan native di Windows**. Jalurnya lewat WSL. Ini urutan
yang paling sedikit menimbulkan masalah.

> ⏱ **Timebox 4 jam.** Kalau setelah 4 jam belum jalan, hentikan. Tetap
> serahkan YAML flow + wrapper Pytest, lalu tulis catatan jujur di README.
> Brief secara eksplisit lebih menghargai itu daripada memaksakan semuanya.

---

## Peta arsitekturnya dulu

Ini yang paling sering membingungkan:

```
Windows                          WSL (Ubuntu)
├── VS Code            <-------> ├── Maestro CLI
├── Android Studio               ├── Java (JDK)
│   └── Emulator (AVD)  <ADB>    └── adb client
└── repo project        <-------> /mnt/c/Users/.../repo
```

**Emulator jalan di Windows, Maestro jalan di WSL.** Keduanya harus bisa
saling melihat lewat ADB. Itu bagian yang paling sering gagal.

---

## 1. Pasang WSL

PowerShell **sebagai Administrator**:

```powershell
wsl --install -d Ubuntu
```

Restart, buat user Linux saat diminta. Verifikasi:

```powershell
wsl --list --verbose
```

Harus muncul `Ubuntu` dengan `VERSION 2`.

## 2. Pasang Java di WSL

Maestro butuh JDK.

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk unzip curl
java -version
```

## 3. Pasang Maestro di WSL

```bash
curl -Ls "https://get.maestro.mobile.dev" | bash
echo 'export PATH="$PATH:$HOME/.maestro/bin"' >> ~/.bashrc
source ~/.bashrc
maestro --version
```

Kalau `maestro --version` keluar, langkah tersulit sudah lewat.

## 4. Pasang Android Studio + emulator (di Windows)

1. Unduh Android Studio, install
2. **More Actions → Virtual Device Manager**
3. Create Device → **Pixel 6**, system image **API 33 (Tiramisu)**
4. Jalankan emulatornya

Verifikasi di PowerShell:

```powershell
adb devices
```

Harus muncul `emulator-5554  device`.

## 5. Sambungkan ADB dari WSL ke emulator Windows ⚠️

Ini bagian yang paling sering gagal, dan penyebab utama orang menyerah.

Pasang adb di WSL:

```bash
sudo apt install -y adb
```

Cari IP Windows dari sisi WSL:

```bash
cat /etc/resolv.conf | grep nameserver
```

Sambungkan:

```bash
adb kill-server
adb connect <IP_WINDOWS>:5555
adb devices
```

**Kalau gagal**, di PowerShell Windows aktifkan dulu TCP/IP pada emulator:

```powershell
adb tcpip 5555
```

lalu ulangi `adb connect` dari WSL.

**Alternatif yang lebih sederhana:** pasang emulator **di dalam WSL** dengan
`sdkmanager` + `avdmanager`. Lebih berat tapi tidak ada urusan jaringan
lintas-sistem. Pilih ini kalau langkah di atas macet lebih dari 1 jam.

## 6. Pasang eWork SFA di emulator

Buka Play Store di emulator, login akun Google, cari **ework - SFA**, install.

Kalau Play Store bermasalah di emulator, unduh APK-nya lalu:

```bash
adb install ework-sfa.apk
```

Ambil `appId` untuk dipakai di YAML:

```bash
adb shell pm list packages | grep -i ework
```

Isi hasilnya ke `EWORK_APP_ID` di `.env`.

## 7. Ambil selector

```bash
cd /mnt/c/Users/<user>/path/ke/repo
maestro studio
```

Buka `http://localhost:9999` di browser Windows. Klik elemen di layar, dan
Maestro Studio menampilkan selector yang benar. Salin ke YAML.

Alternatif tanpa GUI:

```bash
maestro hierarchy > hierarchy.txt
```

## 8. Jalankan flow

```bash
maestro test mobile/flows/login.yaml
```

---

## Masalah yang sering muncul

| Gejala | Penyebab | Solusi |
|---|---|---|
| `maestro: command not found` | PATH belum termuat | `source ~/.bashrc` |
| `No devices found` | WSL tidak melihat emulator | ulangi langkah 5 |
| Flow jalan tapi selector tidak ketemu | selector masih TODO | jalankan `maestro studio` |
| Lambat sekali | akses lintas `/mnt/c` | salin repo ke `~/` di WSL, sinkronkan manual |
| `adb: device offline` | server adb bentrok | `adb kill-server` di KEDUA sisi, sambung ulang |

---

## Kalau mentok

Yang tetap bisa diserahkan dan **tetap dinilai**:

- YAML flow lengkap dengan struktur benar, `runFlow` untuk login, env var, tanpa sleep
- Wrapper Pytest yang memanggilnya
- Catatan jujur di README: apa yang macet, sudah dicoba apa saja

Brief: *"We would rather see three scenarios that genuinely verify behaviour,
with an honest note about the fourth you could not finish."*
