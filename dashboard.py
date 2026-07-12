"""
Светлюкс — дашборд видимости
Читает предагрегированные файлы:
  - visibility_summary.csv  (видимость по доменам)
  - svetlux_positions.csv   (позиции нашего сайта)
"""
import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

st.set_page_config(page_title='Светлюкс — Видимость', page_icon='💡', layout='wide')

st.markdown("""<style>
.metric-card{background:#f8f9fa;border-radius:10px;padding:14px 18px;
             border-left:4px solid #1F4E79;margin-bottom:8px;}
.metric-value{font-size:1.8rem;font-weight:700;color:#1F4E79;}
.metric-label{font-size:0.82rem;color:#666;margin-top:2px;}
</style>""", unsafe_allow_html=True)

DOMAIN_COLORS = {
    'svetlux.ru':'#1F4E79','lu.ru':'#E8543A','vamsvet.ru':'#2E8B57',
    'market-sveta.ru':'#9B59B6','donplafon.ru':'#E67E22',
    'svetilnik-online.ru':'#16A085','divine-light.ru':'#C0392B','220svet.ru':'#7F8C8D',
    'megalamps.ru':'#2980B9','lampadia.ru':'#8E44AD','topsvet.ru':'#27AE60',
    'fedomo.ru':'#F39C12','svetodom.ru':'#1ABC9C','basicdecor.ru':'#D35400',
    'lustranadom.ru':'#2C3E50','citilux.ru':'#E91E63','lampsshop.ru':'#00BCD4',
    'eurosvet.ru':'#FF5722','maytoni.ru':'#607D8B','elektrostandard.ru':'#795548',
    'msveta.ru':'#009688','lustrypremium.ru':'#FF9800',
}

@st.cache_data
def load_summary():
    for p in [Path(__file__).parent/'visibility_summary.csv', Path('visibility_summary.csv')]:
        if p.exists():
            df = pd.read_csv(str(p))
            df['check_date'] = pd.to_datetime(df['check_date']).dt.date
            return df
    return None

@st.cache_data
def load_positions():
    for p in [Path(__file__).parent/'svetlux_positions.csv', Path('svetlux_positions.csv')]:
        if p.exists():
            df = pd.read_csv(str(p))
            df['check_date'] = pd.to_datetime(df['check_date']).dt.date
            df['position'] = pd.to_numeric(df['position'], errors='coerce')
            return df
    return pd.DataFrame()

df_sum = load_summary()
df_pos = load_positions()

if df_sum is None:
    st.error('Файл visibility_summary.csv не найден. Загрузи файлы на GitHub.')
    st.stop()

all_dates  = sorted(df_sum['check_date'].unique(), reverse=True)
all_domains = sorted(df_sum['domain'].unique().tolist())
our = 'svetlux.ru'

# ── Сайдбар ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('⚙️ Настройки')
    engine_label = st.radio('Поисковик', ['Яндекс','Google'], horizontal=True)
    engine_key   = 'yandex' if engine_label=='Яндекс' else 'google'
    sel_date     = st.selectbox('Дата', all_dates,
                                format_func=lambda d: d.strftime('%d.%m.%Y'))
    competitors  = [d for d in all_domains if d != our]
    sel_comp     = st.multiselect('Конкуренты', competitors, default=competitors)
    show_domains = [our] + sel_comp
    st.divider()
    hide_brand = st.toggle('Скрыть брендовые запросы', value=True)
    st.divider()
    st.caption(f'Дат в базе: {len(all_dates)}')
    last = max(all_dates)
    st.caption(f'Обновлено: {last.strftime("%d.%m.%Y")}')

# ── Фильтр данных (только сводка — маленький датафрейм) ───────────────────
mask = (
    (df_sum['check_date'] == sel_date) &
    (df_sum['engine']     == engine_key) &
    (df_sum['hide_brand'] == hide_brand)
)
df_cur = df_sum[mask].copy()

prev_dates = [d for d in all_dates if d < sel_date]
if prev_dates:
    mask_prev = (
        (df_sum['check_date'] == prev_dates[0]) &
        (df_sum['engine']     == engine_key) &
        (df_sum['hide_brand'] == hide_brand)
    )
    df_prev = df_sum[mask_prev].copy()
else:
    df_prev = pd.DataFrame()

our_row  = df_cur[df_cur['domain']==our]
total_q  = int(our_row['total_queries'].iloc[0]) if len(our_row) else 0
vis_cur  = float(our_row['visibility'].iloc[0]) if len(our_row) else 0
top3_cur = int(our_row['top3'].iloc[0]) if len(our_row) else 0
top10_cur= int(our_row['top10'].iloc[0]) if len(our_row) else 0
nf_cur   = int(our_row['not_found'].iloc[0]) if len(our_row) else 0

if len(df_prev):
    our_prev = df_prev[df_prev['domain']==our]
    vis_prev = float(our_prev['visibility'].iloc[0]) if len(our_prev) else None
else:
    vis_prev = None

# ── Заголовок ─────────────────────────────────────────────────────────────
st.title('💡 Светлюкс — Видимость в поисковиках')
st.subheader(f'{engine_label} · {sel_date.strftime("%d.%m.%Y")} · {total_q} запросов')

def delta(cur, prev):
    if prev is None: return ''
    d = cur - prev
    if d == 0: return ' <span style="color:#888">→0</span>'
    color = '#28a745' if d > 0 else '#dc3545'
    arrow = '▲' if d > 0 else '▼'
    return f' <span style="color:{color}">{arrow}{abs(d):.1f}</span>'

c1,c2,c3,c4 = st.columns(4)
for col, val, d_html, label in [
    (c1, f'{vis_cur:.1f}%', delta(vis_cur, vis_prev), 'Видимость svetlux.ru'),
    (c2, top3_cur,  '', 'Запросов в Топ 1–3'),
    (c3, top10_cur, '', 'Запросов в Топ 4–10'),
    (c4, nf_cur,    '', 'Не в Топ-50'),
]:
    col.markdown(
        f'<div class="metric-card"><div class="metric-value">{val}{d_html}</div>'
        f'<div class="metric-label">{label}</div></div>',
        unsafe_allow_html=True)

st.divider()

# ── Таблица + График ──────────────────────────────────────────────────────
col_l, col_r = st.columns(2, gap='large')

with col_l:
    st.subheader('🏆 Сравнение видимости')
    df_show = df_cur[df_cur['domain'].isin(show_domains)].copy()
    if len(df_prev):
        df_show = df_show.merge(
            df_prev[['domain','visibility']].rename(columns={'visibility':'vis_prev'}),
            on='domain', how='left'
        )
        df_show['Δ'] = (df_show['visibility'] - df_show['vis_prev']).round(1)
        df_show['Δ'] = df_show['Δ'].map(
            lambda x: f'+{x:.1f}' if pd.notna(x) and x>0 else (f'{x:.1f}' if pd.notna(x) else '—'))
    df_show = df_show.sort_values('visibility', ascending=False).reset_index(drop=True)
    df_show.index += 1
    cols_show = ['domain','visibility','top3','top10','top20','top50','not_found']
    if 'Δ' in df_show.columns: cols_show.insert(2,'Δ')
    df_show_out = df_show[cols_show].rename(columns={
        'domain':'Домен','visibility':'Видимость','top3':'Топ 1–3',
        'top10':'Топ 4–10','top20':'Топ 11–20','top50':'Топ 21–50','not_found':'Не в топ-50'
    })
    df_show_out['Видимость'] = df_show_out['Видимость'].map(lambda x: f'{x:.1f}%')
    st.dataframe(df_show_out, height=420)

with col_r:
    st.subheader('📊 Видимость')
    df_bar = df_cur[df_cur['domain'].isin(show_domains)].sort_values('visibility')
    fig = px.bar(df_bar, x='visibility', y='domain', orientation='h',
                 color='domain', color_discrete_map=DOMAIN_COLORS,
                 text='visibility', labels={'visibility':'Видимость, %','domain':''})
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(height=max(300, len(show_domains)*22),
                      showlegend=False, margin=dict(l=0,r=70,t=10,b=0),
                      plot_bgcolor='white', paper_bgcolor='white',
                      xaxis=dict(ticksuffix='%'))
    st.plotly_chart(fig, use_container_width=True)

# ── График динамики (если есть история) ──────────────────────────────────
hist_dates = [d for d in all_dates if d <= sel_date]
if len(hist_dates) >= 2:
    st.divider()
    st.subheader('📈 Динамика видимости')
    mask_hist = (
        (df_sum['check_date'].isin(hist_dates)) &
        (df_sum['engine']     == engine_key) &
        (df_sum['hide_brand'] == hide_brand) &
        (df_sum['domain'].isin(show_domains))
    )
    df_hist = df_sum[mask_hist].rename(columns={'check_date':'Дата','domain':'Домен','visibility':'Видимость'})
    fig2 = px.line(df_hist, x='Дата', y='Видимость', color='Домен',
                   color_discrete_map=DOMAIN_COLORS, markers=True,
                   labels={'Видимость':'Видимость, %','Дата':''})
    fig2.update_traces(line_width=2, marker_size=6)
    for tr in fig2.data:
        if tr.name == our: tr.line.width = 4
    fig2.update_layout(height=350, margin=dict(l=0,r=0,t=10,b=0),
                       plot_bgcolor='white', paper_bgcolor='white',
                       yaxis=dict(ticksuffix='%'),
                       legend=dict(orientation='h', y=1.1, x=0, font=dict(size=9)))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Позиции svetlux.ru ────────────────────────────────────────────────────
st.subheader('🔍 Позиции svetlux.ru по запросам')
if len(df_pos):
    mask_p = (
        (df_pos['check_date'] == sel_date) &
        (df_pos['engine']     == engine_key)
    )
    if hide_brand:
        mask_p = mask_p & (~df_pos['is_brand'].fillna(False))
    df_p = df_pos[mask_p][['query','position']].sort_values('position').reset_index(drop=True)

    col_f1, col_f2 = st.columns([2,1])
    with col_f1:
        search = st.text_input('Поиск по запросу', placeholder='люстра')
    with col_f2:
        pos_limit = st.select_slider('Позиции',
            options=['Топ 3','Топ 10','Топ 20','Топ 50','Все'], value='Топ 50')

    lim = {'Топ 3':3,'Топ 10':10,'Топ 20':20,'Топ 50':50,'Все':999}[pos_limit]
    df_p = df_p[df_p['position'] <= lim]
    if search:
        df_p = df_p[df_p['query'].str.contains(search.lower(), na=False)]
    df_p.columns = ['Запрос','Позиция']
    df_p['Позиция'] = df_p['Позиция'].apply(lambda x: int(x) if pd.notna(x) else '—')
    df_p.index = range(1, len(df_p)+1)
    st.dataframe(df_p, height=400)
    st.caption(f'Показано: {len(df_p)} запросов')

st.divider()
st.caption('Данные: XMLRiver.Parser · Топ-50 · Москва')
