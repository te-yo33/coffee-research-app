import streamlit as st
import pandas as pd
import html
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials


# =========================
# 基本設定
# =========================
HEADERS = [
    "実験No", "日付",
    "豆の種類", "焙煎度", "豆量g", "湯量g", "湯温℃",
    "挽き目", "ドリッパー", "フィルター", "煎れ方", "煎れ方メモ",
    "蒸らし有無", "蒸らし時間秒", "蒸らし湯量g",
    "焙煎後日数", "開封後日数",
    "抽出液量g", "抽出時間秒", "TDS%", "抽出収率%",
    "酸味", "甘味", "苦味", "雑味", "香り", "飲みやすさ", "コメント"
]

ROAST_NAMES = {
    1: "かなり浅煎り",
    2: "浅煎り",
    3: "浅煎り寄り",
    4: "中浅煎り",
    5: "中煎り寄り",
    6: "中深煎り",
    7: "深煎り",
    8: "かなり深煎り"
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


# =========================
# 共通関数
# =========================
def esc(value):
    return html.escape(str(value))


def safe_float(value, default=0.0):
    try:
        if value == "" or value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value == "" or value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def calc_yield(tds, beverage_weight, coffee_weight):
    if coffee_weight == 0:
        return 0
    return round(tds * beverage_weight / coffee_weight, 2)


def calc_yield_from_text(tds_text, beverage_text, coffee_text, current_value=""):
    tds = safe_float(tds_text, None)
    beverage = safe_float(beverage_text, None)
    coffee = safe_float(coffee_text, None)

    if tds is None or beverage is None or coffee is None or coffee == 0:
        return current_value

    return round(tds * beverage / coffee, 2)


def judge_tds(tds):
    if tds < 1.20:
        return "薄め", "TDSは目標より薄めです。次回は挽き目を少し細かくする、抽出時間を伸ばすなどが候補です。"
    elif tds > 1.30:
        return "濃いめ", "TDSは目標より濃いめです。次回は挽き目を少し粗くする、抽出時間を短くするなどが候補です。"
    else:
        return "良好", "TDSは1.25%前後でかなり良い範囲です。"


def judge_yield(extraction_yield):
    if extraction_yield < 18:
        return "抽出不足気味"
    elif extraction_yield <= 22:
        return "適正範囲"
    else:
        return "過抽出気味"


def rating_index(value):
    options = ["", "1", "2", "3", "4", "5"]
    value = str(value)
    if value in options:
        return options.index(value)
    return 0


def next_experiment_no(df):
    if df.empty:
        return 1

    exp_no = pd.to_numeric(df["実験No"], errors="coerce")

    if exp_no.dropna().empty:
        return 1

    return int(exp_no.max()) + 1


# =========================
# Google Sheets 接続
# =========================
@st.cache_resource
def get_worksheet():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        spreadsheet_id = st.secrets["SPREADSHEET_ID"]

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )

        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.sheet1

        return worksheet

    except Exception as e:
        st.error("Googleスプレッドシートへの接続に失敗しました。")
        st.write("Secretsの設定、スプレッドシートID、サービスアカウント共有を確認してください。")
        st.exception(e)
        st.stop()


def load_data():
    worksheet = get_worksheet()

    values = worksheet.get_all_values()

    if not values:
        worksheet.update(values=[HEADERS], range_name="A1")
        return pd.DataFrame(columns=HEADERS).astype("object")

    sheet_headers = values[0]
    rows = values[1:]

    if len(sheet_headers) == 0:
        worksheet.update(values=[HEADERS], range_name="A1")
        return pd.DataFrame(columns=HEADERS).astype("object")

    df = pd.DataFrame(rows, columns=sheet_headers)

    for col in HEADERS:
        if col not in df.columns:
            df[col] = ""

    df = df[HEADERS]
    df = df.fillna("").astype("object")

    return df


def save_data(df):
    worksheet = get_worksheet()

    df = df.copy()

    for col in HEADERS:
        if col not in df.columns:
            df[col] = ""

    df = df[HEADERS]
    df = df.fillna("").astype(str)

    rows = [HEADERS] + df.values.tolist()

    worksheet.clear()
    worksheet.update(values=rows, range_name="A1")


# =========================
# ページ設定
# =========================
st.set_page_config(
    page_title="浅煎りコーヒー研究ログ",
    page_icon="☕",
    layout="wide"
)


# =========================
# デザインCSS
# =========================
st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at top left, rgba(205, 133, 63, 0.30), transparent 32%),
        radial-gradient(circle at bottom right, rgba(111, 78, 55, 0.30), transparent 36%),
        linear-gradient(135deg, #160d08 0%, #2b1a12 45%, #0f0b08 100%);
    color: #f7efe7;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1220px;
}

html, body, [class*="css"] {
    font-family: "Yu Gothic", "Hiragino Sans", "Meiryo", sans-serif;
}

h1, h2, h3 {
    color: #fff3e6 !important;
    font-weight: 900 !important;
    letter-spacing: 0.02em;
}

h3 {
    color: #ffe3c2 !important;
}

.hero-card {
    padding: 30px 34px;
    border-radius: 30px;
    background:
        linear-gradient(135deg, rgba(255,255,255,0.16), rgba(255,255,255,0.045));
    border: 1px solid rgba(255,255,255,0.20);
    box-shadow: 0 20px 60px rgba(0,0,0,0.34);
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
}

.hero-label {
    font-size: 14px;
    letter-spacing: 0.22em;
    color: #f2b66d;
    font-weight: 900;
    margin-bottom: 8px;
}

.hero-title {
    font-size: 48px;
    font-weight: 950;
    color: #fff3e6;
    line-height: 1.15;
    text-shadow: 0 6px 25px rgba(0,0,0,0.35);
}

.hero-subtitle {
    font-size: 16px;
    color: #f3d8bd;
    margin-top: 10px;
}

.lab-card {
    background: rgba(255,255,255,0.085);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 22px;
    padding: 18px 20px;
    box-shadow: 0 14px 38px rgba(0,0,0,0.24);
    margin-bottom: 16px;
}

.lab-card-title {
    color: #ffd9ad;
    font-weight: 900;
    font-size: 17px;
    margin-bottom: 8px;
}

.lab-card-body {
    color: #f4dfc9;
    font-size: 14px;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 12px;
    background: rgba(255,255,255,0.07);
    padding: 10px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.12);
}

.stTabs [data-baseweb="tab"] {
    height: 50px;
    padding: 0 24px;
    border-radius: 15px;
    color: #f2d6b8;
    background: rgba(255,255,255,0.055);
    font-weight: 850;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #c47a3a, #ffc078) !important;
    color: #1c1009 !important;
    box-shadow: 0 8px 25px rgba(255, 192, 120, 0.22);
}

.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    background-color: rgba(255,255,255,0.96) !important;
    color: #24140c !important;
    border-radius: 13px !important;
    border: 1px solid rgba(255, 209, 160, 0.62) !important;
    box-shadow: 0 6px 18px rgba(0,0,0,0.10);
}

.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {
    border: 1px solid #ffc078 !important;
    box-shadow: 0 0 0 2px rgba(255, 192, 120, 0.18);
}

.stSelectbox div[data-baseweb="select"] > div {
    background-color: rgba(255,255,255,0.96) !important;
    color: #24140c !important;
    border-radius: 13px !important;
    border: 1px solid rgba(255, 209, 160, 0.62) !important;
}

label {
    color: #ffe7cc !important;
    font-weight: 750 !important;
}

.stButton > button {
    width: 100%;
    border: 2px solid rgba(255, 220, 170, 0.95) !important;
    border-radius: 16px !important;
    padding: 0.88rem 1.2rem !important;
    background: linear-gradient(135deg, #f4a259, #ffd08a) !important;
    color: #2a1406 !important;
    font-weight: 950 !important;
    font-size: 16px !important;
    opacity: 1 !important;
    box-shadow: 0 10px 28px rgba(216, 137, 67, 0.35) !important;
    transition: all 0.15s ease-in-out;
}

.stButton > button p {
    color: #2a1406 !important;
    font-weight: 950 !important;
    opacity: 1 !important;
}

.stButton > button:hover {
    transform: translateY(-2px);
    background: linear-gradient(135deg, #ffb36b, #ffe0a8) !important;
    box-shadow: 0 14px 34px rgba(255, 192, 120, 0.48) !important;
    color: #2a1406 !important;
    border-color: #fff1d5 !important;
}

.stButton > button:disabled,
.stButton > button[disabled] {
    background: linear-gradient(135deg, #b88455, #d7b17d) !important;
    color: #3a1f0d !important;
    border: 2px solid rgba(255, 225, 180, 0.75) !important;
    opacity: 0.95 !important;
    box-shadow: none !important;
}

.stButton > button:disabled p,
.stButton > button[disabled] p {
    color: #3a1f0d !important;
    font-weight: 950 !important;
    opacity: 1 !important;
}

.stAlert {
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.14);
    box-shadow: 0 10px 28px rgba(0,0,0,0.18);
}

[data-testid="stMetric"] {
    background: rgba(255,255,255,0.095);
    border: 1px solid rgba(255,255,255,0.15);
    padding: 18px;
    border-radius: 20px;
    box-shadow: 0 14px 38px rgba(0,0,0,0.25);
}

[data-testid="stMetricValue"] {
    color: #fff3e6 !important;
    font-weight: 950;
}

[data-testid="stMetricLabel"] {
    color: #ffd9ad !important;
}

[data-testid="stDataFrame"] {
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 16px 42px rgba(0,0,0,0.30);
    border: 1px solid rgba(255,255,255,0.10);
}

.stSlider {
    background: rgba(255,255,255,0.065);
    padding: 12px 15px;
    border-radius: 16px;
    margin-bottom: 10px;
    border: 1px solid rgba(255,255,255,0.08);
}

[data-testid="stCaptionContainer"] {
    color: #f1c79a !important;
}

hr {
    border-color: rgba(255,255,255,0.14);
}

.condition-box {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 20px;
    padding: 18px 20px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.20);
    margin-bottom: 14px;
}

.condition-title {
    font-size: 16px;
    font-weight: 900;
    color: #ffd9ad;
    margin-bottom: 10px;
}

.condition-text {
    color: #f5dec7;
    font-size: 14px;
    line-height: 1.8;
}

.danger-card {
    background: rgba(120, 30, 20, 0.28);
    border: 1px solid rgba(255, 120, 90, 0.34);
    border-radius: 20px;
    padding: 18px 20px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.20);
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# ヘッダー
# =========================
st.markdown("""
<div class="hero-card">
    <div class="hero-label">LIGHT ROAST COFFEE LAB</div>
    <div class="hero-title">☕ 浅煎りコーヒー研究ログ</div>
    <div class="hero-subtitle">
        TDS 1.25%前後を安定して出すための実験記録アプリ。
        条件登録、結果入力、データ分析までGoogleスプレッドシートに同期。
    </div>
</div>
""", unsafe_allow_html=True)


df = load_data()


# =========================
# 上部サマリー
# =========================
summary_df = df.copy()

if not summary_df.empty:
    summary_df["TDS%"] = pd.to_numeric(summary_df["TDS%"], errors="coerce")
    summary_df["抽出収率%"] = pd.to_numeric(summary_df["抽出収率%"], errors="coerce")

    total_count = len(summary_df)
    measured_count = summary_df["TDS%"].notna().sum()
    avg_tds = summary_df["TDS%"].mean()
    avg_yield = summary_df["抽出収率%"].mean()
else:
    total_count = 0
    measured_count = 0
    avg_tds = None
    avg_yield = None

col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    st.metric("実験数", total_count)

with col_b:
    st.metric("結果入力済み", measured_count)

with col_c:
    if avg_tds is None or pd.isna(avg_tds):
        st.metric("平均TDS", "-")
    else:
        st.metric("平均TDS", f"{avg_tds:.2f}%")

with col_d:
    if avg_yield is None or pd.isna(avg_yield):
        st.metric("平均抽出収率", "-")
    else:
        st.metric("平均抽出収率", f"{avg_yield:.2f}%")


st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["① 条件登録", "② 結果入力", "③ データ確認", "④ 編集・削除"])


# =========================
# ① 条件登録
# =========================
with tab1:
    st.header("① 抽出前の条件を登録")

    st.markdown("""
    <div class="lab-card">
        <div class="lab-card-title">実験の考え方</div>
        <div class="lab-card-body">
            ここでは抽出前に決まっている条件だけを登録します。
            抽出液量、抽出時間、TDS、味評価は抽出後に「② 結果入力」で記録します。
        </div>
    </div>
    """, unsafe_allow_html=True)

    exp_no = next_experiment_no(df)
    st.info(f"今回の実験No：{exp_no}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("基本条件")

        bean_type = st.text_input("豆の種類", value="Brazil")

        roast_level = st.number_input(
            "焙煎度（1〜8）",
            min_value=1,
            max_value=8,
            value=5,
            step=1
        )
        st.caption(f"焙煎度{roast_level}：{ROAST_NAMES[roast_level]}")

        coffee_weight = st.number_input(
            "豆量g",
            min_value=0.0,
            value=10.0,
            step=0.1
        )

        water_weight = st.number_input(
            "湯量g",
            min_value=0.0,
            value=180.0,
            step=0.1
        )

        water_temp = st.number_input(
            "湯温℃",
            min_value=0.0,
            value=95.0,
            step=0.5
        )

    with col2:
        st.subheader("抽出条件")

        grind_size = st.text_input("挽き目", value="8.1")
        dripper = st.text_input("ドリッパー", value="V60")
        filter_type = st.text_input("フィルター", value="HARIO 白")

        pour_method_choice = st.selectbox(
            "煎れ方",
            ["二刀入れ", "一刀入れ", "その他"]
        )

        if pour_method_choice == "その他":
            pour_method = st.text_input(
                "煎れ方を入力",
                value="",
                placeholder="例）三刀入れ、センター注湯、円を描く注湯"
            )
        else:
            pour_method = pour_method_choice

        pour_memo = st.text_area(
            "煎れ方メモ",
            value="",
            placeholder="例）0:00〜20g蒸らし、0:30〜100g、1:10〜180g"
        )

        bloom = st.selectbox(
            "蒸らし有無",
            ["あり", "なし"]
        )

        bloom_time = st.number_input(
            "蒸らし時間秒",
            min_value=0,
            value=30,
            step=1
        )

        bloom_water = st.number_input(
            "蒸らし湯量g",
            min_value=0.0,
            value=20.0,
            step=0.1
        )

        days_after_roast = st.number_input(
            "焙煎後日数",
            min_value=0,
            value=1,
            step=1
        )

        days_after_open = st.number_input(
            "開封後日数",
            min_value=0,
            value=0,
            step=1
        )

    st.markdown("---")

    if st.button("この条件を保存する"):
        new_row = {
            "実験No": exp_no,
            "日付": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "豆の種類": bean_type,
            "焙煎度": roast_level,
            "豆量g": coffee_weight,
            "湯量g": water_weight,
            "湯温℃": water_temp,
            "挽き目": grind_size,
            "ドリッパー": dripper,
            "フィルター": filter_type,
            "煎れ方": pour_method,
            "煎れ方メモ": pour_memo,
            "蒸らし有無": bloom,
            "蒸らし時間秒": bloom_time,
            "蒸らし湯量g": bloom_water,
            "焙煎後日数": days_after_roast,
            "開封後日数": days_after_open,
            "抽出液量g": "",
            "抽出時間秒": "",
            "TDS%": "",
            "抽出収率%": "",
            "酸味": "",
            "甘味": "",
            "苦味": "",
            "雑味": "",
            "香り": "",
            "飲みやすさ": "",
            "コメント": ""
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)

        st.success(f"実験No.{exp_no} の条件をGoogleスプレッドシートに保存しました。")
        st.rerun()


# =========================
# ② 結果入力
# =========================
with tab2:
    st.header("② 抽出後の結果を入力")

    df = load_data()

    if df.empty:
        st.warning("まだ条件が登録されていません。まずは①条件登録から始めてください。")
    else:
        exp_list = df["実験No"].tolist()

        selected_no = st.selectbox(
            "結果を入力する実験No",
            exp_list
        )

        target = df[df["実験No"] == selected_no].iloc[0]

        st.subheader("対象の条件")

        roast_text = ""
        try:
            roast_num = int(float(target["焙煎度"]))
            roast_text = ROAST_NAMES.get(roast_num, "")
        except Exception:
            roast_text = ""

        st.markdown(f"""
        <div class="condition-box">
            <div class="condition-title">実験No.{esc(target["実験No"])} の抽出条件</div>
            <div class="condition-text">
                豆の種類：{esc(target["豆の種類"])}<br>
                焙煎度：{esc(target["焙煎度"])} {esc(roast_text)}<br>
                豆量：{esc(target["豆量g"])} g ／ 湯量：{esc(target["湯量g"])} g ／ 湯温：{esc(target["湯温℃"])} ℃<br>
                挽き目：{esc(target["挽き目"])}<br>
                ドリッパー：{esc(target["ドリッパー"])} ／ フィルター：{esc(target["フィルター"])}<br>
                煎れ方：{esc(target["煎れ方"])}<br>
                煎れ方メモ：{esc(target["煎れ方メモ"])}<br>
                蒸らし：{esc(target["蒸らし有無"])} ／ 蒸らし時間：{esc(target["蒸らし時間秒"])} 秒 ／ 蒸らし湯量：{esc(target["蒸らし湯量g"])} g<br>
                焙煎後日数：{esc(target["焙煎後日数"])} 日 ／ 開封後日数：{esc(target["開封後日数"])} 日
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("測定結果")

            beverage_weight = st.number_input(
                "抽出液量g",
                min_value=0.0,
                value=safe_float(target["抽出液量g"], 150.0),
                step=0.1
            )

            brew_time = st.number_input(
                "抽出時間秒",
                min_value=0,
                value=safe_int(target["抽出時間秒"], 0),
                step=1
            )

            tds = st.number_input(
                "TDS%",
                min_value=0.0,
                value=safe_float(target["TDS%"], 1.25),
                step=0.01
            )

        with col2:
            st.subheader("味評価")

            acidity = st.slider("酸味", 1, 5, safe_int(target["酸味"], 3))
            sweetness = st.slider("甘味", 1, 5, safe_int(target["甘味"], 3))
            bitterness = st.slider("苦味", 1, 5, safe_int(target["苦味"], 2))
            off_flavor = st.slider("雑味", 1, 5, safe_int(target["雑味"], 3))
            aroma = st.slider("香り", 1, 5, safe_int(target["香り"], 3))
            drinkability = st.slider("飲みやすさ", 1, 5, safe_int(target["飲みやすさ"], 3))

        comment = st.text_area("コメント", value=str(target["コメント"]))

        coffee_weight = safe_float(target["豆量g"])
        extraction_yield = calc_yield(tds, beverage_weight, coffee_weight)

        tds_label, tds_comment = judge_tds(tds)
        yield_label = judge_yield(extraction_yield)

        metric_col1, metric_col2, metric_col3 = st.columns(3)

        with metric_col1:
            st.metric("TDS判定", tds_label)

        with metric_col2:
            st.metric("抽出収率%", f"{extraction_yield:.2f}%")

        with metric_col3:
            st.metric("抽出収率判定", yield_label)

        if st.button("この結果を保存する"):
            idx = df.index[df["実験No"] == selected_no][0]

            df.at[idx, "抽出液量g"] = beverage_weight
            df.at[idx, "抽出時間秒"] = brew_time
            df.at[idx, "TDS%"] = tds
            df.at[idx, "抽出収率%"] = extraction_yield

            df.at[idx, "酸味"] = acidity
            df.at[idx, "甘味"] = sweetness
            df.at[idx, "苦味"] = bitterness
            df.at[idx, "雑味"] = off_flavor
            df.at[idx, "香り"] = aroma
            df.at[idx, "飲みやすさ"] = drinkability
            df.at[idx, "コメント"] = comment

            save_data(df)

            st.success("結果をGoogleスプレッドシートに保存しました。")
            st.info(tds_comment)
            st.rerun()


# =========================
# ③ データ確認
# =========================
with tab3:
    st.header("③ 過去データ確認")

    df = load_data()

    st.subheader("実験ログ一覧")
    st.dataframe(df, width="stretch")

    if not df.empty:
        graph_df = df.copy()

        graph_df["TDS%"] = pd.to_numeric(graph_df["TDS%"], errors="coerce")
        graph_df["抽出収率%"] = pd.to_numeric(graph_df["抽出収率%"], errors="coerce")
        graph_df["実験No"] = pd.to_numeric(graph_df["実験No"], errors="coerce")
        graph_df["焙煎度"] = pd.to_numeric(graph_df["焙煎度"], errors="coerce")

        graph_df = graph_df.dropna(subset=["実験No"])

        st.subheader("TDSの推移")
        st.line_chart(graph_df.set_index("実験No")["TDS%"])

        st.subheader("抽出収率の推移")
        st.line_chart(graph_df.set_index("実験No")["抽出収率%"])

        st.subheader("目標TDS 1.25%に近い順")

        ranking_df = graph_df.dropna(subset=["TDS%"]).copy()

        if ranking_df.empty:
            st.info("まだTDSが入力された実験がありません。")
        else:
            ranking_df["目標との差"] = (ranking_df["TDS%"] - 1.25).abs()
            ranking_df = ranking_df.sort_values("目標との差")

            ranking_cols = [
                "実験No", "豆の種類", "焙煎度", "挽き目",
                "ドリッパー", "フィルター", "煎れ方",
                "TDS%", "抽出収率%", "目標との差", "コメント"
            ]

            st.dataframe(ranking_df[ranking_cols], width="stretch")

        st.subheader("研究メモ")

        valid_df = graph_df.dropna(subset=["TDS%", "抽出収率%"])

        if valid_df.empty:
            st.info("結果が入力されると、ここに簡単な分析メモが表示されます。")
        else:
            best_row = valid_df.iloc[(valid_df["TDS%"] - 1.25).abs().argsort()[:1]].iloc[0]

            st.markdown(f"""
            <div class="lab-card">
                <div class="lab-card-title">現在もっとも目標TDSに近い実験</div>
                <div class="lab-card-body">
                    実験No.{int(best_row["実験No"])} が、TDS 1.25%にもっとも近い条件です。<br>
                    TDS：{best_row["TDS%"]:.2f}% ／ 抽出収率：{best_row["抽出収率%"]:.2f}%<br>
                    豆：{esc(best_row["豆の種類"])} ／ 焙煎度：{esc(best_row["焙煎度"])} ／ 挽き目：{esc(best_row["挽き目"])}<br>
                    ドリッパー：{esc(best_row["ドリッパー"])} ／ フィルター：{esc(best_row["フィルター"])}<br>
                    煎れ方：{esc(best_row["煎れ方"])} ／ 蒸らし：{esc(best_row["蒸らし有無"])}
                </div>
            </div>
            """, unsafe_allow_html=True)


# =========================
# ④ 編集・削除
# =========================
with tab4:
    st.header("④ 過去データの編集・削除")

    df = load_data()

    if df.empty:
        st.warning("編集・削除できるデータがまだありません。")
    else:
        st.markdown("""
        <div class="lab-card">
            <div class="lab-card-title">編集・削除について</div>
            <div class="lab-card-body">
                登録済みの実験データを後から修正できます。
                間違えて登録したデータは、確認チェックを入れてから削除できます。
            </div>
        </div>
        """, unsafe_allow_html=True)

        edit_exp_list = df["実験No"].tolist()

        edit_selected_no = st.selectbox(
            "編集・削除する実験No",
            edit_exp_list,
            key="edit_selected_no"
        )

        edit_idx = df.index[df["実験No"] == edit_selected_no][0]
        edit_target = df.loc[edit_idx]

        st.subheader("選択中のデータ")

        st.markdown(f"""
        <div class="condition-box">
            <div class="condition-title">実験No.{esc(edit_target["実験No"])} の現在データ</div>
            <div class="condition-text">
                日付：{esc(edit_target["日付"])}<br>
                豆：{esc(edit_target["豆の種類"])} ／ 焙煎度：{esc(edit_target["焙煎度"])} ／ 挽き目：{esc(edit_target["挽き目"])}<br>
                ドリッパー：{esc(edit_target["ドリッパー"])} ／ フィルター：{esc(edit_target["フィルター"])} ／ 煎れ方：{esc(edit_target["煎れ方"])}<br>
                TDS：{esc(edit_target["TDS%"])} ／ 抽出収率：{esc(edit_target["抽出収率%"])} ／ コメント：{esc(edit_target["コメント"])}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("データを編集する")

        with st.form("edit_form"):
            edit_col1, edit_col2 = st.columns(2)

            with edit_col1:
                st.markdown("### 基本条件")

                edit_date = st.text_input("日付", value=str(edit_target["日付"]))
                edit_bean_type = st.text_input("豆の種類", value=str(edit_target["豆の種類"]))

                edit_roast_level = st.selectbox(
                    "焙煎度（1〜8）",
                    [1, 2, 3, 4, 5, 6, 7, 8],
                    index=max(0, min(7, safe_int(edit_target["焙煎度"], 5) - 1))
                )
                st.caption(f"焙煎度{edit_roast_level}：{ROAST_NAMES[edit_roast_level]}")

                edit_coffee_weight = st.text_input("豆量g", value=str(edit_target["豆量g"]))
                edit_water_weight = st.text_input("湯量g", value=str(edit_target["湯量g"]))
                edit_water_temp = st.text_input("湯温℃", value=str(edit_target["湯温℃"]))

                st.markdown("### 鮮度条件")

                edit_days_after_roast = st.text_input("焙煎後日数", value=str(edit_target["焙煎後日数"]))
                edit_days_after_open = st.text_input("開封後日数", value=str(edit_target["開封後日数"]))

            with edit_col2:
                st.markdown("### 抽出条件")

                edit_grind_size = st.text_input("挽き目", value=str(edit_target["挽き目"]))
                edit_dripper = st.text_input("ドリッパー", value=str(edit_target["ドリッパー"]))
                edit_filter_type = st.text_input("フィルター", value=str(edit_target["フィルター"]))
                edit_pour_method = st.text_input("煎れ方", value=str(edit_target["煎れ方"]))
                edit_pour_memo = st.text_area("煎れ方メモ", value=str(edit_target["煎れ方メモ"]))

                bloom_options = ["あり", "なし", ""]
                current_bloom = str(edit_target["蒸らし有無"])
                bloom_index = bloom_options.index(current_bloom) if current_bloom in bloom_options else 0

                edit_bloom = st.selectbox(
                    "蒸らし有無",
                    bloom_options,
                    index=bloom_index
                )

                edit_bloom_time = st.text_input("蒸らし時間秒", value=str(edit_target["蒸らし時間秒"]))
                edit_bloom_water = st.text_input("蒸らし湯量g", value=str(edit_target["蒸らし湯量g"]))

            st.markdown("---")

            result_col1, result_col2 = st.columns(2)

            with result_col1:
                st.markdown("### 測定結果")

                edit_beverage_weight = st.text_input("抽出液量g", value=str(edit_target["抽出液量g"]))
                edit_brew_time = st.text_input("抽出時間秒", value=str(edit_target["抽出時間秒"]))
                edit_tds = st.text_input("TDS%", value=str(edit_target["TDS%"]))

                recalculated_yield = calc_yield_from_text(
                    edit_tds,
                    edit_beverage_weight,
                    edit_coffee_weight,
                    current_value=str(edit_target["抽出収率%"])
                )

                st.info(f"保存時の抽出収率：{recalculated_yield}")

            with result_col2:
                st.markdown("### 味評価")

                rating_options = ["", "1", "2", "3", "4", "5"]

                edit_acidity = st.selectbox("酸味", rating_options, index=rating_index(edit_target["酸味"]))
                edit_sweetness = st.selectbox("甘味", rating_options, index=rating_index(edit_target["甘味"]))
                edit_bitterness = st.selectbox("苦味", rating_options, index=rating_index(edit_target["苦味"]))
                edit_off_flavor = st.selectbox("雑味", rating_options, index=rating_index(edit_target["雑味"]))
                edit_aroma = st.selectbox("香り", rating_options, index=rating_index(edit_target["香り"]))
                edit_drinkability = st.selectbox("飲みやすさ", rating_options, index=rating_index(edit_target["飲みやすさ"]))

            edit_comment = st.text_area("コメント", value=str(edit_target["コメント"]))

            update_submitted = st.form_submit_button("この内容で更新する")

        if update_submitted:
            df.at[edit_idx, "日付"] = edit_date
            df.at[edit_idx, "豆の種類"] = edit_bean_type
            df.at[edit_idx, "焙煎度"] = edit_roast_level
            df.at[edit_idx, "豆量g"] = edit_coffee_weight
            df.at[edit_idx, "湯量g"] = edit_water_weight
            df.at[edit_idx, "湯温℃"] = edit_water_temp

            df.at[edit_idx, "挽き目"] = edit_grind_size
            df.at[edit_idx, "ドリッパー"] = edit_dripper
            df.at[edit_idx, "フィルター"] = edit_filter_type
            df.at[edit_idx, "煎れ方"] = edit_pour_method
            df.at[edit_idx, "煎れ方メモ"] = edit_pour_memo

            df.at[edit_idx, "蒸らし有無"] = edit_bloom
            df.at[edit_idx, "蒸らし時間秒"] = edit_bloom_time
            df.at[edit_idx, "蒸らし湯量g"] = edit_bloom_water

            df.at[edit_idx, "焙煎後日数"] = edit_days_after_roast
            df.at[edit_idx, "開封後日数"] = edit_days_after_open

            df.at[edit_idx, "抽出液量g"] = edit_beverage_weight
            df.at[edit_idx, "抽出時間秒"] = edit_brew_time
            df.at[edit_idx, "TDS%"] = edit_tds
            df.at[edit_idx, "抽出収率%"] = recalculated_yield

            df.at[edit_idx, "酸味"] = edit_acidity
            df.at[edit_idx, "甘味"] = edit_sweetness
            df.at[edit_idx, "苦味"] = edit_bitterness
            df.at[edit_idx, "雑味"] = edit_off_flavor
            df.at[edit_idx, "香り"] = edit_aroma
            df.at[edit_idx, "飲みやすさ"] = edit_drinkability
            df.at[edit_idx, "コメント"] = edit_comment

            save_data(df)
            st.success(f"実験No.{edit_selected_no} を更新しました。")
            st.rerun()

        st.markdown("""
        <div class="danger-card">
            <div class="lab-card-title">削除エリア</div>
            <div class="lab-card-body">
                削除すると、この実験データはGoogleスプレッドシートから消えます。
                不安な場合は、先にスプレッドシートをコピーしてバックアップしてください。
            </div>
        </div>
        """, unsafe_allow_html=True)

        confirm_delete = st.checkbox(
            f"実験No.{edit_selected_no} を削除することを確認しました"
        )

        if st.button("この実験データを削除する"):
            if confirm_delete:
                df = df[df["実験No"] != edit_selected_no]
                save_data(df)
                st.success(f"実験No.{edit_selected_no} を削除しました。")
                st.rerun()
            else:
                st.warning("削除するには確認チェックを入れてください。")
