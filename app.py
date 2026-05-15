import streamlit as st
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import math
import io
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Puzzle Creator", layout="wide", page_icon="🧩")

# ══════════════════════════════════════════════════════
# 상수
# ══════════════════════════════════════════════════════
BASE       = Path(__file__).parent
LEVELS_DIR = BASE / "data" / "levels"
INTG_CSV   = BASE / "data" / "integrated_difficulty.csv"
TBLSTAGE   = BASE / "data" / "tblStage_500.xlsx"
ARCHIVE_DIR= BASE / "data" / "archives"

COLOR_MAP  = {0:'Blue',1:'Yellow',2:'Red',3:'Green',4:'Orange',5:'Purple',6:'White',7:'Black'}
HEX_COLORS = {
    'Normal':'#D0D0D0','Blank':'#1a1a2e','Stack':'#4A90D9',
    'Lock':'#5C5C5C','Plank':'#8B5E3C','Ice':'#A8D8EA',
    'StackLock':'#6A4C93','Grass':'#52C41A','Ads':'#FA8C16',
    'CameraPicture':'#EB2F96',
}
CHIP_HEX   = {0:'#1890FF',1:'#FADB14',2:'#F5222D',3:'#52C41A',
              4:'#FA8C16',5:'#722ED1',6:'#FAFAFA',7:'#141414'}
TILETYPE   = {0:'Normal',1:'Blank',2:'Stack',3:'Lock',4:'Plank',
              5:'Ice',6:'StackLock',7:'Grass',8:'Ads',9:'CameraPicture'}
TILE_REV   = {v:k for k,v in TILETYPE.items()}

GITHUB_REPO = "Ahyeong0202/My-Little-Bookstore_Puzzle-Creator"
ARCHIVE_PATH = "data/archives"

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
# ── CSS는 session_state 초기화 이후에 주입 (아래 테마 적용 블록에서 처리)

# ══════════════════════════════════════════════════════
# session_state 초기화
# ══════════════════════════════════════════════════════
for key, default in {
    "intg_df":      None,   # integrated_difficulty.csv
    "tbl_df":       None,   # tblStage_500.xlsx
    "market_df":    None,   # 시장 데이터 CSV
    "level_data":   None,   # 현재 레벨 JSON
    "grid_tiles":   None,   # 3번탭 편집 중 그리드
    "grid_x":       7,
    "grid_y":       7,
    "w_board":      50,     # 판 모양 가중치 %
    "w_gameplay":   50,     # 게임 진행 가중치 %
    "github_token": "",
    "archives":     [],
    "lang":         "한국어",
    "dark_mode":    True,   # 다크모드 기본값
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── 테마 변수 (다크/라이트)
DK = st.session_state.dark_mode
T = {
    "bg":        "#0d1117" if DK else "#ffffff",
    "bg2":       "#161b22" if DK else "#f6f8fa",
    "bg3":       "#21262d" if DK else "#eaeef2",
    "border":    "#30363d" if DK else "#8c959f",
    "text":      "#e6edf3" if DK else "#1f2328",
    "text2":     "#7d8590" if DK else "#656d76",
    "accent":    "#58a6ff" if DK else "#0969da",
    "grid_bg":   "#1a1a2e" if DK else "#f0f4ff",
    "plot_bg":   "#0d1117" if DK else "#ffffff",
    "grid_line": "#21262d" if DK else "#e8ecf0",
}

# ── 동적 CSS 주입
st.markdown(f"""
<style>
/* ── 전체 배경 */
.stApp {{ background-color: {T["bg"]}; color: {T["text"]}; }}
[data-testid="stAppViewContainer"] {{ background-color: {T["bg"]}; }}
[data-testid="stHeader"] {{ background-color: {T["bg"]}; }}

/* ── 사이드바 */
[data-testid="stSidebar"] {{ background: {T["bg2"]}; border-right: 1px solid {T["border"]}; }}
[data-testid="stSidebar"] * {{ color: {T["text"]}; }}

/* ── 입력 위젯 */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div,
[data-testid="stTextArea"] textarea {{
    background-color: {T["bg3"]} !important;
    color: {T["text"]} !important;
    border-color: {T["border"]} !important;
}}

/* ── 카드/섹션 */
.metric-card {{
    background: {T["bg2"]}; border: 1px solid {T["border"]};
    border-radius: 8px; padding: 16px; text-align: center;
}}
.metric-val {{ font-size: 28px; font-weight: 700; color: {T["accent"]}; }}
.metric-lbl {{ font-size: 12px; color: {T["text2"]}; margin-top: 4px; }}

/* ── 뱃지 */
.file-badge {{
    display: inline-block; background: #238636;
    color: white; border-radius: 4px;
    font-size: 11px; padding: 2px 7px; margin: 2px 0;
}}
.file-badge-warn {{
    display: inline-block; background: #9e6a03;
    color: white; border-radius: 4px;
    font-size: 11px; padding: 2px 7px; margin: 2px 0;
}}

/* ── 사이드바 라벨 */
.sidebar-label {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
    color: {T["text2"]}; text-transform: uppercase; margin-bottom: 8px;
}}

/* ── 탭 버튼 */
div[data-testid="stTabs"] button {{ font-size: 14px; }}

/* ── 데이터프레임 */
[data-testid="stDataFrame"] {{ background: {T["bg2"]}; }}

/* ── expander */
[data-testid="stExpander"] {{
    background: {T["bg2"]}; border: 1px solid {T["border"]} !important;
    border-radius: 6px;
}}

/* ── 구분선 */
hr {{ border-color: {T["border"]}; }}

/* ── 파일 업로더 전체 */
[data-testid="stFileUploader"] {{
    background: {T["bg3"]};
    border-radius: 8px;
}}
[data-testid="stFileUploader"] * {{
    color: {T["text"]} !important;
}}
[data-testid="stFileUploader"] label {{
    color: {T["text"]} !important;
    font-weight: 600;
}}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] p,
[data-testid="stFileUploader"] span {{
    color: {T["text2"]} !important;
}}
[data-testid="stFileUploaderDropzone"] {{
    background: {T["bg2"]} !important;
    border: 1.5px dashed {T["border"]} !important;
    border-radius: 6px;
}}
[data-testid="stFileUploaderDropzone"] * {{
    color: {T["text"]} !important;
}}

/* ── 라디오 / 체크박스 / 토글 라벨 */
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label,
[data-testid="stToggle"] label,
.stRadio label, .stCheckbox label {{
    color: {T["text"]} !important;
}}

/* ── selectbox 드롭다운 */
[data-testid="stSelectbox"] label,
[data-testid="stSelectbox"] span,
[data-testid="stNumberInput"] label,
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stSlider"] label {{
    color: {T["text"]} !important;
}}

/* ── 캡션 / 헬프 텍스트 */
[data-testid="stCaptionContainer"] p,
.stCaption {{
    color: {T["text2"]} !important;
}}

/* ── 마크다운 텍스트 */
.stMarkdown p, .stMarkdown li, .stMarkdown h1,
.stMarkdown h2, .stMarkdown h3 {{
    color: {T["text"]};
}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# 헬퍼 함수
# ══════════════════════════════════════════════════════
def df_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")

def df_to_json_bytes(df):
    return json.dumps(df.to_dict(orient='records'), ensure_ascii=False, indent=2).encode("utf-8")

def hex_to_pixel(row, col, size=40):
    # flat-top 헥사, 열(col) 기준 배치
    # 가로: 열마다 size*1.5 간격
    # 세로: 행마다 size*sqrt(3) 간격, 홀수 열은 size*sqrt(3)/2 아래로 offset
    x = size * 1.5 * col
    y = -(size * math.sqrt(3) * row + (size * math.sqrt(3) / 2) * (col % 2))
    return x, y

def make_hex_path(cx, cy, size=38):
    # flat-top: 각도 0°부터 (선이 위아래, 꼭짓점 좌우)
    pts = [(cx + size * math.cos(math.pi / 180 * (60 * i)),
            cy + size * math.sin(math.pi / 180 * (60 * i))) for i in range(6)]
    pts.append(pts[0])
    return [p[0] for p in pts], [p[1] for p in pts]

# ── H1 분석 (level_analyzer_v2 인라인)
NEIGHBORS_EVEN = [(-1,0),(+1,0),(0,-1),(0,+1),(-1,-1),(-1,+1)]
NEIGHBORS_ODD  = [(-1,0),(+1,0),(0,-1),(0,+1),(+1,-1),(+1,+1)]

def open_sides(y, x, tiles, Y, X):
    offsets = NEIGHBORS_EVEN if y%2==0 else NEIGHBORS_ODD
    return sum(1 for dy,dx in offsets
               if 0<=y+dy<Y and 0<=x+dx<X
               and tiles[y+dy][x+dx].get('TileType',1)!=1)

def color_changes(stacks):
    return sum(1 for i in range(1,len(stacks)) if stacks[i]!=stacks[i-1])

def analyze_level(data):
    Y,X = data['YCells'], data['XCells']
    tiles = data['Tiles']
    groups = {t:[] for t in TILETYPE.values()}
    for y in range(Y):
        for x in range(X):
            t  = tiles[y][x]
            tt = t.get('TileType',0)
            groups[TILETYPE[tt]].append((y,x,t))
    def ss(lst): return sum(open_sides(y,x,tiles,Y,X) for y,x,_ in lst)
    sa = groups['Stack']+groups['StackLock']
    return {
        'XCells':X,'YCells':Y,
        'H1_1':X*Y, 'H1_2':ss(groups['Normal']),
        'H1_3':len(groups['Normal']), 'H1_4':ss(sa),
        'H1_5':len(sa),
        'H1_6':sum(len(t.get('Stacks',[])) for _,_,t in sa),
        'H1_7':sum(color_changes(t.get('Stacks',[])) for _,_,t in sa),
        'H1_8':ss(groups['Lock']), 'H1_9':len(groups['Lock']),
        'H1_10':ss(groups['StackLock']), 'H1_11':len(groups['StackLock']),
        'H1_12':(sum(t.get('Level',0) for _,_,t in groups['Lock']+groups['Plank'])+
                 sum(t.get('UnlockLevel',0) for _,_,t in groups['StackLock']+groups['Ice'])),
        'H1_13':ss(groups['Ads']), 'H1_14':min(len(groups['Ads']),3),
        'H1_15':ss(groups['Plank']+groups['Ice']+groups['Grass']+groups['CameraPicture']),
        'tile_counts':{k:len(v) for k,v in groups.items()},
    }

# ── 난이도 공식
def baseline_curve(n_arr):
    return 70 - 52*np.exp(-n_arr/90)

LOCAL_VAR_SEED = [
    3,-2,5,-3,4,-1,6,-4,3,-2,5,-1,4,-3,2,-5,6,-2,3,-4,
    5,-1,4,-3,2,-6,5,-2,4,-1,3,-5,6,-3,2,-4,5,-1,4,-2,
    3,-6,5,-3,4,-1,2,-5,6,-4,3,-2,5,-1,4,-3,6,-2,3,-5,
    4,-1,5,-3,2,-6,4,-2,5,-1,3,-4,6,-2,4,-5,3,-1,5,-3,
    4,-2,6,-1,3,-5,4,-2,5,-3,4,-1,6,-4,2,-5,3,-2,5,-1,
]
def target_curve(n_arr):
    base = baseline_curve(n_arr)
    lv = np.array([LOCAL_VAR_SEED[(int(n)-1)%100] for n in n_arr], dtype=float)
    return np.clip(base + 3.71 + lv, 0, 100)

# ── GitHub 커밋
def github_commit(token, repo, path, content_bytes, message):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code==200 else None
    body = {"message": message, "content": base64.b64encode(content_bytes).decode()}
    if sha: body["sha"] = sha
    resp = requests.put(url, headers=headers, json=body)
    return resp.status_code in (200, 201), resp.json()

# ══════════════════════════════════════════════════════
# 캐시 로더
# ══════════════════════════════════════════════════════
@st.cache_data
def load_intg_local():
    return pd.read_csv(INTG_CSV) if INTG_CSV.exists() else pd.DataFrame()

@st.cache_data
def load_tbl_local():
    if not TBLSTAGE.exists(): return pd.DataFrame()
    df = pd.read_excel(TBLSTAGE, sheet_name='Stage', header=0)
    return df[df['LevelName'].str.startswith('N ', na=False)].reset_index(drop=True)

@st.cache_data
def load_level_local(lv):
    p = LEVELS_DIR/f"N_{lv:03d}.json"
    return json.load(open(p)) if p.exists() else None

# ══════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🧩 Puzzle Creator")
    st.markdown("---")

    # ── 페이지 선택
    st.markdown('<div class="sidebar-label">페이지</div>', unsafe_allow_html=True)
    page = st.radio("", [
        "📖 1. 매뉴얼",
        "📊 2. 난이도 분석",
        "🗺️ 3. 판 모양 뷰어",
        "🔧 4. 설정",
        "🗄️ 5. 아카이브",
    ], label_visibility="collapsed")

    st.markdown("---")

    # ── 파일 업로드
    st.markdown('<div class="sidebar-label">📂 파일 업로드</div>', unsafe_allow_html=True)

    up_intg = st.file_uploader("integrated_difficulty.csv", type=["csv"], key="up_intg")
    if up_intg:
        st.session_state.intg_df = pd.read_csv(up_intg)
        st.markdown('<span class="file-badge">✓ 통합 난이도</span>', unsafe_allow_html=True)
    elif st.session_state.intg_df is None:
        local = load_intg_local()
        if not local.empty:
            st.session_state.intg_df = local
            st.markdown('<span class="file-badge">✓ 통합 난이도 (로컬)</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="file-badge-warn">⚠ 통합 난이도 없음</span>', unsafe_allow_html=True)

    up_tbl = st.file_uploader("tblStage_500.xlsx", type=["xlsx"], key="up_tbl")
    if up_tbl:
        df_raw = pd.read_excel(up_tbl, sheet_name='Stage', header=0)
        st.session_state.tbl_df = df_raw[df_raw['LevelName'].str.startswith('N ', na=False)].reset_index(drop=True)
        st.markdown('<span class="file-badge">✓ tblStage</span>', unsafe_allow_html=True)
    elif st.session_state.tbl_df is None:
        local = load_tbl_local()
        if not local.empty:
            st.session_state.tbl_df = local
            st.markdown('<span class="file-badge">✓ tblStage (로컬)</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="file-badge-warn">⚠ tblStage 없음</span>', unsafe_allow_html=True)

    up_market = st.file_uploader("시장 데이터 CSV", type=["csv"], key="up_market")
    if up_market:
        raw = pd.read_csv(up_market, header=0, skiprows=[1,2])
        raw.columns = raw.columns.str.strip()
        st.session_state.market_df = raw
        st.markdown('<span class="file-badge">✓ 시장 데이터</span>', unsafe_allow_html=True)
    elif st.session_state.market_df is not None:
        st.markdown('<span class="file-badge">✓ 시장 데이터</span>', unsafe_allow_html=True)

    st.markdown("---")

    # ── 다운로드
    st.markdown('<div class="sidebar-label">📥 다운로드</div>', unsafe_allow_html=True)
    intg = st.session_state.intg_df
    if intg is not None:
        st.download_button("CSV — 통합 난이도", df_to_csv_bytes(intg),
                           "integrated_difficulty.csv", "text/csv", use_container_width=True)
        st.download_button("JSON — 통합 난이도", df_to_json_bytes(intg),
                           "integrated_difficulty.json", "application/json", use_container_width=True)
    else:
        st.caption("파일 업로드 후 다운로드 가능")

    st.markdown("---")

    # ── GitHub 토큰
    with st.expander("🔑 GitHub 설정"):
        token_input = st.text_input("Personal Access Token", type="password",
                                    value=st.session_state.github_token)
        if token_input:
            st.session_state.github_token = token_input
        st.caption(f"Repo: {GITHUB_REPO}")

    st.markdown("---")
    # ── 테마 토글
    st.markdown('<div class="sidebar-label">🎨 테마</div>', unsafe_allow_html=True)
    dark_toggle = st.toggle(
        "🌙 다크모드" if DK else "☀️ 라이트모드",
        value=st.session_state.dark_mode,
        key="theme_toggle"
    )
    if dark_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggle
        st.rerun()

    st.markdown("---")
    # ── 언어 (후순위)
    st.markdown('<div class="sidebar-label">🌐 언어 (준비 중)</div>', unsafe_allow_html=True)
    st.toggle("한국어 / English", value=True, disabled=True)

# ══════════════════════════════════════════════════════
# 탭 1 — 매뉴얼
# ══════════════════════════════════════════════════════
if page == "📖 1. 매뉴얼":
    st.title("📖 Puzzle Creator 사용 매뉴얼")
    st.caption("헥사소트 퍼즐 레벨 난이도 설계 & 분석 도구")

    st.markdown("---")

    st.markdown("## 이 앱은 무엇인가요?")
    st.markdown("""
**Puzzle Creator**는 헥사소트(Hexasort) 퍼즐 게임의 레벨 난이도를 **설계하고 분석**하는 통합 도구입니다.

시장 게임 데이터(Lv 1~100 실측값)를 기준선으로 삼아 우리 게임의 판 모양과 스택 구성이
적절한 난이도 곡선을 따르는지 확인하고, 500개 레벨의 파라미터를 관리할 수 있습니다.
    """)

    st.markdown("---")
    st.markdown("## 전체 데이터 흐름")
    st.code("""
시장 데이터 CSV (Lv 1~100 실측 H1 지표)
        ↓  기준선 곡선 도출
   baseline(N) = 70 - 52 × e^(-N/90)
        ↓
우리 게임 목표 난이도 곡선 확정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
N_001~500.json (판 모양)
        ↓  level_analyzer_v2.py
   H1-1 ~ H1-15 지표 추출
        ↓
   board_score (판 모양 난이도, 0~100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
tblStage_500.xlsx (게임 파라미터)
        ↓  DifficultyScore 컬럼
   gameplay_score (게임 진행 난이도, 0~100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
board_score × 50% + gameplay_score × 50%
        ↓
   integrated_difficulty.csv (최종 통합 난이도)
    """, language="")

    st.markdown("---")
    st.markdown("## 탭 안내")
    cols = st.columns(2)
    tabs_info = [
        ("📖 1. 매뉴얼", "지금 보고 계신 페이지입니다. 앱 사용법과 용어를 안내합니다."),
        ("📊 2. 난이도 분석", "시장 데이터 실측값과 우리 게임 통합 난이도를 한 차트에서 비교하고, 판 모양/게임 진행 가중치 비율을 조정합니다."),
        ("🗺️ 3. 판 모양 뷰어", "레벨 JSON 파일을 시각화하고, 새 판을 직접 편집해 JSON으로 저장합니다."),
        ("🔧 4. 설정", "H1 지표별 세부 가중치(%) 조정 및 tblStage 스택 파라미터를 직접 수정합니다."),
        ("🗄️ 5. 아카이브", "설정값을 버전으로 저장하고 GitHub에 자동 커밋합니다. 버전 비교도 가능합니다."),
    ]
    for i, (name, desc) in enumerate(tabs_info):
        with cols[i%2]:
            st.markdown(f"""
<div class="metric-card" style="text-align:left; margin-bottom:12px;">
<strong>{name}</strong><br>
<span style="font-size:13px;color:#8b949e;">{desc}</span>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## 필요한 파일")
    st.markdown("""
| 파일 | 설명 | 사용 탭 |
|---|---|---|
| `integrated_difficulty.csv` | 레벨별 통합 난이도 점수 (board/gameplay/integrated) | 2, 4 |
| `tblStage_500.xlsx` | 스택·게임 파라미터 원본 (Stage 시트) | 2, 4 |
| 시장 데이터 CSV | 경쟁 타이틀 Lv 1~100 H1 실측값 | 2 |
| `N_001.json` ~ `N_500.json` | 레벨별 판 모양 데이터 | 3 |

> **사이드바**에서 파일을 업로드하면 모든 탭에서 유지됩니다.
    """)

    st.markdown("---")
    st.markdown("## 용어 사전")

    with st.expander("TileType — 셀 종류"):
        st.markdown("""
| 코드 | 이름 | 설명 |
|---|---|---|
| 0 | Normal | 일반 빈 셀 |
| 1 | Blank | 비활성 셀 (그리드에서 제외) |
| 2 | Stack | 칩이 쌓인 셀 |
| 3 | Lock | 잠긴 셀 (Level로 해제) |
| 4 | Plank | 나무판 (Level로 해제) |
| 5 | Ice | 얼음 (UnlockLevel로 해제) |
| 6 | StackLock | 잠긴 스택 (UnlockLevel로 해제) |
| 7 | Grass | 잔디 셀 |
| 8 | Ads | 광고 셀 |
| 9 | CameraPicture | 카메라 셀 |
        """)

    with st.expander("H1 지표 — 판 모양 난이도 수치"):
        st.markdown("""
| 지표 | 설명 | 방향 |
|---|---|---|
| H1-1 | 전체 그리드 수 (XCells×YCells) | 많을수록 쉬움 |
| H1-2 | Normal 셀 열린 변 합 | 낮을수록 어려움 |
| H1-3 | Normal 셀 개수 | 적을수록 어려움 |
| H1-4 | Stack+StackLock 열린 변 합 | 낮을수록 어려움 |
| H1-5 | Stack+StackLock 개수 | 많을수록 어려움 |
| H1-6 | 타일 색 총합 | 많을수록 어려움 |
| H1-7 | 색 변화 복잡도 | 많을수록 어려움 |
| H1-8 | Lock 열린 변 합 | 많을수록 어려움 |
| H1-9 | Lock 개수 | 많을수록 어려움 |
| H1-10 | StackLock 열린 변 합 | 많을수록 어려움 |
| H1-11 | StackLock 개수 | 많을수록 어려움 |
| H1-12 | 잠금 해제 기준 합 | 클수록 어려움 |
| H1-13 | Ads 열린 변 합 | 낮을수록 어려움 |
| H1-14 | Ads 수 (최대 3 캡) | 많을수록 쉬움 |
| H1-15 | 기믹 열린 변 합 (Plank/Ice/Grass/Camera) | 낮을수록 어려움 |
        """)

    with st.expander("칩 색상 코드"):
        cols2 = st.columns(4)
        chip_info = [(0,'🔵 Blue','#1890FF'),(1,'🟡 Yellow','#FADB14'),
                     (2,'🔴 Red','#F5222D'),(3,'🟢 Green','#52C41A'),
                     (4,'🟠 Orange','#FA8C16'),(5,'🟣 Purple','#722ED1'),
                     (6,'⬜ White','#AAAAAA'),(7,'⬛ Black','#333333')]
        for i,(code,name,_) in enumerate(chip_info):
            cols2[i%4].markdown(f"**{code}** — {name}")

    with st.expander("난이도 등급"):
        st.markdown("""
| 점수 | 등급 | 색상 |
|---|---|---|
| 0~25 | 매우쉬움 | 🔵 파랑 |
| 25~45 | 쉬움 | 🟢 초록 |
| 45~60 | 보통 | 🟡 노랑 |
| 60~75 | 어려움 | 🟠 주황 |
| 75+ | 매우어려움 | 🔴 빨강 |
        """)

    with st.expander("난이도 곡선 공식"):
        st.markdown(r"""
시장 게임 H1 데이터 통계 분석으로 도출한 공식입니다.

$$\text{baseline}(N) = 70 - 52 \times e^{-N/90}$$

$$\text{target}(N) = \text{baseline}(N) + 3.71 + \text{local\_var}[(N-1) \bmod 100]$$

$$\text{최종값} = \text{clip}(\text{target}, 0, 100)$$

- **Lv 1** ≈ 22pt → **Lv 100** ≈ 57pt → **Lv 200** ≈ 68pt → **~74pt** 수렴
- `local_var`: 시장 게임에서 추출한 100개 오르내림 패턴 반복
        """)

    st.markdown("---")
    st.markdown("## GitHub 저장 안내")
    st.markdown(f"""
5번 탭(아카이브)에서 설정을 저장하면 **{GITHUB_REPO}** 에 자동으로 커밋됩니다.

**최초 설정 (사이드바 → 🔑 GitHub 설정)**
1. GitHub → Settings → Developer Settings → Personal Access Token 발급
2. 권한: `repo` (전체) 체크
3. 발급된 토큰을 사이드바에 입력

저장 경로: `data/archives/YYYYMMDD_HHMMSS.json`
    """)

# ══════════════════════════════════════════════════════
# 탭 2 — 난이도 분석
# ══════════════════════════════════════════════════════
elif page == "📊 2. 난이도 분석":
    st.title("📊 난이도 분석")
    st.caption("시장 데이터 기준선 vs 우리 게임 통합 난이도 비교 + 가중치 조정")

    intg    = st.session_state.intg_df
    market  = st.session_state.market_df

    # ── 상단: 비교 차트
    st.subheader("📈 난이도 곡선 비교")

    n_all   = np.arange(1, 501)
    target  = target_curve(n_all)
    base    = baseline_curve(n_all)

    fig = go.Figure()

    # 목표 곡선 (공식)
    fig.add_trace(go.Scatter(
        x=n_all, y=base, name='기준선 baseline(N)',
        line=dict(color='#58a6ff', width=1.5, dash='dot'), opacity=0.6
    ))
    fig.add_trace(go.Scatter(
        x=n_all, y=target, name='목표 곡선 target(N)',
        line=dict(color='#58a6ff', width=2), opacity=0.9
    ))

    # 시장 데이터 실측
    if market is not None:
        try:
            mk = market.copy()
            mk.columns = [str(c).strip() for c in mk.columns]
            mk = mk[mk['Stage'].apply(lambda x: str(x).strip().lstrip('-').isdigit())]
            mk['Stage'] = mk['Stage'].astype(int)
            # H1 지표로 간이 난이도 점수 계산 (min-max 정규화)
            h_cols = ['H1-2','H1-3 ','H1-4','H1-5','H1-6 ','H1-7 ']
            score_cols = []
            for c in h_cols:
                if c in mk.columns:
                    v = pd.to_numeric(mk[c], errors='coerce').fillna(0)
                    rng = v.max()-v.min()
                    mk[c+'_n'] = (v-v.min())/rng if rng>0 else 0
                    score_cols.append(c+'_n')
            if score_cols:
                mk['market_score'] = mk[score_cols].mean(axis=1)*100
                fig.add_trace(go.Scatter(
                    x=mk['Stage'], y=mk['market_score'],
                    name='시장 데이터 실측 (Lv1~100)',
                    mode='markers+lines',
                    marker=dict(size=5, color='#f78166'),
                    line=dict(color='#f78166', width=1.5, dash='dash')
                ))
        except Exception as e:
            st.warning(f"시장 데이터 파싱 오류: {e}")

    # 우리 게임 통합 난이도
    if intg is not None:
        w_b = st.session_state.w_board
        w_g = st.session_state.w_gameplay
        custom = (intg['board_score']*w_b + intg['gameplay_score']*w_g)/100
        custom_sm = custom.rolling(5, center=True, min_periods=1).mean()
        x_lv = list(range(1, len(intg)+1))
        fig.add_trace(go.Scatter(
            x=x_lv, y=custom.tolist(),
            name='우리 게임 (원시)', line=dict(color='#3fb950', width=1), opacity=0.5
        ))
        fig.add_trace(go.Scatter(
            x=x_lv, y=custom_sm.tolist(),
            name='우리 게임 (이동평균)',
            line=dict(color='#3fb950', width=3)
        ))

    fig.update_layout(
        height=420, plot_bgcolor=T["plot_bg"], paper_bgcolor=T["plot_bg"],
        font_color=T["text"], xaxis_title='레벨', yaxis_title='난이도 점수',
        yaxis=dict(range=[0,105], gridcolor=T["grid_line"]),
        xaxis=dict(gridcolor=T["grid_line"]),
        legend=dict(orientation='h', y=1.12, bgcolor='rgba(0,0,0,0)'),
        margin=dict(l=10,r=10,t=40,b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

    if market is None:
        st.info("💡 사이드바에서 시장 데이터 CSV를 업로드하면 실측값이 차트에 표시됩니다.")
    if intg is None:
        st.info("💡 사이드바에서 integrated_difficulty.csv를 업로드하면 우리 게임 곡선이 표시됩니다.")

    st.markdown("---")

    # ── 중단: 두 탭
    inner_tab1, inner_tab2 = st.tabs(["📋 시장 데이터 원본", "📉 우리 난이도 구간 분석"])

    with inner_tab1:
        if market is None:
            st.warning("사이드바에서 시장 데이터 CSV를 업로드해주세요.")
        else:
            mk_show = market.copy()
            mk_show = mk_show[mk_show['Stage'].apply(lambda x: str(x).strip().lstrip('-').isdigit())]
            st.dataframe(mk_show.reset_index(drop=True), use_container_width=True, height=350)

            # H1 지표별 꺾은선
            st.markdown("**H1 지표별 추이**")
            h1_sel = st.multiselect(
                "표시할 지표",
                ['H1-2','H1-3 ','H1-4','H1-5','H1-6 ','H1-7 ','H1-8 ','H1-9 '],
                default=['H1-5','H1-6 ','H1-7 ']
            )
            if h1_sel:
                fig2 = go.Figure()
                for col in h1_sel:
                    if col in mk_show.columns:
                        vals = pd.to_numeric(mk_show[col], errors='coerce')
                        fig2.add_trace(go.Scatter(
                            x=mk_show['Stage'].astype(int),
                            y=vals, name=col.strip(), mode='lines+markers',
                            marker=dict(size=4)
                        ))
                fig2.update_layout(
                    height=320, plot_bgcolor=T["plot_bg"], paper_bgcolor=T["plot_bg"],
                    font_color=T["text"], xaxis_title='레벨',
                    xaxis=dict(gridcolor=T["grid_line"]), yaxis=dict(gridcolor=T["grid_line"]),
                    legend=dict(orientation='h', y=1.1, bgcolor='rgba(0,0,0,0)'),
                    margin=dict(l=10,r=10,t=30,b=10)
                )
                st.plotly_chart(fig2, use_container_width=True)

    with inner_tab2:
        if intg is None:
            st.warning("사이드바에서 integrated_difficulty.csv를 업로드해주세요.")
        else:
            c1,c2,c3 = st.columns(3)
            c1.markdown(f'<div class="metric-card"><div class="metric-val">{intg["integrated"].mean():.1f}</div><div class="metric-lbl">평균 통합 난이도</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><div class="metric-val">{intg["integrated"].max():.1f}</div><div class="metric-lbl">최고점 (Lv{intg["integrated"].idxmax()+1})</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><div class="metric-val">{intg["integrated"].min():.1f}</div><div class="metric-lbl">최저점 (Lv{intg["integrated"].idxmin()+1})</div></div>', unsafe_allow_html=True)

            st.markdown("")
            zone_size = st.select_slider("구간 크기", [10,25,50,100], value=50)
            zones=[]
            for i in range(0, len(intg), zone_size):
                s2=intg.iloc[i:i+zone_size]
                zones.append({'구간':f"Lv{i+1}-{min(i+zone_size,len(intg))}",
                              '판 모양':round(s2['board_score'].mean(),1),
                              '게임 진행':round(s2['gameplay_score'].mean(),1),
                              '통합 평균':round(s2['integrated'].mean(),1),
                              '최고':round(s2['integrated'].max(),1),
                              '최저':round(s2['integrated'].min(),1)})
            zdf=pd.DataFrame(zones)
            fig3=go.Figure()
            fig3.add_trace(go.Bar(x=zdf['구간'],y=zdf['판 모양'],name='판 모양',marker_color='#fa8c16'))
            fig3.add_trace(go.Bar(x=zdf['구간'],y=zdf['게임 진행'],name='게임 진행',marker_color='#1890ff'))
            fig3.add_trace(go.Scatter(x=zdf['구간'],y=zdf['통합 평균'],mode='lines+markers',name='통합 평균',line=dict(color='#3fb950',width=2)))
            fig3.update_layout(height=300,barmode='group',plot_bgcolor=T["plot_bg"],paper_bgcolor=T["plot_bg"],
                               font_color=T["text"],yaxis=dict(range=[0,100],gridcolor=T["grid_line"]),
                               xaxis=dict(gridcolor=T["grid_line"]),margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig3, use_container_width=True)
            st.dataframe(zdf, use_container_width=True)

    st.markdown("---")

    # ── 하단: 가중치 조정
    st.subheader("⚖️ 가중치 조정")
    if intg is not None:
        w_b = st.slider("판 모양 가중치 (%)", 0, 100, st.session_state.w_board, key="sl_wboard")
        w_g = 100 - w_b
        st.session_state.w_board    = w_b
        st.session_state.w_gameplay = w_g
        st.caption(f"판 모양 **{w_b}%** : 게임 진행 **{w_g}%**")

        custom = (intg['board_score']*w_b + intg['gameplay_score']*w_g)/100
        custom_sm = custom.rolling(5,center=True,min_periods=1).mean()
        result_df = intg[['board_score','gameplay_score']].copy()
        result_df['custom_integrated'] = custom.round(2)
        result_df['custom_smoothed']   = custom_sm.round(2)
        result_df.insert(0,'level',range(1,len(result_df)+1))

        dc1,dc2 = st.columns(2)
        dc1.download_button("📥 CSV 다운로드",df_to_csv_bytes(result_df),
                            f"integrated_w{w_b}_{w_g}.csv","text/csv",use_container_width=True)
        dc2.download_button("📥 JSON 다운로드",df_to_json_bytes(result_df),
                            f"integrated_w{w_b}_{w_g}.json","application/json",use_container_width=True)
    else:
        st.info("integrated_difficulty.csv를 사이드바에서 업로드하면 가중치를 조정할 수 있습니다.")

# ══════════════════════════════════════════════════════
# 탭 3 — 판 모양 뷰어
# ══════════════════════════════════════════════════════
elif page == "🗺️ 3. 판 모양 뷰어":
    st.title("🗺️ 판 모양 뷰어 / JSON 생성기")

    view_tab, edit_tab = st.tabs(["🔍 레벨 뷰어", "✏️ 새 판 편집"])

    # ── 뷰어
    with view_tab:
        col1, col2 = st.columns([1,3])
        with col1:
            src = st.radio("소스", ["레벨 번호","JSON 업로드"], horizontal=True)
            data = None
            if src=="레벨 번호":
                lv = st.number_input("레벨", 1, 500, 1)
                data = load_level_local(int(lv))
                if data is None:
                    st.warning(f"N_{lv:03d}.json 없음 — JSON 업로드 사용")
            else:
                uj = st.file_uploader("JSON 파일", type=["json"], key="uj_view")
                if uj:
                    data = json.load(uj)
                    st.success(f"✅ {uj.name}")

            if data:
                h1 = analyze_level(data)
                st.markdown(f"**보드**: {data['XCells']}×{data['YCells']}")
                with st.expander("타일 구성"):
                    for k,v in h1['tile_counts'].items():
                        if v>0 and k!='Blank':
                            st.markdown(f"- {k}: {v}개")
                with st.expander("H1 지표"):
                    for k in ['H1_1','H1_2','H1_3','H1_5','H1_6','H1_7','H1_9','H1_12','H1_14']:
                        st.markdown(f"**{k}**: {h1[k]}")
                # 단일 레벨 H1 다운로드
                h1e = {k:v for k,v in h1.items() if k!='tile_counts'}
                h1df = pd.DataFrame([h1e])
                st.download_button("📥 H1 CSV",df_to_csv_bytes(h1df),"h1_metrics.csv","text/csv",use_container_width=True)

            show_coord = st.checkbox("좌표 표시",False)
            show_chips = st.checkbox("칩 색상 표시",True)
            hex_size   = st.slider("헥사 크기",20,60,38)

        with col2:
            if data:
                Y,X=data['YCells'],data['XCells']
                tiles=data['Tiles']
                fig=go.Figure()
                for y in range(Y):
                    for x in range(X):
                        tile=tiles[y][x]; tt=tile.get('TileType',0)
                        name=TILETYPE.get(tt,'Normal')
                        if name=='Blank': continue
                        cx,cy=hex_to_pixel(y,x,hex_size)
                        hx,hy=make_hex_path(cx,cy,hex_size*0.92)
                        fig.add_trace(go.Scatter(x=hx,y=hy,fill='toself',
                            fillcolor=HEX_COLORS.get(name,'#CCC'),
                            line=dict(color='white',width=1.5),
                            mode='lines',hoverinfo='skip',showlegend=False))
                        label=name[:2]
                        if name in ('Stack','StackLock','Ice') and 'Stacks' in tile:
                            stacks=tile['Stacks']
                            label='+'.join(COLOR_MAP.get(c,'?')[0] for c in stacks[:4]) if show_chips and stacks else f"S{len(stacks)}"
                        elif name in ('Lock','Plank') and 'Level' in tile:
                            label=f"L{tile['Level']}"
                        elif name=='StackLock' and 'UnlockLevel' in tile:
                            label=f"SL{tile['UnlockLevel']}"
                        if show_coord: label=f"({y},{x})\n{label}"
                        fig.add_annotation(x=cx,y=cy,text=label,showarrow=False,
                            font=dict(size=9,color='white' if tt!=0 else '#333'),align='center')
                fig.update_layout(height=600,margin=dict(l=10,r=10,t=10,b=10),
                    xaxis=dict(visible=False,scaleanchor='y'),yaxis=dict(visible=False),
                    plot_bgcolor=T["grid_bg"],paper_bgcolor=T["grid_bg"],showlegend=False)
                st.plotly_chart(fig,use_container_width=True)
            else:
                st.info("왼쪽에서 레벨을 선택하거나 JSON을 업로드해주세요.")

    # ── 편집기
    with edit_tab:
        st.caption("XCells·YCells 설정 → 행/열로 셀 선택 → 타입 지정 → 셀 적용 → JSON 저장")

        # 그리드 크기 설정
        ec1,ec2,ec3 = st.columns([1,1,2])
        new_x = ec1.number_input("XCells",3,10,st.session_state.grid_x,key="nx")
        new_y = ec2.number_input("YCells",3,10,st.session_state.grid_y,key="ny")
        if ec3.button("🔄 그리드 초기화") or st.session_state.grid_tiles is None \
                or len(st.session_state.grid_tiles)!=new_y \
                or len(st.session_state.grid_tiles[0])!=new_x:
            st.session_state.grid_x = new_x
            st.session_state.grid_y = new_y
            st.session_state.grid_tiles = [[{'TileType':0} for _ in range(new_x)] for _ in range(new_y)]

        tiles_e = st.session_state.grid_tiles
        Y_e, X_e = new_y, new_x

        # ── 메인 레이아웃: 그리드(좌) + 정보패널(우)
        gcol, icol = st.columns([3, 1])

        with icol:
            # ── 셀 선택
            st.markdown("### 📍 셀 선택")
            sel_y = st.number_input("행 (Y, 위→아래)", 0, Y_e-1, 0, key="sel_y")
            sel_x = st.number_input("열 (X, 좌→우)",  0, X_e-1, 0, key="sel_x")

            cur_tile = tiles_e[sel_y][sel_x]
            cur_type = TILETYPE.get(cur_tile.get('TileType', 0), 'Normal')

            st.markdown("---")

            # ── 현재 셀 정보 표시
            st.markdown("### 🔍 현재 셀 정보")
            tile_color = HEX_COLORS.get(cur_type, '#CCC')
            st.markdown(
                f'<div style="background:{tile_color};border-radius:8px;'
                f'padding:8px 12px;margin-bottom:8px;font-weight:700;'
                f'color:{"#333" if cur_type=="Normal" else "white"};font-size:14px;">'
                f'({sel_y}, {sel_x}) — {cur_type}</div>',
                unsafe_allow_html=True
            )

            # 칩 색상 미리보기
            if cur_type in ('Stack', 'StackLock', 'Ice') and 'Stacks' in cur_tile:
                stacks_now = cur_tile['Stacks']
                st.markdown(f"**칩 수**: {len(stacks_now)}개")
                chip_html = ""
                for c in stacks_now:
                    cname = COLOR_MAP.get(c, '?')
                    chex  = CHIP_HEX.get(c, '#888')
                    chip_html += (
                        f'<span style="display:inline-block;background:{chex};'
                        f'color:{"#333" if c in (1,6) else "white"};'
                        f'border-radius:4px;padding:2px 7px;margin:2px;'
                        f'font-size:11px;font-weight:600;">{c} {cname}</span>'
                    )
                st.markdown(chip_html, unsafe_allow_html=True)
            elif cur_type in ('Lock', 'Plank'):
                st.markdown(f"**Level**: {cur_tile.get('Level', 0)}")
            elif cur_type in ('StackLock', 'Ice'):
                st.markdown(f"**UnlockLevel**: {cur_tile.get('UnlockLevel', 0)}")
                if 'Stacks' in cur_tile:
                    st.markdown(f"**칩 수**: {len(cur_tile['Stacks'])}개")

            # 원시 JSON
            with st.expander("raw JSON"):
                st.json(cur_tile)

            st.markdown("---")

            # ── 셀 편집
            st.markdown("### ✏️ 셀 편집")
            new_type = st.selectbox("TileType", [
                'Normal','Blank','Stack','Lock','Plank',
                'Ice','StackLock','Grass','Ads','CameraPicture'
            ], index=list(TILETYPE.values()).index(cur_type), key="sel_type")

            new_stacks, lv_val, ul_val = [], 0, 0

            if new_type in ('Stack', 'StackLock', 'Ice'):
                st.markdown("**칩 색상** (0~7, 콤마구분)")
                # 색상 참조표
                st.markdown(
                    "".join([
                        f'<span style="background:{CHIP_HEX[i]};color:{"#333" if i in (1,6) else "white"};'
                        f'border-radius:3px;padding:1px 5px;margin:1px;font-size:10px;">'
                        f'{i}={COLOR_MAP[i][:3]}</span>'
                        for i in range(8)
                    ]),
                    unsafe_allow_html=True
                )
                stacks_input = st.text_input(
                    "칩 입력",
                    ",".join(map(str, cur_tile.get('Stacks', []))),
                    key="sel_stacks",
                    help="예: 0,1,2,0  → Blue, Yellow, Red, Blue 순서로 쌓임"
                )
                try:
                    new_stacks = [int(s) for s in stacks_input.split(',') if s.strip().isdigit()]
                except:
                    new_stacks = []
                # 입력 미리보기
                if new_stacks:
                    preview_html = "".join([
                        f'<span style="background:{CHIP_HEX.get(c,"#888")};'
                        f'color:{"#333" if c in (1,6) else "white"};'
                        f'border-radius:3px;padding:2px 6px;margin:2px;font-size:11px;">'
                        f'{COLOR_MAP.get(c,"?")}</span>'
                        for c in new_stacks
                    ])
                    st.markdown(preview_html, unsafe_allow_html=True)

            if new_type in ('Lock', 'Plank'):
                lv_val = st.number_input("Level", 0, 9999,
                                         cur_tile.get('Level', 0), key="sel_lv")
            if new_type in ('StackLock', 'Ice'):
                ul_val = st.number_input("UnlockLevel", 0, 9999,
                                          cur_tile.get('UnlockLevel', 0), key="sel_ul")

            if st.button("✅ 셀 적용", use_container_width=True):
                new_cell = {'TileType': TILE_REV[new_type]}
                if new_type in ('Stack', 'StackLock', 'Ice'):
                    new_cell['Stacks'] = new_stacks
                if new_type in ('Lock', 'Plank'):
                    new_cell['Level'] = lv_val
                if new_type in ('StackLock', 'Ice'):
                    new_cell['UnlockLevel'] = ul_val
                st.session_state.grid_tiles[sel_y][sel_x] = new_cell
                st.rerun()

            st.markdown("---")
            # ── JSON 저장
            st.markdown("### 💾 저장")
            fname = st.text_input("파일명", "N_001.json", key="edit_fname")
            json_out = json.dumps({
                "Timestamp": int(datetime.now().timestamp()*1000),
                "GameType": 0, "GridOrientation": 0,
                "XCells": X_e, "YCells": Y_e,
                "Tiles": st.session_state.grid_tiles
            }, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("📥 JSON 다운로드", json_out, fname,
                               "application/json", use_container_width=True)

        # ── 그리드 미리보기 (좌측)
        with gcol:
            fig_e = go.Figure()
            hs = 42
            for y in range(Y_e):
                for x in range(X_e):
                    tile = tiles_e[y][x]
                    tt   = tile.get('TileType', 0)
                    name = TILETYPE.get(tt, 'Normal')
                    cx, cy = hex_to_pixel(y, x, hs)
                    hx, hy = make_hex_path(cx, cy, hs * 0.92)

                    is_sel = (y == sel_y and x == sel_x)
                    fill   = HEX_COLORS.get(name, '#CCC')
                    border_color = '#FFD700' if is_sel else ('#555' if name=='Blank' else 'white')
                    border_w     = 4 if is_sel else 1.5

                    fig_e.add_trace(go.Scatter(
                        x=hx, y=hy, fill='toself',
                        fillcolor=fill,
                        line=dict(color=border_color, width=border_w),
                        mode='lines', hoverinfo='skip', showlegend=False
                    ))

                    # 셀 라벨
                    if name == 'Blank':
                        label = ''
                    elif name in ('Stack', 'StackLock', 'Ice') and 'Stacks' in tile:
                        stacks = tile['Stacks']
                        # 칩 색 이니셜 표시
                        label = '+'.join(COLOR_MAP.get(c,'?')[0] for c in stacks[:3])
                        if len(stacks) > 3:
                            label += f'+{len(stacks)-3}↑'
                    elif name in ('Lock', 'Plank') and 'Level' in tile:
                        label = f"L{tile['Level']}"
                    elif name == 'StackLock' and 'UnlockLevel' in tile:
                        label = f"SL\n{tile['UnlockLevel']}"
                    else:
                        label = name[:2]

                    # 좌표 항상 표시 (편집기에선 유용)
                    coord_label = f"({y},{x})\n{label}"
                    font_color  = 'white' if tt not in (0,) else '#444'

                    fig_e.add_annotation(
                        x=cx, y=cy, text=coord_label,
                        showarrow=False,
                        font=dict(size=9, color=font_color),
                        align='center'
                    )

            fig_e.update_layout(
                height=560,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(visible=False, scaleanchor='y'),
                yaxis=dict(visible=False),
                plot_bgcolor=T["grid_bg"],
                paper_bgcolor=T["grid_bg"],
                showlegend=False
            )
            st.plotly_chart(fig_e, use_container_width=True)

            # 타일 범례
            st.markdown("**타일 범례**")
            legend_html = "".join([
                f'<span style="background:{HEX_COLORS[t]};color:{"#333" if t=="Normal" else "white"};'
                f'border-radius:4px;padding:2px 8px;margin:3px;font-size:11px;display:inline-block;">'
                f'{t}</span>'
                for t in HEX_COLORS if t != 'Blank'
            ])
            st.markdown(legend_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# 탭 4 — 설정
# ══════════════════════════════════════════════════════
elif page == "🔧 4. 설정":
    st.title("🔧 설정")

    set_tab1, set_tab2 = st.tabs(["⚖️ 가중치 세부 설정", "📋 스택 파라미터 수정"])

    # ── 가중치 세부 설정
    with set_tab1:
        st.caption("각 H1 지표의 기여 비율을 설정합니다. 합계가 100%가 되도록 자동 정규화됩니다.")

        H1_INFO = [
            ('H1_1','전체 그리드 수',True),
            ('H1_2','Normal 열린 변 합',True),
            ('H1_3','Normal 개수',True),
            ('H1_4','Stack 열린 변 합',True),
            ('H1_5','Stack 개수',False),
            ('H1_6','타일 색 총합',False),
            ('H1_7','색 변화 복잡도',False),
            ('H1_8','Lock 열린 변 합',False),
            ('H1_9','Lock 개수',False),
            ('H1_10','StackLock 열린 변 합',False),
            ('H1_11','StackLock 개수',False),
            ('H1_12','잠금 해제 기준 합',False),
            ('H1_13','Ads 열린 변 합',True),
            ('H1_14','Ads 수 (최대 3)',True),
            ('H1_15','기믹 열린 변 합',True),
        ]

        if 'h1_weights' not in st.session_state:
            st.session_state.h1_weights = {
                'H1_1':8,'H1_2':12,'H1_3':10,'H1_4':8,'H1_5':10,
                'H1_6':12,'H1_7':12,'H1_8':8,'H1_9':8,'H1_10':5,
                'H1_11':5,'H1_12':6,'H1_13':4,'H1_14':4,'H1_15':4
            }

        total_w = sum(st.session_state.h1_weights.values())
        st.markdown(f"**현재 총합**: {total_w}pt → 각 항목 비율로 환산")

        wc1,wc2 = st.columns(2)
        for i,(key,label,inv) in enumerate(H1_INFO):
            col = wc1 if i%2==0 else wc2
            pct = round(st.session_state.h1_weights[key]/total_w*100,1) if total_w>0 else 0
            new_w = col.slider(
                f"{key} — {label} {'↘역수' if inv else '↗'}",
                0,20,st.session_state.h1_weights[key],key=f"w_{key}"
            )
            st.session_state.h1_weights[key] = new_w
            col.caption(f"비율: **{pct}%**")

        # 실시간 파이 차트
        w_vals = list(st.session_state.h1_weights.values())
        w_keys = list(st.session_state.h1_weights.keys())
        fig_pie = go.Figure(go.Pie(
            labels=w_keys, values=w_vals,
            hole=0.4, textinfo='label+percent',
            textfont=dict(size=10)
        ))
        fig_pie.update_layout(height=350,paper_bgcolor=T["plot_bg"],
                              font_color=T["text"],margin=dict(l=10,r=10,t=10,b=10),
                              showlegend=False)
        st.plotly_chart(fig_pie,use_container_width=True)

        # 가중치를 적용한 난이도 곡선 미리보기
        intg = st.session_state.intg_df
        if intg is not None:
            st.markdown("**가중치 적용 시 난이도 곡선 미리보기**")
            w_b = st.session_state.w_board
            w_g = st.session_state.w_gameplay
            custom = (intg['board_score']*w_b + intg['gameplay_score']*w_g)/100
            custom_sm = custom.rolling(5,center=True,min_periods=1).mean()
            fig_prev=go.Figure()
            fig_prev.add_trace(go.Scatter(x=list(range(1,len(intg)+1)),y=custom_sm.tolist(),
                name='통합 이동평균',line=dict(color='#3fb950',width=2)))
            fig_prev.add_trace(go.Scatter(x=np.arange(1,501),y=target_curve(np.arange(1,501)),
                name='목표 곡선',line=dict(color='#58a6ff',width=1.5,dash='dash'),opacity=0.6))
            fig_prev.update_layout(height=280,plot_bgcolor=T["plot_bg"],paper_bgcolor=T["plot_bg"],
                font_color=T["text"],xaxis_title='레벨',
                xaxis=dict(gridcolor=T["grid_line"]),yaxis=dict(range=[0,105],gridcolor=T["grid_line"]),
                legend=dict(orientation='h',y=1.1,bgcolor='rgba(0,0,0,0)'),
                margin=dict(l=10,r=10,t=30,b=10))
            st.plotly_chart(fig_prev,use_container_width=True)

        # 가중치 설정 JSON 다운로드
        w_config = {"h1_weights": st.session_state.h1_weights,
                    "w_board": st.session_state.w_board,
                    "w_gameplay": st.session_state.w_gameplay}
        st.download_button("📥 가중치 설정 JSON 다운로드",
                           json.dumps(w_config,ensure_ascii=False,indent=2).encode(),
                           "weight_config.json","application/json",use_container_width=True)

    # ── 스택 파라미터 수정
    with set_tab2:
        tbl = st.session_state.tbl_df
        if tbl is None:
            st.warning("사이드바에서 tblStage_500.xlsx를 업로드해주세요.")
        else:
            st.caption("셀을 클릭해 직접 수정할 수 있습니다. 수정 후 Excel로 다운로드하세요.")
            show_cols = st.multiselect(
                "표시할 컬럼",
                tbl.columns.tolist(),
                default=[c for c in ['LevelName','TotalAllocation','InitialAvailableColors',
                                     'DistinctColorCount','ColorDuplicationRate',
                                     'ProgressAddNewColor','NewColorsMilestones','DifficultyScore']
                         if c in tbl.columns]
            )
            if show_cols:
                edited = st.data_editor(tbl[show_cols], use_container_width=True, height=500,
                                        num_rows="fixed")
                # 수정된 내용 session_state 반영
                for col in show_cols:
                    st.session_state.tbl_df[col] = edited[col]

                # CSV 다운로드
                st.download_button("📥 CSV 다운로드",df_to_csv_bytes(edited),
                                   "tblStage_edited.csv","text/csv",use_container_width=True)

# ══════════════════════════════════════════════════════
# 탭 5 — 아카이브
# ══════════════════════════════════════════════════════
elif page == "🗄️ 5. 아카이브":
    st.title("🗄️ 아카이브")
    st.caption("설정값을 버전으로 저장하고 GitHub에 자동 커밋합니다.")

    ac1, ac2 = st.columns([1,1])

    with ac1:
        st.subheader("💾 현재 설정 저장")
        version_name = st.text_input("버전명", f"v_{datetime.now().strftime('%Y%m%d_%H%M')}")
        version_memo = st.text_area("메모", placeholder="예: H1-7 강화 테스트, board 가중치 60%로 조정")

        save_payload = {
            "version": version_name,
            "memo": version_memo,
            "timestamp": datetime.now().isoformat(),
            "w_board": st.session_state.w_board,
            "w_gameplay": st.session_state.w_gameplay,
            "h1_weights": st.session_state.get('h1_weights', {}),
        }
        payload_bytes = json.dumps(save_payload, ensure_ascii=False, indent=2).encode("utf-8")

        st.download_button("📥 로컬에 저장 (JSON)", payload_bytes,
                           f"{version_name}.json","application/json",use_container_width=True)

        st.markdown("")
        if st.button("☁️ GitHub에 커밋", use_container_width=True):
            token = st.session_state.github_token
            if not token:
                st.error("사이드바 → 🔑 GitHub 설정에서 토큰을 먼저 입력해주세요.")
            else:
                path = f"{ARCHIVE_PATH}/{version_name}.json"
                with st.spinner("GitHub에 커밋 중..."):
                    ok, resp = github_commit(
                        token, GITHUB_REPO, path, payload_bytes,
                        f"archive: {version_name} — {version_memo[:50]}"
                    )
                if ok:
                    st.success(f"✅ 커밋 완료! `{path}`")
                    st.session_state.archives.append(save_payload)
                else:
                    st.error(f"❌ 커밋 실패: {resp.get('message','')}")

    with ac2:
        st.subheader("📂 버전 불러오기")
        up_archive = st.file_uploader("저장된 버전 JSON 업로드", type=["json"], key="up_arch")
        if up_archive:
            arch = json.load(up_archive)
            st.json(arch)
            if st.button("이 버전으로 복원"):
                st.session_state.w_board    = arch.get('w_board', 50)
                st.session_state.w_gameplay = arch.get('w_gameplay', 50)
                if 'h1_weights' in arch:
                    st.session_state.h1_weights = arch['h1_weights']
                st.success(f"✅ {arch.get('version','')} 복원 완료!")
                st.rerun()

    st.markdown("---")

    # 이번 세션 저장 기록
    if st.session_state.archives:
        st.subheader("📋 이번 세션 저장 기록")
        arch_df = pd.DataFrame([{
            '버전': a['version'],
            '저장 시각': a['timestamp'][:19],
            '판 모양 %': a['w_board'],
            '게임 진행 %': a['w_gameplay'],
            '메모': a['memo'],
        } for a in st.session_state.archives])
        st.dataframe(arch_df, use_container_width=True)

        # 버전 비교
        if len(st.session_state.archives) >= 2:
            st.subheader("📊 버전 비교 (난이도 곡선)")
            intg = st.session_state.intg_df
            if intg is not None:
                sel_versions = st.multiselect("비교할 버전 선택 (최대 3개)",
                    [a['version'] for a in st.session_state.archives],
                    default=[a['version'] for a in st.session_state.archives[-2:]])
                fig_cmp=go.Figure()
                colors=['#58a6ff','#f78166','#3fb950','#d2a8ff']
                for i,vname in enumerate(sel_versions[:3]):
                    arch_v = next((a for a in st.session_state.archives if a['version']==vname),None)
                    if arch_v:
                        wb=arch_v['w_board']; wg=arch_v['w_gameplay']
                        c=(intg['board_score']*wb+intg['gameplay_score']*wg)/100
                        cs=c.rolling(5,center=True,min_periods=1).mean()
                        fig_cmp.add_trace(go.Scatter(
                            x=list(range(1,len(intg)+1)),y=cs.tolist(),
                            name=f"{vname} (board:{wb}%)",
                            line=dict(color=colors[i],width=2)
                        ))
                fig_cmp.update_layout(height=350,plot_bgcolor=T["plot_bg"],paper_bgcolor=T["plot_bg"],
                    font_color=T["text"],xaxis_title='레벨',
                    xaxis=dict(gridcolor=T["grid_line"]),yaxis=dict(range=[0,105],gridcolor=T["grid_line"]),
                    legend=dict(orientation='h',y=1.1,bgcolor='rgba(0,0,0,0)'),
                    margin=dict(l=10,r=10,t=30,b=10))
                st.plotly_chart(fig_cmp,use_container_width=True)
            else:
                st.info("integrated_difficulty.csv를 사이드바에서 업로드하면 곡선 비교가 가능합니다.")
