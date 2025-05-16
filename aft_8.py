import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, timezone
import streamlit as st
import io

# AFT portfoyundeki hisseler ve agirliklar (%):
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

st.set_page_config(page_title="AFT Fon Simülasyonu", layout="centered")
st.title("📊 AFT Fon Anlık Getiri Simülasyonu")

col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input("Başlangıç Tarihi", value=datetime.today() - timedelta(days=1))
    start_time = st.time_input("Başlangıç Saati", value=datetime.now().replace(hour=18, minute=0).time())

with col2:
    end_date = st.date_input("Bitiş Tarihi", value=datetime.today())
    end_time = st.time_input("Bitiş Saati", value=datetime.now().time())

def get_usdtry_values(start_dt_utc, end_dt_utc):
    usdtry = yf.Ticker("USDTRY=X")
    start_df = usdtry.history(start=start_dt_utc, end=start_dt_utc + timedelta(days=1), interval="1d")
    end_df = usdtry.history(start=end_dt_utc, end=end_dt_utc + timedelta(days=1), interval="1d")
    if start_df.empty or end_df.empty:
        return 0, None, None
    start_val = start_df.iloc[0]["Close"]
    end_val = end_df.iloc[-1]["Close"]
    change_pct = ((end_val - start_val) / start_val) * 100
    return change_pct, start_val, end_val

def run_simulation():
    start_dt_tr = datetime.combine(start_date, start_time).replace(tzinfo=timezone(timedelta(hours=3)))
    end_dt_tr = datetime.combine(end_date, end_time).replace(tzinfo=timezone(timedelta(hours=3)))
    start_dt_utc = start_dt_tr.astimezone(timezone.utc)
    end_dt_utc = end_dt_tr.astimezone(timezone.utc)

    usd_tl_change, usdtry_start, usdtry_end = get_usdtry_values(start_dt_utc, end_dt_utc)
    start_str = f"{usdtry_start:.2f}" if isinstance(usdtry_start, float) else "-"
    end_str = f"{usdtry_end:.2f}" if isinstance(usdtry_end, float) else "-"

    st.markdown(f"""
    ### Zaman Aralığı
    **{start_dt_tr.strftime('%Y-%m-%d %H:%M')}** → **{end_dt_tr.strftime('%Y-%m-%d %H:%M')}**
    
    💱 USD/TRY Kur (Başlangıç): `{start_str}` | USD/TRY Kur (Bitiş): `{end_str}`
    """)

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

            df.index = pd.to_datetime(df.index).tz_localize(None)
            df = df.tz_localize("UTC") if df.index.tz is None else df.tz_convert("UTC")

            start_idx = df.index.get_indexer([pd.Timestamp(start_dt_utc)], method="nearest")[0]
            end_idx = df.index.get_indexer([pd.Timestamp(end_dt_utc)], method="nearest")[0]

            open_price = float(df.iloc[start_idx]["Close"])
            close_price = float(df.iloc[end_idx]["Close"])

            pct_change = ((close_price - open_price) / open_price) * 100
            pct_change_tl = pct_change + usd_tl_change
            weighted = pct_change * weight / 100
            total_contribution_usd += weighted

            results.append((symbol, pct_change, pct_change_tl, weighted))
        except Exception as e:
            results.append((symbol, "HATA", "-", 0))

    total_contribution_tl = total_contribution_usd + usd_tl_change

    df_results = pd.DataFrame(results, columns=["Hisse", "% Değişim USD", "% Değişim TL", "Portföy Katkısı"])
    st.dataframe(df_results.set_index("Hisse"))
    st.markdown(f"""
    ### 📈 Toplam AFT Fon Değişimi
    - **USD**: `{total_contribution_usd:.2f}%`
    - **TL**: `{total_contribution_tl:.2f}%`
    """)

    csv_buffer = io.StringIO()
    df_results.to_csv(csv_buffer, index=False)
    st.download_button("📥 CSV İndir", data=csv_buffer.getvalue(), file_name="aft_fon_sonuclari.csv", mime="text/csv")

if st.button("Simülasyonu Başlat"):
    run_simulation()
