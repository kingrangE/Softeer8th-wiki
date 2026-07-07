"""
render.py  —  Word Cloud 3중 뷰 렌더링
=====================================
radar.db(mentions)를 읽어 포지셔닝/추이 중심의 3개 뷰 + 경쟁 비교 막대를 그린다.

  뷰1  마인드셰어 클라우드      : 전체 DE 기술 share-of-voice
  뷰2  US vs KR 비교           : 국가별 share-of-voice(정규화) 좌우 패널  ← 국내 포함의 핵심 가치
  뷰3  모멘텀 델타             : 분기 share 변화(상승=빨강/하락=파랑)   ← "추이"의 핵심
  (+)  경쟁 기술 막대          : Snowflake/Databricks/BigQuery/Redshift US vs KR

토큰은 모두 영문 canonical(Snowflake, Airflow…)이라 한글 폰트가 필요 없다.
정직한 한계: 뷰3의 분기는 '열린 공고의 게시 분기'라 완전한 시계열이 아니다(라벨 명시).
"""

import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
from wordcloud import WordCloud

from de_lexicon import (WAREHOUSE_COMPETITORS, MODERN_STACK, LEGACY_STACK,
                        COMMODITY_TECH, all_job_categories)
from radar_util import DB_PATH, OUT_DIR, ensure_dirs
from analyze import crawl_summary

# 부트캠프 커리큘럼 관점 기본값: 분기·직무 워드클라우드가 볼 3개 분기
CURRICULUM_QUARTERS = ("2025-Q4", "2026-Q1", "2026-Q2")
_CMAP_BY_COUNTRY = {"KR": "Reds", "US": "Blues"}

# --- 원칙 기반 가중치(렌즈) 상수 ---
RECENCY_DECAY = 0.6        # 최신 분기 가중: 한 분기 오래되면 ×0.6 (선행 신호 강조)
LIFT_CAP = 4.0            # 직무 차별성(lift) 상한 — 희소 노이즈 폭주 방지
LIFT_MIN_SUPPORT = 2       # lift>1 부여 최소 회사 수 — 단발 mention 과대평가 방지
WEIGHT_FULL = dict(recency=True, breadth=True, lift=True)   # 세 가중 전부

# 한글 제목이 깨지지 않도록 macOS 기본 한글 폰트 지정(워드클라우드 토큰은 영문)
for _f in ("AppleGothic", "NanumGothic", "Apple SD Gothic Neo"):
    try:
        plt.rcParams["font.family"] = _f
        break
    except Exception:  # noqa: BLE001
        continue
plt.rcParams["axes.unicode_minus"] = False

WC_KW = dict(width=1200, height=600, background_color="white",
             prefer_horizontal=0.95, max_words=60, random_state=42,
             relative_scaling=0.5)


def load_mentions(db=DB_PATH):
    con = sqlite3.connect(db)
    m = pd.read_sql("SELECT * FROM mentions", con)
    con.close()
    return m


def _drop_commodity(m):
    """워드클라우드용: 범용 커모디티 기술(Python/SQL/AWS/…)을 제외해 특화 도구를 부각."""
    return m[~m["tech"].isin(COMMODITY_TECH)]


def _share(counts):
    """{tech: count} → {tech: 1000*share} (패널 간 비교 가능하도록 정규화)."""
    total = sum(counts.values()) or 1
    return {t: 1000.0 * c / total for t, c in counts.items()}


# ---------- 원칙 기반 가중치(렌즈) ----------
def _quarter_weights(m):
    """{quarter: recency 가중} — 최신 분기=1.0, 한 분기 오래질수록 ×RECENCY_DECAY."""
    qs = sorted(q for q in m["quarter"].dropna().unique() if q)
    last = len(qs) - 1
    return {q: RECENCY_DECAY ** (last - i) for i, q in enumerate(qs)}


def _cell_counts(sub, baseline, recency=True, breadth=True, lift=True, qw=None):
    """한 셀(sub)의 가중 tech 점수 {tech: score}.
    - recency: 최신 분기 mention을 더 세게(셀이 단일 분기면 within-cell no-op)
    - breadth: 공고 수가 아니라 '회사당 1회'(그 회사 최신 recency 가중)로 집계
    - lift   : baseline(동일 국가 전체) 대비 셀 내 상대 빈도로 '차별적' 기술을 부각
    baseline = lift 분모 컨텍스트(예: 같은 국가의 전체 mentions)."""
    df = sub.copy()
    if recency:
        qw = qw if qw is not None else _quarter_weights(baseline)
        floor = min(qw.values()) if qw else 1.0
        df["w"] = df["quarter"].map(qw).fillna(floor)
    else:
        df["w"] = 1.0

    if breadth:                       # 회사당 1회(그 회사의 최신 가중치)
        per = df.groupby(["tech", "company"])["w"].max()
        score = per.groupby("tech").sum()
        support = df.groupby("tech")["company"].nunique().to_dict()
    else:
        score = df.groupby("tech")["w"].sum()
        support = df.groupby("tech").size().to_dict()
    score = score.to_dict()

    if lift and score:                # 직무/분기 차별성
        gl = baseline["tech"].value_counts()
        gtot = gl.sum() or 1
        gshare = {t: gl[t] / gtot for t in gl.index}
        ctot = sum(score.values()) or 1
        for t in list(score):
            cshare = score[t] / ctot
            lv = cshare / (gshare.get(t, 1e-9) + 1e-9)
            if support.get(t, 0) < LIFT_MIN_SUPPORT:
                lv = min(lv, 1.0)     # 희소 tech엔 lift>1 미부여(노이즈 방지)
            score[t] *= min(lv, LIFT_CAP)
    return score


# ---------- 뷰1: 전체 마인드셰어 ----------
def view_mindshare(m, path=None):
    m = _drop_commodity(m)
    freq = m["tech"].value_counts().to_dict()
    wc = WordCloud(colormap="viridis", **WC_KW).generate_from_frequencies(freq)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
    ax.set_title("DE 기술 마인드셰어(범용 Python/SQL/AWS 등 제외)", fontsize=13)
    if path: fig.savefig(path, bbox_inches="tight", dpi=120)
    return fig, freq


# ---------- 뷰2: US vs KR ----------
def view_us_vs_kr(m, path=None):
    m = _drop_commodity(m)
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    out = {}
    for ax, country, cmap in [(axes[0], "US", "Blues"), (axes[1], "KR", "Reds")]:
        counts = m[m.country == country]["tech"].value_counts().to_dict()
        freq = _share(counts)
        out[country] = counts
        wc = WordCloud(colormap=cmap, **WC_KW).generate_from_frequencies(freq)
        ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
        ax.set_title("%s 스타트업 (n=%d 언급)" % (country, sum(counts.values())), fontsize=13)
    fig.suptitle("US vs KR — DE 기술 마인드셰어 비교", fontsize=15)
    if path: fig.savefig(path, bbox_inches="tight", dpi=120)
    return fig, out


# ---------- 뷰3: 모멘텀 델타 ----------
def compute_momentum(m, q_early, q_late):
    """두 분기의 share 차이. 반환 {tech: delta_share_permille}, 현재(late) share."""
    def share(q):
        c = m[m.quarter == q]["tech"].value_counts().to_dict()
        return _share(c)
    se, sl = share(q_early), share(q_late)
    techs = set(se) | set(sl)
    delta = {t: sl.get(t, 0) - se.get(t, 0) for t in techs}
    return delta, sl


def _momentum_color(delta):
    """델타 부호별 색을 주는 color_func 생성(상승 빨강/하락 파랑/보합 회색)."""
    def color_func(word, **kwargs):
        d = delta.get(word, 0)
        if d > 0.5:  return "#c0392b"   # 상승
        if d < -0.5: return "#2471a3"   # 하락
        return "#95a5a6"                # 보합
    return color_func


def pick_momentum_quarters(m, min_total=100, partial_ratio=0.5):
    """모멘텀 비교용 최근 두 '성숙' 분기 선택.
    - 커모디티 제외 카운트 기준(뷰와 일치)
    - 갓 시작된 진행중(부분) 분기는 직전 분기의 절반 미만이면 배제(예: Q3 초입)."""
    qc = _drop_commodity(m)["quarter"].value_counts()
    qs = sorted([q for q in qc.index if q and qc[q] >= min_total])
    if len(qs) >= 3 and qc[qs[-1]] < partial_ratio * qc[qs[-2]]:
        qs = qs[:-1]
    return (qs[-2], qs[-1]) if len(qs) >= 2 else (qs[-1], qs[-1])


def view_momentum(m, q_early, q_late, path=None):
    """국가별 2패널 모멘텀 델타. 각 패널: 크기=해당국 현재 share, 색=해당국 분기 델타."""
    m = _drop_commodity(m)
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    out = {}
    for ax, country in [(axes[0], "US"), (axes[1], "KR")]:
        sub = m[m.country == country]
        delta, cur = compute_momentum(sub, q_early, q_late)
        out[country] = delta
        size_freq = {t: v for t, v in cur.items() if v > 0}
        n_late = int((sub["quarter"] == q_late).sum())
        if not size_freq:
            ax.text(0.5, 0.5, "표본 부족", ha="center", va="center", fontsize=14)
            ax.axis("off"); ax.set_title("%s (%s n=%d)" % (country, q_late, n_late)); continue
        wc = WordCloud(**WC_KW).generate_from_frequencies(size_freq).recolor(
            color_func=_momentum_color(delta))
        ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
        ax.set_title("%s 스타트업 (%s 언급 n=%d)" % (country, q_late, n_late), fontsize=12)
    fig.suptitle("모멘텀 델타 %s→%s  (상승=빨강 / 하락=파랑)\n"
                 "※ 열린 공고의 게시 분기 기준 · 국가별 분기 표본이 얇아 노이즈 큼(부분 신호)"
                 % (q_early, q_late), fontsize=13)
    if path: fig.savefig(path, bbox_inches="tight", dpi=120)
    return fig, out


# ---------- (+) 경쟁 기술 막대: 데이터 웨어하우스 카테고리 ----------
def view_competitor_bar(m, path=None):
    rows = []
    for country in ("US", "KR"):
        counts = m[m.country == country]["tech"].value_counts().to_dict()
        share = _share(counts)
        for tech in WAREHOUSE_COMPETITORS:
            rows.append(dict(country=country, tech=tech, share=share.get(tech, 0)))
    df = pd.DataFrame(rows).pivot(index="tech", columns="country", values="share").fillna(0)
    df = df.reindex(WAREHOUSE_COMPETITORS)
    fig, ax = plt.subplots(figsize=(9, 5))
    df.plot(kind="barh", ax=ax, color={"US": "#2471a3", "KR": "#c0392b"})
    ax.set_xlabel("share-of-voice (‰, 국가 내 정규화)")
    ax.set_title("데이터 웨어하우스 경쟁 마인드셰어 — US vs KR", fontsize=13)
    ax.invert_yaxis()
    if path: fig.savefig(path, bbox_inches="tight", dpi=120)
    return fig, df


# ---------- 세분 제품 티어 ----------
def load_granular(db=DB_PATH):
    con = sqlite3.connect(db)
    g = pd.read_sql("SELECT * FROM granular_mentions", con)
    con.close()
    return g


def view_granular_bar(g, top=18, path=None):
    """세분 제품 top-N의 국가별 share-of-voice(정규화). US편중 위 / KR편중 아래로 정렬."""
    rows = []
    for country in ("US", "KR"):
        sh = _share(g[g.country == country]["product"].value_counts().to_dict())
        for p, v in sh.items():
            rows.append(dict(country=country, product=p, share=v))
    df = (pd.DataFrame(rows).pivot(index="product", columns="country", values="share")
          .reindex(columns=["US", "KR"]).fillna(0))
    df = df.assign(tot=df["US"] + df["KR"]).sort_values("tot", ascending=False).head(top)
    df = df.assign(diff=df["US"] - df["KR"]).sort_values("diff")  # KR편중(아래)→US편중(위)
    fig, ax = plt.subplots(figsize=(10, 8))
    df[["US", "KR"]].plot(kind="barh", ax=ax, color={"US": "#2471a3", "KR": "#c0392b"})
    ax.set_xlabel("share-of-voice (‰, 국가 내 정규화)")
    ax.set_title("세분 제품 마인드셰어 — US vs KR (제품 수준)\n"
                 "위=미국 편중 · 아래=국내 편중", fontsize=13)
    fig.tight_layout()
    if path: fig.savefig(path, bbox_inches="tight", dpi=120)
    return fig, df


def view_stack_profile(g, path=None):
    """스택 성숙도 KPI: 세분제품 언급 중 '모던 데이터 스택' vs '레거시 Hadoop' 비중."""
    rows = []
    for country in ("US", "KR"):
        sub = g[g.country == country]
        total = len(sub) or 1
        rows.append({"country": country,
                     "모던 데이터 스택": sub["product"].isin(MODERN_STACK).sum() / total * 100,
                     "레거시 Hadoop": sub["product"].isin(LEGACY_STACK).sum() / total * 100})
    df = pd.DataFrame(rows).set_index("country")
    fig, ax = plt.subplots(figsize=(8, 5))
    df.plot(kind="bar", ax=ax, color={"모던 데이터 스택": "#27ae60", "레거시 Hadoop": "#e67e22"})
    ax.set_ylabel("세분제품 언급 중 비중 (%)")
    ax.set_title("스택 성숙도 — 모던 데이터 스택 vs 레거시 Hadoop\n"
                 "(모던=Unity Catalog·Snowpark·Fivetran·Monte Carlo 등 / 레거시=Hive·Hadoop)", fontsize=12)
    ax.tick_params(axis="x", rotation=0)
    fig.tight_layout()
    if path: fig.savefig(path, bbox_inches="tight", dpi=120)
    return fig, df


# ---------- (+) 국가별 크롤링 규모 ----------
def view_crawl_volume(summary_df, path=None):
    """국가별 크롤링 규모: 원본 공고 vs 기술직 공고 막대(+ 값 라벨)."""
    df = summary_df.drop(index="합계", errors="ignore")
    fig, ax = plt.subplots(figsize=(9, 5))
    df[["원본공고", "기술직공고"]].plot(kind="bar", ax=ax,
                                    color={"원본공고": "#95a5a6", "기술직공고": "#2471a3"})
    ax.set_ylabel("공고 수")
    ax.set_title("국가별 크롤링 규모 — 원본 공고 vs 기술직 공고", fontsize=13)
    ax.tick_params(axis="x", rotation=0)
    for cont in ax.containers:
        ax.bar_label(cont, fontsize=9)
    fig.tight_layout()
    if path: fig.savefig(path, bbox_inches="tight", dpi=120)
    return fig, df


# ======================================================================
# 커리큘럼 뷰 (부트캠프 타겟) — 직무별 / 분기별
# ----------------------------------------------------------------------
# 상세기획의 비치헤드(국내 부트캠프 커리큘럼 기획자)를 위한 두 결정 지원:
#   · view_quarterly    "이번 기수에 어떤 직무/기술을 타겟으로 열까" (분기 추이)
#   · view_by_category  "그 직무 트랙에서 뭘 가르칠까" (직무별 스택)
# 사용자 결정에 따라 기본 언어(Python/SQL 등)를 '제외하지 않고 포함'한다.
# ======================================================================
def category_techstack(m, include_commodity=True, top=None, weighted=False):
    """직무(category)별 기술 스택 딕셔너리 {category: {tech: count|score}} 를 반환.
    '카테고리별 테크스택 딕셔너리' 산출물(노트북에서 표로 display).
    include_commodity=True → 기본 언어 포함(사용자 결정).
    weighted=True → recency·breadth·lift 가중 점수(그 직무에 차별적인 기술 부각)."""
    if not include_commodity:
        m = _drop_commodity(m)
    qw = _quarter_weights(m) if weighted else None
    out = {}
    for cat in m["category"].value_counts().index:      # 표본 많은 직무부터
        sub = m[m["category"] == cat]
        if weighted:
            score = _cell_counts(sub, m, qw=qw, **WEIGHT_FULL)   # baseline = 전체(국가 무관)
            counts = dict(sorted(score.items(), key=lambda kv: -kv[1]))
        else:
            counts = sub["tech"].value_counts().to_dict()
        if top:
            counts = dict(list(counts.items())[:top])
        out[cat] = counts
    return out


def _cloud_grid(m, rows, row_col, countries, suptitle, path,
                include_commodity, cell_title, weight=None):
    """(행=rows, 열=countries) 워드클라우드 격자를 그리는 공통 헬퍼.
    weight=dict(recency,breadth,lift)이면 가중 점수로 사이징(원본은 weight=None)."""
    if not include_commodity:
        m = _drop_commodity(m)
    qw = _quarter_weights(m) if weight else None
    nrow, ncol = len(rows), len(countries)
    fig, axes = plt.subplots(nrow, ncol, figsize=(6 * ncol, 3.2 * nrow), squeeze=False)
    out = {}
    for j, country in enumerate(countries):
        base = m[m.country == country]                 # lift 분모 = 동일 국가 전체
        for i, rv in enumerate(rows):
            ax = axes[i][j]
            sub = base[base[row_col] == rv]
            if weight:
                counts = _cell_counts(sub, base, qw=qw, **weight)
            else:
                counts = sub["tech"].value_counts().to_dict()
            n = len(sub)                               # 제목 n = raw 기술언급 수(해석성 유지)
            out[(rv, country)] = counts
            ax.axis("off")
            if not counts:
                ax.text(0.5, 0.5, "표본 없음", ha="center", va="center", fontsize=12)
                ax.set_title(cell_title(rv, country, 0), fontsize=11)
                continue
            wc = WordCloud(colormap=_CMAP_BY_COUNTRY.get(country, "viridis"),
                           **WC_KW).generate_from_frequencies(_share(counts))
            ax.imshow(wc, interpolation="bilinear")
            ax.set_title(cell_title(rv, country, n), fontsize=11)
    fig.suptitle(suptitle, fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    if path:
        fig.savefig(path, bbox_inches="tight", dpi=120)
    return fig, out


def view_quarterly(m, quarters=CURRICULUM_QUARTERS, countries=("KR", "US"),
                   include_commodity=True, weighted=False, path=None):
    """분기별 전체 기술 수요 워드클라우드 (행=분기, 열=국가).
    '이번 기수에 어떤 직무/기술을 타겟으로 열까'를 위한 추이 뷰.
    weighted=True → 가중 렌즈(breadth·lift; recency는 셀이 단일 분기라 no-op)."""
    tag = "  [가중 렌즈: 회사 breadth × 차별성 lift]" if weighted else ""
    suptitle = ("분기별 기술 수요 추이 — %s%s\n"
                "※ '현재 열린 공고의 게시 분기' 기준 · 과거 분기(2025-Q4)는 표본 얇음(방향성 지표)"
                % (" → ".join(quarters), tag))
    return _cloud_grid(
        m, list(quarters), "quarter", list(countries), suptitle, path,
        include_commodity,
        cell_title=lambda q, c, n: "%s · %s (n=%d)" % (c, q, n),
        weight=WEIGHT_FULL if weighted else None)


def view_by_category(m, min_mentions=20, countries=("KR", "US"),
                     include_commodity=True, weighted=False, path=None):
    """직무(category)별 기술 스택 워드클라우드 (행=직무, 열=국가).
    '그 직무 트랙에서 뭘 가르칠까'를 위한 커리큘럼 뷰.
    표본이 min_mentions 이상인 직무만, 정의 순서대로 렌더('비기술직' 제외).
    weighted=True → 가중 렌즈(recency·breadth·lift): 그 직무에 '차별적'인 스택이 부각."""
    vc = m["category"].value_counts()
    order = [c for c in all_job_categories() if c in vc.index]  # 정의 순서 고정
    cats = [c for c in order if vc[c] >= min_mentions] or order[:1]
    tag = "  [가중 렌즈: 최신분기 × 회사 breadth × 차별성 lift]" if weighted else " (기본 언어 포함)"
    suptitle = "직무별 기술 스택 — 무엇을 가르칠까 (행=직무 · 열=국가)%s" % tag
    return _cloud_grid(
        m, cats, "category", list(countries), suptitle, path,
        include_commodity,
        cell_title=lambda cat, c, n: "%s · %s (n=%d)" % (cat, c, n),
        weight=WEIGHT_FULL if weighted else None)


def render_all():
    ensure_dirs()
    view_crawl_volume(crawl_summary(), f"{OUT_DIR}/0_crawl_volume.png")   # 국가별 규모
    m = load_mentions()
    view_mindshare(m, f"{OUT_DIR}/1_mindshare.png")
    view_us_vs_kr(m, f"{OUT_DIR}/2_us_vs_kr.png")
    # 델타: 성숙한 최근 두 분기 자동 선택(진행중 부분 분기 배제) → 현재 Q1→Q2
    qe, ql = pick_momentum_quarters(m)
    view_momentum(m, qe, ql, f"{OUT_DIR}/3_momentum.png")
    view_competitor_bar(m, f"{OUT_DIR}/4_competitor_bar.png")
    # 세분 제품 티어
    g = load_granular()
    view_granular_bar(g, path=f"{OUT_DIR}/5_granular_products.png")
    view_stack_profile(g, path=f"{OUT_DIR}/6_stack_profile.png")
    # 커리큘럼 뷰(부트캠프 타겟): 분기별 추이 + 직무별 스택 (원본 빈도)
    view_quarterly(m, path=f"{OUT_DIR}/7_quarterly.png")
    view_by_category(m, path=f"{OUT_DIR}/8_by_category.png")
    # 가중 렌즈(원칙 기반: recency·breadth·lift) — 원본 뷰는 그대로 두고 별도 추가
    view_quarterly(m, weighted=True, path=f"{OUT_DIR}/9_quarterly_weighted.png")
    view_by_category(m, weighted=True, path=f"{OUT_DIR}/10_by_category_weighted.png")
    return m, g


if __name__ == "__main__":
    render_all()
    print("PNG 저장 완료 →", OUT_DIR)
