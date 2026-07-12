"""
Светлюкс — дашборд видимости в поисковиках
Читает данные из positions_export.csv (легче чем SQLite на Streamlit Cloud)
Запуск: streamlit run dashboard.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title='Светлюкс — Видимость в поиске',
    page_icon='💡',
    layout='wide',
)

st.markdown("""
<style>
.metric-card {
    background:#f8f9fa; border-radius:10px;
    padding:16px 20px; border-left:4px solid #1F4E79;
    margin-bottom:8px;
}
.metric-value { font-size:2rem; font-weight:700; color:#1F4E79; }
.metric-label { font-size:0.85rem; color:#666; margin-top:2px; }
</style>
""", unsafe_allow_html=True)

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

BUCKET_COLORS = {
    'Топ 1–3':   '#C6EFCE',
    'Топ 4–10':  '#FFEB9C',
    'Топ 11–20': '#FCE4D6',
    'Топ 21–50': '#F2DCDB',
    '> 50':      '#F2F2F2',
}

@st.cache_data(ttl=300)
def load_data():
    candidates = [
        Path(__file__).parent / 'positions_export.csv',
        Path('positions_export.csv'),
    ]
    for p in candidates:
        if p.exists():
            df = pd.read_csv(str(p))
            df['check_date'] = pd.to_datetime(df['check_date']).dt.date
            df['position'] = pd.to_numeric(df['position'], errors='coerce').astype('float32')
            df['engine'] = df['engine'].astype('category')
            df['domain'] = df['domain'].astype('category')
            return df
    return None

def calc_vis(pos_series, total):
    if total == 0: return 0.0
    def w(p):
        if pd.isna(p): return 0
        if p <= 3:  return [1.0, 0.85, 0.75][int(p)-1]
        if p <= 10: return max(0.55 - (p-4)*0.03, 0.3)
        if p <= 20: return 0.2
        if p <= 50: return 0.05
        return 0
    return round(pos_series.apply(w).sum() / total * 100, 1)

def pos_bucket(p):
    if pd.isna(p): return ''
    if p <= 3:  return 'Топ 1–3'
    if p <= 10: return 'Топ 4–10'
    if p <= 20: return 'Топ 11–20'
    if p <= 50: return 'Топ 21–50'
    return '> 50'

# ── Загрузка ──────────────────────────────────────────────────────────────────
df_all = load_data()

if df_all is None:
    st.warning('Файл positions_export.csv не найден.')
    uploaded = st.file_uploader('Загрузи positions_export.csv', type=['csv'])
    if uploaded:
        df_all = pd.read_csv(uploaded)
        df_all['check_date'] = pd.to_datetime(df_all['check_date']).dt.date
        df_all['position'] = pd.to_numeric(df_all['position'], errors='coerce').astype('float32')
    else:
        st.stop()

# ── Сайдбар ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('⚙️ Настройки')
    engine_label = st.radio('Поисковик', ['Яндекс', 'Google'], horizontal=True)
    engine_key = 'yandex' if engine_label == 'Яндекс' else 'google'

    all_dates = sorted(df_all['check_date'].unique(), reverse=True)
    sel_date = st.selectbox('Дата', all_dates,
        format_func=lambda d: d.strftime('%d.%m.%Y'))

    all_domains = sorted(df_all['domain'].unique().tolist())
    our = 'svetlux.ru'
    competitors = [d for d in all_domains if d != our]
    sel_comp = st.multiselect('Конкуренты', competitors, default=competitors)
    show_domains = [our] + sel_comp

    st.divider()
    st.caption(f'Дат в базе: {len(all_dates)}')
    st.caption(f'Обновлено: {max(all_dates).strftime("%d.%m.%Y")}')

# ── Фильтрация ────────────────────────────────────────────────────────────────
df_e   = df_all[df_all['engine'] == engine_key]
df_cur = df_e[df_e['check_date'] == sel_date]

prev_dates = [d for d in all_dates if d < sel_date]
df_prev = df_e[df_e['check_date'] == prev_dates[0]] if prev_dates else pd.DataFrame()

our_cur  = df_cur[df_cur['domain'] == our]
our_prev = df_prev[df_prev['domain'] == our] if not df_prev.empty else pd.DataFrame()
total_q  = int(our_cur['query'].nunique()) or int(df_cur['query'].nunique())

# ── Заголовок ─────────────────────────────────────────────────────────────────
st.title('💡 Светлюкс — Видимость в поисковиках')
st.subheader(f'{engine_label} · {sel_date.strftime("%d.%m.%Y")} · {total_q} запросов')

# ── КПИ ───────────────────────────────────────────────────────────────────────
vis_cur  = calc_vis(our_cur['position'], total_q)
vis_prev = calc_vis(our_prev['position'], total_q) if not our_prev.empty else None
top3_cur  = int((our_cur['position'] <= 3).sum())
top10_cur = int((our_cur['position'] <= 10).sum())
top3_prev  = int((our_prev['position'] <= 3).sum()) if not our_prev.empty else None
top10_prev = int((our_prev['position'] <= 10).sum()) if not our_prev.empty else None
not_found = int(our_cur['position'].isna().sum())

def delta_str(cur, prev):
    if prev is None: return ''
    d = cur - prev
    if d == 0: return ' <span style="color:#888">→0</span>'
    color = '#28a745' if d > 0 else '#dc3545'
    arrow = '▲' if d > 0 else '▼'
    return f' <span style="color:{color}">{arrow}{abs(d):.1f}</span>'

c1, c2, c3, c4 = st.columns(4)
for col, val, prev, label in [
    (c1, f'{vis_cur}%', f'{vis_prev}%' if vis_prev else None, 'Видимость svetlux.ru'),
    (c2, top3_cur, top3_prev, 'Запросов в Топ 1–3'),
    (c3, top10_cur - top3_cur, (top10_prev - top3_prev) if top10_prev else None, 'Запросов в Топ 4–10'),
    (c4, not_found, None, 'Не в Топ-50'),
]:
    d = delta_str(
        float(str(val).replace('%','')),
        float(str(prev).replace('%','')) if prev is not None else None
    ) if prev is not None else ''
    col.markdown(
        f'<div class="metric-card"><div class="metric-value">{val}{d}</div>'
        f'<div class="metric-label">{label}</div></div>',
        unsafe_allow_html=True
    )

st.divider()

# ── Таблица + График ──────────────────────────────────────────────────────────
col_l, col_r = st.columns(2, gap='large')

with col_l:
    st.subheader('🏆 Сравнение видимости')
    rows = []
    for d in show_domains:
        dc = df_cur[df_cur['domain'] == d]
        dp = df_prev[df_prev['domain'] == d] if not df_prev.empty else pd.DataFrame()
        vis = calc_vis(dc['position'], total_q)
        vis_p = calc_vis(dp['position'], total_q) if not dp.empty else None
        rows.append({
            'Домен': d,
            'Видимость': vis,
            'Δ': round(vis - vis_p, 1) if vis_p is not None else None,
            'Топ 1–3':   int((dc['position'] <= 3).sum()),
            'Топ 4–10':  int(((dc['position'] > 3) & (dc['position'] <= 10)).sum()),
            'Топ 11–20': int(((dc['position'] > 10) & (dc['position'] <= 20)).sum()),
            'Топ 21–50': int(((dc['position'] > 20) & (dc['position'] <= 50)).sum()),
        })

    df_vis = pd.DataFrame(rows).sort_values('Видимость', ascending=False).reset_index(drop=True)
    df_vis.index += 1
    df_vis['Видимость'] = df_vis['Видимость'].map(lambda x: f'{x:.1f}%')
    df_vis['Δ'] = df_vis['Δ'].map(lambda x: f'+{x:.1f}' if pd.notna(x) and x > 0
                                   else (f'{x:.1f}' if pd.notna(x) else '—'))
    st.dataframe(df_vis, height=340)

with col_r:
    st.subheader('📈 Динамика видимости')
    hist = []
    for dt in sorted(df_all['check_date'].unique()):
        df_dt = df_e[df_e['check_date'] == dt]
        tq = int(df_dt[df_dt['domain'] == our]['query'].nunique()) or int(df_dt['query'].nunique())
        for d in show_domains:
            hist.append({'Дата': dt, 'Домен': d,
                         'Видимость': calc_vis(df_dt[df_dt['domain'] == d]['position'], tq)})

    df_hist = pd.DataFrame(hist)

    if df_hist['Дата'].nunique() >= 2:
        fig = px.line(df_hist, x='Дата', y='Видимость', color='Домен',
                      color_discrete_map=DOMAIN_COLORS, markers=True,
                      labels={'Видимость': 'Видимость, %', 'Дата': ''})
        fig.update_traces(line_width=2, marker_size=6)
        fig.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0),
                          plot_bgcolor='white', paper_bgcolor='white',
                          yaxis=dict(ticksuffix='%'),
                          legend=dict(orientation='h', y=1.12, x=0))
        for tr in fig.data:
            if tr.name == our: tr.line.width = 3.5
        st.plotly_chart(fig)
    else:
        df_bar = df_hist[df_hist['Дата'] == sel_date].sort_values('Видимость')
        fig = px.bar(df_bar, x='Видимость', y='Домен', orientation='h',
                     color='Домен', color_discrete_map=DOMAIN_COLORS,
                     text='Видимость', labels={'Видимость': 'Видимость, %'})
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(height=300, showlegend=False,
                          margin=dict(l=0,r=60,t=10,b=0),
                          plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(fig)

st.divider()

# ── Детальные позиции ─────────────────────────────────────────────────────────
st.subheader('🔍 Позиции по запросам')
tab1, tab2 = st.tabs(['svetlux.ru vs конкуренты', 'Только svetlux.ru'])

with tab1:
    search = st.text_input('Поиск по запросу', placeholder='например: люстра')
    queries = sorted(df_cur['query'].unique())
    if search:
        queries = [q for q in queries if search.lower() in q.lower()]

    comp_rows = {'Запрос': queries}
    for d in show_domains:
        pm = dict(zip(df_cur[df_cur['domain']==d]['query'],
                      df_cur[df_cur['domain']==d]['position']))
        comp_rows[d] = [int(pm[q]) if q in pm and pd.notna(pm[q]) else None for q in queries]

    df_comp = pd.DataFrame(comp_rows)
    if our in df_comp.columns:
        df_comp = df_comp.sort_values(our)

    st.dataframe(df_comp.reset_index(drop=True), height=500)

with tab2:
    limit = st.select_slider('Показать позиции',
        options=['Топ 3','Топ 10','Топ 20','Топ 50','Все'], value='Топ 50')
    limits = {'Топ 3':3,'Топ 10':10,'Топ 20':20,'Топ 50':50,'Все':999}

    df_our = our_cur[['query','position']].copy()
    df_our['Группа'] = df_our['position'].apply(pos_bucket)
    df_our = df_our[df_our['position'] <= limits[limit]].sort_values('position')
    df_our.columns = ['Запрос','Позиция','Группа']
    df_our['Позиция'] = df_our['Позиция'].apply(lambda x: int(x) if pd.notna(x) else '—')

    st.dataframe(df_our.reset_index(drop=True), height=500)

st.divider()
st.caption(f'Данные: positions_export.csv · {max(all_dates).strftime("%d.%m.%Y")} · Яндекс регион: Москва')
