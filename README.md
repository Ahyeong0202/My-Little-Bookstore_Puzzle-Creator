# 🧩 Puzzle Creator — My Little Bookstore

> **Automated Hexasort Puzzle Difficulty Design System**
> 헥사소트 퍼즐 레벨 난이도 설계 자동화 시스템

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://my-little-bookstorepuzzle-creator-ebmpaoaz3dupvmmmhdfm3m.streamlit.app)
![Python](https://img.shields.io/badge/Python-3.10+-brown?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.58-brown?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-brown)

---

## 📖 Overview

**Puzzle Creator** is an interactive web dashboard for designing and analyzing level difficulty in *My Little Bookstore*, a hexasort puzzle + bookstore management mobile game developed at **SKKU Game Center Lab** in collaboration with NYU under the RISE program.

### What is Hexasort?

Hexasort is a mobile puzzle genre where players sort colored chips stacked on hexagonal tiles by matching colors. Difficulty is determined by two components:

| Component | Description |
|---|---|
| **Board Layout** | Tile count, stack positions, locked tiles, gimmick placement |
| **Gameplay Parameters** | Allocation target, color pool, duplication rate, unlock timing |

### Why was this built?

| Problem | Previous Approach | Puzzle Creator |
|---|---|---|
| Generate 500 levels | Manual PowerPoint work per level | Auto-generation via difficulty formula |
| No objective difficulty standard | Subjective designer judgment | Real-world market data analysis |
| Can't preview board layouts | Open JSON files manually | Interactive hex grid visualization |
| Hard to tune difficulty weights | Edit code & re-run | Real-time slider adjustment |

---

## 🏗️ System Architecture

```
① Market Data Analysis
   market_lv1_100.csv  ←  SKKU Game Center Lab (real-world Lv 1~100 data)
         ↓  Extract H1-1~H1-15 indicators + weighted sum
   board_score  →  Derive difficulty curve pattern
         ↓
   target(N) = (70 − 52 × e^(−N/90)) + 3.71 + local_var[(N−1) mod 100]

② Automated Level Generation  (generate_levels.py)
   target(N) as difficulty goal
         ↓  Retry board generation (max 10 attempts)
   board_score ≈ target(N)
         ↓
   stack_score_target = target(N) × 2 − board_score  →  tblStage params
         ↓
   Integrated Difficulty = (board_score + stack_score) / 2  ≈  target(N)

③ Visualization & Validation  (this app)
   JSON + tblStage  →  Curve comparison / Board preview / Regeneration
```

---

## 📊 Real-World Data

The difficulty curve is derived from **real gameplay data** collected by the SKKU Game Center Lab:

- **Source**: Top-ranked hexasort puzzle game on the Korean mobile market
- **Coverage**: Levels 1–100, manually played and recorded
- **Metrics**: 15 board-level indicators (H1-1 ~ H1-15)
  - Grid count, stack positions, open-side sums, lock counts, gimmick ratios, color complexity, etc.
- **Limitation**: In-game stack parameters (tblStage equivalent) were not collectible from competitor titles → gameplay weights are heuristic-based, pending validation with post-launch play data

---

## 🖥️ App Features

### 🏠 Home
- Game introduction with hero banner (BG / Icon / Logo assets)
- Gameplay video preview
- 18-slide animated game introduction gallery

### 📖 1. Manual
- Full system overview with data pipeline
- Background: what hexasort is, why this tool was needed
- File structure guide and JSON update workflow
- Glossary: TileType codes, H1 indicators, tblStage parameters, difficulty grades

### 📊 2. Difficulty Analysis
- Market data raw table (Lv 1~100 H1 indicators)
- Board score vs gameplay score vs target(N) curve comparison
- **Stacked bar chart**: board contribution + gameplay contribution per level range
- Real-time weight slider (board % / gameplay %)

### 🗺️ 3. Board Viewer
- Hexagonal grid visualization of JSON board layouts
- Three source modes: Level number / Difficulty filter / JSON upload
- Edit mode: click tiles to change type → real-time H1 recalculation
- Live difficulty score + grade display (매우쉬움 ~ 매우어려움)
- H1 CSV export

### 🎲 4. JSON Generator
- Level range selector with difficulty curve preview
- Real-time generation progress with per-level difficulty display
- ZIP download of generated JSON files

### 🔧 5. Settings
- **H1 Weight Sliders**: Adjust 15 board indicator weights with pie chart
- **tblStage Weight Sliders**: Adjust 7 gameplay parameter weights with curve preview
- **Stack Parameter Editor**: Direct edit of tblStage_500 values

### 🗄️ 6. Archive
- Save and version-control weight configurations to GitHub

---

## 📁 Repository Structure

```
My-Little-Bookstore_Puzzle-Creator/
├── app.py                          # Main Streamlit application
├── generate_levels.py              # Level JSON + tblStage auto-generation
├── level_analyzer_v2.py            # JSON → H1 indicator extractor
├── requirements.txt
├── data/
│   ├── market/
│   │   └── market_lv1_100.csv      # Real-world market data (SKKU Lab)
│   ├── levels/
│   │   └── N_001.json ~ N_500.json # Generated board layout files
│   ├── tblStage_500.xlsx           # Gameplay parameters (500 stages)
│   └── integrated_difficulty.csv   # Computed integrated difficulty scores
└── assets/
    ├── images/
    │   ├── BG.png / Icon.png / Logo.png / Title.png
    │   └── 01.png ~ 18.png         # Game introduction slides
    └── videos/
        └── Hexasort Puzzle.mp4     # Gameplay demo video
```

---

## 🚀 Getting Started

### Local Setup

```bash
git clone https://github.com/Ahyeong0202/My-Little-Bookstore_Puzzle-Creator.git
cd My-Little-Bookstore_Puzzle-Creator
pip install -r requirements.txt
streamlit run app.py
```

### Updating Level JSONs

**Method A — Via App (Recommended)**
1. Open `🎲 4. JSON Generator` tab
2. Select level range with slider
3. Click **Generate** → watch real-time difficulty display
4. Download ZIP → upload to `data/levels/` on GitHub

**Method B — Direct Script**
```python
import json, pandas as pd
from generate_levels import generate_level, target_diff

df = pd.read_excel('data/tblStage_500.xlsx', sheet_name='Stage')
df_n = df[df['LevelName'].str.startswith('N ', na=False)].reset_index(drop=True)

for lv in range(1, 501):
    level_data, stack_params, bs, ss, intg = generate_level(lv, df_n.iloc[lv-1])
    with open(f'data/levels/N_{lv:03d}.json', 'w') as f:
        json.dump(level_data, f, ensure_ascii=False, indent=2)
```

---

## 📐 Difficulty Formula

$$\text{target}(N) = \underbrace{(70 - 52 \times e^{-N/90})}_{\text{base curve}} + 3.71 + \text{local\_var}[(N-1) \bmod 100]$$

- **Base curve**: Exponential convergence — Lv1 ≈ 18pt → Lv100 ≈ 48pt → ~74pt ceiling
- **local_var**: 100-value oscillation pattern extracted from market data (repeats every 100 levels)
- **Integrated difficulty**: `board_score × w% + gameplay_score × (100-w)%` ≈ `target(N)`

---

## 🔄 Iteration Plan

```
Current: Market data-based design (heuristic gameplay weights)
       ↓
Post-launch: Collect real play data (clear rate, attempt count)
       ↓
Validate & correct difficulty weights objectively
       ↓
Regenerate 500+ levels with improved curve
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.10+ | Core logic |
| Streamlit | Web dashboard |
| Plotly | Interactive charts |
| pandas / openpyxl | Data processing |
| GitHub | Version control + Streamlit Cloud deployment |

---

## 👤 Author

**심아영 (Shim Ahyeong)** · 영상학과 2021311066  
SKKU Game Center Lab · Sungkyunkwan University  
Developed with AI assistance (Claude)

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.
