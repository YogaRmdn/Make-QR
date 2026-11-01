# Make-QR

Tool pembuat QR code untuk terminal. Masukkan URL atau domain, hasilnya berupa file PNG dengan nama otomatis mengikuti domain tersebut.

```
⡏⣭⡍⡇⢖⠃⣘⠇⢸⢩⣭⢹
⠧⠭⠥⠇⡏⡯⢳⡳⠸⠬⠭⠼ Tools for make QR
⢟⠬⠶⢍⣐⡐⡛⠘⣞⡩⠈⠵ By Bangyog
⣠⢾⡽⣡⢥⠙⠝⣨⣙⣣⣓⠝ github.com/YogaRmdn
⡖⣒⡒⡆⢳⣫⡣⢿⣐⣸⡧⠞
⣇⣛⣃⡇⡭⠬⠞⣢⢆⡛⠝⣐
```

## Fitur

- **QR dari URL/domain** — `example.com` otomatis menjadi `https://example.com`.
- **Nama file sesuai domain** — `example.com` menghasilkan `example.com.png`.
- **QR berwarna** — atur warna modul dan latar dengan `--fill` dan `--back`.
- **Peringatan kontras** — memberi tahu bila kombinasi warna berisiko sulit dipindai.
- **Banner berwarna** — braille art dengan gradient truecolor dan efek shimmer.
- **Spinner modern** — animasi braille dengan progress bar bergradasi.
- **Mode interaktif & CLI** — bisa dijalankan tanpa argumen atau sekali jalan.
- **Ramah pipe/CI** — warna dan animasi otomatis nonaktif saat output bukan terminal, serta menghormati `NO_COLOR` dan `FORCE_COLOR`.

## Kebutuhan

- Python 3.9+ (diuji pada Python 3.14)
- [`qrcode[pil]`](https://pypi.org/project/qrcode/) 8.x

## Instalasi

```bash
git clone https://github.com/YogaRmdn/Make-QR.git
cd Make-QR

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Pemakaian

Mode interaktif:

```bash
python main.py
```

Langsung sekali jalan:

```bash
python main.py example.com
# ✔ QR code berhasil dibuat → /.../example.com.png (29×29 modul, 1.9 KB)
```

URL lengkap juga bisa, nama file tetap mengikuti domain:

```bash
python main.py "https://sub.example.co.id/halaman?q=1"
# → sub.example.co.id.png
```

QR berwarna:

```bash
python main.py example.com --fill "#00E5FF" --back "#0B0F19"
```

Nama file manual:

```bash
python main.py example.com -o hasil/qr-keren
# → hasil/qr-keren.png
```

## Opsi

| Opsi | Default | Keterangan |
| --- | --- | --- |
| `url` | – | URL/domain tujuan. Kosongkan untuk mode interaktif. |
| `-o, --output` | `<domain>.png` | Path file hasil. Otomatis ditambah `.png` bila tanpa ekstensi. |
| `-f, --fill` | `#000000` | Warna modul QR (hex 6 digit). |
| `-b, --back` | `#FFFFFF` | Warna latar QR (hex 6 digit). |
| `-s, --box-size` | `12` | Ukuran tiap modul dalam piksel (1–40). |
| `--border` | `2` | Lebar quiet zone dalam modul (0–16). |
| `--ec` | `H` | Level error correction: `L`, `M`, `Q`, atau `H`. |
| `--no-color` | – | Matikan warna ANSI. |
| `--no-animation` | – | Matikan animasi banner dan spinner. |
| `--version` | – | Tampilkan versi. |
| `-h, --help` | – | Tampilkan bantuan. |

## Aturan nama file

Nama file default diambil dari host URL:

| Input | Output |
| --- | --- |
| `example.com` | `example.com.png` |
| `https://sub.example.co.id/halaman?q=1` | `sub.example.co.id.png` |
| `http://192.168.1.10:8080/admin` | `192.168.1.10.png` |
| `Example.COM` | `example.com.png` |
| `example.net.` | `example.net.png` |

- Port, path, dan query string tidak dipakai.
- Host ditulis lowercase.
- Karakter yang tidak valid untuk nama file diganti `_`.
- Domain yang sama akan menimpa file yang sudah ada.

## Struktur proyek

```
Make-QR/
├── main.py            # seluruh aplikasi CLI
├── requirements.txt   # dependensi
└── README.md
```

## Tips

- Pakai level error correction `H` (default) agar QR lebih tahan gangguan, termasuk saat dicetak atau memakai warna.
- Untuk QR berwarna, gunakan modul gelap di atas latar terang. Tool akan memberi peringatan bila rasio kontras di bawah 3.0.
- Ingin hasil lebih tajam? Naikkan `--box-size`, misalnya `--box-size 16`.
- Di lingkungan tanpa warna (CI/log), jalankan dengan `--no-color --no-animation`.

## Lisensi

Belum ditentukan. Hubungi pemilik repositori untuk informasi penggunaan.

---

Dibuat oleh **Yoga Ramadani** ([@YogaRmdn](https://github.com/YogaRmdn)).
