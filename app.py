import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request

# --- ページ設定 ---
st.set_page_config(page_title="スロット優秀台レポート作成", layout="centered")

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

# ==========================================
# セッション状態の初期化
# ==========================================
FILES = {
    "1": {"csv": "targets1_data.csv", "txt": "banner_text1.txt", "def_txt": "週間おススメ機種", "color": "#FF0000"},
    "2": {"csv": "targets2_data.csv", "txt": "banner_text2.txt", "def_txt": "月間おススメ機種", "color": "#007BFF"},
    "3": {"csv": "targets3_data.csv", "txt": "banner_text3.txt", "def_txt": "1月の新台", "color": "#28A745"},
    "4": {"csv": None, "txt": "banner_text4.txt", "def_txt": "差玉TOP10", "color": "#000000"}
}

for sid, cfg in FILES.items():
    s_ext = "" if sid == "1" else sid
    if f'it{sid}' not in st.session_state: 
        st.session_state[f'it{sid}'] = load_text_from_file(cfg["txt"], cfg["def_txt"])
    if f'edit_mode{sid}' not in st.session_state: st.session_state[f'edit_mode{sid}'] = False
    if f'bg_color{sid}' not in st.session_state: st.session_state[f'bg_color{sid}'] = cfg["color"]
    if cfg["csv"] and f'targets{sid}' not in st.session_state: 
        st.session_state[f'targets{sid}'] = load_targets_from_file(cfg["csv"])
    if f'report_img{sid}' not in st.session_state: st.session_state[f'report_img{sid}'] = None
    
    design_defaults = {'b_height': 100, 'f_size': 50, 'y_adj': -12, 'thickness': 1}
    for key, val in design_defaults.items():
        full_key = f"{key}{s_ext}"
        if full_key not in st.session_state:
            st.session_state[full_key] = val

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
    t_img = Image.open(buf)
    
    # 看板の作成
    b_img = create_banner(b_text, color, st.session_state[f'b_height{suffix}'], st.session_state[f'f_size{suffix}'], st.session_state[f'y_adj{suffix}'], st.session_state[f'thickness{suffix}'], t_img.width)
    
    # 【B案：物理的に2px重ねる修正】
    overlap = 6 # ここで重ねる量を指定
    
    # キャンバスサイズを重ねる分だけ少し短くする
    combined_height = b_img.height + t_img.height - overlap
    c_img = Image.new("RGBA", (t_img.width, combined_height), (255, 255, 255, 255))
    
    # 1. 看板を先に貼る
    c_img.paste(b_img, (0, 0), b_img)
    # 2. 表を「看板の底辺 - overlap」の位置に貼る（看板の下に表が潜り込む形）
    c_img.paste(t_img, (0, b_img.height - overlap), t_img)
    
    plt.close(fig); return c_img

# --- UI構築 (変更なし) ---
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

        for sid in ["1", "2", "3", "4"]:
            s_ext = "" if sid == "1" else sid
            cfg = FILES[sid]
            st.divider()
            icons = {"1": "🔴", "2": "🔵", "3": "🟢", "4": "⚫"}
            st.header(f"{icons[sid]} レポート {sid}")
            
            c_text, c_btn = st.columns([4, 1])
            with c_text: st.text_input(f"看板{sid}のテキスト", value=st.session_state[f'it{sid}'], key=f"it{sid}", disabled=not st.session_state[f'edit_mode{sid}'])
            with c_btn:
                st.write(" "); st.write(" ")
                if st.button("📝 編集" if not st.session_state[f'edit_mode{sid}'] else "🔒 確定", key=f"eb{sid}"):
                    if st.session_state[f'edit_mode{sid}']: save_text_to_file(st.session_state[f'it{sid}'], cfg["txt"])
                    st.session_state[f'edit_mode{sid}'] = not st.session_state[f'edit_mode{sid}']; st.rerun()

            with st.popover(f"⚙️ デザイン微調整"):
                st.session_state[f'bg_color{sid}'] = st.color_picker("背景色", st.session_state[f'bg_color{sid}'], key=f"cp{sid}")
                st.slider("縦幅", 50, 400, value=st.session_state[f'b_height{s_ext}'], key=f"b_height{s_ext}")
                st.slider("サイズ", 10, 200, value=st.session_state[f'f_size{s_ext}'], key=f"f_size{s_ext}")
                st.slider("位置", -100, 100, value=st.session_state[f'y_adj{s_ext}'], key=f"y_adj{s_ext}")
                st.slider("太さ", 0, 10, value=st.session_state[f'thickness{s_ext}'], key=f"thickness{s_ext}")
            
            st.image(create_banner(st.session_state[f'it{sid}'], st.session_state[f'bg_color{sid}'], st.session_state[f'b_height{s_ext}'], st.session_state[f'f_size{s_ext}'], st.session_state[f'y_adj{s_ext}'], st.session_state[f'thickness{s_ext}'], 800), use_container_width=True)

            if sid != "4":
                st.subheader(f"対象機種の管理")
                with st.popover(f"➕ 機種を追加"):
                    new_ts = []
                    for i in range(1, 4):
                        m = st.selectbox(f"機種 {i}", ["-- 選択 --"] + machine_list, key=f"m{sid}_{i}", on_change=update_display_name, args=(sid, i))
                        if f"d{sid}_{i}" not in st.session_state: st.session_state[f"d{sid}_{i}"] = ""
                        d = st.text_input(f"表示名 {i}", key=f"d{sid}_{i}")
                        t = st.number_input(f"枚数 {i}", value=1000, step=100, key=f"t{sid}_{i}")
                        if m != "-- 選択 --": new_ts.append((m, d if d else apply_rename(m), t))
                    if st.button(f"🚀 リストに登録", key=f"btn{sid}"):
                        st.session_state[f'targets{sid}'].extend(new_ts); save_targets_to_file(st.session_state[f'targets{sid}'], cfg["csv"]); st.rerun()

                if st.session_state[f'targets{sid}']:
                    for i, (cn, dn, t) in enumerate(st.session_state[f'targets{sid}']): st.write(f"{i+1}. {dn} ({t}枚以上)")
                    c_cl, c_ge = st.columns(2)
                    with c_cl: 
                        if st.button(f"🗑️ リストをクリア", key=f"clr{sid}"): st.session_state[f'targets{sid}'] = []; save_targets_to_file([], cfg["csv"]); st.rerun()
                    with c_ge:
                        if st.button(f"🔥 レポート画像を生成", key=f"gen{sid}"):
                            master_rows, h_idx = [], []
                            for cn, dn, thr in st.session_state[f'targets{sid}']:
                                m_df = df[df[col_m_name] == cn].copy()
                                e_df = m_df[m_df[col_diff] >= thr].copy().sort_values(col_number)
                                if not e_df.empty:
                                    h_idx.append(len(master_rows))
                                    master_rows.append([f"{dn} 優秀台"] * 7)
                                    master_rows.append(['台番', '機種名', 'ゲーム数', 'BIG', 'REG', 'AT', '差枚数'])
                                    for _, r in e_df.iterrows():
                                        master_rows.append([str(int(r[col_number])), dn, f"{int(r.get('G数', 0)):,}G", str(int(r.get('BB', 0))), str(int(r.get('RB', 0))), str(int(r.get('ART', 0))), f"+{int(r[col_diff]):,}枚"])
                                    master_rows.append([""] * 7)
                            if master_rows: st.session_state[f'report_img{sid}'] = draw_table_image(master_rows, h_idx, st.session_state[f'bg_color{sid}'], st.session_state[f'it{sid}'], s_ext)
            
            else: # レポート4
                st.subheader("差枚数上位10台を自動抽出")
                if st.button("🔥 TOP10レポートを生成", key="gen4"):
                    top10_df = df.sort_values(by=col_diff, ascending=False).head(10).copy()
                    master_rows = [[f"{st.session_state.it4}"] * 7, ['台番', '機種名', 'ゲーム数', 'BIG', 'REG', 'AT', '差枚数']]
                    h_idx = [0]
                    for _, r in top10_df.iterrows():
                        renamed_m4 = apply_rename(str(r[col_m_name]))
                        master_rows.append([str(int(r[col_number])), renamed_m4, f"{int(r.get('G数', 0)):,}G", str(int(r.get('BB', 0))), str(int(r.get('RB', 0))), str(int(r.get('ART', 0))), f"+{int(r[col_diff]):,}枚"])
                    st.session_state.report_img4 = draw_table_image(master_rows, h_idx, st.session_state.bg_color4, st.session_state.it4, "4")

            if st.session_state[f'report_img{sid}']:
                st.image(st.session_state[f'report_img{sid}'])
                c_img_dl, c_img_cl = st.columns(2)
                with c_img_dl:
                    out = io.BytesIO(); st.session_state[f'report_img{sid}'].convert("RGB").save(out, format="JPEG", quality=95)
                    st.download_button(f"✅ 画像を保存", out.getvalue(), f"report{sid}.jpg", "image/jpeg", key=f"dl{sid}")
                with c_img_cl:
                    if st.button(f"🗑️ 画像をクリア", key=f"img_clear{sid}"):
                        st.session_state[f'report_img{sid}'] = None
                        st.rerun()

    except Exception as e: st.error(f"エラー: {e}")
