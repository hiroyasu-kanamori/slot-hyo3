import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import numpy as np
import json
import base64
import streamlit.components.v1 as components

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- ページ設定 ---
st.set_page_config(page_title="スロット優秀台レポート作成", layout="centered")

st.markdown("""<style>
[data-testid="stNumberInputStepDown"],
[data-testid="stNumberInputStepUp"],
[data-testid="stNumberInput"] button { display: none !important; }
</style>""", unsafe_allow_html=True)

# --- 日本語フォントのセットアップ ---
@st.cache_data
def get_font_path():
    font_path = "NotoSansCJKjp-Regular.otf"
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
        try:
            urllib.request.urlretrieve(url, font_path)
        except Exception as e:
            st.error(f"フォントのダウンロードに失敗しました: {e}")
            return None
    return font_path

font_p = get_font_path()
prop = fm.FontProperties(fname=font_p) if font_p else fm.FontProperties()

# ==========================================
# 機種名置換辞書
# ==========================================
RENAME_FILE = "rename_list.csv"

def get_rename_dict():
    if os.path.exists(RENAME_FILE):
        try:
            try:
                rename_df = pd.read_csv(RENAME_FILE, encoding='utf-8')
            except:
                rename_df = pd.read_csv(RENAME_FILE, encoding='cp932')
            return dict(zip(rename_df['original_name'], rename_df['display_name']))
        except Exception as e:
            st.warning(f"置換ファイルの読み取りエラー: {e}")
            return {}
    return {}

rename_dict = get_rename_dict()

def apply_rename(name):
    if name == "-- 選択 --" or not name: return ""
    return rename_dict.get(name, name)

# ==========================================
# ファイル入出力
# ==========================================
def save_text_to_file(text, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)

def load_text_from_file(filename, default_text):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else default_text
    return default_text

def save_targets_to_file(targets, filename):
    df_save = pd.DataFrame(targets, columns=['csv_name', 'display_name', 'threshold'])
    df_save.to_csv(filename, index=False, encoding='utf-8-sig')

def load_targets_from_file(filename):
    if os.path.exists(filename):
        try:
            df_load = pd.read_csv(filename)
            return [tuple(x) for x in df_load.to_numpy()]
        except:
            return []
    return []

SHIKAKE_FILE = "shikake_content3.json"

def load_shikake_content():
    if os.path.exists(SHIKAKE_FILE):
        try:
            with open(SHIKAKE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) == 7:
                    return data
        except:
            pass
    return [""] * 7

def save_shikake_content(content_list):
    with open(SHIKAKE_FILE, "w", encoding="utf-8") as f:
        json.dump(content_list, f, ensure_ascii=False)

def save_images_to_file(images_dict, filename):
    data = {dn: base64.b64encode(b).decode() for dn, b in images_dict.items()}
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f)

def load_images_from_file(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {dn: base64.b64decode(s) for dn, s in data.items()}
        except:
            pass
    return {}

def save_form_state(sid, data):
    filename = f"form_state{sid}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def load_form_state(sid):
    filename = f"form_state{sid}.json"
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}


# ==========================================
# セッション状態の初期化
# ==========================================
FILES = {
    "1": {"csv": "targets1_data.csv", "txt": "banner_text1.txt", "def_txt": "週間おススメ機種", "color": "#FF0000", "img": "images1.json"},
    "2": {"csv": "targets2_data.csv", "txt": "banner_text2.txt", "def_txt": "月間おススメ機種", "color": "#007BFF", "img": "images2.json"},
    "3": {"csv": "targets3_data.csv", "txt": "banner_text3.txt", "def_txt": "仕掛けレポート",  "color": "#FF6600", "img": "images3.json"},
    "4": {"csv": "targets4_data.csv", "txt": "banner_text4.txt", "def_txt": "1月の新台",       "color": "#DC5DE0", "img": "images4.json"},
    "5": {"csv": None,                "txt": "banner_text5.txt", "def_txt": "差玉TOP10",       "color": "#000000", "img": None}
}

for sid, cfg in FILES.items():
    if f'it{sid}' not in st.session_state:
        st.session_state[f'it{sid}'] = load_text_from_file(cfg["txt"], cfg["def_txt"])
    if f'edit_mode{sid}' not in st.session_state: st.session_state[f'edit_mode{sid}'] = False
    if f'bg_color{sid}' not in st.session_state: st.session_state[f'bg_color{sid}'] = cfg["color"]
    if cfg["csv"] and f'targets{sid}' not in st.session_state:
        st.session_state[f'targets{sid}'] = load_targets_from_file(cfg["csv"])
    if cfg.get("img") and f'images{sid}' not in st.session_state:
        st.session_state[f'images{sid}'] = load_images_from_file(cfg["img"])
    if f'report_img{sid}' not in st.session_state: st.session_state[f'report_img{sid}'] = None
    if sid in ["1", "2", "3", "4"]:
        fs = load_form_state(sid)
        for i in range(1, 4):
            slot = fs.get(str(i), {})
            if f"m{sid}_{i}" not in st.session_state and "m" in slot:
                st.session_state[f"m{sid}_{i}"] = slot["m"]
            if f"d{sid}_{i}" not in st.session_state and "d" in slot:
                st.session_state[f"d{sid}_{i}"] = slot["d"]
            if f"t{sid}_{i}" not in st.session_state and "t" in slot:
                st.session_state[f"t{sid}_{i}"] = slot["t"]

# 仕掛けの内容（永続化）
if 'shikake_content3' not in st.session_state:
    st.session_state['shikake_content3'] = load_shikake_content()
# sc_j キーを初期化（text_input の初期値として使用）
for j in range(7):
    if f'sc_{j}' not in st.session_state:
        st.session_state[f'sc_{j}'] = st.session_state['shikake_content3'][j]
# sn_j_k: セッション内のみ保持（起動時は常にNone）
for j in range(7):
    for k in range(10):
        if f"sn_{j}_{k}" not in st.session_state:
            st.session_state[f"sn_{j}_{k}"] = None

def update_display_name(sid, i):
    selected_machine = st.session_state[f"m{sid}_{i}"]
    st.session_state[f"d{sid}_{i}"] = apply_rename(selected_machine)

# --- 看板作成 ---
def create_banner(text, bg_color, banner_height, font_size, y_offset, stroke_width, width):
    height = banner_height
    radius = 45
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([(0, 0), (width, height)], radius=radius, fill=bg_color)
    try:
        font = ImageFont.truetype(font_p, font_size)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos_x, pos_y = (width - text_w) / 2, (height - text_h) / 2 - (text_h * 0.1) + y_offset
    draw.text((pos_x, pos_y), text, fill="white", font=font, stroke_width=stroke_width)
    return image

# --- レポート生成用描画関数 (B案：物理オーバーラップ版) ---
def draw_table_image(master_rows, h_idx, color, b_text, suffix):
    row_h_inch = 0.85
    num_rows = len(master_rows)
    fig, ax = plt.subplots(figsize=(14, num_rows * row_h_inch))

    # 余白設定も念のため維持
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.axis('off')
    ax.set_position([0, 0, 1, 1])

    table = ax.table(cellText=master_rows, colWidths=[0.1, 0.2, 0.15, 0.1, 0.1, 0.1, 0.25], loc='center', cellLoc='center')
    table.auto_set_font_size(False)

    for (r, c), cell in table.get_celld().items():
        cell.set_height(1.0 / num_rows)
        txt = cell.get_text()
        txt.set_fontproperties(prop)
        txt.set_verticalalignment('center_baseline')
        txt.set_horizontalalignment('center')

        if r in h_idx:
            cell.set_facecolor(color); cell.set_edgecolor(color)
            txt.set_color('black'); txt.set_fontsize(24); txt.set_weight('bold')
            if c == 3: txt.set_text(master_rows[r][0])
            else: txt.set_text("")

            if c == 0: cell.visible_edges = 'TLB'
            elif c == 6: cell.visible_edges = 'TRB'
            else: cell.visible_edges = 'TB'

        elif (r-1) in h_idx:
            cell.set_facecolor('#333333'); txt.set_color('white'); txt.set_fontsize(18)

        elif master_rows[r] == [""] * 7:
            cell.set_height(0.01); cell.visible_edges = ''

        else:
            cell.set_facecolor('#F9F9F9' if r % 2 == 0 else 'white'); txt.set_fontsize(24)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, dpi=150, transparent=True)
    t_img = Image.open(buf).convert('RGBA')

    # 表上部の透明ピクセル行を自動削除
    arr = np.array(t_img)
    alpha = arr[:, :, 3]
    non_empty_rows = np.where(np.any(alpha > 10, axis=1))[0]
    if len(non_empty_rows) > 0:
        first_row = non_empty_rows[0]
        if first_row > 0:
            t_img = t_img.crop((0, first_row, t_img.width, t_img.height))

    # 看板の作成（固定値）
    b_img = create_banner(b_text, color, 200, 100, -23, 2, t_img.width)

    # 看板と表の間の隙間（表のグループ区切り行と同程度）
    gap = 25

    combined_height = b_img.height + gap + t_img.height
    c_img = Image.new("RGBA", (t_img.width, combined_height), (255, 255, 255, 255))

    c_img.paste(b_img, (0, 0), b_img)
    c_img.paste(t_img, (0, b_img.height + gap), t_img)

    padding = 40
    padded = Image.new("RGBA",
        (c_img.width + padding * 2, c_img.height + padding * 2),
        (255, 255, 255, 255))
    padded.paste(c_img, (padding, padding))
    plt.close(fig)
    return padded

# --- 仕掛けテーブルのみ描画（バナーなし・パディングなし）---
def draw_shikake_table_only(master_rows, h_idx, color):
    row_h_inch = 0.85
    num_rows = len(master_rows)
    fig, ax = plt.subplots(figsize=(14, num_rows * row_h_inch))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.axis('off')
    ax.set_position([0, 0, 1, 1])
    table = ax.table(cellText=master_rows, colWidths=[0.1, 0.2, 0.15, 0.1, 0.1, 0.1, 0.25], loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    for (r, c), cell in table.get_celld().items():
        cell.set_height(1.0 / num_rows)
        txt = cell.get_text()
        txt.set_fontproperties(prop)
        txt.set_verticalalignment('center_baseline')
        txt.set_horizontalalignment('center')
        if r in h_idx:
            cell.set_facecolor(color); cell.set_edgecolor(color)
            txt.set_color('black'); txt.set_fontsize(24); txt.set_weight('bold')
            if c == 3: txt.set_text(master_rows[r][0])
            else: txt.set_text("")
            if c == 0: cell.visible_edges = 'TLB'
            elif c == 6: cell.visible_edges = 'TRB'
            else: cell.visible_edges = 'TB'
        elif (r-1) in h_idx:
            cell.set_facecolor('#333333'); txt.set_color('white'); txt.set_fontsize(18)
        elif master_rows[r] == [""] * 7:
            cell.set_height(0.01); cell.visible_edges = ''
        else:
            cell.set_facecolor('#F9F9F9' if r % 2 == 0 else 'white'); txt.set_fontsize(24)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, dpi=150, transparent=True)
    t_img = Image.open(buf).convert('RGBA')
    plt.close(fig)
    arr = np.array(t_img)
    non_empty_rows = np.where(np.any(arr[:, :, 3] > 10, axis=1))[0]
    if len(non_empty_rows) > 0 and non_empty_rows[0] > 0:
        t_img = t_img.crop((0, non_empty_rows[0], t_img.width, t_img.height))
    return t_img

# --- 機種単体テーブル描画（バナーなし）---
def draw_machine_table(rows, color):
    h_idx = [0]
    row_h_inch = 0.85
    num_rows = len(rows)
    fig, ax = plt.subplots(figsize=(14, num_rows * row_h_inch))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.axis('off')
    ax.set_position([0, 0, 1, 1])
    table = ax.table(cellText=rows, colWidths=[0.1, 0.2, 0.15, 0.1, 0.1, 0.1, 0.25], loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    for (r, c), cell in table.get_celld().items():
        cell.set_height(1.0 / num_rows)
        txt = cell.get_text()
        txt.set_fontproperties(prop)
        txt.set_verticalalignment('center_baseline')
        txt.set_horizontalalignment('center')
        if r in h_idx:
            cell.set_facecolor(color); cell.set_edgecolor(color)
            txt.set_color('black'); txt.set_fontsize(24); txt.set_weight('bold')
            if c == 3: txt.set_text(rows[r][0])
            else: txt.set_text("")
            if c == 0: cell.visible_edges = 'TLB'
            elif c == 6: cell.visible_edges = 'TRB'
            else: cell.visible_edges = 'TB'
        elif (r-1) in h_idx:
            cell.set_facecolor('#333333'); txt.set_color('white'); txt.set_fontsize(18)
        else:
            cell.set_facecolor('#F9F9F9' if r % 2 == 0 else 'white'); txt.set_fontsize(24)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, dpi=150, transparent=True)
    t_img = Image.open(buf).convert('RGBA')
    plt.close(fig)
    arr = np.array(t_img)
    non_empty = np.where(np.any(arr[:, :, 3] > 10, axis=1))[0]
    if len(non_empty) > 0 and non_empty[0] > 0:
        t_img = t_img.crop((0, non_empty[0], t_img.width, t_img.height))
    return t_img

# --- 機種画像付きレポート生成（レポート1/2/4用）---
def draw_report_with_machine_images(machine_sections, color, b_text, images_dict=None):
    gap = 25
    padding = 40
    table_imgs = [draw_machine_table(rows, color) for _, rows in machine_sections]
    canvas_w = max(t.width for t in table_imgs)
    b_img = create_banner(b_text, color, 200, 100, -23, 2, canvas_w)
    parts = [b_img]
    for (dn, _), t_img in zip(machine_sections, table_imgs):
        if t_img.width != canvas_w:
            t_img = t_img.resize((canvas_w, int(t_img.height * canvas_w / t_img.width)), Image.LANCZOS)
        img_bytes = (images_dict or {}).get(dn)
        if img_bytes:
            try:
                raw = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                mach_img = raw.resize((canvas_w, int(raw.height * canvas_w / raw.width)), Image.LANCZOS)
                parts.append(mach_img)
            except:
                pass
        parts.append(t_img)
    total_height = sum(p.height for p in parts) + gap * len(parts)
    result = Image.new("RGBA", (canvas_w, total_height), (255, 255, 255, 255))
    y = 0
    for p in parts:
        result.paste(p, (0, y), p)
        y += p.height + gap
    result = result.crop((0, 0, canvas_w, y - gap))
    padded = Image.new("RGBA", (canvas_w + padding * 2, result.height + padding * 2), (255, 255, 255, 255))
    padded.paste(result, (padding, padding))
    return padded

# --- UI構築 ---
st.title("📊 優秀台レポート作成アプリ")
if rename_dict: st.caption(f"ℹ️ 機種名置換辞書（{len(rename_dict)}件）適用中")

st.header("STEP 1: CSVデータの読み込み")
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=['csv'])

if uploaded_file:
    try:
        try: df = pd.read_csv(uploaded_file, encoding='cp932')
        except: uploaded_file.seek(0); df = pd.read_csv(uploaded_file, encoding='utf-8')
        st.success("✅ CSVを読み込みました")
        col_m_name = next((c for c in df.columns if '機種名' in c), None)
        col_number = next((c for c in df.columns if '台番' in c), None)
        col_diff = next((c for c in df.columns if '差枚' in c), None)
        machine_list = sorted(df[col_m_name].unique().tolist())
        # 新しいCSVが来たら台番をリセット
        _csv_name = uploaded_file.name
        if st.session_state.get('_last_csv') != _csv_name:
            for j in range(7):
                for k in range(10):
                    st.session_state[f"sn_{j}_{k}"] = None
            st.session_state['_last_csv'] = _csv_name

        for sid in ["1", "2", "3", "4", "5"]:
            cfg = FILES[sid]
            st.divider()
            icons = {"1": "🔴", "2": "🔵", "3": "🟡", "4": "🟣", "5": "⚫"}
            st.header(f"{icons[sid]} レポート {sid}")

            c_text, c_btn = st.columns([4, 1])
            with c_text: st.text_input(f"看板{sid}のテキスト", value=st.session_state[f'it{sid}'], key=f"it{sid}", disabled=not st.session_state[f'edit_mode{sid}'])
            with c_btn:
                st.write(" "); st.write(" ")
                if st.button("📝 編集" if not st.session_state[f'edit_mode{sid}'] else "🔒 確定", key=f"eb{sid}"):
                    if st.session_state[f'edit_mode{sid}']: save_text_to_file(st.session_state[f'it{sid}'], cfg["txt"])
                    st.session_state[f'edit_mode{sid}'] = not st.session_state[f'edit_mode{sid}']; st.rerun()

            if sid != "4":
                with st.popover("🎨 背景色"):
                    st.session_state[f'bg_color{sid}'] = st.color_picker(
                        "背景色", st.session_state[f'bg_color{sid}'], key=f"cp{sid}")

            st.image(create_banner(st.session_state[f'it{sid}'], st.session_state[f'bg_color{sid}'],
                                    200, 100, -23, 2, 800), use_container_width=True)

            if sid in ["1", "2", "4"]:
                st.subheader(f"対象機種の管理")
                with st.popover(f"➕ 機種を追加"):
                    new_ts = []
                    new_imgs = {}
                    for i in range(1, 4):
                        m = st.selectbox(f"機種 {i}", ["-- 選択 --"] + machine_list, key=f"m{sid}_{i}", on_change=update_display_name, args=(sid, i))
                        if f"d{sid}_{i}" not in st.session_state: st.session_state[f"d{sid}_{i}"] = ""
                        d = st.text_input(f"表示名 {i}", key=f"d{sid}_{i}")
                        t = st.number_input(f"枚数 {i}", value=1000, step=100, key=f"t{sid}_{i}")
                        img_file = st.file_uploader(f"画像 {i}", type=["jpg","jpeg","png"], key=f"img{sid}_{i}")
                        if m != "-- 選択 --":
                            dn_val = d if d else apply_rename(m)
                            new_ts.append((m, dn_val, t))
                            if img_file:
                                new_imgs[dn_val] = img_file.read()
                        st.divider()
                    if st.button(f"🚀 リストに登録", key=f"btn{sid}"):
                        st.session_state[f'targets{sid}'].extend(new_ts)
                        save_targets_to_file(st.session_state[f'targets{sid}'], cfg["csv"])
                        if new_imgs:
                            st.session_state[f'images{sid}'].update(new_imgs)
                            save_images_to_file(st.session_state[f'images{sid}'], cfg["img"])
                        save_form_state(sid, {str(i): {"m": st.session_state.get(f"m{sid}_{i}", "-- 選択 --"), "d": st.session_state.get(f"d{sid}_{i}", ""), "t": st.session_state.get(f"t{sid}_{i}", 1000)} for i in range(1, 4)})
                        st.rerun()

                if st.session_state[f'targets{sid}']:
                    for i, (cn, dn, t) in enumerate(st.session_state[f'targets{sid}']):
                        has_img = ' 📷' if st.session_state.get(f'images{sid}', {}).get(dn) else ''
                        st.write(f"{i+1}. {dn} ({t}枚以上){has_img}")
                    c_cl, c_ge = st.columns(2)
                    with c_cl:
                        if st.button(f"🗑️ リストをクリア", key=f"clr{sid}"):
                            st.session_state[f'targets{sid}'] = []
                            save_targets_to_file([], cfg["csv"])
                            st.session_state[f'images{sid}'] = {}
                            save_images_to_file({}, cfg["img"])
                            st.rerun()
                    with c_ge:
                        if st.button(f"🔥 レポート画像を生成", key=f"gen{sid}"):
                            machine_sections = []
                            for cn, dn, thr in st.session_state[f'targets{sid}']:
                                m_df = df[df[col_m_name] == cn].copy()
                                e_df = m_df[m_df[col_diff] >= thr].copy().sort_values(col_number)
                                if not e_df.empty:
                                    rows = [[f"{dn} 優秀台"] * 7,
                                            ['台番', '機種名', 'ゲーム数', 'BIG', 'REG', 'AT', '差枚数']]
                                    for _, r in e_df.iterrows():
                                        rows.append([str(int(r[col_number])), dn, f"{int(r.get('G数', 0)):,}G", str(int(r.get('BB', 0))), str(int(r.get('RB', 0))), str(int(r.get('ART', 0))), f"+{int(r[col_diff]):,}枚"])
                                    machine_sections.append((dn, rows))
                            if machine_sections:
                                st.session_state[f'report_img{sid}'] = draw_report_with_machine_images(
                                    machine_sections,
                                    st.session_state[f'bg_color{sid}'],
                                    st.session_state[f'it{sid}'],
                                    images_dict=st.session_state.get(f'images{sid}', {}))

            elif sid == "3":
                # === レポート3: 仕掛けUI ===
                st.subheader("対象機種の管理")
                with st.popover("➕ 機種を追加"):
                    new_ts3 = []
                    new_imgs3 = {}
                    for i in range(1, 4):
                        m = st.selectbox(f"機種 {i}", ["-- 選択 --"] + machine_list, key=f"m{sid}_{i}", on_change=update_display_name, args=(sid, i))
                        if f"d{sid}_{i}" not in st.session_state: st.session_state[f"d{sid}_{i}"] = ""
                        d = st.text_input(f"表示名 {i}", key=f"d{sid}_{i}")
                        img_file = st.file_uploader(f"画像 {i}", type=["jpg","jpeg","png"], key=f"img{sid}_{i}")
                        if m != "-- 選択 --":
                            dn_val = d if d else apply_rename(m)
                            new_ts3.append((m, dn_val, 0))
                            if img_file:
                                new_imgs3[dn_val] = img_file.read()
                        st.divider()
                    if st.button("🚀 リストに登録", key=f"btn{sid}"):
                        st.session_state[f'targets{sid}'].extend(new_ts3)
                        save_targets_to_file(st.session_state[f'targets{sid}'], cfg["csv"])
                        if new_imgs3:
                            st.session_state[f'images{sid}'].update(new_imgs3)
                            save_images_to_file(st.session_state[f'images{sid}'], cfg["img"])
                        save_form_state(sid, {str(i): {"m": st.session_state.get(f"m{sid}_{i}", "-- 選択 --"), "d": st.session_state.get(f"d{sid}_{i}", ""), "t": 0} for i in range(1, 4)})
                        st.rerun()

                if st.session_state[f'targets{sid}']:
                    for i, (cn, dn, _) in enumerate(st.session_state[f'targets{sid}']):
                        has_img = ' 📷' if st.session_state.get(f'images{sid}', {}).get(dn) else ''
                        st.write(f"{i+1}. {dn}{has_img}")
                    if st.button("🗑️ リストをクリア", key=f"clr{sid}"):
                        st.session_state[f'targets{sid}'] = []
                        save_targets_to_file([], cfg["csv"])
                        st.session_state[f'images{sid}'] = {}
                        save_images_to_file({}, cfg["img"])
                        st.rerun()

                st.subheader("対象機種の仕掛け")
                with st.popover("🔧 仕掛けを追加"):
                    components.html("""<script>
(function() {
    const doc = window.parent.document;
    function addEnterHandlers() {
        const inputs = doc.querySelectorAll('input[type="number"]');
        inputs.forEach((input) => {
            if (!input.dataset.enterHandled) {
                input.dataset.enterHandled = 'true';
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        const all = doc.querySelectorAll('input[type="number"]');
                        const idx = Array.from(all).indexOf(e.target);
                        if (idx >= 0 && idx < all.length - 1) all[idx + 1].focus();
                    }
                });
            }
        });
    }
    const observer = new MutationObserver(addEnterHandlers);
    observer.observe(doc.body, { childList: true, subtree: true });
    addEnterHandlers();
})();
</script>""", height=0)
                    for j in range(7):
                        st.markdown(f"**仕掛け{j+1}**")
                        col_input, col_btn = st.columns([4, 1])
                        with col_input:
                            st.text_input("仕掛けの内容", key=f"sc_{j}")
                        with col_btn:
                            st.write("")
                            def make_clear(jj):
                                def clear_sc():
                                    st.session_state[f"sc_{jj}"] = ""
                                    current = list(st.session_state.get('shikake_content3', [''] * 7))
                                    current[jj] = ""
                                    save_shikake_content(current)
                                    st.session_state['shikake_content3'] = current
                                return clear_sc
                            st.button("🗑️ クリア", key=f"clear_sc_{j}", on_click=make_clear(j))
                        row1 = st.columns(5)
                        for k in range(5):
                            with row1[k]:
                                st.number_input(f"台番{k+1}", min_value=0, step=1, value=None, key=f"sn_{j}_{k}")
                        row2 = st.columns(5)
                        for k in range(5):
                            with row2[k]:
                                st.number_input(f"台番{k+6}", min_value=0, step=1, value=None, key=f"sn_{j}_{k+5}")
                        st.divider()
                    if st.button("💾 仕掛けの内容を保存", key="save_shikake3"):
                        content_list = [st.session_state.get(f"sc_{j}", "") for j in range(7)]
                        save_shikake_content(content_list)
                        st.session_state['shikake_content3'] = content_list
                        st.rerun()
                saved = st.session_state.get('shikake_content3', [''] * 7)
                for j, c in enumerate(saved):
                    if c:
                        nums = [st.session_state.get(f"sn_{j}_{k}") for k in range(10)]
                        nums = [n for n in nums if n is not None and int(n) > 0]
                        if nums:
                            num_str = "・".join(str(int(n)) for n in nums)
                            st.markdown(f"- 仕掛け{j+1}: {c}　台番: {num_str}")

                if st.button("🔥 レポートを生成", key=f"gen{sid}"):
                    master_rows, h_idx = [], []
                    for j in range(7):
                        content = st.session_state.get(f"sc_{j}", "")
                        numbers = [int(st.session_state[f"sn_{j}_{k}"])
                                   for k in range(10)
                                   if st.session_state.get(f"sn_{j}_{k}") is not None
                                   and int(st.session_state[f"sn_{j}_{k}"]) > 0]
                        if not content or not numbers:
                            continue
                        m_df = df[df[col_number].isin(numbers)].copy().sort_values(col_number)
                        if m_df.empty:
                            continue
                        h_idx.append(len(master_rows))
                        master_rows.append([content] * 7)
                        master_rows.append(['台番', '機種名', 'ゲーム数', 'BIG', 'REG', 'AT', '差枚数'])
                        for _, r in m_df.iterrows():
                            diff_val = int(r[col_diff])
                            diff_str = f"+{diff_val:,}枚" if diff_val >= 0 else f"{diff_val:,}枚"
                            master_rows.append([
                                str(int(r[col_number])),
                                apply_rename(str(r[col_m_name])),
                                f"{int(r.get('G数', 0)):,}G",
                                str(int(r.get('BB', 0))),
                                str(int(r.get('RB', 0))),
                                str(int(r.get('ART', 0))),
                                diff_str
                            ])
                        master_rows.append([""] * 7)
                    if master_rows:
                        _color3 = st.session_state[f'bg_color{sid}']
                        _text3 = st.session_state[f'it{sid}']
                        _images3 = st.session_state.get(f'images{sid}', {})
                        _targets3 = st.session_state.get(f'targets{sid}', [])
                        t_img3 = draw_shikake_table_only(master_rows, h_idx, _color3)
                        b_img3 = create_banner(_text3, _color3, 200, 100, -23, 2, t_img3.width)
                        parts3 = [b_img3]
                        if _targets3:
                            first_dn = _targets3[0][1]
                            img_bytes3 = _images3.get(first_dn)
                            if img_bytes3:
                                try:
                                    raw3 = Image.open(io.BytesIO(img_bytes3)).convert("RGBA")
                                    mach3 = raw3.resize((t_img3.width, int(raw3.height * t_img3.width / raw3.width)), Image.LANCZOS)
                                    parts3.append(mach3)
                                except:
                                    pass
                        parts3.append(t_img3)
                        gap3 = 25
                        total_h3 = sum(p.height for p in parts3) + gap3 * (len(parts3) - 1)
                        result3 = Image.new("RGBA", (t_img3.width, total_h3), (255, 255, 255, 255))
                        y3 = 0
                        for p3 in parts3:
                            result3.paste(p3, (0, y3), p3)
                            y3 += p3.height + gap3
                        padding3 = 40
                        padded3 = Image.new("RGBA", (result3.width + padding3 * 2, result3.height + padding3 * 2), (255, 255, 255, 255))
                        padded3.paste(result3, (padding3, padding3))
                        st.session_state[f'report_img{sid}'] = padded3

            elif sid == "5":
                # 差枚数TOP10
                st.subheader("差枚数上位10台を自動抽出")
                if st.button("🔥 TOP10レポートを生成", key="gen5"):
                    top10_df = df.sort_values(by=col_diff, ascending=False).head(10).copy()
                    master_rows = [[f"{st.session_state['it5']}"] * 7, ['台番', '機種名', 'ゲーム数', 'BIG', 'REG', 'AT', '差枚数']]
                    h_idx = [0]
                    for _, r in top10_df.iterrows():
                        renamed_m5 = apply_rename(str(r[col_m_name]))
                        diff_val = int(r[col_diff])
                        diff_str = f"+{diff_val:,}枚" if diff_val >= 0 else f"{diff_val:,}枚"
                        master_rows.append([str(int(r[col_number])), renamed_m5, f"{int(r.get('G数', 0)):,}G", str(int(r.get('BB', 0))), str(int(r.get('RB', 0))), str(int(r.get('ART', 0))), diff_str])
                    st.session_state['report_img5'] = draw_table_image(master_rows, h_idx, st.session_state['bg_color5'], st.session_state['it5'], "5")

            if st.session_state[f'report_img{sid}']:
                st.image(st.session_state[f'report_img{sid}'])
                c_img_dl, c_img_cl = st.columns(2)
                with c_img_dl:
                    img_buf = io.BytesIO()
                    st.session_state[f'report_img{sid}'].save(img_buf, format="PNG")
                    img_b64 = base64.b64encode(img_buf.getvalue()).decode()
                    components.html(f"""
<button onclick="copyImg_{sid}()" style="background:#4CAF50;color:white;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;font-size:14px;">✅ 画像をクリップボードに保存</button>
<script>
async function copyImg_{sid}() {{
    const b64 = '{img_b64}';
    const bin = atob(b64); const arr = new Uint8Array(bin.length);
    for (let i=0;i<bin.length;i++) arr[i]=bin.charCodeAt(i);
    const blob = new Blob([arr], {{type:'image/png'}});
    try {{
        await navigator.clipboard.write([new ClipboardItem({{'image/png': blob}})]);
        document.getElementById('msg_{sid}').textContent = 'コピーしました！';
    }} catch(e) {{
        document.getElementById('msg_{sid}').textContent = 'コピー失敗: ' + e.message;
    }}
}}
</script>
<span id="msg_{sid}"></span>
""", height=60)
                with c_img_cl:
                    if st.button(f"🗑️ 画像をクリア", key=f"img_clear{sid}"):
                        st.session_state[f'report_img{sid}'] = None
                        st.rerun()

    except Exception as e: st.error(f"エラー: {e}")
