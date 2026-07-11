"""
Светлюкс — дашборд видимости в поисковиках
Запуск локально: streamlit run dashboard.py
"""

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from datetime import datetime

# ── Настройки страницы ────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Светлюкс — Видимость в поиске',
    page_icon='💡',
    layout='wide',
)

# ── Стили ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 16px 20px;
        border-left: 4px solid #1F4E79;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #1F4E79; }
    .metric-label { font-size: 0.85rem; color: #666; margin-top: 2px; }
    .metric-delta-pos { color: #28a745; font-weight: 600; }
    .metric-delta-neg { color: #dc3545; font-weight: 600; }
    h1 { color: #1F4E79; }
    .stSelectbox label { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Загрузка данных ───────────────────────────────────────────────────────────
DOMAIN_COLORS = {
    'svetlux.ru':           '#1F4E79',
    'lu.ru':                '#E8543A',
    'vamsvet.ru':           '#2E8B57',
    'market-sveta.ru':      '#9B59B6',
    'donplafon.ru':         '#E67E22',
    'svetilnik-online.ru':  '#16A085',
    'divine-light.ru':      '#C0392B',
    '220svet.ru':           '#7F8C8D',
}

@st.cache_data(ttl=300)
def load_data(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql('''
        SELECT check_date, query, engine, domain, position
        FROM positions
        ORDER BY check_date, engine, query
    ''', conn)
    conn.close()
    df['check_date'] = pd.to_datetime(df['check_date'])
    return df


def get_db_path() -> str | None:
    """Ищем positions.db рядом со скриптом или в текущей папке."""
    candidates = [
        Path(__file__).parent / 'positions.db',
        Path('positions.db'),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def calc_visibility(df_subset: pd.DataFrame, total_queries: int) -> float:
    """Взвешенная видимость в %."""
    def weight(p):
        if pd.isna(p): return 0
        if p <= 3:  return [1.0, 0.85, 0.75][int(p)-1]
        if p <= 10: return 0.55 - (p - 4) * 0.03
        if p <= 20: return 0.2
        if p <= 50: return 0.05
        return 0
    if total_queries == 0: return 0.0
    return round(df_subset['position'].apply(weight).sum() / total_queries * 100, 1)


# ── Заголовок ─────────────────────────────────────────────────────────────────
st.title('💡 Светлюкс — Видимость в поисковиках')

# ── Источник данных ───────────────────────────────────────────────────────────
db_path = get_db_path()

if not db_path:
    st.warning('База данных positions.db не найдена рядом со скриптом.')
    uploaded = st.file_uploader('Загрузи файл positions.db', type=['db'])
    if uploaded:
        tmp_path = '/tmp/positions_uploaded.db'
        with open(tmp_path, 'wb') as f:
            f.write(uploaded.read())
        db_path = tmp_path
    else:
        st.info('Запусти трекер (rank_tracker.py) чтобы собрать данные, затем загрузи positions.db сюда.')
        st.stop()

df_all = load_data(db_path)

if df_all.empty:
    st.error('В базе данных нет данных. Запусти rank_tracker.py сначала.')
    st.stop()

# ── Фильтры в сайдбаре ────────────────────────────────────────────────────────
with st.sidebar:
    st.header('⚙️ Настройки')

    engine = st.radio('Поисковик', ['Яндекс', 'Google'], horizontal=True)
    engine_key = 'yandex' if engine == 'Яндекс' else 'google'

    all_dates = sorted(df_all['check_date'].dt.date.unique(), reverse=True)
    selected_date = st.selectbox(
        'Дата',
        all_dates,
        format_func=lambda d: d.strftime('%d.%m.%Y')
    )

    all_domains = df_all['domain'].unique().tolist()
    our_domain = 'svetlux.ru'
    competitors = [d for d in all_domains if d != our_domain]
    selected_domains = st.multiselect(
        'Домены для сравнения',
        competitors,
        default=competitors,
    )
    show_domains = [our_domain] + selected_domains

    st.divider()
    st.caption(f'Дат в базе: {len(all_dates)}')
    last_update = df_all['check_date'].max().strftime('%d.%m.%Y %H:%M')
    st.caption(f'Последнее обновление: {last_update}')

# ── Данные для выбранной даты ─────────────────────────────────────────────────
df_engine = df_all[df_all['engine'] == engine_key].copy()
df_cur  = df_engine[df_engine['check_date'].dt.date == selected_date]
prev_dates = [d for d in all_dates if d < selected_date]
df_prev = df_engine[df_engine['check_date'].dt.date == prev_dates[0]] if prev_dates else pd.DataFrame()

total_queries = df_cur[df_cur['domain'] == our_domain]['query'].nunique()
if total_queries == 0:
    total_queries = df_cur['query'].nunique()

# ── КПИ-карточки ──────────────────────────────────────────────────────────────
st.subheader(f'📊 {engine} · {selected_date.strftime("%d.%m.%Y")} · {total_queries} запросов')

our_cur  = df_cur[df_cur['domain'] == our_domain]
our_prev = df_prev[df_prev['domain'] == our_domain] if not df_prev.empty else pd.DataFrame()

vis_cur  = calc_visibility(our_cur, total_queries)
vis_prev = calc_visibility(our_prev, total_queries) if not our_prev.empty else None
vis_delta = round(vis_cur - vis_prev, 1) if vis_prev is not None else None

top3_cur  = int((our_cur['position'] <= 3).sum())
top10_cur = int((our_cur['position'] <= 10).sum())
top3_prev  = int((our_prev['position'] <= 3).sum()) if not our_prev.empty else None
top10_prev = int((our_prev['position'] <= 10).sum()) if not our_prev.empty else None

def delta_html(val, prev, invert=False):
    if prev is None: return ''
    d = val - prev
    if d == 0: return '<span style="color:#888">→ 0</span>'
    color = '#28a745' if (d > 0 and not invert) or (d < 0 and invert) else '#dc3545'
    arrow = '▲' if d > 0 else '▼'
    return f'<span style="color:{color}">{arrow} {abs(d)}</span>'

col1, col2, col3, col4 = st.columns(4)

with col1:
    delta_str = f' {delta_html(vis_cur, vis_prev)}' if vis_delta is not None else ''
    st.markdown(f'''<div class="metric-card">
        <div class="metric-value">{vis_cur}%{delta_str}</div>
        <div class="metric-label">Видимость svetlux.ru</div>
    </div>''', unsafe_allow_html=True)

with col2:
    d3 = delta_html(top3_cur, top3_prev)
    st.markdown(f'''<div class="metric-card">
        <div class="metric-value">{top3_cur} {d3}</div>
        <div class="metric-label">Запросов в Топ 1–3</div>
    </div>''', unsafe_allow_html=True)

with col3:
    d10 = delta_html(top10_cur, top10_prev)
    st.markdown(f'''<div class="metric-card">
        <div class="metric-value">{top10_cur} {d10}</div>
        <div class="metric-label">Запросов в Топ 4–10</div>
    </div>''', unsafe_allow_html=True)

with col4:
    not_found = int((our_cur['position'].isna()).sum())
    st.markdown(f'''<div class="metric-card">
        <div class="metric-value">{not_found}</div>
        <div class="metric-label">Не в Топ-50</div>
    </div>''', unsafe_allow_html=True)

st.divider()

# ── Таблица видимости + График динамики ───────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap='large')

# ── ТАБЛИЦА ──
with col_left:
    st.subheader('🏆 Сравнение видимости')

    vis_rows = []
    for domain in show_domains:
        d_cur  = df_cur[df_cur['domain'] == domain]
        d_prev = df_prev[df_prev['domain'] == domain] if not df_prev.empty else pd.DataFrame()
        tq = total_queries

        vis  = calc_visibility(d_cur, tq)
        visp = calc_visibility(d_prev, tq) if not d_prev.empty else None
        delta = round(vis - visp, 1) if visp is not None else None

        vis_rows.append({
            'Домен': domain,
            'Видимость': vis,
            'Δ': delta,
            'Топ 1–3': int((d_cur['position'] <= 3).sum()),
            'Топ 4–10': int(((d_cur['position'] > 3) & (d_cur['position'] <= 10)).sum()),
            'Топ 11–20': int(((d_cur['position'] > 10) & (d_cur['position'] <= 20)).sum()),
            'Топ 21–50': int(((d_cur['position'] > 20) & (d_cur['position'] <= 50)).sum()),
        })

    df_vis_table = pd.DataFrame(vis_rows).sort_values('Видимость', ascending=False).reset_index(drop=True)
    df_vis_table.index = df_vis_table.index + 1

    def color_delta(val):
        if pd.isna(val) or val == 0: return 'color: gray'
        return 'color: #28a745; font-weight:600' if val > 0 else 'color: #dc3545; font-weight:600'

    def color_our(row):
        if row['Домен'] == our_domain:
            return ['font-weight:bold; background:#EEF5FF'] * len(row)
        return [''] * len(row)

    styled = (
        df_vis_table.style
        .apply(color_our, axis=1)
        .map(color_delta, subset=['Δ'])
        .format({'Видимость': '{:.1f}%', 'Δ': lambda x: f'+{x:.1f}' if x and x > 0 else (f'{x:.1f}' if x is not None and not pd.isna(x) else '—')})
    )
    st.dataframe(styled, use_container_width=True, height=350)

# ── ГРАФИК ──
with col_right:
    st.subheader('📈 Динамика видимости по неделям')

    history_rows = []
    for dt in sorted(df_all['check_date'].dt.date.unique()):
        df_dt = df_engine[df_engine['check_date'].dt.date == dt]
        tq = df_dt[df_dt['domain'] == our_domain]['query'].nunique()
        if tq == 0: tq = df_dt['query'].nunique()
        for domain in show_domains:
            d_dt = df_dt[df_dt['domain'] == domain]
            vis = calc_visibility(d_dt, tq)
            history_rows.append({'Дата': dt, 'Домен': domain, 'Видимость': vis})

    df_hist = pd.DataFrame(history_rows)

    if len(df_hist['Дата'].unique()) >= 2:
        fig = px.line(
            df_hist,
            x='Дата', y='Видимость', color='Домен',
            color_discrete_map=DOMAIN_COLORS,
            markers=True,
            labels={'Видимость': 'Видимость, %', 'Дата': ''},
        )
        fig.update_traces(line_width=2.5, marker_size=7)
        fig.update_layout(
            height=340,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
            yaxis=dict(ticksuffix='%', gridcolor='#f0f0f0'),
            plot_bgcolor='white',
            paper_bgcolor='white',
        )
        # Выделяем наш домен
        for trace in fig.data:
            if trace.name == our_domain:
                trace.line.width = 3.5
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('Накопи хотя бы 2 недели данных — тогда здесь появится график динамики.')
        # Показываем бар-чарт текущих значений
        df_bar = df_hist[df_hist['Дата'] == selected_date].sort_values('Видимость', ascending=True)
        fig = px.bar(
            df_bar, x='Видимость', y='Домен', orientation='h',
            color='Домен', color_discrete_map=DOMAIN_COLORS,
            labels={'Видимость': 'Видимость, %'},
            text='Видимость',
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(
            height=320, showlegend=False,
            margin=dict(l=0, r=60, t=10, b=0),
            xaxis=dict(ticksuffix='%'),
            plot_bgcolor='white', paper_bgcolor='white',
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Детальная таблица позиций ─────────────────────────────────────────────────
st.subheader('🔍 Позиции по запросам')

tab1, tab2 = st.tabs([f'svetlux.ru vs конкуренты', f'Только svetlux.ru'])

with tab1:
    # Сводная таблица: запрос × домен → позиция
    queries_list = sorted(df_cur['query'].unique())
    comp_data = {'Запрос': queries_list}
    for domain in show_domains:
        pos_map = dict(zip(
            df_cur[df_cur['domain'] == domain]['query'],
            df_cur[df_cur['domain'] == domain]['position']
        ))
        comp_data[domain] = [pos_map.get(q) for q in queries_list]

    df_comp = pd.DataFrame(comp_data)
    df_comp = df_comp.sort_values(our_domain)

    # Поиск по запросу
    search = st.text_input('Поиск по запросу', placeholder='например: люстра')
    if search:
        df_comp = df_comp[df_comp['Запрос'].str.contains(search, case=False, na=False)]

    def highlight_our(val):
        if pd.isna(val): return 'color: #ccc'
        if val <= 3:  return 'color: #28a745; font-weight:700'
        if val <= 10: return 'color: #856404; font-weight:600'
        if val <= 20: return 'color: #dc7633'
        return 'color: #dc3545'

    domain_cols = [c for c in df_comp.columns if c != 'Запрос']
    styled_comp = (
        df_comp.style
        .applymap(highlight_our, subset=domain_cols)
        .format({c: lambda x: str(int(x)) if pd.notna(x) else '—' for c in domain_cols})
    )
    st.dataframe(styled_comp, use_container_width=True, height=450)

with tab2:
    df_our = df_cur[df_cur['domain'] == our_domain][['query','position']].copy()

    if not df_prev.empty:
        df_our_prev = df_prev[df_prev['domain'] == our_domain][['query','position']].copy()
        df_our = df_our.merge(df_our_prev, on='query', suffixes=('_cur','_prev'))
        df_our['Δ'] = (df_our['position_prev'] - df_our['position_cur']).round(0)
        df_our.columns = ['Запрос', 'Позиция', f'Позиция ({prev_dates[0].strftime("%d.%m")})', 'Δ (рост +)']
    else:
        df_our.columns = ['Запрос', 'Позиция']

    df_our = df_our.sort_values('Позиция')

    pos_filter = st.select_slider(
        'Показать позиции',
        options=['Топ 3', 'Топ 10', 'Топ 20', 'Топ 50', 'Все'],
        value='Топ 50'
    )
    limits = {'Топ 3': 3, 'Топ 10': 10, 'Топ 20': 20, 'Топ 50': 50, 'Все': 999}
    limit = limits[pos_filter]
    df_filtered = df_our[df_our['Позиция'] <= limit] if 'Позиция' in df_our.columns else df_our

    def color_pos(val):
        if pd.isna(val): return ''
        if val <= 3:  return 'background-color:#C6EFCE; font-weight:700'
        if val <= 10: return 'background-color:#FFEB9C'
        if val <= 20: return 'background-color:#FCE4D6'
        return 'background-color:#F2DCDB'

    style_cols = ['Позиция']
    st.dataframe(
        df_filtered.style.applymap(color_pos, subset=style_cols),
        use_container_width=True,
        height=450
    )

# ── Футер ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption(f'Данные из positions.db · Последнее обновление: {last_update} · Регион Яндекса: Москва')
