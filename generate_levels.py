"""
generate_levels_v2.py
─────────────────────
target(N) 곡선에 맞게 보드판 JSON + tblStage 파라미터를 함께 생성.

핵심 로직:
  1. target(N) 계산
  2. 보드판 생성 (board_score ≈ target(N), 반복 시도)
  3. stack_score_target = target(N)*2 - board_score (클리핑)
  4. stack_score_target → tblStage 파라미터 역산
  5. 통합 난이도 = (board_score + stack_score) / 2 ≈ target(N)
"""

import json, random, math, io, zipfile, sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from level_analyzer_v2 import analyze_level

# ════════════════════════════════════════
# 설정
# ════════════════════════════════════════
TOLERANCE = 8.0   # 보드판 허용 오차 (±점)
MAX_TRIES = 10    # 레벨당 최대 시도 횟수

# ════════════════════════════════════════
# 난이도 공식
# ════════════════════════════════════════
LOCAL_VAR = [
    -4.18,-10.77,-9.35,0.77,-12.51,-24.5,16.84,7.51,-23.07,-4.67,
    49.59,28.79,-0.01,-7.79,-21.15,0.89,26.65,31.29,18.55,10.54,
    64.81,44.5,-0.6,26.22,18.69,15.97,18.07,48.05,15.12,46.61,
    -0.1,36.66,9.08,-1.83,-10.36,-9.82,16.77,-5.48,-2.13,0.26,
    -35.93,-12.55,-8.93,8.39,23.32,-11.53,3.89,-13.47,8.79,14.44,
    -19.23,-9.61,-6.62,-0.31,-15.68,-45.8,-17.16,8.99,-15.73,6.0,
    -12.44,-5.44,33.37,7.2,2.44,-12.58,-8.38,22.13,-14.12,-6.12,
    -17.77,-24.71,32.97,-11.54,1.42,-8.55,-1.06,-9.44,7.65,-0.38,
    -34.71,-29.79,-21.23,-26.16,2.33,12.95,-16.47,-34.48,5.62,9.64,
    -15.79,-14.75,44.79,5.4,-39.42,-16.52,-20.26,-44.14,1.36,-8.16
]
LOCAL_MEAN = 3.7109

def target_diff(N: int) -> float:
    b = 70 - 52 * math.exp(-N / 90) + LOCAL_MEAN
    return round(float(np.clip(b + LOCAL_VAR[(N-1) % 100], 0, 100)), 1)

# ════════════════════════════════════════
# 보드판 난이도 점수 (H1 기반)
# ════════════════════════════════════════
W_H1 = {
    'H1_1':(8,True),  'H1_2':(12,True), 'H1_3':(10,True), 'H1_4':(8,True),
    'H1_5':(10,False),'H1_6':(12,False),'H1_7':(12,False),
    'H1_8':(8,False), 'H1_9':(8,False), 'H1_10':(5,False),'H1_11':(5,False),
    'H1_12':(6,False),'H1_13':(4,True), 'H1_14':(4,True), 'H1_15':(4,True),
}
H1_REF = {
    'H1_1':(7,29),  'H1_2':(13,114),'H1_3':(6,20),
    'H1_4':(0,34),  'H1_5':(0,12),  'H1_6':(0,44),
    'H1_7':(0,33),  'H1_8':(0,33),  'H1_9':(0,18),
    'H1_10':(0,28), 'H1_11':(0,8),  'H1_12':(0,2915),
    'H1_13':(0,10), 'H1_14':(0,4),  'H1_15':(0,40),
}
TW_H1 = sum(v[0] for v in W_H1.values())

def board_score(h1: dict) -> float:
    score = 0.0
    for k, (w, inv) in W_H1.items():
        v = h1.get(k, 0)
        lo, hi = H1_REF[k]
        rng = hi - lo if hi > lo else 1
        vn = max(0.0, min(1.0, (v - lo) / rng))
        if inv: vn = 1 - vn
        score += vn * w
    return round(score / TW_H1 * 100, 1)

# ════════════════════════════════════════
# 스택 난이도 점수 역산
# ════════════════════════════════════════
TW_STACK = 82

def _norm(v, lo, hi, inv=False):
    if hi == lo: return 0.0
    n = max(0.0, min(1.0, (v - lo) / (hi - lo)))
    return 1 - n if inv else n

def _denorm(vn, lo, hi, inv=False):
    vn = max(0.0, min(1.0, vn))
    if inv: vn = 1 - vn
    return lo + vn * (hi - lo)

def infer_stack_params(target_score: float, lv: int, tbl_row: pd.Series) -> dict:
    """
    stack_score_target → tblStage 파라미터 역산
    기존 tbl_row의 색상 구성은 유지하고, 숫자 파라미터만 조정
    """
    t = max(0.0, min(100.0, target_score)) / 100.0

    # 역산
    alloc   = int(round(_denorm(t,   10,  300)))
    init_c  = max(1, min(5, int(round(_denorm(t, 1, 5)))))
    dist_c  = round(max(1.0, min(4.0, _denorm(t, 1, 4))), 1)
    dup_r   = round(max(0.1, min(0.8, _denorm(t, 0.1, 0.8, inv=True))), 2)
    prog1   = int(round(max(2, min(alloc-1, _denorm(t, 2, 30, inv=True)))))
    new_c   = max(0, min(5, int(round(_denorm(t, 0, 5)))))
    gimmick = round(max(0.0, min(0.5, _denorm(t, 0, 0.5))), 2)

    # 검증
    s = (_norm(alloc,  10, 300)       * 20 +
         _norm(init_c,  1,   5)       * 12 +
         _norm(dist_c,  1,   4)       * 10 +
         _norm(dup_r, 0.1, 0.8, True) *  8 +
         _norm(prog1,   2,  30, True)  * 10 +
         _norm(new_c,   0,   5)        *  8 +
         _norm(gimmick, 0, 0.5)        * 14)
    actual_stack = round(s / TW_STACK * 100, 1)

    # 색상 풀은 기존 tbl_row 유지 (init_c 수에 맞게 잘라서 사용)
    init_colors_raw = str(tbl_row['InitialAvailableColors']) if not pd.isna(tbl_row['InitialAvailableColors']) else 'Blue,Red'
    init_colors_list = [c.strip() for c in init_colors_raw.split(',') if c.strip()]
    # init_c 수에 맞게 조정
    ALL_COLORS = ['Blue','Red','Yellow','Green','Orange','Purple','White','Black']
    # init_colors_list를 init_c 수에 맞게 조정 (무한루프 방지)
    for c in ALL_COLORS:
        if len(init_colors_list) >= init_c: break
        if c not in init_colors_list:
            init_colors_list.append(c)
    init_colors_list = init_colors_list[:init_c]

    new_colors_raw = str(tbl_row['NewColorsMilestones']) if not pd.isna(tbl_row['NewColorsMilestones']) else ''
    new_colors_list = [c.strip() for c in new_colors_raw.split(',') if c.strip() and c.strip() not in init_colors_list]
    # new_colors_list를 new_c 수에 맞게 조정 (무한루프 방지)
    for c in ALL_COLORS:
        if len(new_colors_list) >= new_c: break
        if c not in init_colors_list and c not in new_colors_list:
            new_colors_list.append(c)
    new_colors_list = new_colors_list[:new_c]

    # ProgressAddNewColor: alloc 내 균등 분배
    if new_c > 0:
        step = alloc / (new_c + 1)
        prog_values = [max(1, int(step * (i+1))) for i in range(new_c)]
        prog_str = ','.join(str(v) for v in prog_values)
    else:
        prog_str = ''

    # DistinctColorCount: 임계값 수+1 개 (마지막 값 = dist_c)
    n_thresholds = new_c + 1
    dist_start = max(1.0, dist_c - 1.0)
    dist_vals = [round(dist_start + (dist_c - dist_start) * i / max(n_thresholds-1, 1), 1)
                 for i in range(n_thresholds)]
    dist_str = ','.join(str(v) for v in dist_vals)

    # ColorDuplicationRate: 전 구간 동일
    dup_str = str(dup_r)

    return {
        'TotalAllocation': alloc,
        'InitialAvailableColors': ','.join(init_colors_list),
        'DistinctColorCount': dist_str,
        'ColorDuplicationRate': dup_str,
        'ProgressAddNewColor': prog_str,
        'NewColorsMilestones': ','.join(new_colors_list),
        'actual_stack_score': actual_stack,
        'gimmick_ratio': gimmick,
    }

# ════════════════════════════════════════
# 보드판 생성 (목표 board_score 맞추기)
# ════════════════════════════════════════
COLOR_MAP = {'Blue':0,'Yellow':1,'Red':2,'Green':3,
             'Orange':4,'Purple':5,'White':6,'Black':7}
TILETYPE  = {'Normal':0,'Blank':1,'Stack':2,'Lock':3,'Plank':4,
             'Ice':5,'StackLock':6,'Grass':7,'Ads':8}
UNLOCK_LV = {'StackLock':29,'Ads':49,'Lock':9,'Plank':59,'Ice':179,'Grass':299}

def _parse_colors(val):
    if pd.isna(val): return []
    return [c.strip() for c in str(val).split(',') if c.strip()]

def _make_hex_board(target_cells, max_dim=8):
    best_r = 1
    for r in range(1, 8):
        if 3*r*r+3*r+1 <= target_cells: best_r = r
        else: break
    r = best_r
    dim = min(2*r+1, max_dim)
    Y, X = dim, dim
    cy, cx = Y//2, X//2
    playable = set()
    for y in range(Y):
        for x in range(X):
            col  = x - (y-(y&1))//2
            cc   = cx - (cy-(cy&1))//2
            dcol = col - cc; drow = y - cy
            if max(abs(dcol), abs(drow), abs(dcol+drow)) <= r:
                playable.add((y, x))
    tiles = [[{'TileType':1} for _ in range(X)] for _ in range(Y)]
    for (y,x) in playable: tiles[y][x] = {'TileType':0}
    return X, Y, tiles, playable

def _build_board(lv, color_ints, board_target, rng, total_alloc):
    # board_target에 따라 파라미터 범위 설정
    t = board_target / 100.0

    # 그리드 크기: 높은 점수 → 작은 보드
    cells_lo = int(15 + (1-t) * 34)
    cells_hi = int(20 + (1-t) * 29)
    target_cells = rng.randint(max(15, cells_lo), min(49, cells_hi))

    X, Y, tiles, playable = _make_hex_board(target_cells)
    pl = list(playable); rng.shuffle(pl)

    # 스택 수: 높은 점수 → 많은 스택
    n_stacks = rng.randint(max(2, int(2 + t*5)), max(3, int(3 + t*4)))
    n_stacks = min(n_stacks, len(pl))

    # 칩 깊이: 높은 점수 → 깊은 칩
    chip_lo = int(2 + t * 4)
    chip_hi = int(4 + t * 4)

    avail = ['Normal', 'Stack']
    for t_type, ul in UNLOCK_LV.items():
        if lv >= ul: avail.append(t_type)

    stack_pos = pl[:n_stacks]
    gimmick_types = [t for t in ['Lock','StackLock','Plank','Ice','Grass','Ads'] if t in avail]
    remaining = [p for p in pl if p not in stack_pos]

    gim_ratio = 0.05 + (board_target / 100) * 0.20
    n_gimmick = min(max(0, int(len(pl) * gim_ratio)), len(remaining))
    gimmick_pos = [(remaining[j], rng.choice(gimmick_types))
                   for j in range(n_gimmick)] if gimmick_types else []

    for (y, x) in stack_pos:
        chips = [rng.choice(color_ints) for _ in range(rng.randint(chip_lo, chip_hi))] if color_ints else [0]
        if 'StackLock' in avail and rng.random() < (0.1 + board_target/200):
            ul = max(1, rng.choice([int(total_alloc*0.3), int(total_alloc*0.5), int(total_alloc*0.7)]))
            tiles[y][x] = {'TileType':TILETYPE['StackLock'],'UnlockLevel':ul,'Stacks':chips}
        else:
            tiles[y][x] = {'TileType':TILETYPE['Stack'],'Stacks':chips}

    for (y, x), ttype in gimmick_pos:
        if ttype == 'Lock':
            tiles[y][x] = {'TileType':TILETYPE['Lock'],
                           'Level':max(1,rng.choice([int(total_alloc*0.3),int(total_alloc*0.6)]))}
        elif ttype == 'Plank':
            tiles[y][x] = {'TileType':TILETYPE['Plank'],'Level':rng.randint(1,4)}
        elif ttype == 'Ice':
            chips = [rng.choice(color_ints) for _ in range(rng.randint(chip_lo,chip_hi))] if color_ints else [0]
            tiles[y][x] = {'TileType':TILETYPE['Ice'],'UnlockLevel':rng.randint(1,3),'Stacks':chips}
        elif ttype == 'StackLock':
            chips = [rng.choice(color_ints) for _ in range(rng.randint(chip_lo,chip_hi))] if color_ints else [0]
            tiles[y][x] = {'TileType':TILETYPE['StackLock'],
                           'UnlockLevel':max(1,int(total_alloc*0.3)),'Stacks':chips}
        elif ttype == 'Grass':
            tiles[y][x] = {'TileType':TILETYPE['Grass']}
        elif ttype == 'Ads':
            tiles[y][x] = {'TileType':TILETYPE['Ads']}

    return {'Timestamp':1778220483778+lv,'GameType':0,
            'GridOrientation':0,'XCells':X,'YCells':Y,'Tiles':tiles}

# ════════════════════════════════════════
# 핵심: 레벨 생성 (보드 + tblStage 함께)
# ════════════════════════════════════════
def generate_level(lv: int, tbl_row: pd.Series) -> tuple:
    """
    returns: (level_data dict, updated_params dict, board_score, stack_score, integrated)
    """
    t = target_diff(lv)

    # 색상 풀
    try: init_c = _parse_colors(tbl_row['InitialAvailableColors'])
    except: init_c = ['Blue','Red']
    try: new_c = _parse_colors(tbl_row['NewColorsMilestones'])
    except: new_c = []
    color_pool = list(dict.fromkeys(init_c + new_c))
    color_ints = [COLOR_MAP[c] for c in color_pool if c in COLOR_MAP]
    try: total_alloc = int(tbl_row['TotalAllocation']) if not pd.isna(tbl_row['TotalAllocation']) else 100
    except: total_alloc = 100

    # 1) 보드판 생성: board_score ≈ target(N)
    best_data  = None
    best_bs    = 50.0
    best_error = float('inf')

    for attempt in range(MAX_TRIES):
        rng = random.Random(42 + lv * 1000 + attempt)
        level_data = _build_board(lv, color_ints, t, rng, total_alloc)
        h1 = analyze_level(level_data)
        bs = board_score(h1)
        error = abs(bs - t)

        if error < best_error:
            best_error = error
            best_data  = level_data
            best_bs    = bs

        # 오차 8점 이내면 조기 종료
        if error <= 8.0:
            break
    # best 무조건 사용 (달성 불가 목표여도 최선값 반환)

    # 2) stack_score_target 역산
    stack_target = max(0.0, min(100.0, t * 2 - best_bs))
    stack_params = infer_stack_params(stack_target, lv, tbl_row)

    # 3) 통합 난이도
    integrated = round((best_bs + stack_params['actual_stack_score']) / 2, 1)

    return best_data, stack_params, best_bs, stack_params['actual_stack_score'], integrated

# ════════════════════════════════════════
# 범위 생성 → zip bytes (JSON만)
# ════════════════════════════════════════
def generate_range_zip(start, end, df_n, callback=None):
    """JSON zip 반환. tblStage 업데이트는 별도 함수로."""
    buf   = io.BytesIO()
    total = end - start + 1

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for lv in range(start, end + 1):
            idx = lv - 1
            row = df_n.iloc[idx] if idx < len(df_n) else df_n.iloc[-1]
            level_data, stack_params, bs, ss, intg = generate_level(lv, row)
            json_bytes = json.dumps(level_data, ensure_ascii=False, indent=2).encode('utf-8')
            zf.writestr(f"N_{lv:03d}.json", json_bytes)
            if callback:
                callback(lv - start + 1, total, lv, bs, ss, intg)

    return buf.getvalue()

# ════════════════════════════════════════
# 500개 전체 생성 (JSON + tblStage 업데이트)
# ════════════════════════════════════════
def generate_all(df_n: pd.DataFrame, out_dir: str, tblstage_path: str = None, callback=None):
    """
    500개 JSON 생성 + tblStage DifficultyScore/파라미터 업데이트
    """
    import openpyxl
    from pathlib import Path

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    results = []

    for lv in range(1, 501):
        idx = lv - 1
        row = df_n.iloc[idx] if idx < len(df_n) else df_n.iloc[-1]
        level_data, stack_params, bs, ss, intg = generate_level(lv, row)

        # JSON 저장
        with open(out / f"N_{lv:03d}.json", 'w', encoding='utf-8') as f:
            json.dump(level_data, f, ensure_ascii=False, indent=2)

        results.append({
            'lv': lv,
            'board_score': bs,
            'stack_score': ss,
            'integrated': intg,
            'target': target_diff(lv),
            **stack_params
        })

        if callback:
            callback(lv, 500, lv, bs, ss, intg)

    return results
