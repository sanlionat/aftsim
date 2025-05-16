import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="AFT Fon Simülasyonu", layout="centered")
st.title("AFT Fon Getiri Simülasyonu")

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
    "SMSN.L": 4.91
}

# Fonksiyon: TR saatine göre önceki 18:00
def round_to_prev_18(dt):
    dt_tr = dt.astimezone(timezone(timedelta(hours=3)))
    if dt_tr.hour >= 18:
        return dt_tr.replace(hour=18, minute=0, second=0, microsecond=0)
    else:
        return (dt_tr - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)

now = datetime.now(timezone.utc)
def_end_dt = round_to_prev_18(now)
def_start_dt = def_end_dt - timedelta(days=1)

# Başlangıç zamanı girişleri
st.subheader("Zaman Aralığı Seçimi")
col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input("Başlangıç Tarihi", def_start_dt.date())
    start_hour = st.number_input("Başlangıç Saati", min_value=0, max_value=23, value=def_start_dt.hour)
    start_minute = st.number_input("Başlangıç Dakikası", min_value=0, max_value=59, value=def_start_dt.minute)

with col2:
    end_date = st.date_input("Bitiş Tarihi", def_end_dt.date())
    end_hour = st.number_input("Bitiş Saati", min_value=0, max_value=23, value=def_end_dt.hour)
    end_minute = st.number_input("Bitiş Dakikası", min_value=0, max_value=59, value=def_end_dt.minute)

start_dt = datetime.combine(start_date, datetime.min.time()).replace(hour=start_hour, minute=start_minute, tzinfo=timezone(timedelta(hours=3))).astimezone(timezone.utc)
end_dt = datetime.combine(end_date, datetime.min.time()).replace(hour=end_hour, minute=end_minute, tzinfo=timezone(timedelta(hours=3))).astimezone(timezone.utc)

# Fonksiyon: USD/TRY kuru alımı
def get_usdtry_rate(dt):
    usdtry = yf.Ticker("USDTRY=X")
    df = usdtry.history(start=dt, end=dt + timedelta(days=1), interval="1d")
    if df.empty:
        return None
    return df.iloc[0]["Close"]

if st.button("Simülasyonu Başlat"):
    st.info(f"Başlangıç: {start_dt.astimezone(timezone(timedelta(hours=3)))} → Bitiş: {end_dt.astimezone(timezone(timedelta(hours=3)))})")

    usdtry_start = get_usdtry_rate(start_dt)
    usdtry_end = get_usdtry_rate(end_dt)
    usd_tl_change = ((usdtry_end - usdtry_start) / usdtry_start * 100) if usdtry_start and usdtry_end else 0

    start_str = f"{usdtry_start:.2f}" if usdtry_start else "-"
    end_str = f"{usdtry_end:.2f}" if usdtry_end else "-"
    st.write(f"💱 USD/TRY Kur (Başlangıç): {start_str} | USD/TRY Kur (Bitiş): {end_str}")

    total_contribution_usd = 0
    results = []

    for symbol, weight in symbols_weights.items():
        try:
            interval = "1m"
            max_minutes = (end_dt - start_dt).total_seconds() / 60
            if max_minutes > 7 * 24 * 60:
                interval = "5m" if max_minutes <= 59 * 24 * 60 else "1h"

            df = yf.download(symbol, start=start_dt - timedelta(minutes=5), end=end_dt + timedelta(minutes=5), interval=interval, progress=False)
            if df.empty:
                raise ValueError("Veri yok")

            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            else:
                df.index = df.index.tz_convert("UTC")

            start_idx = df.index.get_indexer([pd.Timestamp(start_dt)], method="nearest")[0]
            end_idx = df.index.get_indexer([pd.Timestamp(end_dt)], method="nearest")[0]

            open_price = float(df.iloc[start_idx]["Close"])
            close_price = float(df.iloc[end_idx]["Close"])

            pct_change = ((close_price - open_price) / open_price) * 100
            pct_change_tl = pct_change + usd_tl_change
            weighted = pct_change * weight / 100
            total_contribution_usd += weighted

            results.append((symbol, pct_change, pct_change_tl, weighted))
        except Exception as e:
            results.append((symbol, "HATA", "-", 0))
            st.warning(f"⚠️ {symbol} için hata: {e}")

    total_contribution_tl = total_contribution_usd + usd_tl_change

    st.subheader("📋 Hisse Performansları")
    df_result = pd.DataFrame(results, columns=["Hisse", "% Değişim USD", "% Değişim TL", "Portföy Katkısı"])
    df_result = df_result.round(2)
    st.dataframe(df_result.set_index("Hisse"))

    st.success(f"📈 Toplam AFT Fon Değişimi: {total_contribution_usd:.2f}% (USD), {total_contribution_tl:.2f}% (TL)")
