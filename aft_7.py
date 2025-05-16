import sys
sys.stdout = open("log.txt", "w", encoding="utf-8")
sys.stderr = sys.stdout

import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta
import tkinter as tk
from tkinter import messagebox, filedialog
from tkcalendar import DateEntry
import csv
import os

symbols_weights = {
    "AAPL": 4.86,
    "ADBE": 4.83,
    "AMD": 4.75,
    "AMZN": 4.77,
    "AVGO": 4.77,
    "BABA": 4.93,
    "CRM": 4.87,
    "DELL": 4.64,
    "GOOGL": 5.32,
    "INTC": 4.64,
    "INTU": 4.86,
    "META": 4.75,
    "MSFT": 4.84,
    "MU": 4.73,
    "NFLX": 4.93,
    "NVDA": 5.25,
    "QCOM": 4.83,
    "TSLA": 4.79,
    "TSM": 4.85,
    "005930.KQ": 4.91  # Samsung (KRX instead of SMSN.L)
}

results_cache = None

root = tk.Tk()
root.title("AFT Fon Anlık Getiri Simülasyonu")
root.geometry("400x480")

start_label = tk.Label(root, text="Başlangıç Tarihi:")
start_label.pack()
start_date = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
start_date.pack()
start_hour = tk.Spinbox(root, from_=0, to=23, width=5, format="%02.0f")
start_minute = tk.Spinbox(root, from_=0, to=59, width=5, format="%02.0f")
tk.Label(root, text="Saat: ").pack()
start_hour.pack()
tk.Label(root, text="Dakika: ").pack()
start_minute.pack()

end_label = tk.Label(root, text="Bitiş Tarihi:")
end_label.pack()
end_date = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
end_date.pack()
end_hour = tk.Spinbox(root, from_=0, to=23, width=5, format="%02.0f")
end_minute = tk.Spinbox(root, from_=0, to=59, width=5, format="%02.0f")
tk.Label(root, text="Saat: ").pack()
end_hour.pack()
tk.Label(root, text="Dakika: ").pack()
end_minute.pack()

# Set default datetime to the closest past 18:00 and 24h earlier
now_tr = datetime.now(timezone(timedelta(hours=3)))
closest_18 = now_tr.replace(hour=18, minute=0, second=0, microsecond=0)
if now_tr.hour < 18:
    closest_18 = closest_18 - timedelta(days=1)
start_dt_default = closest_18 - timedelta(days=1)

start_date.set_date(start_dt_default.date())
start_hour.delete(0, tk.END)
start_hour.insert(0, start_dt_default.hour)
start_minute.delete(0, tk.END)
start_minute.insert(0, start_dt_default.minute)

end_date.set_date(closest_18.date())
end_hour.delete(0, tk.END)
end_hour.insert(0, closest_18.hour)
end_minute.delete(0, tk.END)
end_minute.insert(0, closest_18.minute)


def fill_now():
    now = datetime.now(timezone(timedelta(hours=3)))
    end_date.set_date(now.date())
    end_hour.delete(0, tk.END)
    end_hour.insert(0, now.hour)
    end_minute.delete(0, tk.END)
    end_minute.insert(0, now.minute)

def get_usdtry_change(start_dt_utc, end_dt_utc):
    df = yf.download("USDTRY=X", start=start_dt_utc, end=end_dt_utc, interval="1d", progress=False)
    if df.empty or len(df) < 2:
        return 0, None, None
    first = df.iloc[0]["Close"]
    last = df.iloc[-1]["Close"]
    return ((first - last) / last) * 100, first, last

def calculate(start_dt_utc=None, end_dt_utc=None, label_override=None):
    global results_cache

    try:
        if not start_dt_utc or not end_dt_utc:
            start_dt_tr = datetime.strptime(start_date.get(), "%Y-%m-%d")
            start_dt_tr = start_dt_tr.replace(hour=int(start_hour.get()), minute=int(start_minute.get()))
            start_dt_utc = start_dt_tr.replace(tzinfo=timezone(timedelta(hours=3))).astimezone(timezone.utc)

            end_dt_tr = datetime.strptime(end_date.get(), "%Y-%m-%d")
            end_dt_tr = end_dt_tr.replace(hour=int(end_hour.get()), minute=int(end_minute.get()))
            end_dt_utc = end_dt_tr.replace(tzinfo=timezone(timedelta(hours=3))).astimezone(timezone.utc)
            end_input_label = f"{end_dt_tr.strftime('%Y-%m-%d %H:%M')}"
        else:
            start_dt_tr = start_dt_utc.astimezone(timezone(timedelta(hours=3)))
            end_input_label = label_override or "NOW"
    except Exception as e:
        messagebox.showerror("Hata", f"Zaman formatı hatalı: {e}")
        return

    # USD/TRY kurlarını ayrı ayrı çek
    usdtry = yf.Ticker("USDTRY=X")
    usdtry_start_df = usdtry.history(start=start_dt_utc, end=start_dt_utc + timedelta(days=1), interval="1d")
    usdtry_end_df = usdtry.history(start=end_dt_utc, end=end_dt_utc + timedelta(days=1), interval="1d")

    usdtry_start = usdtry_start_df["Close"].iloc[0] if not usdtry_start_df.empty else None
    usdtry_end = usdtry_end_df["Close"].iloc[0] if not usdtry_end_df.empty else None

    usd_tl_change = 0
    if usdtry_start and usdtry_end:
        usd_tl_change = ((usdtry_end - usdtry_start) / usdtry_start) * 100

    start_str = f"{usdtry_start:.2f}" if isinstance(usdtry_start, float) else "-"
    end_str = f"{usdtry_end:.2f}" if isinstance(usdtry_end, float) else "-"

    output = f"\n📊 AFT Fon – {start_dt_tr} → {end_input_label} (UTC: {start_dt_utc.strftime('%Y-%m-%d %H:%M')} → {end_dt_utc.strftime('%Y-%m-%d %H:%M')})\n"
    output += f"\n💱 USD/TRY Kur (Başlangıç): {start_str} | USD/TRY Kur (Bitiş): {end_str}\n"

    total_contribution_usd = 0
    results = []

    for symbol, weight in symbols_weights.items():
        try:
            interval = "1m"
            max_minutes = (end_dt_utc - start_dt_utc).total_seconds() / 60
            if max_minutes > 7 * 24 * 60:
                interval = "5m" if max_minutes <= 59 * 24 * 60 else "1h"

            df = yf.download(symbol, start=start_dt_utc - timedelta(minutes=5), end=end_dt_utc + timedelta(minutes=5), interval=interval, progress=False)
            if df.empty:
                raise ValueError("Veri yok")

            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            else:
                df.index = df.index.tz_convert("UTC")

            start_idx = df.index.get_indexer([pd.Timestamp(start_dt_utc).tz_convert("UTC")], method="nearest")[0]
            end_idx = df.index.get_indexer([pd.Timestamp(end_dt_utc).tz_convert("UTC")], method="nearest")[0]

            open_price = float(df.iloc[start_idx]["Close"].item()) if hasattr(df.iloc[start_idx]["Close"], 'item') else float(df.iloc[start_idx]["Close"])
            close_price = float(df.iloc[end_idx]["Close"].item()) if hasattr(df.iloc[end_idx]["Close"], 'item') else float(df.iloc[end_idx]["Close"])

            pct_change = ((close_price - open_price) / open_price) * 100
            pct_change_tl = pct_change + usd_tl_change
            weighted = pct_change * weight / 100
            total_contribution_usd += weighted

            results.append((symbol, pct_change, pct_change_tl, weighted))

        except Exception as e:
            results.append((symbol, "HATA", "-", 0))
            output += f"⚠️ {symbol} için hata: {e}\n"

    total_contribution_tl = total_contribution_usd + usd_tl_change

    if isinstance(total_contribution_usd, pd.Series):
        total_contribution_usd = total_contribution_usd.iloc[0]
    if isinstance(total_contribution_tl, pd.Series):
        total_contribution_tl = total_contribution_tl.iloc[0]

    output += "\n📋 Hisse Performansları:\n"
    for symbol, pct, pct_tl, contrib in results:
        if not isinstance(pct, float) and isinstance(pct, pd.Series): pct = pct.iloc[0]
        if not isinstance(pct_tl, float) and isinstance(pct_tl, pd.Series): pct_tl = pct_tl.iloc[0]
        if not isinstance(contrib, float) and isinstance(contrib, pd.Series): contrib = contrib.iloc[0]

        pct_str = f"{pct:.2f}%" if isinstance(pct, float) else pct
        tl_str = f"{pct_tl:.2f}%" if isinstance(pct_tl, float) else pct_tl
        contrib_str = f"{contrib:.2f}%" if isinstance(contrib, float) else "-"
        output += f"{symbol:<8} | USD: {pct_str:>7} | TL: {tl_str:>7} | Katkı: {contrib_str:>6}\n"

    output += f"\n📈 Toplam AFT Fon Değişimi: {total_contribution_usd:.2f}% (USD), {total_contribution_tl:.2f}% (TL)"
    results_cache = (results, total_contribution_usd, total_contribution_tl)

    result_window = tk.Toplevel()
    result_window.title("Simülasyon Sonucu")
    text = tk.Text(result_window, height=30, width=70)
    text.insert(tk.END, output)
    text.pack()
    save_button = tk.Button(result_window, text="CSV Kaydet", command=export_csv)
    save_button.pack(pady=5)

def run_intraday():
    now = datetime.now(timezone.utc)
    start_tr = now.astimezone(timezone(timedelta(hours=3))).replace(hour=18, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_utc = start_tr.astimezone(timezone.utc)
    calculate(start_utc, now, "Anlık")

def export_csv():
    if not results_cache:
        messagebox.showerror("Hata", "Önce hesaplama yapılmalı.")
        return

    results, total_contribution_usd, total_contribution_tl = results_cache
    filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[["CSV files", "*.csv"]], title="CSV olarak kaydet")
    if not filepath:
        return

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Hisse", "USD Değişim (%)", "TL Değişim (%)", "Portföy Katkısı (%)", "Durum"])
        for symbol, pct, pct_tl, contrib in results:
            if pct == "HATA":
                writer.writerow([symbol, "-", "-", "-", "HATA"])
            else:
                writer.writerow([symbol, f"{pct:.2f}", f"{pct_tl:.2f}", f"{contrib:.2f}", "OK"])
        writer.writerow(["TOPLAM", "", "", f"{total_contribution_usd:.2f} / {total_contribution_tl:.2f}", ""])

    messagebox.showinfo("Başarılı", f"CSV dosyası kaydedildi:\n{filepath}")

calculate_btn = tk.Button(root, text="Simülasyonu Başlat", command=calculate)
calculate_btn.pack(pady=5)

realtime_btn = tk.Button(root, text="Anlık", command=run_intraday, bg="lightgreen")
realtime_btn.pack(pady=5)

nowfill_btn = tk.Button(root, text="Bitiş = Şimdi", command=fill_now)
nowfill_btn.pack(pady=5)

root.mainloop()
