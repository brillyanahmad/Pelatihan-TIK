"""
Analisis penjualan UMKM (Shopee + Tokopedia digabung).

Cara pakai:
    python analisis.py

Membaca  : data/produk.csv, data/shopee.csv, data/tokopedia.csv
Menghasilkan: data.js  (dibaca oleh index.html)

Hanya memakai pustaka bawaan Python, tidak perlu pip install.
Laba = omzet - modal (HPP) - biaya platform.
"""
import csv
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"

PLATFORM = {"shopee": "Shopee", "tokopedia": "Tokopedia"}


def baca_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def muat_produk():
    produk = {}
    for r in baca_csv(DATA / "produk.csv"):
        produk[r["sku"].strip()] = {
            "nama": r["nama_produk"].strip(),
            "modal": float(r["harga_modal"]),
            "stok_awal": int(r["stok_awal"]),
            "stok_min": int(r["stok_minimum"]),
        }
    return produk


def muat_penjualan(kunci, produk):
    """Baca satu file penjualan marketplace menjadi daftar transaksi seragam."""
    baris, dilewati = [], 0
    for r in baca_csv(DATA / f"{kunci}.csv"):
        sku = r["sku"].strip()
        if sku not in produk:
            dilewati += 1
            continue
        jumlah = int(r["jumlah"])
        omzet = jumlah * float(r["harga_jual"])
        modal = jumlah * produk[sku]["modal"]
        biaya = float(r.get("biaya_platform") or 0)
        baris.append({
            "tanggal": r["tanggal"][:10],
            "order_id": r["order_id"],
            "platform": kunci,
            "sku": sku,
            "jumlah": jumlah,
            "omzet": omzet,
            "modal": modal,
            "biaya": biaya,
            "laba": omzet - modal - biaya,
        })
    if dilewati:
        print(f"  ! {kunci}: {dilewati} baris dilewati (SKU tidak ada di produk.csv)")
    return baris


def gabung_penjualan(produk):
    """Gabungkan semua marketplace menjadi satu daftar transaksi."""
    semua = []
    for kunci in PLATFORM:
        if (DATA / f"{kunci}.csv").exists():
            semua += muat_penjualan(kunci, produk)
    semua.sort(key=lambda r: r["tanggal"])
    return semua


def ringkasan(rows):
    omzet = sum(r["omzet"] for r in rows)
    laba = sum(r["laba"] for r in rows)
    return {
        "omzet": omzet,
        "modal": sum(r["modal"] for r in rows),
        "biaya": sum(r["biaya"] for r in rows),
        "laba": laba,
        "unit": sum(r["jumlah"] for r in rows),
        "order": len({(r["platform"], r["order_id"]) for r in rows}),
        "margin": round(laba / omzet * 100, 1) if omzet else 0,
    }


def analisis_produk(rows, produk):
    """Peringkat produk: terlaris (unit), lengkap dengan omzet, laba, margin."""
    agg = defaultdict(lambda: {"unit": 0, "omzet": 0.0, "laba": 0.0})
    for r in rows:
        a = agg[r["sku"]]
        a["unit"] += r["jumlah"]
        a["omzet"] += r["omzet"]
        a["laba"] += r["laba"]
    hasil = []
    for sku, p in produk.items():
        a = agg[sku]
        hasil.append({
            "sku": sku, "nama": p["nama"], "unit": a["unit"],
            "omzet": a["omzet"], "laba": a["laba"],
            "margin": round(a["laba"] / a["omzet"] * 100, 1) if a["omzet"] else 0,
        })
    hasil.sort(key=lambda x: (-x["unit"], -x["laba"]))
    for i, h in enumerate(hasil, 1):
        h["peringkat"] = i
    return hasil


def tren_harian(rows, daftar_tanggal):
    per_hari = defaultdict(lambda: {"omzet": 0.0, "laba": 0.0, "unit": 0})
    for r in rows:
        d = per_hari[r["tanggal"]]
        d["omzet"] += r["omzet"]
        d["laba"] += r["laba"]
        d["unit"] += r["jumlah"]
    return [{"tanggal": t, **per_hari[t]} for t in daftar_tanggal]


def per_platform(semua):
    hasil = []
    for kunci, nama in PLATFORM.items():
        rows = [r for r in semua if r["platform"] == kunci]
        hasil.append({"kunci": kunci, "nama": nama, **ringkasan(rows)})
    return hasil


def hitung_stok(produk, semua, jumlah_hari):
    """Stok gudang dipakai bersama semua marketplace: sisa = stok awal - total terjual."""
    terjual = defaultdict(int)
    for r in semua:
        terjual[r["sku"]] += r["jumlah"]
    hasil = []
    for sku, p in produk.items():
        sisa = p["stok_awal"] - terjual[sku]
        rata = terjual[sku] / jumlah_hari if jumlah_hari else 0
        if sisa <= 0:
            status = "habis"
        elif sisa <= p["stok_min"]:
            status = "menipis"
        else:
            status = "aman"
        hasil.append({
            "sku": sku, "nama": p["nama"], "stok_awal": p["stok_awal"],
            "terjual": terjual[sku], "sisa": sisa, "stok_min": p["stok_min"],
            "hari_habis": round(sisa / rata) if rata > 0 and sisa > 0 else None,
            "nilai_stok": max(sisa, 0) * p["modal"], "status": status,
        })
    hasil.sort(key=lambda x: (["habis", "menipis", "aman"].index(x["status"]), x["sisa"]))
    return hasil


def rupiah(n):
    return "Rp " + f"{round(n):,}".replace(",", ".")


def buat_insight(rows, produk_rank, platform, stok):
    teks = []
    if produk_rank and produk_rank[0]["unit"] > 0:
        p = produk_rank[0]
        teks.append(f"{p['nama']} paling laku: {p['unit']} unit terjual dengan laba {rupiah(p['laba'])}.")
        terbaik = max((x for x in produk_rank if x["omzet"] > 0), key=lambda x: x["margin"], default=None)
        if terbaik:
            teks.append(f"Margin tertinggi ada di {terbaik['nama']} ({terbaik['margin']}%).")
        terendah = min((x for x in produk_rank if x["omzet"] > 0), key=lambda x: x["margin"], default=None)
        if terendah and terendah is not terbaik:
            teks.append(f"Margin terendah di {terendah['nama']} ({terendah['margin']}%), cek harga jual atau modalnya.")
    aktif = [p for p in platform if p["omzet"] > 0]
    if len(aktif) > 1:
        unggul = max(aktif, key=lambda x: x["laba"])
        teks.append(f"{unggul['nama']} menyumbang laba terbesar: {rupiah(unggul['laba'])}.")
    restock = [s["nama"] for s in stok if s["status"] in ("habis", "menipis")]
    if restock:
        teks.append("Perlu restock: " + ", ".join(restock) + ".")
    return teks


def bulatkan(obj):
    """Bulatkan angka desimal agar data.js ringkas."""
    if isinstance(obj, float):
        return round(obj, 1)
    if isinstance(obj, dict):
        return {k: bulatkan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [bulatkan(v) for v in obj]
    return obj


def build():
    produk = muat_produk()
    semua = gabung_penjualan(produk)
    if not semua:
        raise SystemExit("Tidak ada data penjualan. Isi data/shopee.csv dan data/tokopedia.csv.")

    awal = date.fromisoformat(semua[0]["tanggal"])
    akhir = date.fromisoformat(semua[-1]["tanggal"])
    hari = [(awal + timedelta(days=i)).isoformat() for i in range((akhir - awal).days + 1)]

    stok = hitung_stok(produk, semua, len(hari))
    platform = per_platform(semua)

    analisis = {}
    for kunci in ["semua", *PLATFORM]:
        rows = semua if kunci == "semua" else [r for r in semua if r["platform"] == kunci]
        rank = analisis_produk(rows, produk)
        analisis[kunci] = {
            "ringkasan": ringkasan(rows),
            "produk": rank,
            "tren": tren_harian(rows, hari),
            "insight": buat_insight(rows, rank, platform, stok),
        }

    hasil = {
        "periode": {"awal": hari[0], "akhir": hari[-1], "hari": len(hari)},
        "analisis": analisis,
        "platform": platform,
        "stok": stok,
        "nilai_stok_total": sum(s["nilai_stok"] for s in stok),
    }
    with open(BASE / "data.js", "w", encoding="utf-8") as f:
        f.write("window.DATA = " + json.dumps(bulatkan(hasil), ensure_ascii=False) + ";\n")
    print(f"Selesai: {len(semua)} transaksi dianalisis -> data.js")


if __name__ == "__main__":
    build()
