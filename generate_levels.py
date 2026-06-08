"""
generate_levels_v2.py
─────────────────────
target(N) 곡선에 맞게 보드판 JSON + tblStage 파라미터를 함께 생성.
"""

import json, random, math, io, zipfile, sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from level_analyzer_v2 import analyze_level

TOLERANCE = 8.0
MAX_TRIES = 10

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

def target_diff(N):
    b = 70 - 52 * math.exp(-N / 90) + LOCAL_MEAN
    return round(float(np.clip(b + LOCAL_VAR[(N-1) % 100], 0, 100)), 1)

W_H1 = {
    'H1_1':(8,True),'H1_2':(12,True),'H1_3':(10,True),'H1_4':(8,True),
    'H1_5':(10,False),'H1_6':(12,False),'H1_7':(12,False),
    'H1_8':(8,False),'H1_9':(8,False),'H1_10':(5,False),'H1_11':(5,False),
    'H1_12':(6,False),'H1_13':(4,True),'H1_14':(4,True),'H1_15':(4,True),
}
H1_REF = {
    'H1_1':(7,29),'H1_2':(13,114),'H1_3':(6,20),
    'H1_4':(0,34),'H1_5':(0,12),'H1_6':(0,44),
    'H1_7':(0,33),'H1_8':(0,33),'H1_9':(0,18),
    'H1_10':(0,28),'H1_11':(0,8),'H1_12':(0,2915),
    'H1_13':(0,10),'H1_14':(0,4),'H1_15':(0,40),
}
TW_H1 = sum(v[0] for v in W_H1.values())

def board_score(h1):
    score = 0.0
    for k,(w,inv) in W_H1.items():
        v = h1.get(k,0)
        lo,hi = H1_REF[k]
        rng = hi-lo if hi>lo else 1
        vn = max(0.0,min(1.0,(v-lo)/rng))
        if inv: vn = 1-vn
        score += vn*w
    return round(score/TW_H1*100,1)

TW_STACK = 82

def _norm(v,lo,hi,inv=False):
    if hi==lo: return 0.0
    n = max(0.0,min(1.0,(v-lo)/(hi-lo)))
    return 1-n if inv else n

def _denorm(vn,lo,hi,inv=False):
    vn = max(0.0,min(1.0,vn))
    if inv: vn = 1-vn
    return lo+vn*(hi-lo)

def infer_stack_params(target_score, lv, tbl_row):
    t = max(0.0,min(100.0,target_score))/100.0
    alloc   = int(round(_denorm(t,10,300)))
    init_c  = max(1,min(5,int(round(_denorm(t,1,5)))))
    dist_c  = round(max(1.0,min(4.0,_denorm(t,1,4))),1)
    dup_r   = round(max(0.1,min(0.8,_denorm(t,0.1,0.8,inv=True))),2)
    prog1   = int(round(max(2,min(alloc-1,_denorm(t,2,30,inv=True)))))
    new_c   = max(0,min(5,int(round(_denorm(t,0,5)))))
    gimmick = round(max(0.0,min(0.5,_denorm(t,0,0.5))),2)

    s = (_norm(alloc,10,300)*20+_norm(init_c,1,5)*12+_norm(dist_c,1,4)*10+
         _norm(dup_r,0.1,0.8,True)*8+_norm(prog1,2,30,True)*10+
         _norm(new_c,0,5)*8+_norm(gimmick,0,0.5)*14)
    actual_stack = round(s/TW_STACK*100,1)

    # ── 색상 목록은 tbl_row에서 그대로 사용 (generate_level에서 이미 설정됨)
    init_colors_raw = str(tbl_row['InitialAvailableColors']) if not pd.isna(tbl_row['InitialAvailableColors']) else 'Blue,Red'
    init_colors_list = [c.strip() for c in init_colors_raw.split(',') if c.strip()]

    new_colors_raw = str(tbl_row['NewColorsMilestones']) if not pd.isna(tbl_row['NewColorsMilestones']) else ''
    new_colors_list = [c.strip() for c in new_colors_raw.split(',') if c.strip()]

    prog_raw = str(tbl_row['ProgressAddNewColor']) if not pd.isna(tbl_row.get('ProgressAddNewColor', float('nan'))) else ''
    prog_str = prog_raw if prog_raw and prog_raw != 'nan' else ''

    # DistinctColorCount: 구간별 색상 수 증가
    actual_new_c = len(new_colors_list)
    n_thresholds = actual_new_c + 1
    dist_start = max(1.0, dist_c - 1.0)
    dist_vals = [round(dist_start+(dist_c-dist_start)*i/max(n_thresholds-1,1),1) for i in range(n_thresholds)]
    dist_str = ','.join(str(v) for v in dist_vals)

    return {
        'TotalAllocation': alloc,
        'InitialAvailableColors': ','.join(init_colors_list),
        'DistinctColorCount': dist_str,
        'ColorDuplicationRate': str(dup_r),
        'ProgressAddNewColor': prog_str,
        'NewColorsMilestones': ','.join(new_colors_list),
        'actual_stack_score': actual_stack,
        'gimmick_ratio': gimmick,
    }

COLOR_MAP = {'Blue':0,'Yellow':1,'Red':2,'Green':3,'Orange':4,'Purple':5,'White':6,'Black':7}
TILETYPE  = {'Normal':0,'Blank':1,'Stack':2,'Lock':3,'Plank':4,'Ice':5,'StackLock':6,'Grass':7,'Ads':8}
UNLOCK_LV = {'StackLock':29,'Ads':49,'Lock':9,'Plank':59,'Ice':179,'Grass':299}

def _parse_colors(val):
    if pd.isna(val): return []
    return [c.strip() for c in str(val).split(',') if c.strip()]

def _make_hex_board(target_cells, max_dim=5, shape_seed=0):
    """
    5×4 기본 그리드 + shape_seed로 Blank 위치를 다르게 → 판 모양 다양화
    최소 10칸, Normal 60% 보장
    """
    import random as _rnd
    sr = _rnd.Random(shape_seed)

    # 기본 5×4 헥사 그리드 (r=2)
    r = 2
    Y, X = 4, 5
    cy, cx = Y//2, X//2
    playable = set()
    for y in range(Y):
        for x in range(X):
            col  = x - (y-(y&1))//2
            cc   = cx - (cy-(cy&1))//2
            dcol = col - cc; drow = y - cy
            if max(abs(dcol), abs(drow), abs(dcol+drow)) <= r:
                playable.add((y, x))

    # shape_seed 기반으로 가장자리 칸 일부를 Blank로 제거 (모양 다양화)
    # 가장자리: 이웃이 4개 이하인 칸
    def count_neighbors(y, x, pl):
        NEIGH_E = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1)]
        NEIGH_O = [(-1,0),(1,0),(0,-1),(0,1),(1,-1),(1,1)]
        offs = NEIGH_E if y%2==0 else NEIGH_O
        return sum(1 for dy,dx in offs if (y+dy,x+dx) in pl)

    edge_cells = [p for p in playable if count_neighbors(p[0],p[1],playable) <= 3]
    sr.shuffle(edge_cells)

    # shape 타입: 0=원형(제거없음), 1=좌상 제거, 2=우하 제거, 3=좌하 제거
    shape_type = shape_seed % 4
    remove_count = [0, 2, 3, 2][shape_type]
    remove_count = min(remove_count, len(playable)-10)  # 최소 10칸 보장

    to_remove = set()
    if shape_type == 1:  # 좌상 모서리
        candidates = sorted(edge_cells, key=lambda p: p[0]+p[1])[:remove_count*2]
        to_remove = set(sr.sample(candidates, min(remove_count, len(candidates))))
    elif shape_type == 2:  # 우하 모서리
        candidates = sorted(edge_cells, key=lambda p: -(p[0]+p[1]))[:remove_count*2]
        to_remove = set(sr.sample(candidates, min(remove_count, len(candidates))))
    elif shape_type == 3:  # 좌하 모서리
        candidates = sorted(edge_cells, key=lambda p: -p[0]+p[1])[:remove_count*2]
        to_remove = set(sr.sample(candidates, min(remove_count, len(candidates))))

    playable = playable - to_remove

    tiles = [[{'TileType':1} for _ in range(X)] for _ in range(Y)]
    for (y,x) in playable: tiles[y][x] = {'TileType':0}
    return X, Y, tiles, playable

def _build_board(lv, color_ints, init_ints, board_target, rng, total_alloc):
    t = board_target/100.0

    # 판 크기: lv 기반 패턴 + 노이즈로 다양성 확보
    # 19칸(5×4), 22칸(5×4+노이즈), 25칸(5×4 max) 혼합
    lv_var = [19,22,19,25,19,22,25,19,22,19,25,22,19,25,19,22,19,25,22,19]
    base_cells = lv_var[(lv-1) % len(lv_var)]
    target_cells = max(19, min(25, base_cells + rng.randint(-1, 1)))

    X,Y,tiles,playable = _make_hex_board(target_cells, shape_seed=lv*7)
    pl=list(playable); rng.shuffle(pl)

    # Normal 60% 보장: 전체 playable의 최대 40%만 비Normal로 사용
    max_non_normal = max(1, int(len(pl) * 0.40))

    # 스택 수
    n_stacks=rng.randint(max(2,int(2+t*3)),max(3,int(3+t*3)))
    n_stacks=min(n_stacks, max_non_normal)
    n_stacks=min(n_stacks,len(pl))
    chip_lo=int(2+t*4); chip_hi=int(4+t*4)

    avail=['Normal','Stack']
    for t_type,ul in UNLOCK_LV.items():
        if lv>=ul: avail.append(t_type)

    stack_pos=pl[:n_stacks]
    gimmick_types=[t for t in ['Lock','StackLock','Plank','Ice','Grass','Ads'] if t in avail]
    remaining=[p for p in pl if p not in stack_pos]
    # 기믹도 non_normal 예산 안에서 제한
    remaining_budget = max_non_normal - n_stacks
    gim_ratio=0.05+(board_target/100)*0.15
    n_gimmick=min(max(0,int(len(pl)*gim_ratio)), remaining_budget, len(remaining))
    gimmick_pos=[(remaining[j],rng.choice(gimmick_types)) for j in range(n_gimmick)] if gimmick_types else []

    for (y,x) in stack_pos:
        depth = rng.randint(chip_lo,chip_hi)
        chips = [rng.choice(color_ints) for _ in range(depth-1)] + [rng.choice(init_ints)] if color_ints else [0]
        if 'StackLock' in avail and rng.random()<(0.1+board_target/200):
            ul=max(1,rng.choice([int(total_alloc*0.3),int(total_alloc*0.5),int(total_alloc*0.7)]))
            tiles[y][x]={'TileType':TILETYPE['StackLock'],'UnlockLevel':ul,'Stacks':chips}
        else:
            tiles[y][x]={'TileType':TILETYPE['Stack'],'Stacks':chips}

    for (y,x),ttype in gimmick_pos:
        if ttype=='Lock':
            tiles[y][x]={'TileType':TILETYPE['Lock'],'Level':max(1,rng.choice([int(total_alloc*0.3),int(total_alloc*0.6)]))}
        elif ttype=='Plank':
            tiles[y][x]={'TileType':TILETYPE['Plank'],'Level':rng.randint(1,4)}
        elif ttype=='Ice':
            d=rng.randint(chip_lo,chip_hi)
            chips=[rng.choice(color_ints) for _ in range(d-1)]+[rng.choice(init_ints)] if color_ints else [0]
            tiles[y][x]={'TileType':TILETYPE['Ice'],'UnlockLevel':rng.randint(1,3),'Stacks':chips}
        elif ttype=='StackLock':
            d=rng.randint(chip_lo,chip_hi)
            chips=[rng.choice(color_ints) for _ in range(d-1)]+[rng.choice(init_ints)] if color_ints else [0]
            tiles[y][x]={'TileType':TILETYPE['StackLock'],'UnlockLevel':max(1,int(total_alloc*0.3)),'Stacks':chips}
        elif ttype=='Grass':
            tiles[y][x]={'TileType':TILETYPE['Grass']}
        elif ttype=='Ads':
            tiles[y][x]={'TileType':TILETYPE['Ads']}

    return {'Timestamp':1778220483778+lv,'GameType':0,'GridOrientation':0,'XCells':X,'YCells':Y,'Tiles':tiles}

# ── 색상 분포 설정
# 초기 등장 색 수: 2→30%, 3→50%, 4→15%, 5→5%
_INIT_POOL  = [2]*30 + [3]*50 + [4]*15 + [5]*5
# 합계 색 수 (초기+임계치): 3→30%, 4→40%, 5→20%, 6→10%
_TOTAL_POOL = [3]*30 + [4]*40 + [5]*20 + [6]*10
_ALL_COLORS = ['Blue','Red','Yellow','Green','Orange','Purple','White','Black']

def generate_level(lv, tbl_row):
    t = target_diff(lv)

    # ── 색상 수 샘플링 (lv 기반 시드, random() 기반으로 편향 없음)
    color_rng = random.Random(lv * 31337)
    r1 = color_rng.random()
    if r1 < 0.30:   n_init = 2
    elif r1 < 0.80: n_init = 3
    elif r1 < 0.95: n_init = 4
    else:            n_init = 5
    r2 = color_rng.random()
    if r2 < 0.30:   n_total = 3
    elif r2 < 0.70: n_total = 4
    elif r2 < 0.90: n_total = 5
    else:            n_total = 6
    n_total = max(n_total, n_init + 1)  # 임계치 색 최소 1개
    n_total = min(n_total, 8)

    # ── 색상 배분: 8가지 중 n_total개 랜덤 선택
    pool = _ALL_COLORS[:]
    color_rng.shuffle(pool)
    chosen     = pool[:n_total]
    init_c     = chosen[:n_init]
    new_c_list = chosen[n_init:]

    color_ints = [COLOR_MAP[c] for c in chosen if c in COLOR_MAP]
    init_ints  = [COLOR_MAP[c] for c in init_c if c in COLOR_MAP]
    if not color_ints: color_ints = [0, 2]
    if not init_ints:  init_ints  = color_ints

    try: total_alloc = int(tbl_row['TotalAllocation']) if not pd.isna(tbl_row['TotalAllocation']) else 100
    except: total_alloc = 100

    # ── tbl_row 업데이트 (infer_stack_params에서 사용)
    n_new = len(new_c_list)
    prog_vals = []
    if n_new > 0:
        step = total_alloc / (n_new + 1)
        seen = set()
        for i in range(1, n_new + 1):
            v = round(step * i / 10) * 10
            v = max(10, min(v, total_alloc - 10))
            while v in seen: v += 10
            seen.add(v)
            prog_vals.append(v)
    tbl_row = tbl_row.copy()
    tbl_row['InitialAvailableColors'] = ','.join(init_c)
    tbl_row['NewColorsMilestones']    = ','.join(new_c_list)
    tbl_row['ProgressAddNewColor']    = ','.join(str(v) for v in prog_vals)

    best_data=None; best_bs=50.0; best_error=float('inf')
    for attempt in range(MAX_TRIES):
        rng=random.Random(42+lv*1000+attempt)
        level_data=_build_board(lv,color_ints,init_ints,t,rng,total_alloc)
        h1=analyze_level(level_data)
        bs=board_score(h1)
        error=abs(bs-t)
        if error<best_error: best_error=error; best_data=level_data; best_bs=bs
        if error<=8.0: break

    stack_target=max(0.0,min(100.0,t*2-best_bs))
    stack_params=infer_stack_params(stack_target,lv,tbl_row)
    integrated=round((best_bs+stack_params['actual_stack_score'])/2,1)
    return best_data,stack_params,best_bs,stack_params['actual_stack_score'],integrated

def generate_range_zip(start, end, df_n, callback=None):
    buf=io.BytesIO(); total=end-start+1
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as zf:
        for lv in range(start,end+1):
            idx=lv-1
            row=df_n.iloc[idx] if idx<len(df_n) else df_n.iloc[-1]
            level_data,stack_params,bs,ss,intg=generate_level(lv,row)
            zf.writestr(f"N_{lv:03d}.json",json.dumps(level_data,ensure_ascii=False,indent=2).encode('utf-8'))
            if callback: callback(lv-start+1,total,lv,bs,ss,intg)
    return buf.getvalue()
