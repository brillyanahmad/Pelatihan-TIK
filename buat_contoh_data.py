"""Membuat data contoh di folder data/. Ganti dengan ekspor asli dari Shopee dan Tokopedia."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)
DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

# sku, nama, harga modal, harga jual, stok awal, stok minimum, popularitas
PRODUK = [
    ("KRP-01", "Keripik Tempe Original", 9000, 18000, 900, 100, 10),
    ("SMB-01", "Sambal Bawang Botol", 14000, 28000, 600, 80, 8),
    ("KPI-01", "Kopi Arabika 200g", 38000, 69000, 400, 60, 6),
    ("MDU-01", "Madu Hutan 250ml", 45000, 85000, 300, 50, 4),
    ("BRW-01", "Brownies Kering", 12000, 25000, 500, 70, 7),
    ("ABN-01", "Abon Sapi 100g", 22000, 39000, 260, 40, 5),
    ("TEH-01", "Teh Rosella 20 Sachet", 11000, 22000, 350, 50, 3),
    ("TAS-01", "Tas Anyaman Mini", 52000, 95000, 120, 20, 1),
]

with open(DATA / "produk.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["sku", "nama_produk", "harga_modal", "stok_awal", "stok_minimum"])
    for p in PRODUK:
        w.writerow([p[0], p[1], p[2], p[4], p[5]])

akhir = date(2026, 10, 28)
bobot = [p[6] for p in PRODUK]
for nama, prefix, fee, order_per_hari in [("shopee", "SPE", 0.08, 11), ("tokopedia", "TKP", 0.06, 8)]:
    with open(DATA / f"{nama}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tanggal", "order_id", "sku", "jumlah", "harga_jual", "biaya_platform"])
        n = 1
        for i in range(30):
            tgl = akhir - timedelta(days=29 - i)
            akhir_pekan = 1.3 if tgl.weekday() >= 5 else 1
            for _ in range(int(random.randint(order_per_hari - 4, order_per_hari + 4) * akhir_pekan)):
                p = random.choices(PRODUK, weights=bobot)[0]
                jml = random.choice([1, 1, 1, 2, 2, 3])
                harga = p[3]
                w.writerow([tgl.isoformat(), f"{prefix}{tgl:%m%d}{n:04d}", p[0], jml, harga, round(jml * harga * fee)])
                n += 1
print("Data contoh dibuat di folder data/")
