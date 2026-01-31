import os
import json
import csv
from datetime import datetime

import streamlit as st
import matplotlib.pyplot as plt

# =========================
# matplotlib 日本語フォント対策（Windows向け）
# =========================
plt.rcParams["font.family"] = "Meiryo"  # まずはメイリオ
plt.rcParams["axes.unicode_minus"] = False  # マイナス記号の文字化け対策


# =========================
# 基本設定
# =========================
st.set_page_config(page_title="買い物計算ツール", layout="centered")
st.title("🛒 買い物計算ツール（Streamlit版）")

DATA_DIR = "data"
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
HISTORY_PATH = os.path.join(DATA_DIR, "history.csv")


# =========================
# フォルダ＆設定（JSON）
# =========================
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_settings():
    ensure_data_dir()
    default = {"tax_rate": 0.10}
    if not os.path.exists(SETTINGS_PATH):
        return default
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "tax_rate" not in data:
            data["tax_rate"] = default["tax_rate"]
        return data
    except Exception:
        return default


def save_settings(settings: dict):
    ensure_data_dir()
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


# =========================
# 履歴（CSV）
# =========================
def append_history_row(row: dict):
    """
    CSVに履歴を1行追記（なければヘッダーも作る）
    memo列あり
    """
    ensure_data_dir()
    file_exists = os.path.exists(HISTORY_PATH)

    # ★ memo列を含める
    fieldnames = ["datetime", "count", "subtotal", "tax_rate", "total", "memo"]

    with open(HISTORY_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        # memoが無い場合でも落ちないように保険
        if "memo" not in row:
            row["memo"] = ""
        writer.writerow(row)


def read_history_rows():
    """CSV履歴を読み込み、list[dict]で返す（ファイルが無ければ空）"""
    if not os.path.exists(HISTORY_PATH):
        return []
    rows = []
    with open(HISTORY_PATH, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # 古いCSVにmemo列が無い場合の保険
            if "memo" not in r:
                r["memo"] = ""
            rows.append(r)
    return rows


def delete_history_file():
    """履歴CSVを削除（全履歴クリア）"""
    if os.path.exists(HISTORY_PATH):
        os.remove(HISTORY_PATH)
        return True
    return False


# =========================
# パース（数値以外スキップ）
# =========================
def parse_price(text: str):
    if text is None:
        return None
    s = text.strip()
    if s == "":
        return None
    try:
        s = s.replace(",", "")
        value = float(s)
        if value < 0:
            return None
        return value
    except Exception:
        return None


# =========================
# 起動時にdataフォルダを確実に作る
# =========================
ensure_data_dir()


# =========================
# セッション状態（undo用）
# =========================
if "prices" not in st.session_state:
    st.session_state.prices = []


# =========================
# 設定読み込み（税率）
# =========================
settings = load_settings()
tax_rate = float(settings.get("tax_rate", 0.10))


# =========================
# メニュー
# =========================
page = st.sidebar.radio("メニュー", ["計算", "履歴", "グラフ", "設定"])


# =========================
# 計算ページ
# =========================
if page == "計算":
    st.subheader("価格入力（Enterで追加OK）")

    # メモ欄（Enterで価格追加しても消えないようフォーム外）
    memo = st.text_input(
        "メモ（任意：店名/カテゴリ/買ったもの）",
        key="memo",
        placeholder="例：スーパー / 食材 / 牛乳とパン",
    )

    # Enter対応フォーム（入力後にクリア）
    with st.form(
        "add_form", clear_on_submit=True
    ):  # ★あなたの希望：clear_on_submit=True
        price_text = st.text_input("価格を入力（例: 120 / 980.5 / 1,200）")
        add = st.form_submit_button("追加（EnterでもOK）")

    undo = st.button("undo（最後を取り消し）", use_container_width=True)

    if add:
        value = parse_price(price_text)
        if value is None:
            st.warning("数値として読めないのでスキップしました。")
        else:
            st.session_state.prices.append(value)
            st.success(f"{value:.2f} を追加しました。")

    if undo:
        if st.session_state.prices:
            removed = st.session_state.prices.pop()
            st.info(f"{removed:.2f} を取り消しました。")
        else:
            st.warning("取り消すものがありません。")

    st.divider()
    st.subheader("現在の明細")

    if st.session_state.prices:
        subtotal = sum(st.session_state.prices)
        total = subtotal * (1 + tax_rate)

        colS, colC = st.columns(2)

        with colS:
            if st.button("この結果を履歴に保存", use_container_width=True):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                append_history_row(
                    {
                        "datetime": now,
                        "count": len(st.session_state.prices),
                        "subtotal": round(subtotal, 2),
                        "tax_rate": tax_rate,
                        "total": round(total, 2),
                        "memo": st.session_state.get("memo", ""),
                    }
                )
                st.success("履歴に保存しました！")

        with colC:
            if st.button("全クリア", use_container_width=True):
                st.session_state.prices = []
                st.info("入力をクリアしました。")
                st.rerun()

        st.write("入力された価格一覧：")
        st.write(st.session_state.prices)

        colA, colB = st.columns(2)
        with colA:
            st.metric("小計", f"{subtotal:.2f}")
        with colB:
            st.metric("税込合計", f"{total:.2f}", delta=f"税率 {tax_rate*100:.1f}%")

    else:
        st.caption("まだ価格が入っていません。上で追加してください。")


# =========================
# 履歴ページ
# =========================
elif page == "履歴":
    st.subheader("履歴（CSV）")

    st.warning("⚠ 履歴を削除すると元に戻せません。")
    confirm = st.checkbox("削除することを理解しました（取り消し不可）")

    if st.button("履歴を全削除", use_container_width=True, disabled=not confirm):
        ok = delete_history_file()
        if ok:
            st.success("履歴を全削除しました。")
        else:
            st.info("履歴ファイルがまだありません。")
        st.rerun()

    st.divider()

    rows = read_history_rows()
    if not rows:
        st.caption("履歴がありません。計算ページで保存するとここに出ます。")
    else:
        st.dataframe(rows, use_container_width=True)

    # ★ history.csv が無いときに落ちないように安全化
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "rb") as f:
            st.download_button(
                label="CSVをダウンロード",
                data=f,
                file_name="history.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.caption("※ まだCSVが作られていません（最初に1回保存すると作成されます）")


# =========================
# グラフページ
# =========================
elif page == "グラフ":
    st.subheader("グラフ（発信映え）")

    # 表示件数を選べるように（発信向けは10〜20が見やすい）
    n = st.slider("表示する履歴件数", min_value=5, max_value=50, value=15, step=1)

    # -------------------------
    # ① セッション内の価格（今入力してるやつ）
    # -------------------------
    st.write("① いま入力している価格（セッション内）")
    if not st.session_state.prices:
        st.caption("価格が入っていません。計算ページで追加してください。")
    else:
        fig = plt.figure()
        plt.plot(st.session_state.prices, marker="o")
        plt.title("Prices (current session)")
        plt.xlabel("Index")
        plt.ylabel("Price")
        plt.grid(True, linewidth=0.3)
        st.pyplot(fig)

    st.divider()

    # -------------------------
    # ② 履歴：日時ラベル付きの合計推移
    # -------------------------
    st.write("② 履歴：合計の推移（日時ラベル付き）")
    rows = read_history_rows()
    if not rows:
        st.caption("履歴がありません。計算ページで保存すると出ます。")
    else:
        recent = rows[-n:]

        x_labels = []
        totals = []
        memos = []

        for r in recent:
            # datetimeは "YYYY-MM-DD HH:MM:SS" の想定
            dt = r.get("datetime", "")
            # 発信向けに短く（例: 01-31 23:10）
            label = dt[5:16] if len(dt) >= 16 else dt
            x_labels.append(label)

            try:
                totals.append(float(r.get("total", 0)))
            except Exception:
                totals.append(0.0)

            memos.append(r.get("memo", ""))

        fig2 = plt.figure()
        plt.plot(totals, marker="o")
        plt.title("Total trend (recent)")
        plt.xlabel("DateTime")
        plt.ylabel("Total")
        plt.grid(True, linewidth=0.3)

        # x軸ラベルを表示（見切れ防止）
        plt.xticks(range(len(x_labels)), x_labels, rotation=45, ha="right")
        plt.tight_layout()
        st.pyplot(fig2)

        # 発信向け：グラフと一緒に「メモ付き一覧」も出すと伝わりやすい
        st.caption(
            "※ グラフだけだとメモが見えないので、下に一覧も出します（スクショ用）"
        )
        st.dataframe(recent, use_container_width=True)

    st.divider()

    # -------------------------
    # ③ オプション：メモ別に合計をざっくり集計（棒グラフ）
    # -------------------------
    st.write("③（おまけ）メモ別の合計（ざっくり）")
    rows = read_history_rows()
    if not rows:
        st.caption("履歴がありません。")
    else:
        # memoが空のものは "(no memo)" にまとめる
        buckets = {}
        for r in rows:
            memo = (r.get("memo", "") or "").strip()
            if memo == "":
                memo = "(no memo)"
            try:
                t = float(r.get("total", 0))
            except Exception:
                t = 0.0
            buckets[memo] = buckets.get(memo, 0.0) + t

        # 上位10件に絞る（見やすさ優先）
        items = sorted(buckets.items(), key=lambda x: x[1], reverse=True)[:10]
        labels = [k for k, _ in items]
        values = [v for _, v in items]

        fig3 = plt.figure()
        plt.bar(range(len(labels)), values)
        plt.title("Total by memo (top 10)")
        plt.xlabel("Memo")
        plt.ylabel("Total")
        plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
        plt.tight_layout()
        st.pyplot(fig3)


# =========================
# 設定ページ（税率保存）
# =========================
elif page == "設定":
    st.subheader("設定（税率の保存）")

    st.write(f"現在の税率：**{tax_rate*100:.1f}%**")

    new_tax_percent = st.number_input(
        "税率（%）",
        min_value=0.0,
        max_value=100.0,
        value=float(tax_rate * 100),
        step=0.1,
    )

    if st.button("保存", use_container_width=True):
        settings["tax_rate"] = float(new_tax_percent / 100.0)
        save_settings(settings)
        st.success("税率を保存しました！")
        st.rerun()
