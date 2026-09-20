import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import ta
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================================================
# ⚙️ إعداد الصفحة
# =========================================================

st.set_page_config(
    page_title="EGX AI PRO MAX V11 IDEAL - عربي",
    page_icon="📈",
    layout="wide"
)

st.title("🚀 EGX AI PRO MAX V11.1 IDEAL")
st.caption(
    "📊 فحص الأسهم المصرية • تحليل متعدد الفترات • Entry/Target Engine احترافي • Risk Management"
)

# =========================================================
# 📌 قائمة الأسهم
# =========================================================

EGX100 = [
    "COMI.CA",
    "MFPC.CA",
    "PHDC.CA",
    "ORAS.CA",
    "HDBK.CA",
    "EFIH.CA",
    "AMES.CA",
    "INEG.CA",
    "BTFH.CA",
    "BIOC.CA",
    "CLHO.CA",
    "MBSC.CA",
    "MTIE.CA",
    "EGTS.CA",
    "EGSA.CA",
    "MHOT.CA",
    "EGBE.CA",
    "IFAP.CA",
    "PRDC.CA",
    "MIPH.CA",
    "MPCI.CA",
    "MOIN.CA",
    "ISMQ.CA",
    "AXPH.CA",
    "PHTV.CA",
    "CPCI.CA",
    "NINH.CA",
    "SPIN.CA",
    "ENGC.CA",
    "CNFN.CA",
    "SVCE.CA",
    "KABO.CA",
    "OFH.CA",
    "GSSC.CA",
    "WCDF.CA",
    "MFSC.CA",
    "SAIB.CA",
    "ACGC.CA",
    "UEFM.CA",
    "KZPC.CA",
    "ADCI.CA",
    "INFI.CA",
    "ASCM.CA",
    "ZEOT.CA",
    "SMFR.CA",
    "ETRS.CA",
    "EDFM.CA",
    "MILS.CA",
    "GBCO.CA",
    "HRHO.CA",
    "TMGH.CA",
    "FWRY.CA",
    "SWDY.CA",
    "ETEL.CA",
    "AMOC.CA",
    "HELI.CA",
    "EAST.CA",
    "EFID.CA",
    "JUFO.CA",
    "ABUK.CA",
    "ESRS.CA",
    "EMFD.CA",
    "CCAP.CA",
    "CICH.CA",
    "OCDI.CA",
    "ORHD.CA",
    "MASR.CA",
    "ADIB.CA",
    "SAUD.CA",
    "CIEB.CA",
    "FAIT.CA",
    "CANA.CA",
    "EXPA.CA",
    "ARCC.CA",
    "AJWA.CA",
    "MICH.CA",
    "SUGR.CA",
    "POUL.CA",
    "DOMT.CA",
    "ISMA.CA",
    "UEGC.CA",
    "OLFI.CA",
    "SKPC.CA",
    "AMER.CA",
    "TALM.CA",
    "ORWE.CA",
    "SPMD.CA",
    "ZMID.CA",
    "MENA.CA",
    "DAPH.CA",
    "RAYA.CA",
    "EGAL.CA",
    "ECAP.CA",
    "MPRC.CA",
    "NCCW.CA",
    "SCEM.CA",
    "ARAB.CA",
    "GDWA.CA",
    "ELEC.CA",
    "IRON.CA",
    "ATQA.CA",
    "EGCH.CA",
    "ALCN.CA",
    "MPCO.CA",
    "ELSH.CA",
    "MEPA.CA",
    "ODIN.CA",
    "EGAS.CA",
    "RACC.CA",
    "PRCL.CA",
    "BINV.CA",
    "EDBM.CA",
    "MCQE.CA",
    "MOIL.CA",
    "NIPH.CA",
    "ISPH.CA",
    "DSCW.CA",
    "UNIT.CA",
    "PHAR.CA",
    "TRTO.CA",
    "ICFC.CA",
    "ELKA.CA",
    "ATLC.CA",
    "COSG.CA",
    "AMPI.CA",
    "COPR.CA"
]

EGX100 = list(dict.fromkeys(EGX100))

# =========================================================
# 🌐 DYNAMIC EGX UNIVERSE (OFFICIAL + STRATEGIC FALLBACK)
# =========================================================
OFFICIAL_EGX_URL = "https://www.egx.com.eg/en/CurrentIndexConstituntes.aspx?Nav=1&type=1"

def fetch_official_egx100(timeout=12):
    """Try to read current EGX100 constituents from EGX official page.
    Returns Yahoo-style symbols or an empty list on failure; never breaks the app.
    """
    try:
        html = requests.get(OFFICIAL_EGX_URL, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"}).text
        tables = pd.read_html(html)
        candidates=[]
        for t in tables:
            for col in t.columns:
                vals=t[col].astype(str).str.upper().str.strip()
                for v in vals:
                    if v.endswith('.CA') and 2 <= len(v) <= 20:
                        candidates.append(v)
                    elif v.replace('.','').isalnum() and 2 <= len(v) <= 8 and v not in {"CODE","SYMBOL","TICKER"}:
                        # Only accept compact ticker-like cells.
                        if any(ch.isalpha() for ch in v): candidates.append(v + '.CA')
        out=list(dict.fromkeys(candidates))
        # Avoid replacing the strategic universe with a malformed scrape.
        return out if len(out)>=50 else []
    except Exception:
        return []

def get_active_universe(auto_update=True):
    strategic=list(EGX100)
    if not auto_update:
        return strategic, "STATIC_STRATEGIC"
    official=fetch_official_egx100()
    if official:
        merged=list(dict.fromkeys(official + strategic))
        return merged, "OFFICIAL_EGX100_PLUS_STRATEGIC"
    return strategic, "STATIC_FALLBACK"

TOTAL_STOCKS = len(EGX100)

# Universe is intentionally broad; weak/invalid names are filtered by data quality and liquidity later.

# =========================================================
# 🎛️ إعدادات الفحص
# =========================================================

st.sidebar.header("⚙️ إعدادات الفحص")
auto_update_universe = st.sidebar.checkbox("🌐 تحديث مكونات EGX100 تلقائيًا", value=True)

period_daily = st.sidebar.selectbox(
    "📅 فترة البيانات اليومية",
    ["3mo", "6mo", "1y", "2y", "3y", "5y", "max"],
    index=6
)

period_weekly = st.sidebar.selectbox(
    "📅 فترة البيانات الأسبوعية",
    ["3y", "5y", "10y", "max"],
    index=3
)

period_monthly = st.sidebar.selectbox(
    "📅 فترة البيانات الشهرية",
    ["10y", "15y", "20y", "max"],
    index=3
)

max_workers = st.sidebar.slider(
    "⚡ عدد الاتصالات المتوازية",
    min_value=2,
    max_value=16,
    value=8,
    step=1
)

top_n = st.sidebar.slider(
    "🏆 عدد أفضل الأسهم",
    min_value=5,
    max_value=100,
    value=20,
    step=5
)

# =========================================================
# 💰 إدارة رأس المال
# =========================================================

st.sidebar.markdown("---")
st.sidebar.header("💰 إدارة المخاطر")

capital = st.sidebar.number_input(
    "رأس المال بالجنيه",
    min_value=1000.0,
    max_value=100000000.0,
    value=100000.0,
    step=5000.0
)

risk_percent = st.sidebar.slider(
    "مخاطرة الصفقة %",
    min_value=0.5,
    max_value=10.0,
    value=2.0,
    step=0.5
)

run_backtest = st.sidebar.checkbox(
    "🧪 تشغيل Backtest تاريخي حقيقي",
    value=True
)
backtest_bars = st.sidebar.slider(
    "عدد شموع الـ Backtest لكل سهم",
    min_value=100,
    max_value=1000,
    value=300,
    step=50
)

# تكاليف التنفيذ والقيود الواقعية
st.sidebar.markdown("---")
st.sidebar.header("🧾 واقعية التنفيذ")
commission_pct = st.sidebar.number_input(
    "عمولة التنفيذ لكل جانب %", min_value=0.0, max_value=2.0, value=0.15, step=0.01
)
slippage_pct = st.sidebar.number_input(
    "Slippage لكل جانب %", min_value=0.0, max_value=2.0, value=0.10, step=0.01
)
max_position_pct = st.sidebar.slider(
    "أقصى حجم مركز من رأس المال %", min_value=5, max_value=100, value=20, step=5
)
monte_carlo_runs = st.sidebar.slider(
    "عدد محاكاة Monte Carlo", min_value=100, max_value=2000, value=500, step=100
)

# =========================================================
# 📊 معلومات
# =========================================================

st.sidebar.markdown("---")

st.sidebar.metric(
    "📊 عدد الأسهم للفحص",
    TOTAL_STOCKS
)

st.sidebar.markdown("---")

st.sidebar.info(
    """
    📌 النظام يقوم بفحص:

    • Daily / Weekly / Monthly
    • EMA20 / EMA50 / EMA200
    • RSI / MACD / ADX / ATR
    • OBV / MFI / Stochastic RSI / VWAP
    • Volume Ratio
    • Support / Resistance
    • Swing High / Swing Low
    • Fibonacci
    • Fibonacci Extensions
    • Professional Pullback
    • Professional Breakout
    • Trend Alignment
    • Entry Quality
    • Target Quality
    • Risk / Reward
    • Risk Management
    • 4 Targets
    • Backtest واقعي بتكاليف التنفيذ وSlippage
    • Strict Structural Targets فقط في Backtest
    • Partial Take Profit + Trailing Stop
    • Historical TP Probability / Expectancy
    • Walk-Forward / Out-of-Sample
    • Monte Carlo / Sharpe / Sortino / Calmar
    """
)

# =========================================================
# 🧠 ثوابت النظام
# =========================================================

MIN_DAILY_ROWS = 60
MIN_WEEKLY_ROWS = 80
MIN_MONTHLY_ROWS = 36

DOWNLOAD_RETRIES = 4
DOWNLOAD_RETRY_DELAY = 2
DOWNLOAD_BATCH_SIZE = 25

EMA200_REQUIRED_ROWS = 200

# Backtest / Structure / Liquidity
BACKTEST_WARMUP = 220
PIVOT_RADIUS = 3
LIQUIDITY_LOOKBACK = 20
RS_LOOKBACK = 20
DEFAULT_COMMISSION_PCT = 0.15
DEFAULT_SLIPPAGE_PCT = 0.10
DEFAULT_MAX_POSITION_PCT = 20.0
RAW_AUDIT_VERSION = "V11.1"
BACKTEST_HORIZONS = (250, 500, 750, 1000)

# =========================================================
# 📥 DATA ENGINE
# =========================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False
)
def load_data(symbols, period, interval):

    if not symbols:
        return pd.DataFrame()

    symbols = tuple(symbols)

    last_error = None

    for attempt in range(DOWNLOAD_RETRIES):

        try:

            # Download in manageable batches to reduce Yahoo partial/batch failures.
            chunks = [list(symbols)[i:i + DOWNLOAD_BATCH_SIZE] for i in range(0, len(symbols), DOWNLOAD_BATCH_SIZE)]
            parts = []
            for chunk in chunks:
                part = yf.download(
                    tickers=chunk,
                    period=period,
                    interval=interval,
                    group_by="ticker",
                    threads=True,
                    auto_adjust=True,
                    progress=False,
                    timeout=30
                )
                if part is not None and not part.empty:
                    parts.append(part)
            if parts:
                try:
                    data = pd.concat(parts, axis=1)
                except Exception:
                    data = parts[0]
                if data is not None and not data.empty:
                    return data

            last_error = "Yahoo returned empty data"

        except Exception as e:

            last_error = str(e)

        if attempt < DOWNLOAD_RETRIES - 1:

            time.sleep(
                DOWNLOAD_RETRY_DELAY *
                (attempt + 1)
            )

    return pd.DataFrame()


# =========================================================
# 🔍 استخراج بيانات السهم
# =========================================================

def extract_symbol_data(data, symbol):

    try:

        if data is None or data.empty:
            return pd.DataFrame()

        if isinstance(data.columns, pd.MultiIndex):

            level0 = data.columns.get_level_values(0)
            level1 = data.columns.get_level_values(1)

            if symbol in level0:

                df = data[symbol].copy()

            elif symbol in level1:

                df = data.xs(
                    symbol,
                    axis=1,
                    level=1
                ).copy()

            else:

                return pd.DataFrame()

        else:

            df = data.copy()

        df.columns = [
            str(c).strip()
            for c in df.columns
        ]

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        if not all(
            c in df.columns
            for c in required
        ):

            return pd.DataFrame()

        df = df[required].copy()

        for col in required:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.replace(
            [np.inf, -np.inf],
            np.nan
        )

        df = df.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close"
            ]
        )

        df["Volume"] = df["Volume"].fillna(0)

        df = df[
            (df["High"] >= df["Low"]) &
            (df["Close"] > 0) &
            (df["Open"] > 0)
        ]

        df = df.sort_index()

        df = df[
            ~df.index.duplicated(
                keep="last"
            )
        ]

        return df

    except Exception:

        return pd.DataFrame()


# =========================================================
# 🧪 RAW DATA AUDIT
# =========================================================
def extract_symbol_data_raw(data, symbol):
    """Extract without cleaning so the audit sees what the provider actually returned."""
    if data is None or getattr(data, "empty", True): return pd.DataFrame()
    try:
        if isinstance(data.columns, pd.MultiIndex):
            if symbol in data.columns.get_level_values(0): d=data[symbol].copy()
            elif symbol in data.columns.get_level_values(-1): d=data.xs(symbol, axis=1, level=-1).copy()
            else: return pd.DataFrame()
        else: d=data.copy()
        return d
    except Exception:
        return pd.DataFrame()

def calculate_raw_data_audit(df, interval="1d"):
    """Provider-level audit before cleaning: missing OHLC, duplicates, gaps, stale bars and history."""
    if df is None or df.empty:
        return {"raw_quality":0.0,"raw_rows":0,"raw_missing_pct":100.0,"raw_duplicate_pct":0.0,"raw_gap_pct":0.0,"raw_bad_ohlc_pct":100.0,"raw_zero_volume_pct":100.0}
    d=df.copy(); req=["Open","High","Low","Close","Volume"]
    if any(c not in d.columns for c in req):
        return {"raw_quality":0.0,"raw_rows":len(d),"raw_missing_pct":100.0,"raw_duplicate_pct":0.0,"raw_gap_pct":0.0,"raw_bad_ohlc_pct":100.0,"raw_zero_volume_pct":100.0}
    n=max(len(d),1)
    missing=float(d[req].isna().sum().sum())/(n*len(req))
    bad=((d["High"]<d[["Open","Close","Low"]].max(axis=1)) | (d["Low"]>d[["Open","Close","High"]].min(axis=1))).mean()
    zero=(pd.to_numeric(d["Volume"],errors="coerce")<=0).mean()
    dup=float(d.index.duplicated().mean())
    ret=pd.to_numeric(d["Close"],errors="coerce").pct_change().abs()
    gap=float((ret>0.30).mean()) if len(d)>5 else 0.0
    hist=min(1.0,len(d)/max(EMA200_REQUIRED_ROWS,220))
    penalty=.35*missing+.20*bad+.15*zero+.05*dup+.15*gap
    quality=float(np.clip((.50+.50*hist)*(1-penalty)*100,0,100))
    return {"raw_quality":round(quality,2),"raw_rows":int(len(d)),"raw_missing_pct":round(missing*100,2),"raw_duplicate_pct":round(dup*100,2),"raw_gap_pct":round(gap*100,2),"raw_bad_ohlc_pct":round(float(bad)*100,2),"raw_zero_volume_pct":round(float(zero)*100,2)}

# =========================================================
# 🧪 DATA QUALITY
# =========================================================

def calculate_data_quality(df):
    """Professional data quality audit. Returns score + diagnostics."""
    if df is None or df.empty:
        return {"quality":0.0,"missing_pct":100.0,"ohlc_bad_pct":100.0,"zero_volume_pct":100.0,"duplicate_pct":0.0,"gap_pct":0.0,"stale_pct":0.0,"history_score":0.0,"rows":0}
    d=df.copy(); required=["Open","High","Low","Close","Volume"]
    if any(c not in d.columns for c in required):
        return {"quality":0.0,"missing_pct":100.0,"ohlc_bad_pct":100.0,"zero_volume_pct":100.0,"duplicate_pct":0.0,"gap_pct":0.0,"stale_pct":0.0,"history_score":0.0,"rows":int(len(d))}
    n=max(len(d),1)
    missing=float(d[required].isna().sum().sum())/(n*len(required))
    high_bad=(d["High"]<d[["Open","Close","Low"]].max(axis=1)).mean()
    low_bad=(d["Low"]>d[["Open","Close","High"]].min(axis=1)).mean()
    ohlc_bad=float(max(high_bad,low_bad))
    vol=pd.to_numeric(d["Volume"],errors="coerce")
    zero_vol=float((vol<=0).mean())
    duplicate=float(d.index.duplicated().mean())
    ret=pd.to_numeric(d["Close"],errors="coerce").pct_change().abs()
    gap=float((ret>0.30).mean()) if len(d)>5 else 0.0
    # stale prices: unchanged close for 3+ consecutive sessions
    same=d["Close"].diff().abs().fillna(1).eq(0)
    stale=float(same.rolling(3,min_periods=3).sum().ge(3).mean())
    history_score=min(1.0,len(d)/max(EMA200_REQUIRED_ROWS,220))
    penalty=.35*missing+.20*ohlc_bad+.15*zero_vol+.05*duplicate+.15*gap+.10*stale
    quality=float(np.clip((0.50+0.50*history_score)*(1-penalty)*100,0,100))
    return {"quality":round(quality,2),"missing_pct":round(missing*100,2),"ohlc_bad_pct":round(ohlc_bad*100,2),"zero_volume_pct":round(zero_vol*100,2),"duplicate_pct":round(duplicate*100,2),"gap_pct":round(gap*100,2),"stale_pct":round(stale*100,2),"history_score":round(history_score*100,2),"rows":int(len(d))}


def atr(df, period=14):

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()


# =========================================================
# 📊 ADX
# =========================================================

def adx(df, period=14):

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    plus_dm_raw = high.diff()
    minus_dm_raw = -low.diff()

    plus_dm = np.where(
        (plus_dm_raw > minus_dm_raw) &
        (plus_dm_raw > 0),
        plus_dm_raw,
        0.0
    )

    minus_dm = np.where(
        (minus_dm_raw > plus_dm_raw) &
        (minus_dm_raw > 0),
        minus_dm_raw,
        0.0
    )

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ],
        axis=1
    ).max(axis=1)

    atr_val = tr.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    plus_di = (
        100 *
        pd.Series(
            plus_dm,
            index=df.index
        ).ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period
        ).mean()
        /
        (atr_val + 1e-9)
    )

    minus_di = (
        100 *
        pd.Series(
            minus_dm,
            index=df.index
        ).ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period
        ).mean()
        /
        (atr_val + 1e-9)
    )

    dx = (
        abs(
            plus_di -
            minus_di
        )
        /
        (
            plus_di +
            minus_di +
            1e-9
        )
    ) * 100

    return dx.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()


# =========================================================
# 📐 خطي Regression بسيط
# =========================================================

def linear_slope(series, window=10):

    if len(series) < window:
        return np.nan

    values = series.iloc[-window:].values.astype(float)

    if not np.all(np.isfinite(values)):
        return np.nan

    x = np.arange(window)

    try:

        slope = np.polyfit(
            x,
            values,
            1
        )[0]

        return float(slope)

    except Exception:

        return np.nan


# =========================================================
# 📈 TECHNICAL ENGINE
# =========================================================

def add_indicators(df):

    df = df.copy()

    if len(df) < 30:
        return df

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    # =====================================================
    # EMA20
    # =====================================================

    df["ema20"] = close.ewm(
        span=20,
        adjust=False
    ).mean()

    # =====================================================
    # EMA50
    # =====================================================

    df["ema50"] = close.ewm(
        span=50,
        adjust=False
    ).mean()

    # =====================================================
    # EMA200
    #
    # مهم:
    # لا نعتبر EMA200 مكتملًا إلا بعد 200 شمعة
    # =====================================================

    if len(df) >= EMA200_REQUIRED_ROWS:

        df["ema200"] = close.ewm(
            span=200,
            adjust=False,
            min_periods=200
        ).mean()

        df["ema200_complete"] = True

    else:

        df["ema200"] = np.nan
        df["ema200_complete"] = False

    # =====================================================
    # RSI
    # =====================================================

    df["rsi"] = ta.momentum.RSIIndicator(
        close=close,
        window=14
    ).rsi()

    # =====================================================
    # MACD
    # =====================================================

    macd_obj = ta.trend.MACD(
        close=close,
        window_slow=26,
        window_fast=12,
        window_sign=9
    )

    df["macd"] = macd_obj.macd()

    df["macd_signal"] = (
        macd_obj.macd_signal()
    )

    df["macd_hist"] = (
        macd_obj.macd_diff()
    )

    # =====================================================
    # Volume MA
    # =====================================================

    df["vol_ma"] = vol.rolling(
        20,
        min_periods=10
    ).mean()

    # =====================================================
    # Volume Ratio
    # =====================================================

    df["volume_ratio"] = (
        vol /
        (df["vol_ma"] + 1e-9)
    )

    # =====================================================
    # OBV
    # =====================================================

    try:

        df["obv"] = (
            ta.volume
            .OnBalanceVolumeIndicator(
                close=close,
                volume=vol
            )
            .on_balance_volume()
        )

        df["obv_ma"] = (
            df["obv"]
            .rolling(
                20,
                min_periods=10
            )
            .mean()
        )

        df["obv_slope"] = (
            df["obv"] -
            df["obv"].shift(5)
        )

    except Exception:

        df["obv"] = np.nan
        df["obv_ma"] = np.nan
        df["obv_slope"] = np.nan

    # =====================================================
    # MFI
    # =====================================================

    try:

        df["mfi"] = (
            ta.volume
            .MFIIndicator(
                high=high,
                low=low,
                close=close,
                volume=vol,
                window=14
            )
            .money_flow_index()
        )

    except Exception:

        df["mfi"] = np.nan

    # =====================================================
    # Stochastic RSI
    # =====================================================

    try:

        stoch = ta.momentum.StochRSIIndicator(
            close=close,
            window=14,
            smooth1=3,
            smooth2=3
        )

        df["stoch_rsi"] = (
            stoch.stochrsi()
        )

        df["stoch_rsi_k"] = (
            stoch.stochrsi_k()
        )

        df["stoch_rsi_d"] = (
            stoch.stochrsi_d()
        )

        df["stoch_rsi_k_slope"] = (
            df["stoch_rsi_k"] -
            df["stoch_rsi_k"].shift(1)
        )

    except Exception:

        df["stoch_rsi"] = np.nan
        df["stoch_rsi_k"] = np.nan
        df["stoch_rsi_d"] = np.nan
        df["stoch_rsi_k_slope"] = np.nan

    # =====================================================
    # PROFESSIONAL VWAP: rolling 20 + anchored 60 sessions
    # =====================================================
    try:
        typical_price=(high+low+close)/3
        pv=typical_price*vol
        roll_vol=vol.rolling(20,min_periods=5).sum()
        df["vwap"]=pv.rolling(20,min_periods=5).sum()/(roll_vol+1e-9)
        anchor=60
        df["anchored_vwap"]=pv.rolling(anchor,min_periods=20).sum()/(vol.rolling(anchor,min_periods=20).sum()+1e-9)
        df["vwap_distance"]=(close-df["vwap"])/(close+1e-9)
    except Exception:
        df["vwap"]=np.nan; df["anchored_vwap"]=np.nan; df["vwap_distance"]=np.nan

    # =====================================================
    # ATR
    # =====================================================

    df["atr"] = atr(
        df,
        14
    )

    df["atr_pct"] = (
        df["atr"] /
        (close + 1e-9)
    )

    # =====================================================
    # ADX
    # =====================================================

    df["adx"] = adx(
        df,
        14
    )

    # =====================================================
    # Support / Resistance
    # =====================================================

    df["support"] = (
        low
        .rolling(
            20,
            min_periods=10
        )
        .min()
    )

    df["resistance"] = (
        high
        .rolling(
            20,
            min_periods=10
        )
        .max()
    )

    # =====================================================
    # Previous Support / Resistance
    # =====================================================

    df["previous_support"] = (
        low
        .rolling(
            20,
            min_periods=10
        )
        .min()
        .shift(1)
    )

    df["previous_resistance"] = (
        high
        .rolling(
            20,
            min_periods=10
        )
        .max()
        .shift(1)
    )

    # =====================================================
    # Swing High / Swing Low
    #
    # نستخدم مستويات تاريخية حقيقية داخل النوافذ
    # =====================================================

    df["swing_high_20"] = (
        high
        .rolling(
            20,
            min_periods=10
        )
        .max()
        .shift(1)
    )

    df["swing_low_20"] = (
        low
        .rolling(
            20,
            min_periods=10
        )
        .min()
        .shift(1)
    )

    df["swing_high_60"] = (
        high
        .rolling(
            60,
            min_periods=20
        )
        .max()
        .shift(1)
    )

    df["swing_low_60"] = (
        low
        .rolling(
            60,
            min_periods=20
        )
        .min()
        .shift(1)
    )

    # =====================================================
    # Fibonacci
    # =====================================================

    swing_high = (
        high
        .rolling(
            60,
            min_periods=20
        )
        .max()
    )

    swing_low = (
        low
        .rolling(
            60,
            min_periods=20
        )
        .min()
    )

    fib_range = (
        swing_high -
        swing_low
    )

    df["fib_236"] = (
        swing_high -
        fib_range * 0.236
    )

    df["fib_382"] = (
        swing_high -
        fib_range * 0.382
    )

    df["fib_500"] = (
        swing_high -
        fib_range * 0.500
    )

    df["fib_618"] = (
        swing_high -
        fib_range * 0.618
    )

    df["fib_786"] = (
        swing_high -
        fib_range * 0.786
    )

    # =====================================================
    # Fibonacci Extensions
    # =====================================================

    df["fib_ext_1272"] = (
        swing_low +
        fib_range * 1.272
    )

    df["fib_ext_1618"] = (
        swing_low +
        fib_range * 1.618
    )

    df["fib_ext_2000"] = (
        swing_low +
        fib_range * 2.000
    )

    # =====================================================
    # Trend Slope
    # =====================================================

    df["ema20_slope"] = (
        df["ema20"] -
        df["ema20"].shift(5)
    ) / (
        df["Close"] + 1e-9
    )

    df["ema50_slope"] = (
        df["ema50"] -
        df["ema50"].shift(5)
    ) / (
        df["Close"] + 1e-9
    )

    # =====================================================
    # Candle Body
    # =====================================================

    candle_range = (
        high -
        low
    ).replace(
        0,
        np.nan
    )

    df["body_pct"] = (
        abs(
            close -
            df["Open"]
        ) /
        candle_range
    )

    df["bullish_candle"] = (
        close >
        df["Open"]
    )

    # =====================================================
    # ATR مناسب للاختراق
    # =====================================================

    df["atr_expansion"] = (
        df["atr"] /
        (
            df["atr"]
            .rolling(
                20,
                min_periods=10
            )
            .mean()
            +
            1e-9
        )
    )

    # =====================================================
    # Breakout متقدم
    # =====================================================

    previous_resistance = (
        high
        .rolling(
            20,
            min_periods=10
        )
        .max()
        .shift(1)
    )

    close_above_resistance = (
        close >
        previous_resistance
    )

    breakout_volume = (
        df["volume_ratio"] >= 1.30
    )

    breakout_volume_strong = (
        df["volume_ratio"] >= 1.50
    )

    atr_is_healthy = (
        df["atr_pct"] >= 0.015
    )

    atr_not_extreme = (
        df["atr_pct"] <= 0.12
    )

    candle_quality = (
        df["body_pct"] >= 0.45
    )

    bullish_candle = (
        df["bullish_candle"]
    )

    trend_breakout = (
        (
            close > df["ema20"]
        ) &
        (
            df["ema20"] > df["ema50"]
        )
    )

    df["breakout"] = (
        close_above_resistance &
        breakout_volume &
        atr_is_healthy &
        atr_not_extreme &
        candle_quality &
        bullish_candle &
        trend_breakout
    )

    # =====================================================
    # Pullback متقدم
    # =====================================================

    distance_ema20 = (
        abs(
            close -
            df["ema20"]
        ) /
        (close + 1e-9)
    )

    distance_ema50 = (
        abs(
            close -
            df["ema50"]
        ) /
        (close + 1e-9)
    )

    near_ema20 = (
        distance_ema20 <= 0.025
    )

    near_ema50 = (
        distance_ema50 <= 0.035
    )

    trend_bullish = (
        (close > df["ema50"]) &
        (df["ema20"] > df["ema50"]) &
        (df["ema20_slope"] > 0)
    )

    support_near = (
        (
            abs(
                close -
                df["previous_support"]
            ) /
            (close + 1e-9)
        ) <= 0.04
    )

    fib_support_near = (
        (
            (
                abs(close - df["fib_382"]) /
                (close + 1e-9)
            ) <= 0.025
        )
        |
        (
            (
                abs(close - df["fib_500"]) /
                (close + 1e-9)
            ) <= 0.025
        )
        |
        (
            (
                abs(close - df["fib_618"]) /
                (close + 1e-9)
            ) <= 0.025
        )
    )

    # انخفاض ضغط البيع:
    # حجم البيع الحالي ليس أعلى بشكل حاد
    # والسهم لا يغلق بالقرب من قاع الشمعة
    close_location = (
        close -
        low
    ) / (
        candle_range +
        1e-9
    )

    selling_pressure_reduced = (
        (
            df["volume_ratio"] <= 1.30
        ) &
        (
            close_location >= 0.45
        )
    )

    bullish_confirmation = (
        (
            bullish_candle &
            (
                body := df["body_pct"]
            ).ge(0.35)
        )
        |
        (
            close >
            df["ema20"]
        )
    )

    pullback_score = (
        trend_bullish.astype(int) * 2 +
        (
            near_ema20 |
            near_ema50
        ).astype(int) * 2 +
        support_near.astype(int) +
        fib_support_near.astype(int) +
        selling_pressure_reduced.astype(int) +
        bullish_confirmation.astype(int)
    )

    df["pullback_quality_score"] = (
        pullback_score
    )

    df["pullback"] = (
        (
            pullback_score >= 6
        ) &
        trend_bullish
    )

    # =====================================================
    # Confirmed Swing Engine - no look-ahead at decision time
    # Pivot is only considered confirmed after PIVOT_RADIUS candles
    # =====================================================
    w = PIVOT_RADIUS * 2 + 1
    ph_candidate = high.eq(high.rolling(w, center=True, min_periods=w).max())
    pl_candidate = low.eq(low.rolling(w, center=True, min_periods=w).min())

    df["confirmed_swing_high_raw"] = high.where(ph_candidate).shift(PIVOT_RADIUS)
    df["confirmed_swing_low_raw"] = low.where(pl_candidate).shift(PIVOT_RADIUS)
    df["confirmed_swing_high"] = df["confirmed_swing_high_raw"].ffill()
    df["confirmed_swing_low"] = df["confirmed_swing_low_raw"].ffill()

    # Last confirmed pivot timestamps, also shifted by confirmation delay.
    idx_num = pd.Series(np.arange(len(df), dtype=float), index=df.index)
    df["confirmed_high_idx"] = idx_num.where(ph_candidate).shift(PIVOT_RADIUS).ffill()
    df["confirmed_low_idx"] = idx_num.where(pl_candidate).shift(PIVOT_RADIUS).ffill()

    # =====================================================
    # Confirmed Fibonacci - based on the latest confirmed impulse
    # =====================================================
    bull_leg = (
        df["confirmed_low_idx"].notna() &
        df["confirmed_high_idx"].notna() &
        (df["confirmed_low_idx"] < df["confirmed_high_idx"])
    )
    fib_hi = df["confirmed_swing_high"]
    fib_lo = df["confirmed_swing_low"]
    fib_range_confirmed = (fib_hi - fib_lo).where(bull_leg)

    for ratio, col in [(0.236, "fib_236"), (0.382, "fib_382"), (0.500, "fib_500"), (0.618, "fib_618"), (0.786, "fib_786")]:
        df[col] = (fib_hi - fib_range_confirmed * ratio).where(fib_range_confirmed > 0)

    # Bullish extensions are measured from confirmed low -> confirmed high.
    df["fib_ext_1272"] = (fib_hi + fib_range_confirmed * 0.272).where(fib_range_confirmed > 0)
    df["fib_ext_1618"] = (fib_hi + fib_range_confirmed * 0.618).where(fib_range_confirmed > 0)
    df["fib_ext_2000"] = (fib_hi + fib_range_confirmed * 1.000).where(fib_range_confirmed > 0)

    # =====================================================
    # Liquidity Engine: EGP turnover, not raw share volume
    # =====================================================
    df["turnover"] = close * vol
    df["turnover_ma20"] = df["turnover"].rolling(LIQUIDITY_LOOKBACK, min_periods=10).median()
    df["liquidity_ratio"] = df["turnover"] / (df["turnover_ma20"] + 1e-9)
    df["absolute_liquidity"] = df["turnover_ma20"]
    # 0..100 score: ~1m=50, ~10m=75, ~100m=100 (currency neutral log scale)
    df["absolute_liquidity_score"] = np.clip((np.log10(df["absolute_liquidity"].clip(lower=1))-4)/4*100,0,100)

    # Relative strength is computed later against the EGX cross-sectional proxy.
    df["return_20d"] = close.pct_change(RS_LOOKBACK)

    return df


# =========================================================
# 🧠 MARKET REGIME
# =========================================================

def market_regime(last):

    score = 0

    checks = [
        (
            np.isfinite(last.get("ema200", np.nan)) and
            last["Close"] > last["ema200"]
        ),
        last["ema20"] > last["ema50"],
        (
            np.isfinite(last.get("ema200", np.nan)) and
            last["ema50"] > last["ema200"]
        ),
        last["macd"] > last["macd_signal"],
        last["rsi"] > 50,
        last["adx"] > 20
    ]

    score = sum(checks)

    if score >= 6:
        return "🚀 قوي جداً"

    elif score >= 4:
        return "🟢 صعود"

    elif score >= 3:
        return "🟡 محايد"

    else:
        return "🔴 هبوط"


# =========================================================
# 📊 TIMEFRAME SCORE
# =========================================================

def timeframe_score(df):

    if df is None or df.empty:
        return 0

    last = df.iloc[-1]

    score = 0

    if (
        np.isfinite(last.get("ema200", np.nan)) and
        last["Close"] > last["ema200"]
    ):
        score += 25

    if last["ema20"] > last["ema50"]:
        score += 20

    if (
        np.isfinite(last.get("ema200", np.nan)) and
        last["ema50"] > last["ema200"]
    ):
        score += 20

    if last["macd"] > last["macd_signal"]:
        score += 15

    if last["rsi"] > 50:
        score += 10

    if last["ema20_slope"] > 0:
        score += 10

    # لا نعطي Score EMA200 كامل إذا غير مكتمل
    if not bool(last.get("ema200_complete", False)):
        score = min(
            score,
            55
        )

    return score


# =========================================================
# 📊 TREND ALIGNMENT
# =========================================================

def trend_alignment_score(
    df_d,
    df_w,
    df_m
):

    daily_score = timeframe_score(
        df_d
    )

    weekly_score = timeframe_score(
        df_w
    )

    monthly_score = timeframe_score(
        df_m
    )

    alignment = (
        daily_score * 0.40 +
        weekly_score * 0.35 +
        monthly_score * 0.25
    )

    return min(
        100,
        max(
            0,
            alignment
        )
    )


# =========================================================
# 🎯 حساب Pullback Entry
# =========================================================

def calculate_pullback_entry(df_d):
    last = df_d.iloc[-1]
    close = float(last["Close"])
    atr_val = float(last.get("atr", close * 0.03))
    if not np.isfinite(atr_val) or atr_val <= 0:
        atr_val = close * 0.03

    levels = []
    candidates = [
        ("Confirmed Support", last.get("previous_support", np.nan)),
        ("Confirmed Swing Low", last.get("confirmed_swing_low", np.nan)),
        ("EMA20", last.get("ema20", np.nan)),
        ("EMA50", last.get("ema50", np.nan)),
        ("Fib 38.2%", last.get("fib_382", np.nan)),
        ("Fib 50%", last.get("fib_500", np.nan)),
        ("Fib 61.8%", last.get("fib_618", np.nan)),
    ]
    for name, level in candidates:
        try:
            level = float(level)
            if np.isfinite(level) and level > 0 and level <= close:
                levels.append((name, level))
        except Exception:
            pass

    if not levels:
        return close, "لا توجد منطقة Pullback مؤكدة أسفل السعر"

    max_distance = max(atr_val * 1.5, close * 0.06)
    nearby = [x for x in levels if close - x[1] <= max_distance]
    if not nearby:
        return close, "لا يوجد Pullback قريب بما يكفي؛ انتظار تأكيد سعري"

    # Prefer the strongest structural level when several levels are close.
    priority = {"Confirmed Support": 1, "Confirmed Swing Low": 2, "Fib 61.8%": 3, "Fib 50%": 4, "Fib 38.2%": 5, "EMA50": 6, "EMA20": 7}
    name, price = min(nearby, key=lambda x: (priority.get(x[0], 99), abs(close-x[1])))
    return float(price), f"منطقة {name} مؤكدة + مسافة Pullback ضمن {max_distance/close*100:.1f}%"



# =========================================================
# 🎯 Entry Engine
# =========================================================

def build_confirmation_checklist(df_d, df_w=None, df_m=None, entry_type="انتظار تأكيد"):
    """Return explicit, actionable conditions still missing for confirmation."""
    if entry_type != "انتظار تأكيد": return []
    x=df_d.iloc[-1] if df_d is not None and not df_d.empty else pd.Series(dtype=float)
    checks=[]
    try:
        close=float(x.get("Close",np.nan)); ema20=float(x.get("ema20",np.nan)); ema50=float(x.get("ema50",np.nan)); rsi=float(x.get("rsi",np.nan)); macd=float(x.get("macd",np.nan)); ms=float(x.get("macd_signal",np.nan)); vr=float(x.get("volume_ratio",np.nan)); atrp=float(x.get("atr_pct",np.nan)); res=float(x.get("previous_resistance",np.nan))
        if np.isfinite(res) and close<=res: checks.append(f"إغلاق فوق المقاومة {res:.2f}")
        elif not np.isfinite(res): checks.append("اختراق مقاومة مؤكدة")
        if np.isfinite(vr) and vr<1.30: checks.append("Volume Ratio ≥ 1.30")
        if np.isfinite(rsi) and rsi<50: checks.append("RSI ≥ 50")
        if np.isfinite(macd) and np.isfinite(ms) and macd<=ms: checks.append("MACD أعلى من Signal")
        if np.isfinite(close) and np.isfinite(ema20) and close<=ema20: checks.append("السعر فوق EMA20")
        if np.isfinite(ema20) and np.isfinite(ema50) and ema20<=ema50: checks.append("EMA20 أعلى من EMA50")
        if np.isfinite(atrp) and not (0.015<=atrp<=0.12): checks.append("ATR% داخل النطاق المقبول")
    except Exception: pass
    return checks[:5]

def determine_entry(
    df_d,
    alignment
):

    last = df_d.iloc[-1]

    market_price = float(
        last["Close"]
    )

    previous_resistance = float(
        last.get(
            "previous_resistance",
            np.nan
        )
    )

    ema20 = float(
        last["ema20"]
    )

    ema50 = float(
        last["ema50"]
    )

    breakout = bool(
        last.get(
            "breakout",
            False
        )
    )

    pullback = bool(
        last.get(
            "pullback",
            False
        )
    )

    volume_ratio = float(
        last["volume_ratio"]
    )

    atr_pct = float(
        last["atr_pct"]
    )

    body_pct = float(
        last.get(
            "body_pct",
            0
        )
    )

    # =====================================================
    # 1️⃣ Breakout
    # =====================================================

    if (
        breakout and
        np.isfinite(previous_resistance) and
        market_price > previous_resistance and
        volume_ratio >= 1.5 and
        0.015 <= atr_pct <= 0.12 and
        body_pct >= 0.45 and
        alignment >= 60
    ):

        return {
            "type": "دخول اختراق",
            "price": market_price,
            "reason": (
                "اختراق مقاومة سابقة + حجم قوي + "
                "شمعة اختراق جيدة + ATR مناسب + "
                "Trend Alignment قوي"
            )
        }

    # =====================================================
    # 2️⃣ Professional Pullback
    # =====================================================

    if (
        pullback and
        ema20 > ema50 and
        alignment >= 55
    ):

        pullback_price, pullback_reason = (
            calculate_pullback_entry(
                df_d
            )
        )

        return {
            "type": "دخول عند Pullback",
            "price": pullback_price,
            "reason": (
                "اتجاه صاعد + منطقة دعم/EMA/Fibonacci + "
                "انخفاض ضغط البيع + تأكيد سعري | "
                + pullback_reason
            )
        }

    # =====================================================
    # 3️⃣ Immediate
    # =====================================================

    if (
        market_price > ema20 and
        market_price > ema50 and
        last["rsi"] >= 50 and
        last["macd"] > last["macd_signal"] and
        market_price > last["vwap"] and
        volume_ratio >= 1.0 and
        alignment >= 50
    ):

        return {
            "type": "دخول فوري",
            "price": market_price,
            "reason": (
                "السعر فوق EMA20/50 وVWAP + "
                "RSI إيجابي + MACD إيجابي + "
                "حجم مقبول + Trend Alignment"
            )
        }

    # =====================================================
    # 4️⃣ Confirmation
    # =====================================================

    return {
        "type": "انتظار تأكيد",
        "price": market_price,
        "reason": (
            "لا توجد حاليًا شروط كافية "
            "لدخول اختراق أو Pullback أو دخول فوري"
        )
    }


# =========================================================
# 🎯 TARGET ENGINE HELPERS
# =========================================================

def add_target_level(
    levels,
    price,
    reason,
    category
):

    try:

        price = float(price)

        if (
            np.isfinite(price) and
            price > 0
        ):

            levels.append({
                "price": price,
                "reason": reason,
                "category": category
            })

    except Exception:
        pass


def deduplicate_levels(
    levels,
    tolerance
):

    if not levels:
        return []

    levels = sorted(
        levels,
        key=lambda x: x["price"]
    )

    result = []

    for level in levels:

        if not result:

            result.append(level)

        else:

            previous = result[-1]

            relative_gap = (
                abs(
                    level["price"] -
                    previous["price"]
                )
                /
                max(
                    previous["price"],
                    1e-9
                )
            )

            if relative_gap >= tolerance:

                result.append(level)

            else:

                # نحتفظ بالأعلى أولوية
                priority = {
                    "Resistance": 1,
                    "Swing High": 2,
                    "Weekly": 3,
                    "Monthly": 4,
                    "Fibonacci": 5,
                    "ATR": 6
                }

                old_priority = priority.get(
                    previous["category"],
                    99
                )

                new_priority = priority.get(
                    level["category"],
                    99
                )

                if new_priority < old_priority:

                    result[-1] = level

    return result


# =========================================================
# 🛡️ PROFESSIONAL RISK & TARGET ENGINE
# =========================================================

def calculate_risk_engine(df_d, entry, capital, risk_percent, df_w=None, df_m=None, max_position_pct=DEFAULT_MAX_POSITION_PCT):
    last = df_d.iloc[-1]
    support = float(last.get("previous_support", np.nan))
    atr_val = float(last.get("atr", np.nan))
    if not np.isfinite(atr_val) or atr_val <= 0:
        atr_val = entry * 0.03

    bullish = bool(last.get("ema20", entry) > last.get("ema50", entry))
    # Stop is structural first, ATR only protects when no valid structure exists.
    stop_candidates = []
    for level in [support, last.get("confirmed_swing_low", np.nan)]:
        try:
            level = float(level)
            if np.isfinite(level) and 0 < level < entry:
                stop_candidates.append(level - atr_val * 0.20)
        except Exception:
            pass
    stop_candidates.append(entry - atr_val * (1.5 if bullish else 1.2))
    stop_candidates = [x for x in stop_candidates if np.isfinite(x) and 0 < x < entry]
    stop = max(stop_candidates) if stop_candidates else entry * 0.95

    risk_per_share = entry - stop
    if risk_per_share <= 0 or not np.isfinite(risk_per_share):
        risk_per_share = entry * 0.03
        stop = entry - risk_per_share
    risk_pct_actual = risk_per_share / entry
    allowed_loss = capital * risk_percent / 100.0
    position_size = allowed_loss / risk_per_share
    # V9: position-size cap prevents a mathematically valid but practically
    # oversized position when the stop is tight.
    max_position_value = capital * (float(max_position_pct) / 100.0)
    position_size = min(position_size, max_position_value / entry)
    position_value = position_size * entry

    # =====================================================
    # Target Engine: STRUCTURAL ONLY. No ATR-generated/fake targets.
    # =====================================================
    levels = []
    def add(price, reason, category):
        try:
            price = float(price)
            if np.isfinite(price) and price > entry:
                levels.append({"price": price, "reason": reason, "category": category})
        except Exception:
            pass

    add(last.get("previous_resistance", np.nan), "المقاومة اليومية السابقة", "Resistance")
    add(last.get("resistance", np.nan), "المقاومة اليومية الحالية", "Resistance")
    add(last.get("confirmed_swing_high", np.nan), "آخر Swing High مؤكد", "Swing High")

    for col, reason, cat in [
        ("fib_ext_1272", "Fibonacci Extension 127.2% مبني على Swing مؤكد", "Fibonacci"),
        ("fib_ext_1618", "Fibonacci Extension 161.8% مبني على Swing مؤكد", "Fibonacci"),
        ("fib_ext_2000", "Fibonacci Extension 200% مبني على Swing مؤكد", "Fibonacci"),
    ]:
        add(last.get(col, np.nan), reason, cat)

    if df_w is not None and not df_w.empty:
        try:
            w_high = df_w["High"].rolling(20, min_periods=10).max().shift(1).iloc[-1]
            add(w_high, "مقاومة Weekly سابقة", "Weekly")
        except Exception:
            pass
    if df_m is not None and not df_m.empty:
        try:
            m_high = df_m["High"].rolling(12, min_periods=6).max().shift(1).iloc[-1]
            add(m_high, "مقاومة Monthly سابقة", "Monthly")
        except Exception:
            pass

    priority = {"Resistance":1, "Swing High":2, "Weekly":3, "Monthly":4, "Fibonacci":5}
    levels.sort(key=lambda x: x["price"])
    dedup=[]
    for x in levels:
        if not dedup or abs(x["price"]-dedup[-1]["price"])/max(dedup[-1]["price"],1e-9) >= 0.008:
            dedup.append(x)
        elif priority.get(x["category"],99) < priority.get(dedup[-1]["category"],99):
            dedup[-1]=x

    min_gap = max(atr_val * 0.40, entry * 0.012)
    selected=[]
    for x in dedup:
        if not selected or x["price"] >= selected[-1]["price"] + min_gap:
            selected.append(x)
        if len(selected) >= 4:
            break

    # Do NOT fabricate missing targets.
    while len(selected) < 4:
        selected.append({"price": np.nan, "reason": "لا يوجد مستوى سعري هيكلي موثوق كافٍ", "category": "غير متاح"})

    prices=[x["price"] for x in selected]
    profits=[((p-entry)/entry*100) if np.isfinite(p) else np.nan for p in prices]
    rr=[((p-entry)/risk_per_share) if np.isfinite(p) else np.nan for p in prices]
    points={"Resistance":1.0,"Swing High":0.95,"Weekly":0.9,"Monthly":0.9,"Fibonacci":0.8,"غير متاح":0.0}
    target_quality=float(np.mean([points.get(x["category"],0.0) for x in selected])*100)

    structural_count=sum(np.isfinite(prices))
    return {
        "entry": float(entry), "stop": float(stop),
        "tp1": float(prices[0]) if np.isfinite(prices[0]) else np.nan,
        "tp2": float(prices[1]) if np.isfinite(prices[1]) else np.nan,
        "tp3": float(prices[2]) if np.isfinite(prices[2]) else np.nan,
        "tp4": float(prices[3]) if np.isfinite(prices[3]) else np.nan,
        "tp1_profit_pct": float(profits[0]) if np.isfinite(profits[0]) else np.nan,
        "tp2_profit_pct": float(profits[1]) if np.isfinite(profits[1]) else np.nan,
        "tp3_profit_pct": float(profits[2]) if np.isfinite(profits[2]) else np.nan,
        "tp4_profit_pct": float(profits[3]) if np.isfinite(profits[3]) else np.nan,
        "tp1_reason": selected[0]["reason"], "tp2_reason": selected[1]["reason"], "tp3_reason": selected[2]["reason"], "tp4_reason": selected[3]["reason"],
        "tp1_category": selected[0]["category"], "tp2_category": selected[1]["category"], "tp3_category": selected[2]["category"], "tp4_category": selected[3]["category"],
        "rr1": float(rr[0]) if np.isfinite(rr[0]) else np.nan, "rr2": float(rr[1]) if np.isfinite(rr[1]) else np.nan, "rr3": float(rr[2]) if np.isfinite(rr[2]) else np.nan, "rr4": float(rr[3]) if np.isfinite(rr[3]) else np.nan,
        "target_quality": target_quality, "risk_pct": float(risk_pct_actual*100),
        "position_size": float(position_size), "position_value": float(position_value),
        "structural_target_count": structural_count
    }



# =========================================================
# 🧠 CONFIDENCE ENGINE
# =========================================================

def ai_confidence(
    last_d,
    last_w,
    last_m,
    alignment,
    data_quality
):

    score = 0
    total = 13

    if (
        np.isfinite(last_d.get("ema200", np.nan)) and
        last_d["Close"] > last_d["ema200"]
    ):
        score += 1

    if (
        np.isfinite(last_w.get("ema200", np.nan)) and
        last_w["Close"] > last_w["ema200"]
    ):
        score += 1

    if (
        np.isfinite(last_m.get("ema200", np.nan)) and
        last_m["Close"] > last_m["ema200"]
    ):
        score += 1

    if last_d["macd"] > last_d["macd_signal"]:
        score += 1

    if 45 < last_d["rsi"] < 70:
        score += 1

    if last_d["volume_ratio"] > 1:
        score += 1

    if last_d["adx"] > 20:
        score += 1

    if 40 < last_d["mfi"] < 80:
        score += 1

    if (
        np.isfinite(last_d["obv"]) and
        np.isfinite(last_d["obv_ma"]) and
        last_d["obv"] > last_d["obv_ma"]
    ):
        score += 1

    if (
        np.isfinite(last_d["stoch_rsi_k"]) and
        np.isfinite(last_d["stoch_rsi_d"]) and
        last_d["stoch_rsi_k"] >
        last_d["stoch_rsi_d"]
    ):
        score += 1

    if (
        np.isfinite(last_d["vwap"]) and
        last_d["Close"] > last_d["vwap"]
    ):
        score += 1

    if alignment >= 60:
        score += 1

    if data_quality >= 90:
        score += 1

    return score / total


# =========================================================
# 🧠 CONFIDENCE TARGET MODEL
# =========================================================

def estimate_probabilities(
    base_conf,
    rr1,
    rr2,
    rr3,
    rr4,
    alignment,
    adx_val
):

    trend_factor = (
        alignment /
        100
    )

    momentum_factor = min(
        1.0,
        max(
            0.5,
            adx_val / 35
        )
    )

    base = (
        base_conf * 0.60 +
        trend_factor * 0.25 +
        momentum_factor * 0.15
    )

    tp1 = base

    if rr1 >= 2:
        tp1 += 0.05

    elif rr1 < 1.2:
        tp1 -= 0.10

    tp1 = min(
        0.90,
        max(
            0.20,
            tp1
        )
    )

    tp2 = tp1 * 0.82

    if rr2 >= 2:
        tp2 += 0.03

    elif rr2 < 1.5:
        tp2 -= 0.05

    tp2 = min(
        0.82,
        max(
            0.15,
            tp2
        )
    )

    tp3 = tp2 * 0.78

    if rr3 >= 2.5:
        tp3 += 0.03

    elif rr3 < 2:
        tp3 -= 0.05

    tp3 = min(
        0.75,
        max(
            0.10,
            tp3
        )
    )

    tp4 = tp3 * 0.72

    if rr4 >= 3:
        tp4 += 0.03

    elif rr4 < 2.5:
        tp4 -= 0.05

    tp4 = min(
        0.68,
        max(
            0.08,
            tp4
        )
    )

    return (
        tp1,
        tp2,
        tp3,
        tp4
    )


# =========================================================
# 🧠 PROFESSIONAL MARKET REGIME / STRATEGY CLASSIFIER
# =========================================================
def classify_market_regime(df):
    if df is None or len(df)<50: return "NEUTRAL",0.0
    x=add_indicators(df.copy()); last=x.iloc[-1]
    checks=[last.get("Close",0)>last.get("ema200",np.inf), last.get("ema20",0)>last.get("ema50",0), last.get("macd",0)>last.get("macd_signal",0), last.get("rsi",50)>50]
    score=sum(bool(v) for v in checks)/len(checks)*100
    atr=float(last.get("atr_pct",0) or 0)
    if atr>0.10: return "HIGH_VOLATILITY",score
    if score>=75: return "BULL",score
    if score<=25: return "BEAR",score
    return "NEUTRAL",score

def classify_strategy(row):
    if bool(row.get("breakout",False)): return "BREAKOUT"
    if bool(row.get("pullback",False)): return "PULLBACK"
    return "MOMENTUM"

# =========================================================
# 🧠 التحليل الرئيسي
# =========================================================

def analyze(
    df_d,
    df_w,
    df_m,
    capital,
    risk_percent,
    max_position_pct=DEFAULT_MAX_POSITION_PCT
):

    df_d = add_indicators(
        df_d
    )

    df_w = add_indicators(
        df_w
    )

    df_m = add_indicators(
        df_m
    )

    # =====================================================
    # التأكد من البيانات
    # =====================================================

    if len(df_d) < MIN_DAILY_ROWS:
        raise ValueError(
            "بيانات يومية غير كافية"
        )

    if len(df_w) < MIN_WEEKLY_ROWS:
        raise ValueError(
            "بيانات أسبوعية غير كافية"
        )

    if len(df_m) < MIN_MONTHLY_ROWS:
        raise ValueError(
            "بيانات شهرية غير كافية"
        )

    # =====================================================
    # Data Quality
    # =====================================================

    quality_d = calculate_data_quality(
        df_d
    )

    quality_w = calculate_data_quality(
        df_w
    )

    quality_m = calculate_data_quality(
        df_m
    )

    data_quality = (
        quality_d["quality"] * 0.50 +
        quality_w["quality"] * 0.30 +
        quality_m["quality"] * 0.20
    )

    # =====================================================
    # تنظيف المؤشرات
    # =====================================================

    required_daily = [
        "ema20",
        "ema50",
        "rsi",
        "macd",
        "macd_signal",
        "macd_hist",
        "vol_ma",
        "volume_ratio",
        "obv",
        "obv_ma",
        "obv_slope",
        "mfi",
        "stoch_rsi",
        "stoch_rsi_k",
        "stoch_rsi_d",
        "stoch_rsi_k_slope",
        "vwap",
        "support",
        "resistance",
        "previous_support",
        "previous_resistance",
        "atr",
        "adx",
        "ema20_slope",
        "ema50_slope",
        "body_pct"
    ]

    required_tf = [
        "ema20",
        "ema50",
        "macd",
        "macd_signal",
        "rsi",
        "ema20_slope"
    ]

    # EMA200 لا يدخل في required_tf
    # لأننا نريد معرفة هل هو مكتمل أم لا
    df_d = df_d.dropna(
        subset=required_daily
    )

    df_w = df_w.dropna(
        subset=required_tf
    )

    df_m = df_m.dropna(
        subset=required_tf
    )

    if (
        df_d.empty or
        df_w.empty or
        df_m.empty
    ):

        raise ValueError(
            "المؤشرات غير متاحة"
        )

    # =====================================================
    # آخر قراءة
    # =====================================================

    last_d = df_d.iloc[-1]
    last_w = df_w.iloc[-1]
    last_m = df_m.iloc[-1]

    market_price = float(
        last_d["Close"]
    )

    if market_price <= 0:
        raise ValueError(
            "سعر غير صحيح"
        )

    # =====================================================
    # Liquidity + Relative Strength
    # =====================================================
    liquidity_ratio = float(last_d.get("liquidity_ratio", np.nan))
    if not np.isfinite(liquidity_ratio):
        liquidity_ratio = 0.0
    stock_return_20 = float(last_d.get("return_20d", np.nan))
    market_return_20 = float(last_d.get("market_return_20", np.nan))
    if not np.isfinite(stock_return_20):
        stock_return_20 = 0.0
    if not np.isfinite(market_return_20):
        market_return_20 = 0.0
    relative_strength = stock_return_20 - market_return_20
    liquidity_score = 5 if liquidity_ratio >= 2 else 4 if liquidity_ratio >= 1.5 else 3 if liquidity_ratio >= 1.0 else 1 if liquidity_ratio >= 0.7 else 0
    absolute_liquidity = float(last_d.get("absolute_liquidity", 0.0) or 0.0)
    absolute_liquidity_score = float(last_d.get("absolute_liquidity_score", 0.0) or 0.0)
    strategy_type = classify_strategy(last_d)
    regime_name, regime_score = classify_market_regime(df_d)
    rs_score = 5 if relative_strength >= 0.10 else 4 if relative_strength >= 0.05 else 3 if relative_strength >= 0 else 1 if relative_strength >= -0.05 else 0

    # =====================================================
    # EMA200 Quality
    # =====================================================

    daily_ema200_complete = (
        len(df_d) >= EMA200_REQUIRED_ROWS
    )

    weekly_ema200_complete = (
        len(df_w) >= EMA200_REQUIRED_ROWS
    )

    monthly_ema200_complete = (
        len(df_m) >= EMA200_REQUIRED_ROWS
    )

    ema200_status = (
        "✅ مكتمل"
        if (
            daily_ema200_complete and
            weekly_ema200_complete and
            monthly_ema200_complete
        )
        else "⚠️ غير مكتمل"
    )

    # =====================================================
    # Trend Alignment
    # =====================================================

    alignment = trend_alignment_score(
        df_d,
        df_w,
        df_m
    )

    # =====================================================
    # Market Regime
    # =====================================================

    regime = market_regime(
        last_d
    )

    # =====================================================
    # Entry Engine
    # =====================================================

    entry_info = determine_entry(
        df_d,
        alignment
    )

    entry = float(
        entry_info["price"]
    )

    entry_type = entry_info["type"]
    entry_reason = entry_info["reason"]
    confirmation_checklist = build_confirmation_checklist(df_d, df_w, df_m, entry_type)

    # =====================================================
    # Risk / Target Engine
    # =====================================================

    risk = calculate_risk_engine(
        df_d,
        entry,
        capital,
        risk_percent,
        df_w,
        df_m,
        max_position_pct
    )

    stop = risk["stop"]

    tp1 = risk["tp1"]
    tp2 = risk["tp2"]
    tp3 = risk["tp3"]
    tp4 = risk["tp4"]

    # =====================================================
    # Score جديد من 100
    #
    # 25 Trend
    # 15 Momentum
    # 15 Volume / Money Flow
    # 10 Trend Strength
    # 10 Price Structure
    # 10 Entry Quality
    # 10 Target Quality
    # 5 Risk
    #
    # TOTAL = 100
    # =====================================================

    score = 0.0

    # =====================================================
    # 1. Trend Quality = 25
    #
    # لا نكرر EMA20/50/200 بشكل زائد
    # =====================================================

    trend_component = (
        alignment * 0.25
    )

    score += trend_component

    # =====================================================
    # 2. Momentum = 15
    # =====================================================

    rsi = float(
        last_d["rsi"]
    )

    momentum_score = 0

    if 50 <= rsi <= 65:
        momentum_score += 7

    elif 45 <= rsi < 50:
        momentum_score += 5

    elif 65 < rsi <= 70:
        momentum_score += 5

    elif 35 <= rsi < 45:
        momentum_score += 2

    if (
        last_d["macd"] >
        last_d["macd_signal"]
    ):
        momentum_score += 5

    elif last_d["macd_hist"] > 0:
        momentum_score += 3

    stoch_k = float(
        last_d["stoch_rsi_k"]
    )

    stoch_d = float(
        last_d["stoch_rsi_d"]
    )

    if stoch_k > stoch_d:
        momentum_score += 3

    score += min(
        15,
        momentum_score
    )

    # =====================================================
    # 3. Volume / Money Flow = 10
    # =====================================================

    volume_ratio = float(
        last_d["volume_ratio"]
    )

    money_score = 0

    if volume_ratio >= 2:
        money_score += 5

    elif volume_ratio >= 1.5:
        money_score += 4

    elif volume_ratio >= 1.1:
        money_score += 3

    elif volume_ratio >= 0.8:
        money_score += 1

    mfi = float(
        last_d["mfi"]
    )

    if 50 <= mfi <= 75:
        money_score += 4

    elif 40 <= mfi < 50:
        money_score += 2

    elif 75 < mfi <= 85:
        money_score += 2

    obv = float(
        last_d["obv"]
    )

    obv_ma = float(
        last_d["obv_ma"]
    )

    obv_slope = float(
        last_d["obv_slope"]
    )

    if (
        obv > obv_ma and
        obv_slope > 0
    ):
        money_score += 6

    elif (
        obv > obv_ma or
        obv_slope > 0
    ):
        money_score += 4

    elif obv_slope > 0:
        money_score += 2

    score += min(
        10,
        money_score
    )

    # =====================================================
    # 4. Trend Strength = 5
    # =====================================================

    adx_val = float(
        last_d["adx"]
    )

    strength_score = 0

    if adx_val >= 30:
        strength_score = 5
    elif adx_val >= 25:
        strength_score = 4
    elif adx_val >= 20:
        strength_score = 3
    elif adx_val >= 15:
        strength_score = 1.5

    # V9: cap ADX contribution at the declared 5 points.
    score += min(5, strength_score)

    # =====================================================
    # 5. Price Structure = 10
    # =====================================================

    structure_score = 0

    if (
        last_d["ema20_slope"] > 0 and
        last_d["ema50_slope"] > 0
    ):
        structure_score += 4

    elif last_d["ema20_slope"] > 0:
        structure_score += 2

    if (
        last_d["Close"] >
        last_d["vwap"]
    ):
        structure_score += 3

    if (
        last_d["Close"] >
        last_d["ema50"]
    ):
        structure_score += 3

    score += min(
        10,
        structure_score
    )

    # =====================================================
    # 6. Entry Quality = 10
    # =====================================================

    entry_score = 0

    if entry_type == "دخول عند Pullback":
        entry_score = 10

    elif entry_type == "دخول اختراق":
        entry_score = 9

    elif entry_type == "دخول فوري":
        entry_score = 7

    else:
        entry_score = 2

    score += entry_score

    # =====================================================
    # 7. Target Quality = 10
    # =====================================================

    target_quality = float(
        risk["target_quality"]
    )

    target_component = (
        target_quality *
        0.10
    )

    score += target_component

    # =====================================================
    # 8. Risk Quality = 5
    # =====================================================

    rr1 = float(
        risk["rr1"]
    )

    risk_pct_actual = float(
        risk["risk_pct"]
    )

    risk_score = 0

    if np.isfinite(rr1) and rr1 >= 2:
        risk_score += 3

    elif rr1 >= 1.5:
        risk_score += 2

    elif rr1 >= 1.2:
        risk_score += 1

    if risk_pct_actual <= 5:
        risk_score += 2

    elif risk_pct_actual <= 8:
        risk_score += 1

    score += min(
        5,
        risk_score
    )

    # =====================================================
    # EMA200 incomplete penalty
    # =====================================================

    incomplete_count = sum([
        not daily_ema200_complete,
        not weekly_ema200_complete,
        not monthly_ema200_complete
    ])

    if incomplete_count >= 2:
        score -= 4

    elif incomplete_count == 1:
        score -= 2

    # =====================================================
    # لا نعطي 85+ إذا كان Entry مجرد انتظار
    # =====================================================

    if entry_type == "انتظار تأكيد":

        score = min(
            score,
            69
        )

    # =====================================================
    # Final Score
    # =====================================================

    score = min(
        100,
        max(
            0,
            score
        )
    )

    # =====================================================
    # Confidence
    # =====================================================

    base_conf = ai_confidence(
        last_d,
        last_w,
        last_m,
        alignment,
        data_quality
    )

    (
        tp1_prob,
        tp2_prob,
        tp3_prob,
        tp4_prob
    ) = estimate_probabilities(
        base_conf,
        0 if not np.isfinite(risk["rr1"]) else risk["rr1"],
        0 if not np.isfinite(risk["rr2"]) else risk["rr2"],
        0 if not np.isfinite(risk["rr3"]) else risk["rr3"],
        0 if not np.isfinite(risk["rr4"]) else risk["rr4"],
        alignment,
        adx_val
    )

    # =====================================================
    # Signal
    # =====================================================

    if (
        score >= 85 and
        np.isfinite(rr1) and rr1 >= 1.5 and
        alignment >= 65 and
        entry_type != "انتظار تأكيد"
    ):

        signal = "🔥 قوي جداً"

    elif (
        score >= 70 and
        np.isfinite(rr1) and rr1 >= 1.3 and
        entry_type != "انتظار تأكيد"
    ):

        signal = "🟢 قوي"

    elif score >= 55:

        signal = "🟡 متوسط"

    else:

        signal = "⚠️ متابعة"

    # =====================================================
    # المدة المتوقعة
    # =====================================================

    volatility = (
        float(last_d["atr"]) /
        entry
    )

    if volatility > 0.07:
        time_est = "1 - 3 أسابيع"

    elif volatility > 0.04:
        time_est = "3 - 8 أسابيع"

    elif volatility > 0.02:
        time_est = "1 - 3 شهور"

    else:
        time_est = "2 - 4 شهور"

    # =====================================================
    # النتيجة
    # =====================================================

    return {

        "التقييم": round(
            score,
            2
        ),

        "الإشارة": signal,

        "الاتجاه": regime,

        "نوع الدخول": entry_type,
        "قائمة التأكيد": " • ".join(confirmation_checklist) if confirmation_checklist else "مكتمل",

        "سبب الدخول": entry_reason,

        "سعر الدخول": round(
            entry,
            2
        ),

        "وقف الخسارة": round(
            stop,
            2
        ),

        "الهدف الأول": round(
            tp1,
            2
        ),

        "الهدف الثاني": round(
            tp2,
            2
        ),

        "الهدف الثالث": round(
            tp3,
            2
        ),

        "الهدف الرابع": round(
            tp4,
            2
        ),

        "سبب الهدف الأول": risk[
            "tp1_reason"
        ],

        "سبب الهدف الثاني": risk[
            "tp2_reason"
        ],

        "سبب الهدف الثالث": risk[
            "tp3_reason"
        ],

        "سبب الهدف الرابع": risk[
            "tp4_reason"
        ],

        "نوع الهدف الأول": risk[
            "tp1_category"
        ],

        "نوع الهدف الثاني": risk[
            "tp2_category"
        ],

        "نوع الهدف الثالث": risk[
            "tp3_category"
        ],

        "نوع الهدف الرابع": risk[
            "tp4_category"
        ],

        "ربح الهدف الأول %": round(
            risk["tp1_profit_pct"],
            2
        ),

        "ربح الهدف الثاني %": round(
            risk["tp2_profit_pct"],
            2
        ),

        "ربح الهدف الثالث %": round(
            risk["tp3_profit_pct"],
            2
        ),

        "ربح الهدف الرابع %": round(
            risk["tp4_profit_pct"],
            2
        ),

        "R/R الهدف الأول": round(
            risk["rr1"],
            2
        ),

        "R/R الهدف الثاني": round(
            risk["rr2"],
            2
        ),

        "R/R الهدف الثالث": round(
            risk["rr3"],
            2
        ),

        "R/R الهدف الرابع": round(
            risk["rr4"],
            2
        ),

        "ثقة الهدف الأول %": round(
            tp1_prob * 100,
            1
        ),

        "ثقة الهدف الثاني %": round(
            tp2_prob * 100,
            1
        ),

        "ثقة الهدف الثالث %": round(
            tp3_prob * 100,
            1
        ),

        "ثقة الهدف الرابع %": round(
            tp4_prob * 100,
            1
        ),

        "جودة الأهداف": round(
            target_quality,
            1
        ),

        "EMA200": ema200_status,

        "التذبذب ATR %": round(
            volatility * 100,
            2
        ),

        "قوة الاتجاه ADX": round(
            adx_val,
            2
        ),

        "مؤشر RSI": round(
            rsi,
            2
        ),

        "المدة المتوقعة": time_est,
        "السيولة Ratio": round(liquidity_ratio, 2),
        "متوسط قيمة التداول": round(absolute_liquidity, 2),
        "Absolute Liquidity Score": round(absolute_liquidity_score, 2),
        "استراتيجية الإشارة": strategy_type,
        "حالة السوق": regime_name,
        "قوة السوق": round(regime_score, 1),
        "قوة السيولة": round(liquidity_score + rs_score, 2),
        "Relative Strength %": round(relative_strength * 100, 2),
        "عدد الأهداف الهيكلية": int(risk.get("structural_target_count", 0)),

        # =================================================
        # معلومات داخلية
        # =================================================

        "_entry_type": entry_type,

        "_trend_alignment": round(
            alignment,
            2
        ),

        "_data_quality": round(
            data_quality,
            2
        ),

        "_ema200_daily": (
            "مكتمل"
            if daily_ema200_complete
            else "غير مكتمل"
        ),

        "_ema200_weekly": (
            "مكتمل"
            if weekly_ema200_complete
            else "غير مكتمل"
        ),

        "_ema200_monthly": (
            "مكتمل"
            if monthly_ema200_complete
            else "غير مكتمل"
        ),

        "_risk_pct": round(
            risk["risk_pct"],
            2
        ),

        "_rr1": round(
            risk["rr1"],
            2
        ),

        "_rr2": round(
            risk["rr2"],
            2
        ),

        "_rr3": round(
            risk["rr3"],
            2
        ),

        "_rr4": round(
            risk["rr4"],
            2
        ),

        "_target_quality": round(
            target_quality,
            2
        ),

        "_position_size": round(
            risk["position_size"],
            2
        ),

        "_position_value": round(
            risk["position_value"],
            2
        ),

        "_obv": round(
            obv,
            2
        ),

        "_obv_ma": round(
            obv_ma,
            2
        ),

        "_stoch_rsi_k": round(
            stoch_k,
            4
        ),

        "_stoch_rsi_d": round(
            stoch_d,
            4
        ),

        "_vwap": round(
            float(last_d["vwap"]),
            4
        ),

        "_pullback_quality": round(
            float(
                last_d.get(
                    "pullback_quality_score",
                    0
                )
            ),
            2
        ),

        "_volume_ratio": round(
            volume_ratio,
            2
        ),
        "_liquidity_ratio": round(liquidity_ratio, 2),
        "_relative_strength": round(relative_strength * 100, 2),
        "_structural_target_count": int(risk.get("structural_target_count", 0))
    }


# =========================================================
# 🧪 V9 REALISTIC HISTORICAL BACKTEST / VALIDATION ENGINE
# =========================================================
def _bt_signal(row):
    """Signal logic shared by the V9 backtest. Only signal-bar information."""
    try:
        close=float(row["Close"]); ema20=float(row["ema20"]); ema50=float(row["ema50"])
        rsi=float(row["rsi"]); macd=float(row["macd"]); macd_signal=float(row["macd_signal"])
        vol_ratio=float(row["volume_ratio"]); body_pct=float(row["body_pct"]); atr_pct=float(row["atr_pct"])
    except Exception:
        return False
    if not all(np.isfinite(x) for x in [close,ema20,ema50,rsi,macd,macd_signal,vol_ratio,body_pct,atr_pct]):
        return False
    breakout=bool(row.get("breakout",False))
    pullback=bool(row.get("pullback",False))
    immediate=(close>ema20>ema50 and rsi>=50 and macd>macd_signal and vol_ratio>=1.0 and 0.015<=atr_pct<=0.12)
    try: prev_res=float(row.get("previous_resistance",np.nan))
    except Exception: prev_res=np.nan
    breakout_fallback=np.isfinite(prev_res) and close>prev_res and vol_ratio>=1.30 and body_pct>=0.35 and close>ema20>ema50 and 0.015<=atr_pct<=0.12
    pullback_fallback=(close>ema20>ema50 and (abs(close-ema20)/close<=0.03 or abs(close-ema50)/close<=0.05) and rsi>=45 and macd>=macd_signal)
    return bool(breakout or pullback or immediate or breakout_fallback or pullback_fallback)


def _bt_structural_targets(row, entry):
    vals=[]
    for col,name in [
        ("previous_resistance","مقاومة يومية سابقة"),("resistance","مقاومة يومية"),
        ("confirmed_swing_high","آخر Swing High مؤكد"),("fib_ext_1272","Fib 127.2%"),
        ("fib_ext_1618","Fib 161.8%"),("fib_ext_2000","Fib 200%")]:
        try:
            x=float(row.get(col,np.nan))
            if np.isfinite(x) and x>entry*1.001: vals.append((x,name))
        except Exception: pass
    vals=sorted(vals,key=lambda z:z[0])
    out=[]
    for x,name in vals:
        if not out or abs(x-out[-1][0])/max(out[-1][0],1e-9)>=0.008:
            out.append((x,name))
        if len(out)>=4: break
    return out


def _simulate_bt_window(df, start_idx, end_idx, commission_pct=0.15, slippage_pct=0.10):
    trades=[]; equity=1.0; peak=1.0; max_dd=0.0; next_allowed=start_idx
    signals=entries=skipped_no_target=skipped_bad_stop=0
    warmup=max(BACKTEST_WARMUP,220)
    for i in range(max(start_idx,warmup), min(end_idx,len(df)-2)):
        if i<next_allowed: continue
        row=df.iloc[i]
        try:
            needed=["Open","High","Low","Close","ema20","ema50","rsi","macd","macd_signal","atr","volume_ratio","body_pct","atr_pct"]
            if not all(np.isfinite(float(row.get(c,np.nan))) for c in needed): continue
            atr_val=float(row["atr"]); close=float(row["Close"])
            if atr_val<=0 or close<=0 or not _bt_signal(row): continue
            signals+=1
            raw_entry=float(df.iloc[i+1]["Open"])
            if not np.isfinite(raw_entry) or raw_entry<=0: continue
            # Buy-side execution cost: worse fill.
            entry=raw_entry*(1+slippage_pct/100.0+commission_pct/100.0)
            try: swing=float(row.get("confirmed_swing_low",np.nan))
            except Exception: swing=np.nan
            if np.isfinite(swing) and 0<swing<entry:
                stop=max(swing-atr_val*0.20, entry-atr_val*1.50)
            else: stop=entry-atr_val*1.50
            if not np.isfinite(stop) or stop<=0 or stop>=entry:
                skipped_bad_stop+=1; continue
            targets=_bt_structural_targets(row,entry)
            # V9 STRICT: no ATR target fallback. No structural target = no trade.
            if not targets:
                skipped_no_target+=1; continue
            entries+=1
            tprices=[x[0] for x in targets]
            # Partial exits: 25% at each available target. Remainder exits on trailing stop / final close.
            remaining=1.0; realized=0.0; tp_hits=0; exit_i=None
            trail=stop
            for j in range(i+1,min(end_idx,len(df))):
                bar=df.iloc[j]
                try: low=float(bar["Low"]); high=float(bar["High"]); close_j=float(bar["Close"])
                except Exception: continue
                # Conservative OHLC assumption: stop wins ties.
                if low<=trail:
                    exit_raw=trail*(1-slippage_pct/100.0-commission_pct/100.0)
                    realized += remaining*((exit_raw-entry)/entry); remaining=0; exit_i=j; break
                while tp_hits<len(tprices) and high>=tprices[tp_hits]:
                    qty=min(0.25,remaining)
                    exit_raw=tprices[tp_hits]*(1-slippage_pct/100.0-commission_pct/100.0)
                    realized += qty*((exit_raw-entry)/entry)
                    remaining-=qty; tp_hits+=1
                    # Progressive trailing: break-even after TP1, then prior-bar low / ATR trail.
                    if tp_hits==1: trail=max(trail,entry)
                    else: trail=max(trail,float(bar["Low"]), close_j-atr_val*1.5)
                if remaining<=1e-9:
                    exit_i=j; break
                # trailing update only after a confirmed target hit
                if tp_hits>0:
                    trail=max(trail,close_j-atr_val*1.5)
            if remaining>1e-9:
                j=min(end_idx-1,len(df)-1)
                exit_raw=float(df.iloc[j]["Close"])*(1-slippage_pct/100.0-commission_pct/100.0)
                realized += remaining*((exit_raw-entry)/entry); exit_i=j
            ret=float(realized)
            equity*=max(0.0001,1+ret); peak=max(peak,equity); max_dd=max(max_dd,(peak-equity)/peak)
            trades.append({"return":ret,"tp_hits":tp_hits,"bars":int(exit_i-i),"entry":entry,"entry_idx":int(i),"exit_idx":int(exit_i)})
            next_allowed=max(next_allowed,int(exit_i)+1)
        except Exception:
            continue
    return trades,equity,max_dd,signals,entries,skipped_no_target,skipped_bad_stop


def _summarize_bt(trades,equity,max_dd,signals,entries,skipped_no_target,skipped_bad_stop,test_bars=252, df=None):
    rets=np.array([t["return"] for t in trades],dtype=float) if trades else np.array([],dtype=float)
    wins=rets[rets>0]; losses=rets[rets<0]
    gross_win=float(wins.sum()) if len(wins) else 0.0; gross_loss=float(abs(losses.sum())) if len(losses) else 0.0
    pf=(gross_win/gross_loss) if gross_loss>0 else (999.0 if gross_win>0 else 0.0)
    expectancy=float(rets.mean()) if len(rets) else 0.0
    # Daily closed-equity curve: capital is updated on the day a trade closes.
    daily_sharpe=daily_sortino=daily_calmar=0.0
    curve_dd=max_dd
    if df is not None and len(df):
        try:
            idx=pd.DatetimeIndex(df.index)
            curve=pd.Series(1.0,index=idx,dtype=float)
            eq=1.0
            exits={}
            for t in trades: exits[int(t.get("exit_idx",0))]=max(0.0001,1+float(t["return"]))
            for i in range(len(curve)):
                if i in exits: eq*=exits[i]
                curve.iloc[i]=eq
            dr=curve.pct_change().replace([np.inf,-np.inf],np.nan).dropna()
            if len(dr)>1 and float(dr.std(ddof=1))>0: daily_sharpe=float(dr.mean()/dr.std(ddof=1)*np.sqrt(252))
            downside=dr[dr<0]
            if len(downside)>1 and float(downside.std(ddof=1))>0: daily_sortino=float(dr.mean()/downside.std(ddof=1)*np.sqrt(252))
            roll=curve.cummax(); curve_dd=float((1-curve/roll).max())
            yrs=max(len(curve)/252.0,1/252); cagr=eq**(1/yrs)-1 if eq>0 and trades else 0.0
            daily_calmar=(cagr/curve_dd) if curve_dd>0 else 0.0
        except Exception: pass
    # Fallback to legacy trade-close metrics if a curve cannot be built.
    std=float(rets.std(ddof=1)) if len(rets)>1 else 0.0
    years=max(test_bars/252.0,1/252)
    cagr=equity**(1/years)-1 if equity>0 and trades else 0.0
    sharpe=daily_sharpe if daily_sharpe!=0 else ((float(rets.mean())/std*np.sqrt(max(1,len(rets)))) if std>0 else 0.0)
    sortino=daily_sortino if daily_sortino!=0 else 0.0
    calmar=daily_calmar if daily_calmar!=0 else ((cagr/max(curve_dd,1e-12)) if curve_dd>0 else 0.0)
    return {"trades":len(trades),"closed_trades":len(trades),"open_trades":0,
            "win_rate":(len(wins)/len(rets)*100 if len(rets) else 0.0),"profit_pct":(equity-1)*100,
            "max_drawdown_pct":curve_dd*100,"profit_factor":pf,"avg_trade_pct":expectancy*100,
            "expectancy_pct":expectancy*100,"avg_win_pct":(wins.mean()*100 if len(wins) else 0),
            "avg_loss_pct":(losses.mean()*100 if len(losses) else 0),"sharpe":sharpe,"sortino":sortino,
            "calmar":calmar,"signals":signals,"entries":entries,"skipped_no_target":skipped_no_target,
            "skipped_bad_stop":skipped_bad_stop,"tp1_hit_rate":(sum(t["tp_hits"]>=1 for t in trades)/len(trades)*100 if trades else 0),
            "tp2_hit_rate":(sum(t["tp_hits"]>=2 for t in trades)/len(trades)*100 if trades else 0),
            "tp3_hit_rate":(sum(t["tp_hits"]>=3 for t in trades)/len(trades)*100 if trades else 0),
            "tp4_hit_rate":(sum(t["tp_hits"]>=4 for t in trades)/len(trades)*100 if trades else 0),
            "bars_used":int(test_bars),"avg_holding_bars":(float(np.mean([x["bars"] for x in trades])) if trades else 0.0),
            "cagr_pct":cagr*100,"daily_equity_curve":curve if df is not None and len(df) else None}


def run_multi_horizon_backtest(df, commission_pct=None, slippage_pct=None, monte_carlo_runs=500, horizons=BACKTEST_HORIZONS):
    """Run independent chronological horizons and measure robustness across horizons."""
    runs={}
    for h in horizons:
        try: runs[h]=run_real_backtest(df, h, commission_pct, slippage_pct, monte_carlo_runs)
        except Exception: runs[h]={"trades":0,"profit_pct":0.0,"max_drawdown_pct":0.0,"expectancy_pct":0.0,"sharpe":0.0,"sortino":0.0,"calmar":0.0,"walk_forward_score":0.0,"oos_return_pct":0.0}
    vals=[r.get("profit_pct",0.0) for r in runs.values() if r.get("trades",0)>0]
    positive=sum(v>0 for v in vals) / len(vals) if vals else 0.0
    mean_ret=float(np.mean(vals)) if vals else 0.0
    cv=float(np.std(vals,ddof=1)/max(abs(mean_ret),1e-9)) if len(vals)>1 else 9.0
    stability=float(np.clip(70*positive + 30*(1/(1+cv)),0,100)) if vals else 0.0
    return runs, round(stability,2)

def statistical_evidence_weight(trades):
    """Confidence weight for historical evidence; avoids treating 10 trades like 100+."""
    try: n=float(trades)
    except Exception: n=0
    if n<=0: return 0.0
    return round(float(np.clip(1-np.exp(-n/30.0),0,1)*100),2)

def run_real_backtest(df, max_bars=300, commission_pct=None, slippage_pct=None, monte_carlo_runs=500):
    empty={"trades":0,"closed_trades":0,"open_trades":0,"win_rate":0.0,"profit_pct":0.0,"max_drawdown_pct":0.0,"profit_factor":0.0,"avg_trade_pct":0.0,"expectancy_pct":0.0,"avg_win_pct":0.0,"avg_loss_pct":0.0,"sharpe":0.0,"sortino":0.0,"calmar":0.0,"signals":0,"entries":0,"skipped_no_target":0,"skipped_bad_stop":0,"bars_used":0,"tp1_hit_rate":0.0,"tp2_hit_rate":0.0,"tp3_hit_rate":0.0,"tp4_hit_rate":0.0,"monte_carlo_5pct":0.0,"monte_carlo_median":0.0,"monte_carlo_95pct":0.0,"walk_forward_score":0.0,"oos_return_pct":0.0}
    if df is None or df.empty: return empty
    try: bt=add_indicators(df.copy())
    except Exception: return empty
    if bt.empty: return empty
    comm=DEFAULT_COMMISSION_PCT if commission_pct is None else float(commission_pct)
    slip=DEFAULT_SLIPPAGE_PCT if slippage_pct is None else float(slippage_pct)
    warmup=max(BACKTEST_WARMUP,220); test_bars=max(50,int(max_bars)); start=max(warmup,len(bt)-test_bars-1); end=len(bt)-1
    trades,equity,dd,signals,entries,snt,sbs=_simulate_bt_window(bt,start,end,comm,slip)
    out=_summarize_bt(trades,equity,dd,signals,entries,snt,sbs,max(1,end-start),bt); out["bars_used"]=max(0,end-start)
    # Monte Carlo on trade returns: distribution of terminal equity.
    if trades and monte_carlo_runs:
        rng=np.random.default_rng(42); r=np.array([t["return"] for t in trades],float); sims=[]
        for _ in range(int(monte_carlo_runs)):
            # block bootstrap preserves some serial dependence in winning/losing clusters
            block=max(1,min(5,len(r)//3 or 1)); sample=[]
            while len(sample)<len(r):
                j=int(rng.integers(0,max(1,len(r)-block+1))); sample.extend(r[j:j+block])
            sample=np.array(sample[:len(r)],float); sims.append(float(np.prod(np.maximum(0.0001,1+sample))-1)*100)
        out["monte_carlo_5pct"]=float(np.percentile(sims,5)); out["monte_carlo_median"]=float(np.percentile(sims,50)); out["monte_carlo_95pct"]=float(np.percentile(sims,95))
    # Walk-forward / OOS: three chronological test windows, fixed strategy (no future fitting).
    n=len(bt); window=max(50,min(test_bars,n//5)); oos=[]
    for k in range(3):
        e=n-k*window; st_idx=max(warmup,e-window)
        if e-st_idx<50: continue
        tr,eq,dd2,sg,en,sn,sb=_simulate_bt_window(bt,st_idx,e,comm,slip)
        if tr: oos.append((eq-1)*100)
    if oos:
        out["oos_return_pct"]=float(np.mean(oos)); out["walk_forward_score"]=float(sum(x>0 for x in oos)/len(oos)*100)
    return out


def estimate_historical_probabilities(bt):
    return tuple(bt.get(k,0.0)/100.0 for k in ["tp1_hit_rate","tp2_hit_rate","tp3_hit_rate","tp4_hit_rate"])


def _clip_score(value, low, high):
    """تحويل قيمة رقمية إلى درجة 0-100 بشكل محافظ."""
    try:
        x = float(value)
    except Exception:
        return np.nan
    if not np.isfinite(x):
        return np.nan
    if high <= low:
        return 50.0
    return float(np.clip((x - low) / (high - low) * 100.0, 0.0, 100.0))


def calculate_trading_rank(row, backtest_enabled=True):
    """Professional hybrid ranking: current setup + historical OOS + risk + liquidity."""
    parts=[]
    def add(v,w):
        try:
            v=float(v)
            if np.isfinite(v): parts.append((float(np.clip(v,0,100)),float(w)))
        except Exception: pass
    add(row.get("التقييم",np.nan),20)
    add(row.get("جودة الأهداف",np.nan),5)
    add(_clip_score(row.get("R/R الهدف الأول",np.nan),0.8,4.0),5)
    add(row.get("Absolute Liquidity Score",row.get("قوة السيولة",np.nan)),10)
    # Penalize incomplete data explicitly rather than silently excluding the stock.
    completeness_penalty=float(row.get("Data Completeness Penalty",0) or 0)
    add(max(0,100-completeness_penalty*4),5)
    trades=row.get("Backtest Trades",0)
    try: trades=float(trades)
    except Exception: trades=0
    if backtest_enabled and trades>=10:
        add(_clip_score(row.get("قيمة متوقعة %",np.nan),-2,4),20)
        add(row.get("احتمال TP1 التاريخي %",np.nan),15)
        add(row.get("Walk Forward Score %",np.nan),12)
        add(_clip_score(row.get("OOS Return %",np.nan),-20,40),5)
        add(row.get("Backtest Stability Score",np.nan),10)
        evidence=float(row.get("Statistical Evidence Weight",np.nan))
        if np.isfinite(evidence): add(evidence,8)
        ddq=_clip_score(row.get("Backtest Max DD %",np.nan),0,35)
        if np.isfinite(ddq): add(100-ddq,10)
    elif backtest_enabled:
        # no historical evidence => penalize confidence rather than fabricate weights
        add(row.get("السيولة Ratio",np.nan),5)
    if not parts: return 0.0
    return round(sum(v*w for v,w in parts)/sum(w for v,w in parts),2)


def apply_trading_ranking(df, backtest_enabled=True):
    """إضافة الترتيب التداولي وفرز الأسهم من الأقوى للأضعف."""
    out = df.copy()
    if out.empty:
        return out
    out["الترتيب التداولي"] = out.apply(
        lambda r: calculate_trading_rank(r, backtest_enabled), axis=1
    )
    out = out.sort_values(
        ["الترتيب التداولي", "التقييم"],
        ascending=[False, False]
    ).reset_index(drop=True)
    out["الترتيب"] = np.arange(1, len(out) + 1)
    return out


def build_market_return_proxy(data, symbols):
    returns=[]
    for symbol in symbols:
        try:
            d=extract_symbol_data(data,symbol)
            if not d.empty and len(d)>=RS_LOOKBACK+1:
                r=d["Close"].pct_change(RS_LOOKBACK).iloc[-1]
                if np.isfinite(r): returns.append(float(r))
        except Exception: pass
    return float(np.median(returns)) if returns else 0.0


# =========================================================
# ⚡ معالجة سهم واحد
# =========================================================

def process(
    symbol,
    daily,
    weekly,
    monthly,
    capital,
    risk_percent,
    market_return_20=0.0,
    run_backtest=False,
    backtest_bars=300,
    max_position_pct=DEFAULT_MAX_POSITION_PCT
):

    clean_symbol = symbol.replace(
        ".CA",
        ""
    )

    try:

        df_d = extract_symbol_data(
            daily,
            symbol
        )

        df_w = extract_symbol_data(
            weekly,
            symbol
        )

        df_m = extract_symbol_data(
            monthly,
            symbol
        )

        raw_d = calculate_raw_data_audit(extract_symbol_data_raw(daily, symbol), "1d")
        raw_w = calculate_raw_data_audit(extract_symbol_data_raw(weekly, symbol), "1wk")
        raw_m = calculate_raw_data_audit(extract_symbol_data_raw(monthly, symbol), "1mo")

        if df_d.empty:

            return {
                "السهم": clean_symbol,
                "الحالة": "❌ لا توجد بيانات يومية"
            }

        if len(df_d) < MIN_DAILY_ROWS:

            return {
                "السهم": clean_symbol,
                "الحالة": "❌ بيانات يومية غير كافية"
            }

        # Data completeness penalty: do not discard a valid daily stock solely because W/M is weak.
        completeness_penalty = 0.0
        if df_w.empty or len(df_w) < MIN_WEEKLY_ROWS:
            df_w = df_d.resample("W-FRI").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()
            completeness_penalty += 8.0
        if df_m.empty or len(df_m) < MIN_MONTHLY_ROWS:
            df_m = df_d.resample("ME").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()
            completeness_penalty += 10.0
        if len(df_w) < MIN_WEEKLY_ROWS: completeness_penalty += 4.0
        if len(df_m) < MIN_MONTHLY_ROWS: completeness_penalty += 5.0

        df_d["market_return_20"] = market_return_20
        result = analyze(
            df_d,
            df_w,
            df_m,
            capital,
            risk_percent,
            max_position_pct
        )
        result["Raw Daily Quality %"] = raw_d["raw_quality"]
        result["Raw Weekly Quality %"] = raw_w["raw_quality"]
        result["Raw Monthly Quality %"] = raw_m["raw_quality"]
        result["Data Completeness Penalty"] = round(completeness_penalty,2)
        result["التقييم"] = round(max(0.0, float(result.get("التقييم",0.0)) - completeness_penalty),2)
        if run_backtest:
            horizons, stability_score = run_multi_horizon_backtest(df_d, commission_pct, slippage_pct, monte_carlo_runs)
            bt = horizons.get(backtest_bars) or horizons.get(500) or run_real_backtest(df_d, backtest_bars, commission_pct, slippage_pct, monte_carlo_runs)
            result["Backtest Stability Score"] = stability_score
            result["Statistical Evidence Weight"] = statistical_evidence_weight(bt.get("trades",0))
            result["Daily Equity Curve"] = "مُفعّل (Closed-Equity Daily)"
            result["Backtest Horizons"] = ", ".join(f"{h}:{horizons[h].get('profit_pct',0):.1f}%" for h in horizons)
            # Use stability/evidence as ranking inputs, not cosmetic labels.
            result["Backtest Trades"] = bt["trades"]
            result["Backtest Win Rate %"] = round(bt["win_rate"], 1)
            result["Backtest Return %"] = round(bt["profit_pct"], 2)
            result["Backtest Max DD %"] = round(bt["max_drawdown_pct"], 2)
            result["Backtest Profit Factor"] = round(bt["profit_factor"], 2)
            result["Backtest Signals"] = int(bt.get("signals", 0))
            result["Backtest Valid Entries"] = int(bt.get("entries", 0))
            result["Backtest No Target"] = int(bt.get("skipped_no_target", 0))
            result["Backtest Bad Stop"] = int(bt.get("skipped_bad_stop", 0))
            result["Backtest Invalid Indicators"] = 0
            result["Backtest Expectancy %"] = round(bt.get("expectancy_pct",0.0),3)
            result["Backtest Avg Win %"] = round(bt.get("avg_win_pct",0.0),2)
            result["Backtest Avg Loss %"] = round(bt.get("avg_loss_pct",0.0),2)
            result["Backtest Sharpe"] = round(bt.get("sharpe",0.0),2)
            result["Backtest Sortino"] = round(bt.get("sortino",0.0),2)
            result["Backtest Calmar"] = round(bt.get("calmar",0.0),2)
            result["Backtest TP1 Probability %"] = round(bt.get("tp1_hit_rate",0.0),1)
            result["Backtest TP2 Probability %"] = round(bt.get("tp2_hit_rate",0.0),1)
            result["Backtest TP3 Probability %"] = round(bt.get("tp3_hit_rate",0.0),1)
            result["Backtest TP4 Probability %"] = round(bt.get("tp4_hit_rate",0.0),1)
            result["Monte Carlo 5% Return %"] = round(bt.get("monte_carlo_5pct",0.0),2)
            result["Monte Carlo Median Return %"] = round(bt.get("monte_carlo_median",0.0),2)
            result["Monte Carlo 95% Return %"] = round(bt.get("monte_carlo_95pct",0.0),2)
            result["Walk Forward Score %"] = round(bt.get("walk_forward_score",0.0),1)
            result["OOS Return %"] = round(bt.get("oos_return_pct",0.0),2)
            # V9: historical probabilities replace synthetic confidence for trading decisions.
            result["احتمال TP1 التاريخي %"] = round(bt.get("tp1_hit_rate",0.0),1)
            result["احتمال TP2 التاريخي %"] = round(bt.get("tp2_hit_rate",0.0),1)
            result["احتمال TP3 التاريخي %"] = round(bt.get("tp3_hit_rate",0.0),1)
            result["احتمال TP4 التاريخي %"] = round(bt.get("tp4_hit_rate",0.0),1)
            result["قيمة متوقعة %"] = round(bt.get("expectancy_pct",0.0),3)
            # Historical evidence overrides synthetic confidence when sample is sufficient.
            if bt.get("trades",0) >= 10:
                hist_conf = np.mean([bt.get("tp1_hit_rate",0), bt.get("tp2_hit_rate",0), bt.get("tp3_hit_rate",0), bt.get("tp4_hit_rate",0)])
                result["ثقة الهدف الأول %"] = round(bt.get("tp1_hit_rate",0),1)
                result["ثقة الهدف الثاني %"] = round(bt.get("tp2_hit_rate",0),1)
                result["ثقة الهدف الثالث %"] = round(bt.get("tp3_hit_rate",0),1)
                result["ثقة الهدف الرابع %"] = round(bt.get("tp4_hit_rate",0),1)
                result["ثقة الإشارة التاريخية %"] = round(hist_conf,1)
            else:
                result["ثقة الإشارة التاريخية %"] = np.nan
            result["حالة التحقق"] = ("🟢 قوي" if bt.get("walk_forward_score",0)>=66 and bt.get("expectancy_pct",0)>0 and bt.get("profit_factor",0)>1.1 else "🟡 محايد" if bt.get("trades",0)>=10 else "⚪ بيانات غير كافية")
        else:
            result["Backtest Trades"] = 0
            result["Backtest Win Rate %"] = np.nan
            result["Backtest Return %"] = np.nan
            result["Backtest Max DD %"] = np.nan
            result["Backtest Profit Factor"] = np.nan
            result["Backtest Signals"] = np.nan
            result["Backtest Valid Entries"] = np.nan
            result["Backtest No Target"] = np.nan
            result["Backtest Bad Stop"] = np.nan
            result["Backtest Invalid Indicators"] = np.nan
            for _k in ["Backtest Expectancy %","Backtest Avg Win %","Backtest Avg Loss %","Backtest Sharpe","Backtest Sortino","Backtest Calmar","Backtest TP1 Probability %","Backtest TP2 Probability %","Backtest TP3 Probability %","Backtest TP4 Probability %","Monte Carlo 5% Return %","Monte Carlo Median Return %","Monte Carlo 95% Return %","Walk Forward Score %","OOS Return %","احتمال TP1 التاريخي %","احتمال TP2 التاريخي %","احتمال TP3 التاريخي %","احتمال TP4 التاريخي %","قيمة متوقعة %"]: result[_k]=np.nan
            result["حالة التحقق"]="⚪ Backtest غير مفعل"
            result["Backtest Stability Score"] = np.nan
            result["Statistical Evidence Weight"] = np.nan
            result["Daily Equity Curve"] = "غير مفعّل"
            result["Backtest Horizons"] = "غير مفعل"

        result["السهم"] = clean_symbol
        result["الحالة"] = "✅ تم التحليل"

        return result

    except Exception as e:

        return {
            "السهم": clean_symbol,
            "الحالة": f"❌ {str(e)[:120]}"
        }


# =========================================================
# 🚀 تشغيل الفحص
# =========================================================

if st.button(
    "🚀 بدء فحص الأسهم",
    use_container_width=True
):

    st.info(
        f"📡 جاري فحص {TOTAL_STOCKS} سهم..."
    )

    progress = st.progress(
        0
    )

    status_text = st.empty()

    # =====================================================
    # Daily
    # =====================================================

    with st.spinner(
        "📥 جاري تحميل البيانات اليومية..."
    ):

        daily = load_data(
            EGX100,
            period_daily,
            "1d"
        )

    progress.progress(
        20
    )

    # =====================================================
    # Weekly
    # =====================================================

    status_text.info(
        "📥 جاري تحميل البيانات الأسبوعية..."
    )

    weekly = load_data(
        EGX100,
        period_weekly,
        "1wk"
    )

    progress.progress(
        40
    )

    # =====================================================
    # Monthly
    # =====================================================

    status_text.info(
        "📥 جاري تحميل البيانات الشهرية..."
    )

    monthly = load_data(
        EGX100,
        period_monthly,
        "1mo"
    )

    progress.progress(
        50
    )

    # =====================================================
    # Data Engine Stats
    # =====================================================

    status_text.info(
        "🔍 جاري فحص جودة البيانات والتغطية..."
    )

    data_engine_stats = []

    for symbol in EGX100:

        df_d_check = extract_symbol_data(
            daily,
            symbol
        )

        df_w_check = extract_symbol_data(
            weekly,
            symbol
        )

        df_m_check = extract_symbol_data(
            monthly,
            symbol
        )

        qd = calculate_data_quality(
            df_d_check
        )

        qw = calculate_data_quality(
            df_w_check
        )

        qm = calculate_data_quality(
            df_m_check
        )
        rawd = calculate_raw_data_audit(extract_symbol_data_raw(daily, symbol), "1d")
        raww = calculate_raw_data_audit(extract_symbol_data_raw(weekly, symbol), "1wk")
        rawm = calculate_raw_data_audit(extract_symbol_data_raw(monthly, symbol), "1mo")

        quality = (
            qd["quality"] * 0.50 +
            qw["quality"] * 0.30 +
            qm["quality"] * 0.20
        )

        data_engine_stats.append({

            "symbol": symbol,

            "daily_rows":
                qd.get("rows", 0),

            "weekly_rows":
                qw.get("rows", 0),

            "monthly_rows":
                qm.get("rows", 0),

            "daily_quality":
                qd["quality"],

            "weekly_quality":
                qw["quality"],

            "monthly_quality":
                qm["quality"],
            "raw_daily_quality": rawd["raw_quality"],
            "raw_weekly_quality": raww["raw_quality"],
            "raw_monthly_quality": rawm["raw_quality"],

            "data_quality":
                round(
                    quality,
                    2
                ),

            "daily_ema200":
                (
                    "✅"
                    if qd.get("rows", 0) >= 200
                    else "⚠️"
                ),

            "weekly_ema200":
                (
                    "✅"
                    if qw.get("rows", 0) >= 200
                    else "⚠️"
                ),

            "monthly_ema200":
                (
                    "✅"
                    if qm.get("rows", 0) >= 200
                    else "⚠️"
                )
        })

    # =====================================================
    # Relative Strength market proxy
    # =====================================================
    market_return_20 = build_market_return_proxy(daily, EGX100)

    # =====================================================
    # التحليل
    # =====================================================

    results = []

    status_text.info(
        f"🧠 جاري تحليل {TOTAL_STOCKS} سهم بالتوازي..."
    )

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:

        futures = {

            executor.submit(
                process,
                symbol,
                daily,
                weekly,
                monthly,
                capital,
                risk_percent,
                market_return_20,
                run_backtest,
                backtest_bars,
                max_position_pct
            ): symbol

            for symbol in EGX100
        }

        completed = 0

        for future in as_completed(
            futures
        ):

            try:

                result = future.result()

                if result:
                    results.append(
                        result
                    )

            except Exception as e:

                symbol = futures[
                    future
                ]

                results.append({

                    "السهم":
                        symbol.replace(
                            ".CA",
                            ""
                        ),

                    "الحالة":
                        f"❌ {str(e)[:120]}"
                })

            completed += 1

            progress.progress(
                50 +
                int(
                    completed /
                    TOTAL_STOCKS *
                    50
                )
            )

    progress.progress(
        100
    )

    status_text.success(
        "✅ انتهى الفحص بالكامل"
    )

    # =====================================================
    # النتائج
    # =====================================================

    if not results:

        st.error(
            "❌ لم يتم الحصول على أي نتائج."
        )

        st.stop()

    df_all = pd.DataFrame(
        results
    )

    # =====================================================
    # الأسهم الناجحة
    # =====================================================

    df_ok = df_all[
        df_all["الحالة"] ==
        "✅ تم التحليل"
    ].copy()

    if not df_ok.empty and "عدد الأهداف الهيكلية" in df_ok.columns:
        no_targets = int((df_ok["عدد الأهداف الهيكلية"] < 1).sum())
        if no_targets:
            st.warning(f"⚠️ {no_targets} سهم بدون مستوى Target هيكلي موثوق؛ النظام لا يخترع أهداف ATR بديلة.")

    # =====================================================
    # التغطية
    # =====================================================

    total = TOTAL_STOCKS

    analyzed = int(
        (
            df_all["الحالة"] ==
            "✅ تم التحليل"
        ).sum()
    )

    failed = total - analyzed

    coverage = (
        analyzed /
        total *
        100
        if total > 0
        else 0
    )

    # =====================================================
    # Data Quality
    # =====================================================

    stats_df = pd.DataFrame(
        data_engine_stats
    )

    if not stats_df.empty:

        avg_quality = float(
            stats_df[
                "data_quality"
            ].mean()
        )

        daily_coverage = float(
            (
                stats_df[
                    "daily_rows"
                ] >= MIN_DAILY_ROWS
            ).mean() * 100
        )

        weekly_coverage = float(
            (
                stats_df[
                    "weekly_rows"
                ] >= MIN_WEEKLY_ROWS
            ).mean() * 100
        )

        monthly_coverage = float(
            (
                stats_df[
                    "monthly_rows"
                ] >= MIN_MONTHLY_ROWS
            ).mean() * 100
        )

        daily_ema200_coverage = float(
            (
                stats_df[
                    "daily_rows"
                ] >= 200
            ).mean() * 100
        )

        weekly_ema200_coverage = float(
            (
                stats_df[
                    "weekly_rows"
                ] >= 200
            ).mean() * 100
        )

        monthly_ema200_coverage = float(
            (
                stats_df[
                    "monthly_rows"
                ] >= 200
            ).mean() * 100
        )

    else:

        avg_quality = 0
        daily_coverage = 0
        weekly_coverage = 0
        monthly_coverage = 0
        daily_ema200_coverage = 0
        weekly_ema200_coverage = 0
        monthly_ema200_coverage = 0

    # =====================================================
    # ملخص الفحص
    # =====================================================

    st.subheader(
        "📊 ملخص الفحص"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "📊 الأسهم المطلوبة",
        total
    )

    c2.metric(
        "✅ تم تحليلها",
        analyzed
    )

    c3.metric(
        "❌ فشل",
        failed
    )

    c4.metric(
        "📡 نسبة التغطية",
        f"{coverage:.1f}%"
    )

    # =====================================================
    # جودة البيانات
    # =====================================================

    st.subheader(
        "📡 جودة البيانات"
    )

    q1, q2, q3, q4 = st.columns(4)

    q1.metric(
        "⭐ جودة البيانات",
        f"{avg_quality:.1f}%"
    )

    q2.metric(
        "📅 تغطية Daily",
        f"{daily_coverage:.1f}%"
    )

    q3.metric(
        "📆 تغطية Weekly",
        f"{weekly_coverage:.1f}%"
    )

    q4.metric(
        "🗓️ تغطية Monthly",
        f"{monthly_coverage:.1f}%"
    )

    st.subheader(
        "📐 تغطية EMA200 الحقيقي"
    )

    e1, e2, e3 = st.columns(3)

    e1.metric(
        "Daily EMA200",
        f"{daily_ema200_coverage:.1f}%"
    )

    e2.metric(
        "Weekly EMA200",
        f"{weekly_ema200_coverage:.1f}%"
    )

    e3.metric(
        "Monthly EMA200",
        f"{monthly_ema200_coverage:.1f}%"
    )

    # =====================================================
    # الأسهم الناجحة
    # =====================================================

    if not df_ok.empty:

        # ترتيب تداولي: لا يعتمد على Score الفني وحده، بل يدمج جودة الإشارة
        # مع نتائج الباك تست الواقعية عندما تكون متاحة.
        df_ok = apply_trading_ranking(
            df_ok,
            backtest_enabled=run_backtest
        )

        # =================================================
        # أفضل الأسهم
        # =================================================

        st.subheader(
            f"🏆 أفضل {min(top_n, len(df_ok))} سهم"
        )

        top_df = df_ok.head(
            top_n
        ).copy()

        preferred_cols = [

            "الترتيب",
            "السهم",
            "الترتيب التداولي",
            "التقييم",
            "الإشارة",
            "الاتجاه",
            "قائمة التأكيد",
            "نوع الدخول",
            "سبب الدخول",
            "سعر الدخول",
            "وقف الخسارة",

            "الهدف الأول",
            "ربح الهدف الأول %",
            "R/R الهدف الأول",
            "سبب الهدف الأول",

            "الهدف الثاني",
            "ربح الهدف الثاني %",
            "R/R الهدف الثاني",
            "سبب الهدف الثاني",

            "الهدف الثالث",
            "ربح الهدف الثالث %",
            "R/R الهدف الثالث",
            "سبب الهدف الثالث",

            "الهدف الرابع",
            "ربح الهدف الرابع %",
            "R/R الهدف الرابع",
            "سبب الهدف الرابع",

            "جودة الأهداف",
            "EMA200",

            "ثقة الهدف الأول %",
            "ثقة الهدف الثاني %",
            "ثقة الهدف الثالث %",
            "ثقة الهدف الرابع %",

            "مؤشر RSI",
            "قوة الاتجاه ADX",
            "التذبذب ATR %",
            "السيولة Ratio",
            "Relative Strength %",
            "عدد الأهداف الهيكلية",
            "Backtest Trades",
            "Backtest Win Rate %",
            "Backtest Return %",
            "Backtest Max DD %",
            "Backtest Profit Factor",
            "Backtest Expectancy %",
            "Backtest Avg Win %",
            "Backtest Avg Loss %",
            "Backtest Sharpe",
            "Backtest Sortino",
            "Backtest Calmar",
            "احتمال TP1 التاريخي %",
            "احتمال TP2 التاريخي %",
            "احتمال TP3 التاريخي %",
            "احتمال TP4 التاريخي %",
            "Walk Forward Score %",
            "OOS Return %",
            "Monte Carlo 5% Return %",
            "Monte Carlo Median Return %",
            "Monte Carlo 95% Return %",
            "حالة التحقق",
            "المدة المتوقعة"
        ]

        existing_cols = [
            c for c in preferred_cols
            if c in top_df.columns
        ]

        top_df = top_df[
            existing_cols
        ]

        top_display = top_df.rename(columns={
            "Backtest Trades": "عدد صفقات الباك تست",
            "Backtest Win Rate %": "نسبة الصفقات الرابحة %",
            "Backtest Return %": "عائد الباك تست %",
            "Backtest Max DD %": "أقصى تراجع في الباك تست %",
            "Backtest Profit Factor": "معامل الربح Profit Factor",
            "Backtest Expectancy %": "القيمة المتوقعة لكل صفقة %",
            "Backtest Avg Win %": "متوسط الربح %",
            "Backtest Avg Loss %": "متوسط الخسارة %",
            "Backtest Sharpe": "Sharpe معامل شارب",
            "Backtest Sortino": "Sortino معامل سورتينو",
            "Backtest Calmar": "Calmar معامل كالمار",
            "احتمال TP1 التاريخي %": "احتمال تحقيق الهدف الأول تاريخيًا %",
            "احتمال TP2 التاريخي %": "احتمال تحقيق الهدف الثاني تاريخيًا %",
            "احتمال TP3 التاريخي %": "احتمال تحقيق الهدف الثالث تاريخيًا %",
            "احتمال TP4 التاريخي %": "احتمال تحقيق الهدف الرابع تاريخيًا %",
            "Walk Forward Score %": "درجة Walk-Forward %",
            "OOS Return %": "عائد الاختبار خارج العينة OOS %",
            "Monte Carlo 5% Return %": "أدنى 5% Monte Carlo %",
            "Monte Carlo Median Return %": "الوسيط Monte Carlo %",
            "Monte Carlo 95% Return %": "أعلى 5% Monte Carlo %"
        })
        st.caption(
            "📌 ترتيب الأسهم هنا هو الترتيب التداولي النهائي، وليس التقييم الفني فقط. "
            "عند تفعيل الباك تست يدخل احتمال تحقق TP1 التاريخي والقيمة المتوقعة وR/R وجودة الأهداف وWalk-Forward وOOS ومخاطر التراجع ضمن الترتيب. "
            "لو الباك تست غير كافٍ، النظام يقلل وزنه ولا يخترع نتائج تاريخية."
        )

        st.dataframe(
            top_display,
            use_container_width=True,
            hide_index=True
        )

        # =================================================
        # الأسهم القوية
        # =================================================

        strong = df_ok[
            df_ok["التقييم"] > 70
        ].copy()

        st.subheader(
            f"🔥 الأسهم القوية: {len(strong)}"
        )

        if not strong.empty:

            strong = strong[
                existing_cols
            ]

            st.dataframe(
                strong,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.warning(
                "⚠️ لا توجد أسهم قوية حالياً حسب شروط النظام."
            )

        # =================================================
        # جميع الأسهم
        # =================================================

        st.subheader(
            "📋 جميع الأسهم التي تم تحليلها"
        )

        st.dataframe(
            df_ok[
                existing_cols
            ],
            use_container_width=True,
            hide_index=True
        )

        # =================================================
        # CSV
        # =================================================

        csv_ok = (
            df_ok[
                existing_cols
            ]
            .to_csv(
                index=False
            )
            .encode(
                "utf-8-sig"
            )
        )

        st.download_button(
            "⬇️ تحميل نتائج الأسهم المحللة",
            csv_ok,
            "EGX_AI_PRO_MAX_V8.2_RESULTS_AR.csv",
            "text/csv",
            use_container_width=True
        )

        # =================================================
        # معلومات المحرك
        # =================================================

        with st.expander(
            "🔬 معلومات المحرك المتقدمة"
        ):

            internal_cols = [

                "السهم",

                "_entry_type",
                "_trend_alignment",
                "_data_quality",

                "_ema200_daily",
                "_ema200_weekly",
                "_ema200_monthly",

                "_risk_pct",

                "_rr1",
                "_rr2",
                "_rr3",
                "_rr4",

                "_target_quality",

                "_position_size",
                "_position_value",

                "_pullback_quality",
                "_volume_ratio",
                "_liquidity_ratio",
                "_relative_strength",
                "_structural_target_count",

                "_obv",
                "_obv_ma",

                "_stoch_rsi_k",
                "_stoch_rsi_d",

                "_vwap"
            ]

            available_internal = [
                c for c in internal_cols
                if c in df_ok.columns
            ]

            internal_df = (
                df_ok[
                    available_internal
                ]
                .rename(
                    columns={

                        "_entry_type":
                            "نوع الدخول",

                        "_trend_alignment":
                            "Trend Alignment",

                        "_data_quality":
                            "جودة البيانات",

                        "_ema200_daily":
                            "Daily EMA200",

                        "_ema200_weekly":
                            "Weekly EMA200",

                        "_ema200_monthly":
                            "Monthly EMA200",

                        "_risk_pct":
                            "المخاطرة %",

                        "_rr1":
                            "R/R TP1",

                        "_rr2":
                            "R/R TP2",

                        "_rr3":
                            "R/R TP3",

                        "_rr4":
                            "R/R TP4",

                        "_target_quality":
                            "جودة الأهداف",

                        "_position_size":
                            "حجم المركز",

                        "_position_value":
                            "قيمة المركز",

                        "_pullback_quality":
                            "Pullback Quality",

                        "_volume_ratio":
                            "Volume Ratio",
                        "_liquidity_ratio":
                            "Liquidity Ratio",
                        "_relative_strength":
                            "Relative Strength %",
                        "_structural_target_count":
                            "عدد الأهداف الهيكلية",

                        "_obv":
                            "OBV",

                        "_obv_ma":
                            "OBV MA",

                        "_stoch_rsi_k":
                            "Stoch RSI K",

                        "_stoch_rsi_d":
                            "Stoch RSI D",

                        "_vwap":
                            "VWAP"
                    }
                )
            )

            st.dataframe(
                internal_df,
                use_container_width=True,
                hide_index=True
            )

        # =================================================
        # تفاصيل الأهداف
        # =================================================

        with st.expander(
            "🎯 تفاصيل Target Engine"
        ):

            target_cols = [

                "السهم",

                "سعر الدخول",

                "الهدف الأول",
                "نوع الهدف الأول",
                "سبب الهدف الأول",
                "ربح الهدف الأول %",
                "R/R الهدف الأول",

                "الهدف الثاني",
                "نوع الهدف الثاني",
                "سبب الهدف الثاني",
                "ربح الهدف الثاني %",
                "R/R الهدف الثاني",

                "الهدف الثالث",
                "نوع الهدف الثالث",
                "سبب الهدف الثالث",
                "ربح الهدف الثالث %",
                "R/R الهدف الثالث",

                "الهدف الرابع",
                "نوع الهدف الرابع",
                "سبب الهدف الرابع",
                "ربح الهدف الرابع %",
                "R/R الهدف الرابع",

                "جودة الأهداف"
            ]

            available_target_cols = [
                c for c in target_cols
                if c in df_ok.columns
            ]

            st.dataframe(
                df_ok[
                    available_target_cols
                ],
                use_container_width=True,
                hide_index=True
            )

        # =================================================
        # تفاصيل Entry
        # =================================================

        with st.expander(
            "🎯 تفاصيل Entry Engine"
        ):

            entry_cols = [

                "السهم",
                "التقييم",
                "الإشارة",
                "الاتجاه",
                "نوع الدخول",
                "سبب الدخول",
                "سعر الدخول",
                "وقف الخسارة",
                "جودة الأهداف",
                "R/R الهدف الأول",
                "مؤشر RSI",
                "قوة الاتجاه ADX",
                "التذبذب ATR %",
                "EMA200",
                "احتمال TP1 التاريخي %",
                "قيمة متوقعة %",
                "حالة التحقق"
            ]

            available_entry_cols = [
                c for c in entry_cols
                if c in df_ok.columns
            ]

            st.dataframe(
                df_ok[
                    available_entry_cols
                ],
                use_container_width=True,
                hide_index=True
            )

        # =================================================
        # Data Quality Details
        # =================================================

        with st.expander(
            "📡 تفاصيل جودة البيانات لكل سهم"
        ):

            quality_display = (
                stats_df
                .rename(
                    columns={

                        "symbol":
                            "السهم",

                        "daily_rows":
                            "شموع Daily",

                        "weekly_rows":
                            "شموع Weekly",

                        "monthly_rows":
                            "شموع Monthly",

                        "daily_quality":
                            "جودة Daily %",

                        "weekly_quality":
                            "جودة Weekly %",

                        "monthly_quality":
                            "جودة Monthly %",

                        "data_quality":
                            "جودة البيانات %",

                        "daily_ema200":
                            "Daily EMA200",

                        "weekly_ema200":
                            "Weekly EMA200",

                        "monthly_ema200":
                            "Monthly EMA200"
                    }
                )
            )

            st.dataframe(
                quality_display,
                use_container_width=True,
                hide_index=True
            )

    # =====================================================
    # الأسهم الفاشلة
    # =====================================================

    df_failed = df_all[
        df_all["الحالة"] !=
        "✅ تم التحليل"
    ].copy()

    if not df_failed.empty:

        st.subheader(
            f"⚠️ الأسهم التي فشل تحميل/تحليل بياناتها: {len(df_failed)}"
        )

        st.dataframe(
            df_failed[
                [
                    "السهم",
                    "الحالة"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        csv_failed = (
            df_failed[
                [
                    "السهم",
                    "الحالة"
                ]
            ]
            .to_csv(
                index=False
            )
            .encode(
                "utf-8-sig"
            )
        )

        st.download_button(
            "⬇️ تحميل قائمة الأخطاء",
            csv_failed,
            "EGX_AI_PRO_MAX_V8_2_ERRORS_AR.csv",
            "text/csv",
            use_container_width=True
        )

    # =====================================================
    # الحالة النهائية
    # =====================================================

    st.success(
        f"""
🔥 الفحص اكتمل بنجاح

📊 إجمالي الأسهم: {total}

✅ تم تحليل: {analyzed}

❌ فشل: {failed}

📡 نسبة تغطية البيانات: {coverage:.1f}%

⭐ متوسط جودة البيانات: {avg_quality:.1f}%

📅 Daily Coverage: {daily_coverage:.1f}%

📆 Weekly Coverage: {weekly_coverage:.1f}%

🗓️ Monthly Coverage: {monthly_coverage:.1f}%

📐 Daily EMA200 الحقيقي: {daily_ema200_coverage:.1f}%

📐 Weekly EMA200 الحقيقي: {weekly_ema200_coverage:.1f}%

📐 Monthly EMA200 الحقيقي: {monthly_ema200_coverage:.1f}%
"""
    )
