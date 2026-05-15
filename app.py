import streamlit as st
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import math
import io

st.set_page_config(page_title="Puzzle Creator Dashboard", layout="wide", page_icon="🧩")

# ── 경로
BASE = Path(__file__).parent
LEVELS_DIR = BASE / "data" / "levels"
INTEGRATED_CSV = BASE / "data" / "integrated_difficulty.csv"
TBLSTAGE_PATH = BASE / "data" / "tblStage_500.xlsx"

# ── 색상
COLOR_MAP = {0:'Blue',1:'Yellow',2:'Red',3:'Green',4:'Orange',5:'Purple',6:'White',7:'Black'}
HEX_COLORS = {
    'Normal':'#D0D0D0','Blank':'#1a1a2e','Stack':'#4A90D9',
    'Lock':'#2C2C2C','Plank':'#8B5E3C','Ice':'#A8D8EA',
    'StackLock':'#6A4C93','Grass':'#52C41A','Ads':'#FA8C16',
    'CameraPicture':'#EB2F96',
}
CHIP_COLORS = {
    0:'#1890FF',1:'#FADB14',2:'#F5222D',3:'#52C41A',
    4:'#FA8C16',5:'#722ED1',6:'#FAFAFA',7:'#141414'
}
TILETYPE_NAME = {
    0:'Normal',1:'Blank',2:'Stack',3:'Lock',4:'Plank',
    5:'Ice',6:'StackLock',7:'Grass',8:'Ads',9:'CameraPicture'
}
NEIGH_EVEN = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1)]
NEIGH_ODD  = [(-1,0),(1,0),(0,-1),(0,1),(1,-1),(1,1)]

# ── 헥사 그리드 → Plotly 좌표 변환
def hex_to_pixel(row, col, size=40):
    x = size * math.sqrt(3) * (col + 0.5 * (row % 2))
    y = size * 1.5 * row
    return x, -y

def make_hex_path(cx, cy, size=38):
    pts = []
    for i in range(6):
        angle = math.pi/180 * (60*i - 30)
        pts.append((cx + size*math.cos(angle), cy + size*math.sin(angle)))
    pts.append(pts[0])
    return [p[0] for p in pts], [p[1] for p in pts]

# ── 캐시 로더
@st.cache_data
def load_integrated():
    if INTEGRATED_CSV.exists():
        return pd.read_csv(INTEGRATED_CSV)
    return pd.DataFrame()

@st.cache_data
def load_tblstage():
    if TBLSTAGE_PATH.exists():
        df = pd.read_excel(TBLSTAGE_PATH, sheet_name='Stage', header=0)
        return df[df['LevelName'].str.startswith('N ', na=False)].reset_index(drop=True)
    return pd.DataFrame()

@st.cache_data
def load_level(lv: int):
    path = LEVELS_DIR / f"N_{lv:03d}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None

# ── level_analyzer_v2 인라인 (import 없이 동작하도록 내장)
TILE = {
    0:'Normal',1:'Blank',2:'Stack',3:'Lock',
    4:'Plank',5:'Ice',6:'StackLock',7:'Grass',
    8:'Ads',9:'CameraPicture',
}
NEIGHBORS_EVEN = [(-1,0),(+1,0),(0,-1),(0,+1),(-1,-1),(-1,+1)]
NEIGHBORS_ODD  = [(-1,0),(+1,0),(0,-1),(0,+1),(+1,-1),(+1,+1)]

def open_sides(y, x, tiles, Y, X):
    offsets = NEIGHBORS_EVEN if y % 2 == 0 else NEIGHBORS_ODD
    count = 0
    for dy, dx in offsets:
        ny, nx = y+dy, x+dx
        if 0 <= ny < Y and 0 <= nx < X:
            if tiles[ny][nx].get('TileType', 1) != 1:
                count += 1
    return count

def color_changes(stacks: list) -> int:
    return sum(1 for i in range(1, len(stacks)) if stacks[i] != stacks[i-1])

def analyze_level(data: dict) -> dict:
    Y = data['YCells']
    X = data['XCells']
    tiles = data['Tiles']

    groups = {t: [] for t in TILE.values()}
    for y in range(Y):
        for x in range(X):
            t = tiles[y][x]
            tt = t.get('TileType', 0)
            groups[TILE[tt]].append((y, x, t))

    def side_sum(cell_list):
        return sum(open_sides(y, x, tiles, Y, X) for y, x, _ in cell_list)

    stacks_all = groups['Stack'] + groups['StackLock']

    H1_1  = X * Y
    H1_2  = side_sum(groups['Normal'])
    H1_3  = len(groups['Normal'])
    H1_4  = side_sum(stacks_all)
    H1_5  = len(stacks_all)
    H1_6  = sum(len(t.get('Stacks', [])) for _, _, t in stacks_all)
    H1_7  = sum(color_changes(t.get('Stacks', [])) for _, _, t in stacks_all)
    H1_8  = side_sum(groups['Lock'])
    H1_9  = len(groups['Lock'])
    H1_10 = side_sum(groups['StackLock'])
    H1_11 = len(groups['StackLock'])
    H1_12 = (sum(t.get('Level', 0) for _, _, t in groups['Lock'] + groups['Plank']) +
              sum(t.get('UnlockLevel', 0) for _, _, t in groups['StackLock'] + groups['Ice']))
    H1_13 = side_sum(groups['Ads'])
    H1_14 = min(len(groups['Ads']), 3)
    gimmicks = groups['Plank'] + groups['Ice'] + groups['Grass'] + groups['CameraPicture']
    H1_15 = side_sum(gimmicks)

    return {
        'XCells': X, 'YCells': Y,
        'H1_1':H1_1,'H1_2':H1_2,'H1_3':H1_3,'H1_4':H1_4,'H1_5':H1_5,
        'H1_6':H1_6,'H1_7':H1_7,'H1_8':H1_8,'H1_9':H1_9,'H1_10':H1_10,
        'H1_11':H1_11,'H1_12':H1_12,'H1_13':H1_13,'H1_14':H1_14,'H1_15':H1_15,
        'tile_counts': {k: len(v) for k, v in groups.items()},
    }

# ── 다운로드 헬퍼
def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")

def df_to_json_bytes(df: pd.DataFrame) -> bytes:
    return json.dumps(
        df.to_dict(orient='records'),
        ensure_ascii=False, indent=2
    ).encode("utf-8")

# ── 사이드바
st.sidebar.title("🧩 Puzzle Creator")
tab = st.sidebar.radio("페이지", ["🗺️ 판 모양 뷰어", "📊 난이도 계산기", "📈 난이도 곡선", "🔗 통합 분석"])

# ════════════════════════════════════════
# 탭 1: 판 모양 뷰어
# ════════════════════════════════════════
if tab == "🗺️ 판 모양 뷰어":
    st.title("🗺️ 판 모양 뷰어")

    col1, col2 = st.columns([1, 3])

    with col1:
        # ── 소스 선택
        source = st.radio("데이터 소스", ["레벨 번호로 불러오기", "JSON 파일 업로드"], horizontal=True)
        st.markdown("---")

        data = None

        if source == "레벨 번호로 불러오기":
            lv = st.number_input("레벨 선택", min_value=1, max_value=500, value=1, step=1)
            data = load_level(int(lv))
            if data is None:
                st.warning(f"N_{lv:03d}.json 파일을 찾을 수 없습니다.\nJSON 파일 업로드를 이용해 주세요.")

        else:  # JSON 업로드
            uploaded_json = st.file_uploader(
                "레벨 JSON 파일 업로드",
                type=["json"],
                accept_multiple_files=False,
                help="N_001.json 형식의 레벨 파일을 올려주세요."
            )
            if uploaded_json:
                try:
                    data = json.load(uploaded_json)
                    st.success(f"✅ {uploaded_json.name} 로드 완료")
                except Exception as e:
                    st.error(f"파일 읽기 오류: {e}")

        st.markdown("---")
        show_coord = st.checkbox("좌표 표시", value=False)
        show_chips = st.checkbox("칩 색상 표시", value=True)
        hex_size   = st.slider("헥사 크기", 20, 60, 38)

    if data is not None:
        Y = data['YCells']; X = data['XCells']
        tiles = data['Tiles']

        # 타일 통계
        type_count = {}
        for y in range(Y):
            for x in range(X):
                tt = tiles[y][x].get('TileType', 0)
                name = TILETYPE_NAME.get(tt, str(tt))
                type_count[name] = type_count.get(name, 0) + 1

        with col1:
            st.markdown(f"**보드**: {X}×{Y}")
            st.markdown("**타일 구성**")
            for name, cnt in sorted(type_count.items(), key=lambda x: -x[1]):
                if name != 'Blank':
                    st.markdown(f"- {name}: {cnt}개")

            h1 = analyze_level(data)
            with st.expander("H1 지표"):
                for k in ['H1_1','H1_2','H1_3','H1_5','H1_6','H1_7','H1_9','H1_12','H1_14']:
                    st.markdown(f"**{k}**: {h1[k]}")

            # ── H1 지표 CSV 다운로드
            st.markdown("---")
            h1_export = {k: v for k, v in h1.items() if k != 'tile_counts'}
            h1_df = pd.DataFrame([h1_export])
            st.download_button(
                label="📥 H1 지표 CSV 다운로드",
                data=df_to_csv_bytes(h1_df),
                file_name="h1_metrics.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.download_button(
                label="📥 H1 지표 JSON 다운로드",
                data=df_to_json_bytes(h1_df),
                file_name="h1_metrics.json",
                mime="application/json",
                use_container_width=True
            )

        with col2:
            fig = go.Figure()
            for y in range(Y):
                for x in range(X):
                    tile = tiles[y][x]
                    tt   = tile.get('TileType', 0)
                    name = TILETYPE_NAME.get(tt, 'Normal')
                    if name == 'Blank':
                        continue
                    cx, cy = hex_to_pixel(y, x, hex_size)
                    hx, hy = make_hex_path(cx, cy, hex_size*0.92)
                    color  = HEX_COLORS.get(name, '#CCCCCC')

                    fig.add_trace(go.Scatter(
                        x=hx, y=hy, fill='toself',
                        fillcolor=color, line=dict(color='white', width=1.5),
                        mode='lines', hoverinfo='skip', showlegend=False
                    ))

                    label = name[:2]
                    if name in ('Stack','StackLock','Ice') and 'Stacks' in tile:
                        stacks = tile['Stacks']
                        if show_chips and stacks:
                            label = '+'.join(COLOR_MAP.get(c,'?')[0] for c in stacks[:4])
                        else:
                            label = f"S{len(stacks)}"
                    elif name in ('Lock','Plank') and 'Level' in tile:
                        label = f"L{tile['Level']}"
                    elif name == 'StackLock' and 'UnlockLevel' in tile:
                        label = f"SL{tile['UnlockLevel']}"

                    if show_coord:
                        label = f"({y},{x})\n{label}"

                    fig.add_annotation(
                        x=cx, y=cy, text=label,
                        showarrow=False,
                        font=dict(size=9, color='white' if tt not in (0,) else '#333'),
                        align='center'
                    )

            fig.update_layout(
                height=600, margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(visible=False, scaleanchor='y'),
                yaxis=dict(visible=False),
                plot_bgcolor='#1a1a2e', paper_bgcolor='#1a1a2e',
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════
# 탭 2: 난이도 계산기
# ════════════════════════════════════════
elif tab == "📊 난이도 계산기":
    st.title("📊 난이도 계산기")
    st.caption("Stage 탭 파라미터 기반 난이도 점수 계산 (#Level_Calculator 재현)")

    # ── 데이터 소스 선택
    source2 = st.radio("데이터 소스", ["로컬 파일 사용 (tblStage_500.xlsx)", "Excel 파일 직접 업로드"], horizontal=True)

    tbl = pd.DataFrame()

    if source2 == "로컬 파일 사용 (tblStage_500.xlsx)":
        tbl = load_tblstage()
        if tbl.empty:
            st.warning("tblStage_500.xlsx를 data/ 폴더에 넣어주세요. 또는 파일을 직접 업로드해 주세요.")
    else:
        uploaded_xlsx = st.file_uploader(
            "tblStage Excel 파일 업로드 (.xlsx)",
            type=["xlsx"],
            help="'Stage' 시트가 있고 LevelName 컬럼을 포함한 파일이어야 합니다."
        )
        if uploaded_xlsx:
            try:
                df_raw = pd.read_excel(uploaded_xlsx, sheet_name='Stage', header=0)
                tbl = df_raw[df_raw['LevelName'].str.startswith('N ', na=False)].reset_index(drop=True)
                st.success(f"✅ {uploaded_xlsx.name} 로드 완료 — {len(tbl)}개 레벨")
            except Exception as e:
                st.error(f"파일 읽기 오류: {e}")

    intg = load_integrated()

    if not tbl.empty:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("⚙️ 가중치 설정")
            w_alloc = st.slider("TotalAllocation",    0, 30, 20)
            w_init  = st.slider("초기 색상 수",       0, 20, 12)
            w_dist  = st.slider("스택당 색상 수",     0, 20, 10)
            w_dup   = st.slider("중복 확률 (역수)",   0, 20,  8)
            w_prog  = st.slider("첫 임계값 (역수)",   0, 20, 10)
            w_new   = st.slider("추가 색상 수",       0, 20,  8)
            w_gim   = st.slider("기믹 비율",          0, 20, 14)
            total_w = w_alloc+w_init+w_dist+w_dup+w_prog+w_new+w_gim
            st.metric("총 가중치", f"{total_w} pt")

        def parse_avg(val):
            try:
                parts = [float(x) for x in str(val).split(',')]
                return np.mean(parts)
            except: return 0.0

        def parse_first(val):
            try: return float(str(val).split(',')[0])
            except: return 0.0

        def parse_count(val):
            if pd.isna(val): return 0
            return len([c for c in str(val).split(',') if c.strip()])

        def norm(v, lo, hi, inv=False):
            if hi==lo: return 0.0
            n = max(0.0, min(1.0, (v-lo)/(hi-lo)))
            return 1-n if inv else n

        RANGES = dict(alloc=(10,300),init=(1,5),dist=(1,4),dup=(0.1,0.8),prog=(2,30),new=(0,5))

        scores = []
        for _, row in tbl.iterrows():
            alloc = float(row['TotalAllocation']) if not pd.isna(row['TotalAllocation']) else 0
            init  = parse_count(row['InitialAvailableColors'])
            dist  = parse_avg(row['DistinctColorCount'])
            dup   = parse_avg(row['ColorDuplicationRate'])
            prog  = parse_first(row['ProgressAddNewColor'])
            new_c = parse_count(row['NewColorsMilestones'])
            gim   = sum([float(row.get(c,0) or 0) for c in ['GrassCount','WoodCount','IceCount','TurnCount','CameraPictureCount']])
            gim_r = gim/max(alloc,1)

            s = (norm(alloc,*RANGES['alloc'])*w_alloc +
                 norm(init, *RANGES['init'])*w_init +
                 norm(dist, *RANGES['dist'])*w_dist +
                 norm(dup,  *RANGES['dup'],inv=True)*w_dup +
                 norm(prog, *RANGES['prog'],inv=True)*w_prog +
                 norm(new_c,*RANGES['new'])*w_new +
                 norm(gim_r,0,0.5)*w_gim)
            scores.append(round(s/total_w*100 if total_w>0 else 0, 1))

        tbl['계산_난이도'] = scores

        with col2:
            st.subheader("📋 레벨별 난이도")
            lv_range = st.slider("레벨 범위", 1, len(tbl), (1, min(100, len(tbl))))
            sub = tbl.iloc[lv_range[0]-1:lv_range[1]].copy()
            sub.index = range(lv_range[0], lv_range[1]+1)

            grade_map = lambda d: '매우쉬움' if d<25 else '쉬움' if d<45 else '보통' if d<60 else '어려움' if d<75 else '매우어려움'
            color_map_g = {'매우쉬움':'#1890FF','쉬움':'#52C41A','보통':'#FADB14','어려움':'#FA8C16','매우어려움':'#F5222D'}

            fig = go.Figure()
            x_vals = list(range(lv_range[0], lv_range[1]+1))
            y_vals = sub['계산_난이도'].tolist()
            colors = [color_map_g[grade_map(d)] for d in y_vals]

            fig.add_trace(go.Bar(x=x_vals, y=y_vals, marker_color=colors, name='계산 난이도'))
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=pd.Series(y_vals).rolling(5,center=True,min_periods=1).mean().tolist(),
                mode='lines', line=dict(color='white',width=2), name='이동평균'
            ))
            fig.update_layout(height=400, margin=dict(l=10,r=10,t=10,b=10),
                              plot_bgcolor='#0e1117', paper_bgcolor='#0e1117',
                              font_color='white', xaxis_title='레벨', yaxis_title='난이도',
                              yaxis=dict(range=[0,105]))
            st.plotly_chart(fig, use_container_width=True)

            show_cols = ['LevelName','TotalAllocation','계산_난이도']
            st.dataframe(sub[show_cols].rename(columns={'계산_난이도':'난이도점수'}), height=300)

            # ── 다운로드 (전체 500레벨 기준)
            st.markdown("---")
            full_result = tbl[['LevelName','TotalAllocation','계산_난이도']].copy()
            full_result.columns = ['LevelName','TotalAllocation','난이도점수']
            full_result.insert(0, 'level', range(1, len(full_result)+1))

            st.caption(f"💾 다운로드: 전체 {len(full_result)}개 레벨 / 현재 가중치 기준")
            dcol1, dcol2 = st.columns(2)
            dcol1.download_button(
                label="📥 CSV 다운로드",
                data=df_to_csv_bytes(full_result),
                file_name=f"calculated_difficulty_w{total_w}.csv",
                mime="text/csv",
                use_container_width=True
            )
            dcol2.download_button(
                label="📥 JSON 다운로드",
                data=df_to_json_bytes(full_result),
                file_name=f"calculated_difficulty_w{total_w}.json",
                mime="application/json",
                use_container_width=True
            )

# ════════════════════════════════════════
# 탭 3: 난이도 곡선
# ════════════════════════════════════════
elif tab == "📈 난이도 곡선":
    st.title("📈 난이도 곡선")

    # ── 데이터 소스 선택
    source3 = st.radio("데이터 소스", ["로컬 파일 사용 (integrated_difficulty.csv)", "CSV 파일 직접 업로드"], horizontal=True)

    intg = pd.DataFrame()

    if source3 == "로컬 파일 사용 (integrated_difficulty.csv)":
        intg = load_integrated()
        if intg.empty:
            st.warning("integrated_difficulty.csv를 data/ 폴더에 넣어주세요. 또는 파일을 직접 업로드해 주세요.")
    else:
        uploaded_csv = st.file_uploader(
            "integrated_difficulty CSV 파일 업로드",
            type=["csv"],
            help="board_score, gameplay_score, integrated, integrated_sm 컬럼이 필요합니다."
        )
        if uploaded_csv:
            try:
                intg = pd.read_csv(uploaded_csv)
                st.success(f"✅ {uploaded_csv.name} 로드 완료 — {len(intg)}개 레벨")
            except Exception as e:
                st.error(f"파일 읽기 오류: {e}")

    if not intg.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("평균 통합 난이도", f"{intg['integrated'].mean():.1f}")
        col2.metric("최고점 (레벨)", f"{intg['integrated'].max():.1f} (Lv{intg['integrated'].idxmax()+1})")
        col3.metric("최저점 (레벨)", f"{intg['integrated'].min():.1f} (Lv{intg['integrated'].idxmin()+1})")

        lv_range = st.slider("레벨 범위", 1, len(intg), (1, len(intg)), key='curve_range')
        sub = intg.iloc[lv_range[0]-1:lv_range[1]]
        x   = list(range(lv_range[0], lv_range[1]+1))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=sub['board_score'].tolist(),
                                 mode='lines', name='판 모양 난이도',
                                 line=dict(color='#FA8C16', width=1, dash='dot')))
        fig.add_trace(go.Scatter(x=x, y=sub['gameplay_score'].tolist(),
                                 mode='lines', name='게임 진행 난이도',
                                 line=dict(color='#1890FF', width=1, dash='dot')))
        fig.add_trace(go.Scatter(x=x, y=sub['integrated'].tolist(),
                                 mode='lines', name='통합 원시값',
                                 line=dict(color='#AAAAAA', width=1)))
        fig.add_trace(go.Scatter(x=x, y=sub['integrated_sm'].tolist(),
                                 mode='lines', name='통합 이동평균',
                                 line=dict(color='#52C41A', width=3)))

        fig.update_layout(height=450, margin=dict(l=10,r=10,t=20,b=10),
                          plot_bgcolor='#0e1117', paper_bgcolor='#0e1117',
                          font_color='white', xaxis_title='레벨', yaxis_title='난이도',
                          yaxis=dict(range=[0,105]), legend=dict(orientation='h',y=1.1))
        st.plotly_chart(fig, use_container_width=True)

        # 구간 평균
        st.subheader("구간별 평균")
        zone_size = st.select_slider("구간 크기", [10,25,50,100], value=50)
        total_lv = len(intg)
        zones = []
        for i in range(0, total_lv, zone_size):
            lo2, hi2 = i, min(i+zone_size, total_lv)
            sub2 = intg.iloc[lo2:hi2]
            zones.append({
                '구간': f"Lv{lo2+1}-{hi2}",
                '판 모양': round(sub2['board_score'].mean(),1),
                '게임 진행': round(sub2['gameplay_score'].mean(),1),
                '통합 평균': round(sub2['integrated'].mean(),1),
                '최고': round(sub2['integrated'].max(),1),
                '최저': round(sub2['integrated'].min(),1),
            })
        zone_df = pd.DataFrame(zones)

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=zone_df['구간'], y=zone_df['판 모양'],
                              name='판 모양', marker_color='#FA8C16'))
        fig2.add_trace(go.Bar(x=zone_df['구간'], y=zone_df['게임 진행'],
                              name='게임 진행', marker_color='#1890FF'))
        fig2.add_trace(go.Scatter(x=zone_df['구간'], y=zone_df['통합 평균'],
                                  mode='lines+markers', name='통합 평균',
                                  line=dict(color='#52C41A', width=2)))
        fig2.update_layout(height=350, barmode='group',
                           plot_bgcolor='#0e1117', paper_bgcolor='#0e1117',
                           font_color='white', yaxis=dict(range=[0,100]),
                           margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(zone_df, use_container_width=True)

        # ── 다운로드
        st.markdown("---")
        st.caption("💾 현재 로드된 난이도 데이터 다운로드")
        dcol1, dcol2 = st.columns(2)
        dcol1.download_button(
            label="📥 CSV 다운로드",
            data=df_to_csv_bytes(intg),
            file_name="integrated_difficulty_export.csv",
            mime="text/csv",
            use_container_width=True
        )
        dcol2.download_button(
            label="📥 JSON 다운로드",
            data=df_to_json_bytes(intg),
            file_name="integrated_difficulty_export.json",
            mime="application/json",
            use_container_width=True
        )

# ════════════════════════════════════════
# 탭 4: 통합 분석
# ════════════════════════════════════════
elif tab == "🔗 통합 분석":
    st.title("🔗 통합 분석")

    # ── 데이터 소스 선택
    source4 = st.radio("데이터 소스", ["로컬 파일 사용 (integrated_difficulty.csv)", "CSV 파일 직접 업로드"], horizontal=True)

    intg = pd.DataFrame()

    if source4 == "로컬 파일 사용 (integrated_difficulty.csv)":
        intg = load_integrated()
        if intg.empty:
            st.warning("integrated_difficulty.csv가 없습니다. 또는 파일을 직접 업로드해 주세요.")
    else:
        uploaded_csv4 = st.file_uploader(
            "integrated_difficulty CSV 파일 업로드",
            type=["csv"],
            help="board_score, gameplay_score 컬럼이 필요합니다.",
            key="upload_intg4"
        )
        if uploaded_csv4:
            try:
                intg = pd.read_csv(uploaded_csv4)
                st.success(f"✅ {uploaded_csv4.name} 로드 완료 — {len(intg)}개 레벨")
            except Exception as e:
                st.error(f"파일 읽기 오류: {e}")

    if not intg.empty:
        w_board    = st.slider("판 모양 가중치 (%)", 0, 100, 50)
        w_gameplay = 100 - w_board
        st.caption(f"판 모양 {w_board}% : 게임 진행 {w_gameplay}%")

        custom    = (intg['board_score']*w_board + intg['gameplay_score']*w_gameplay) / 100
        custom_sm = custom.rolling(5, center=True, min_periods=1).mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(range(1,len(intg)+1)), y=custom.tolist(),
                                 mode='lines', name='통합 원시',
                                 line=dict(color='#AAAAAA',width=1)))
        fig.add_trace(go.Scatter(x=list(range(1,len(intg)+1)), y=custom_sm.tolist(),
                                 mode='lines', name='통합 이동평균',
                                 line=dict(color='#52C41A',width=3)))
        fig.add_trace(go.Scatter(x=list(range(1,len(intg)+1)), y=intg['integrated_sm'].tolist(),
                                 mode='lines', name='기존 50:50',
                                 line=dict(color='#1890FF',width=1,dash='dash')))

        fig.update_layout(height=450, plot_bgcolor='#0e1117', paper_bgcolor='#0e1117',
                          font_color='white', xaxis_title='레벨', yaxis_title='난이도',
                          yaxis=dict(range=[0,105]),
                          legend=dict(orientation='h',y=1.1),
                          margin=dict(l=10,r=10,t=30,b=10))
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("평균", f"{custom.mean():.1f}")
        col2.metric("최고", f"{custom.max():.1f} (Lv{custom.idxmax()+1})")
        col3.metric("최저", f"{custom.min():.1f} (Lv{custom.idxmin()+1})")

        # 등급 분포
        grades = pd.cut(custom, bins=[0,25,45,60,75,100],
                        labels=['매우쉬움','쉬움','보통','어려움','매우어려움'])
        grade_cnt = grades.value_counts().sort_index()
        fig3 = px.bar(x=grade_cnt.index, y=grade_cnt.values,
                      color=grade_cnt.index,
                      color_discrete_map={'매우쉬움':'#1890FF','쉬움':'#52C41A',
                                          '보통':'#FADB14','어려움':'#FA8C16','매우어려움':'#F5222D'})
        fig3.update_layout(height=300, showlegend=False,
                           plot_bgcolor='#0e1117', paper_bgcolor='#0e1117',
                           font_color='white', xaxis_title='등급', yaxis_title='개수',
                           margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)

        # ── 다운로드
        st.markdown("---")
        result_df = intg[['board_score','gameplay_score']].copy()
        result_df['custom_integrated'] = custom.round(2)
        result_df['custom_smoothed']   = custom_sm.round(2)
        result_df.insert(0, 'level', range(1, len(result_df)+1))

        st.caption(f"💾 다운로드: 판 모양 {w_board}% : 게임 진행 {w_gameplay}% 기준")
        dcol1, dcol2 = st.columns(2)
        dcol1.download_button(
            label="📥 CSV 다운로드",
            data=df_to_csv_bytes(result_df),
            file_name=f"integrated_w{w_board}_{w_gameplay}.csv",
            mime="text/csv",
            use_container_width=True
        )
        dcol2.download_button(
            label="📥 JSON 다운로드",
            data=df_to_json_bytes(result_df),
            file_name=f"integrated_w{w_board}_{w_gameplay}.json",
            mime="application/json",
            use_container_width=True
        )
