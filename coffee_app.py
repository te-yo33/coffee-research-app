import os
import uuid
from datetime import date, datetime

import pandas as pd
import streamlit as st


# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="Roast & Brew Lab",
    page_icon="☕",
    layout="wide",
)

DATA_DIR = "data"
BEANS_FILE = os.path.join(DATA_DIR, "beans.csv")
ROASTS_FILE = os.path.join(DATA_DIR, "roasts.csv")
BREWS_FILE = os.path.join(DATA_DIR, "brews.csv")

os.makedirs(DATA_DIR, exist_ok=True)


# =========================
# CSVの列定義
# =========================
BEANS_COLUMNS = [
    "bean_id",
    "bean_name",
    "origin",
    "variety",
    "process",
    "memo",
    "created_at",
]

ROASTS_COLUMNS = [
    "roast_id",
    "bean_id",
    "bean_name",
    "roast_date",
    "green_weight_g",
    "roasted_weight_g",
    "weight_loss_percent",
    "roaster",
    "roast_speed",
    "charge_temp_c",
    "total_roast_time_sec",
    "first_crack_start_sec",
    "development_time_sec",
    "drop_temp_c",
    "roast_level_8",
    "agtron_value",
    "bean_color_score",
    "roast_color_hex",
    "unevenness_score",
    "roast_aroma_score",
    "roast_memo",
    "created_at",
]

BREWS_COLUMNS = [
    "brew_id",
    "roast_id",
    "bean_name",
    "brew_date",
    "days_after_roast",
    "dripper",
    "filter_type",
    "grind_size",
    "dose_g",
    "water_g",
    "brew_ratio",
    "water_temp_c",
    "brew_time_sec",
    "beverage_g",
    "tds_percent",
    "extraction_yield_percent",
    "acidity_score",
    "sweetness_score",
    "bitterness_score",
    "aroma_score",
    "body_score",
    "aftertaste_score",
    "misc_score",
    "overall_score",
    "brew_memo",
    "created_at",
]


# =========================
# 共通関数
# =========================
def load_csv(path: str, columns: list[str]) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df[columns]
    return pd.DataFrame(columns=columns)


def save_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def make_id(prefix: str) -> str:
    today = datetime.now().strftime("%Y%m%d")
    short = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{today}-{short}"


def safe_float(value, default=0.0) -> float:
    try:
        if value == "" or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0) -> int:
    try:
        if value == "" or pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def sec_to_minsec(seconds: int) -> str:
    seconds = safe_int(seconds)
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


def calc_weight_loss(green_g: float, roasted_g: float) -> float:
    if green_g <= 0 or roasted_g <= 0:
        return 0.0
    return round((green_g - roasted_g) / green_g * 100, 2)


def calc_brew_ratio(water_g: float, dose_g: float) -> float:
    if dose_g <= 0 or water_g <= 0:
        return 0.0
    return round(water_g / dose_g, 2)


def calc_extraction_yield(beverage_g: float, tds_percent: float, dose_g: float) -> float:
    if beverage_g <= 0 or tds_percent <= 0 or dose_g <= 0:
        return 0.0
    return round(beverage_g * (tds_percent / 100) / dose_g * 100, 2)


def get_roast_label(row: pd.Series) -> str:
    roast_date = row.get("roast_date", "")
    bean_name = row.get("bean_name", "")
    speed = row.get("roast_speed", "")
    agtron = row.get("agtron_value", "")
    roast_id = row.get("roast_id", "")
    return f"{roast_id} / {bean_name} / {roast_date} / {speed} / Agtron {agtron}"


# =========================
# データ読み込み
# =========================
beans_df = load_csv(BEANS_FILE, BEANS_COLUMNS)
roasts_df = load_csv(ROASTS_FILE, ROASTS_COLUMNS)
brews_df = load_csv(BREWS_FILE, BREWS_COLUMNS)


# =========================
# サイドバー
# =========================
st.sidebar.title("☕ Roast & Brew Lab")
st.sidebar.write("焙煎ログと抽出ログをつなげて、味の変化を研究するアプリです。")

page = st.sidebar.radio(
    "ページ選択",
    [
        "ホーム",
        "豆マスタ登録",
        "焙煎ログ登録",
        "抽出ログ登録",
        "分析",
        "データ一覧・検索",
    ],
)

st.sidebar.divider()
st.sidebar.caption("CSVは data フォルダに自動保存されます。")


# =========================
# ホーム
# =========================
if page == "ホーム":
    st.title("Roast & Brew Lab ☕")
    st.write("焙煎条件、豆色、Agtron値、抽出条件、味の評価をつなげて記録する研究ログアプリです。")

    c1, c2, c3 = st.columns(3)
    c1.metric("登録豆数", len(beans_df))
    c2.metric("焙煎ログ数", len(roasts_df))
    c3.metric("抽出ログ数", len(brews_df))

    st.subheader("データの流れ")
    st.code(
        """
豆マスタ
  ↓
焙煎ログ：高速 / 中速 / 低速、Agtron値、豆色スコア、カラー値
  ↓
抽出ログ：湯温、挽き目、TDS、収率、味評価
  ↓
分析：焙煎方法と抽出結果・味の関係を見る
        """.strip()
    )

    st.info("まずは『豆マスタ登録』→『焙煎ログ登録』→『抽出ログ登録』の順番で使います。")


# =========================
# 豆マスタ登録
# =========================
elif page == "豆マスタ登録":
    st.title("豆マスタ登録")
    st.write("同じ豆を何回も焙煎・抽出で使えるように、豆そのものの情報を登録します。")

    with st.form("bean_form"):
        bean_name = st.text_input("豆名", placeholder="例：Ethiopia Yirgacheffe")
        origin = st.text_input("産地", placeholder="例：Ethiopia")
        variety = st.text_input("品種", placeholder="例：Heirloom")
        process = st.selectbox("精製方法", ["", "Washed", "Natural", "Honey", "Anaerobic", "Other"])
        memo = st.text_area("メモ")
        submitted = st.form_submit_button("豆を登録")

    if submitted:
        if bean_name.strip() == "":
            st.error("豆名は必須です。")
        else:
            new_row = {
                "bean_id": make_id("B"),
                "bean_name": bean_name.strip(),
                "origin": origin.strip(),
                "variety": variety.strip(),
                "process": process,
                "memo": memo.strip(),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            beans_df = pd.concat([beans_df, pd.DataFrame([new_row])], ignore_index=True)
            save_csv(beans_df, BEANS_FILE)
            st.success("豆を登録しました。")
            st.rerun()

    st.subheader("登録済みの豆")
    st.dataframe(beans_df, use_container_width=True)


# =========================
# 焙煎ログ登録
# =========================
elif page == "焙煎ログ登録":
    st.title("焙煎ログ登録")
    st.write("焙煎速度、Agtron値、豆色スコア、焙煎度カラー値を記録します。")

    if beans_df.empty:
        st.warning("先に『豆マスタ登録』で豆を登録してください。")
    else:
        bean_options = {
            f"{row['bean_id']} / {row['bean_name']} / {row['origin']} / {row['process']}": row
            for _, row in beans_df.iterrows()
        }

        with st.form("roast_form"):
            selected_bean_label = st.selectbox("焙煎する豆", list(bean_options.keys()))
            selected_bean = bean_options[selected_bean_label]

            c1, c2, c3 = st.columns(3)
            roast_date = c1.date_input("焙煎日", value=date.today())
            roaster = c2.text_input("焙煎機", placeholder="例：手網 / Gene Cafe / Aillio Bullet")
            roast_speed = c3.selectbox("焙煎スピード", ["高速", "中速", "低速"])

            c4, c5, c6 = st.columns(3)
            green_weight_g = c4.number_input("生豆量 g", min_value=0.0, value=100.0, step=1.0)
            roasted_weight_g = c5.number_input("焙煎後重量 g", min_value=0.0, value=85.0, step=1.0)
            weight_loss_percent = calc_weight_loss(green_weight_g, roasted_weight_g)
            c6.metric("重量減少率", f"{weight_loss_percent:.2f}%")

            st.markdown("#### 焙煎プロファイル")
            c7, c8, c9 = st.columns(3)
            charge_temp_c = c7.number_input("投入温度 ℃", min_value=0.0, value=180.0, step=1.0)
            total_roast_time_sec = c8.number_input("総焙煎時間 秒", min_value=0, value=480, step=10)
            drop_temp_c = c9.number_input("排出温度 ℃", min_value=0.0, value=200.0, step=1.0)

            c10, c11, c12 = st.columns(3)
            first_crack_start_sec = c10.number_input("1ハゼ開始 秒", min_value=0, value=360, step=10)
            development_time_sec = c11.number_input("デベロップメント時間 秒", min_value=0, value=90, step=10)
            roast_level_8 = c12.slider("焙煎度 8段階", 1, 8, 3)

            st.markdown("#### 焙煎後の豆の結果")
            c13, c14, c15 = st.columns(3)
            agtron_value = c13.number_input("Agtron値", min_value=0.0, max_value=150.0, value=85.0, step=1.0)
            bean_color_score = c14.slider("豆色スコア 明るい1〜暗い10", 1, 10, 4)
            roast_color_hex = c15.color_picker("焙煎度カラー値", "#8B5A2B")

            c16, c17 = st.columns(2)
            unevenness_score = c16.slider("焼きムラ 少ない1〜多い5", 1, 5, 2)
            roast_aroma_score = c17.slider("焙煎後の香り 1〜5", 1, 5, 3)

            roast_memo = st.text_area("焙煎メモ", placeholder="例：高速気味。酸が残りそう。1ハゼ後は短め。")
            submitted = st.form_submit_button("焙煎ログを登録")

        if submitted:
            if total_roast_time_sec <= 0:
                st.error("総焙煎時間は1秒以上にしてください。")
            elif first_crack_start_sec > total_roast_time_sec:
                st.error("1ハゼ開始時間が総焙煎時間を超えています。")
            else:
                new_row = {
                    "roast_id": make_id("R"),
                    "bean_id": selected_bean["bean_id"],
                    "bean_name": selected_bean["bean_name"],
                    "roast_date": roast_date.strftime("%Y-%m-%d"),
                    "green_weight_g": green_weight_g,
                    "roasted_weight_g": roasted_weight_g,
                    "weight_loss_percent": weight_loss_percent,
                    "roaster": roaster.strip(),
                    "roast_speed": roast_speed,
                    "charge_temp_c": charge_temp_c,
                    "total_roast_time_sec": total_roast_time_sec,
                    "first_crack_start_sec": first_crack_start_sec,
                    "development_time_sec": development_time_sec,
                    "drop_temp_c": drop_temp_c,
                    "roast_level_8": roast_level_8,
                    "agtron_value": agtron_value,
                    "bean_color_score": bean_color_score,
                    "roast_color_hex": roast_color_hex,
                    "unevenness_score": unevenness_score,
                    "roast_aroma_score": roast_aroma_score,
                    "roast_memo": roast_memo.strip(),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                roasts_df = pd.concat([roasts_df, pd.DataFrame([new_row])], ignore_index=True)
                save_csv(roasts_df, ROASTS_FILE)
                st.success("焙煎ログを登録しました。")
                st.rerun()

    st.subheader("登録済みの焙煎ログ")
    if not roasts_df.empty:
        show_roasts = roasts_df.copy()
        show_roasts["総焙煎時間"] = show_roasts["total_roast_time_sec"].apply(sec_to_minsec)
        st.dataframe(show_roasts, use_container_width=True)
    else:
        st.info("まだ焙煎ログはありません。")


# =========================
# 抽出ログ登録
# =========================
elif page == "抽出ログ登録":
    st.title("抽出ログ登録")
    st.write("登録済みの焙煎ログを選んで、その豆で抽出した結果を記録します。")

    if roasts_df.empty:
        st.warning("先に『焙煎ログ登録』で焙煎ログを登録してください。")
    else:
        roast_options = {get_roast_label(row): row for _, row in roasts_df.iterrows()}

        with st.form("brew_form"):
            selected_roast_label = st.selectbox("使用する焙煎豆", list(roast_options.keys()))
            selected_roast = roast_options[selected_roast_label]

            c1, c2, c3 = st.columns(3)
            brew_date = c1.date_input("抽出日", value=date.today())
            roast_date_value = datetime.strptime(str(selected_roast["roast_date"]), "%Y-%m-%d").date()
            days_after_roast = (brew_date - roast_date_value).days
            c2.metric("焙煎後日数", f"{days_after_roast}日")
            c3.write("使用豆")
            c3.write(selected_roast["bean_name"])

            st.markdown("#### 抽出条件")
            c4, c5, c6 = st.columns(3)
            dripper = c4.text_input("ドリッパー", placeholder="例：V60 / Origami / Kalita")
            filter_type = c5.text_input("フィルター", placeholder="例：ペーパー / メタル")
            grind_size = c6.number_input("挽き目", min_value=0.0, value=8.0, step=0.1)

            c7, c8, c9 = st.columns(3)
            dose_g = c7.number_input("粉量 g", min_value=0.0, value=15.0, step=0.5)
            water_g = c8.number_input("湯量 g", min_value=0.0, value=240.0, step=5.0)
            brew_ratio = calc_brew_ratio(water_g, dose_g)
            c9.metric("抽出比率", f"1:{brew_ratio:.2f}")

            c10, c11, c12 = st.columns(3)
            water_temp_c = c10.number_input("湯温 ℃", min_value=0.0, value=92.0, step=1.0)
            brew_time_sec = c11.number_input("抽出時間 秒", min_value=0, value=180, step=5)
            beverage_g = c12.number_input("抽出液量 g", min_value=0.0, value=200.0, step=5.0)

            c13, c14 = st.columns(2)
            tds_percent = c13.number_input("TDS %", min_value=0.0, value=1.30, step=0.01)
            extraction_yield_percent = calc_extraction_yield(beverage_g, tds_percent, dose_g)
            c14.metric("収率", f"{extraction_yield_percent:.2f}%")

            st.markdown("#### 味の評価 1〜5")
            c15, c16, c17, c18 = st.columns(4)
            acidity_score = c15.slider("酸味", 1, 5, 3)
            sweetness_score = c16.slider("甘味", 1, 5, 3)
            bitterness_score = c17.slider("苦味", 1, 5, 2)
            aroma_score = c18.slider("香り", 1, 5, 3)

            c19, c20, c21, c22 = st.columns(4)
            body_score = c19.slider("ボディ", 1, 5, 3)
            aftertaste_score = c20.slider("後味", 1, 5, 3)
            misc_score = c21.slider("雑味 少ない5〜多い1", 1, 5, 4)
            overall_score = c22.slider("総合評価", 1, 5, 3)

            brew_memo = st.text_area("抽出メモ", placeholder="例：酸味は明るいが少し薄い。次は挽き目を細かくする。")
            submitted = st.form_submit_button("抽出ログを登録")

        if submitted:
            if days_after_roast < 0:
                st.error("抽出日が焙煎日より前になっています。")
            elif dose_g <= 0:
                st.error("粉量は0より大きくしてください。")
            elif water_g <= 0:
                st.error("湯量は0より大きくしてください。")
            elif tds_percent <= 0:
                st.error("TDSは0より大きくしてください。")
            else:
                new_row = {
                    "brew_id": make_id("BR"),
                    "roast_id": selected_roast["roast_id"],
                    "bean_name": selected_roast["bean_name"],
                    "brew_date": brew_date.strftime("%Y-%m-%d"),
                    "days_after_roast": days_after_roast,
                    "dripper": dripper.strip(),
                    "filter_type": filter_type.strip(),
                    "grind_size": grind_size,
                    "dose_g": dose_g,
                    "water_g": water_g,
                    "brew_ratio": brew_ratio,
                    "water_temp_c": water_temp_c,
                    "brew_time_sec": brew_time_sec,
                    "beverage_g": beverage_g,
                    "tds_percent": tds_percent,
                    "extraction_yield_percent": extraction_yield_percent,
                    "acidity_score": acidity_score,
                    "sweetness_score": sweetness_score,
                    "bitterness_score": bitterness_score,
                    "aroma_score": aroma_score,
                    "body_score": body_score,
                    "aftertaste_score": aftertaste_score,
                    "misc_score": misc_score,
                    "overall_score": overall_score,
                    "brew_memo": brew_memo.strip(),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                brews_df = pd.concat([brews_df, pd.DataFrame([new_row])], ignore_index=True)
                save_csv(brews_df, BREWS_FILE)
                st.success("抽出ログを登録しました。")
                st.rerun()

    st.subheader("登録済みの抽出ログ")
    if not brews_df.empty:
        st.dataframe(brews_df, use_container_width=True)
    else:
        st.info("まだ抽出ログはありません。")


# =========================
# 分析
# =========================
elif page == "分析":
    st.title("分析")
    st.write("焙煎条件と抽出結果・味の関係を見ます。")

    if roasts_df.empty or brews_df.empty:
        st.warning("分析には焙煎ログと抽出ログの両方が必要です。")
    else:
        merged = brews_df.merge(
            roasts_df,
            on=["roast_id", "bean_name"],
            how="left",
            suffixes=("_brew", "_roast"),
        )

        numeric_cols = [
            "agtron_value",
            "bean_color_score",
            "total_roast_time_sec",
            "development_time_sec",
            "weight_loss_percent",
            "days_after_roast",
            "water_temp_c",
            "grind_size",
            "tds_percent",
            "extraction_yield_percent",
            "acidity_score",
            "sweetness_score",
            "bitterness_score",
            "aroma_score",
            "body_score",
            "aftertaste_score",
            "misc_score",
            "overall_score",
        ]
        for col in numeric_cols:
            if col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors="coerce")

        st.subheader("焙煎スピード別の平均評価")
        speed_summary = (
            merged.groupby("roast_speed")[[
                "overall_score",
                "acidity_score",
                "sweetness_score",
                "bitterness_score",
                "aroma_score",
                "tds_percent",
                "extraction_yield_percent",
            ]]
            .mean()
            .round(2)
            .reset_index()
        )
        st.dataframe(speed_summary, use_container_width=True)

        chart_target = st.selectbox(
            "棒グラフにする項目",
            [
                "overall_score",
                "acidity_score",
                "sweetness_score",
                "bitterness_score",
                "aroma_score",
                "tds_percent",
                "extraction_yield_percent",
            ],
        )
        chart_df = speed_summary.set_index("roast_speed")[[chart_target]]
        st.bar_chart(chart_df)

        st.subheader("散布図で関係を見る")
        c1, c2 = st.columns(2)
        x_col = c1.selectbox(
            "横軸",
            [
                "agtron_value",
                "bean_color_score",
                "total_roast_time_sec",
                "development_time_sec",
                "weight_loss_percent",
                "days_after_roast",
                "water_temp_c",
                "grind_size",
                "tds_percent",
                "extraction_yield_percent",
            ],
        )
        y_col = c2.selectbox(
            "縦軸",
            [
                "overall_score",
                "acidity_score",
                "sweetness_score",
                "bitterness_score",
                "aroma_score",
                "tds_percent",
                "extraction_yield_percent",
            ],
        )

        scatter_df = merged[[x_col, y_col, "roast_speed", "bean_name"]].dropna()
        st.scatter_chart(scatter_df, x=x_col, y=y_col)

        st.subheader("結合済みデータ")
        st.dataframe(merged, use_container_width=True)

        st.download_button(
            "結合済みデータをCSVでダウンロード",
            data=merged.to_csv(index=False, encoding="utf-8-sig"),
            file_name="roast_brew_merged.csv",
            mime="text/csv",
        )


# =========================
# データ一覧・検索
# =========================
elif page == "データ一覧・検索":
    st.title("データ一覧・検索")

    tab1, tab2, tab3 = st.tabs(["豆", "焙煎ログ", "抽出ログ"])

    with tab1:
        st.subheader("豆データ")
        keyword = st.text_input("豆データ検索", key="bean_search", placeholder="豆名、産地、精製方法など")
        df = beans_df.copy()
        if keyword:
            mask = df.astype(str).apply(lambda x: x.str.contains(keyword, case=False, na=False)).any(axis=1)
            df = df[mask]
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "豆データをCSVでダウンロード",
            data=beans_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="beans.csv",
            mime="text/csv",
        )

    with tab2:
        st.subheader("焙煎ログ")
        keyword = st.text_input("焙煎ログ検索", key="roast_search", placeholder="豆名、焙煎速度、メモなど")
        df = roasts_df.copy()
        if keyword:
            mask = df.astype(str).apply(lambda x: x.str.contains(keyword, case=False, na=False)).any(axis=1)
            df = df[mask]
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "焙煎ログをCSVでダウンロード",
            data=roasts_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="roasts.csv",
            mime="text/csv",
        )

    with tab3:
        st.subheader("抽出ログ")
        keyword = st.text_input("抽出ログ検索", key="brew_search", placeholder="豆名、ドリッパー、味メモなど")
        df = brews_df.copy()
        if keyword:
            mask = df.astype(str).apply(lambda x: x.str.contains(keyword, case=False, na=False)).any(axis=1)
            df = df[mask]
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "抽出ログをCSVでダウンロード",
            data=brews_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="brews.csv",
            mime="text/csv",
        )
