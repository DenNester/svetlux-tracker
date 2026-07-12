import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

st.set_page_config(page_title='Светлюкс — Видимость', page_icon='💡', layout='wide')

st.markdown("""
<style>
.metric-card { background:#f8f9fa; border-radius:10px; padding:14px 18px;
               border-left:4px solid #1F4E79; margin-bottom:8px; }
.metric-value { font-size:1.8rem; font-weight:700; color:#1F4E79; }
.metric-label { font-size:0.82rem; color:#666; margin-top:2px; }
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

BRAND_PATTERNS = ['светлый сайт','светлюкс','svetlux','svetliy sayt']

@st.cache_data(ttl=600, show_spinner='Загрузка данных...')
def load_data():
    for p in [Path(__file__).parent/'positions_export.csv', Path('positions_export.csv')]:
        if p.exists():
            df = pd.read_csv(str(p), dtype={'query':'string','engine':'category',
                                             'domain':'category','check_date':'string'})
            df['position'] = pd.to_numeric(df['position'], errors='coerce').astype('float32')
            df['check_date'] = pd.to_datetime(df['check_date']).dt.date
            return df
    return None

@st.cache_data(ttl=600, show_spinner=False)
def get_visibility_table(csv_path, engine_key, date_str, hide_brand):
    df = load_data()
    if df is None: return None, 0, {}
    date = pd.to_datetime(date_str).date()
    df_e = df[df['engine']==engine_key]
    df_cur = df_e[df_e['check_date']==date].copy()
    if hide_brand:
        df_cur = df_cur[~df_cur['query'].apply(lambda q: any(p in str(q).lower() for p in BRAND_PATTERNS))]
    total = int(df_cur['query'].nunique())

    def w(p):
        if pd.isna(p): return 0.0
        if p<=3: return [1.0,0.85,0.75][int(p)-1]
        if p<=10: return max(0.55-(p-4)*0.03, 0.3)
        if p<=20: return 0.2
        if p<=50: return 0.05
        return 0.0

    rows = []
    for domain, grp in df_cur.groupby('domain'):
        best = grp.groupby('query')['position'].min()
        vis = round(best.apply(w).sum() / total * 100, 1) if total > 0 else 0
        rows.append({
            'Домен': domain, 'Видимость': vis,
            'Топ 1–3': int((best<=3).sum()),
            'Топ 4–10': int(((best>3)&(best<=10)).sum()),
            'Топ 11–20': int(((best>10)&(best<=20)).sum()),
            'Топ 21–50': int(((best>20)&(best<=50)).sum()),
        })
    df_vis = pd.DataFrame(rows).sort_values('Видимость', ascending=False).reset_index(drop=True)
    df_vis.index += 1

    our_row = df_vis[df_vis['Домен']=='svetlux.ru']
    our_stats = our_row.iloc[0].to_dict() if len(our_row) else {}
    return df_vis, total, our_stats

@st.cache_data(ttl=600, show_spinner=False)
def get_our_positions(csv_path, engine_key, date_str, hide_brand):
    df = load_data()
    if df is None: return pd.DataFrame()
    date = pd.to_datetime(date_str).date()
    df_cur = df[(df['engine']==engine_key)&(df['check_date']==date)&(df['domain']=='svetlux.ru')].copy()
    if hide_brand:
        df_cur = df_cur[~df_cur['query'].apply(lambda q: any(p in str(q).lower() for p in BRAND_PATTERNS))]
    return df_cur[['query','position']].sort_values('position').reset_index(drop=True)

# ── Загрузка ──────────────────────────────────────────────────────────────
df_all = load_data()
if df_all is None:
    st.warning('Файл positions_export.csv не найден.')
    up = st.file_uploader('Загрузи positions_export.csv', type=['csv'])
    if up:
        st.cache_data.clear()
        with open('positions_export.csv','wb') as f: f.write(up.read())
        st.rerun()
    st.stop()

csv_path = str(Path(__file__).parent/'positions_export.csv')
all_dates = sorted(df_all['check_date'].unique(), reverse=True)
all_domains = sorted(df_all['domain'].unique().tolist())
our = 'svetlux.ru'

# ── Сайдбар ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('⚙️ Настройки')
    engine_label = st.radio('Поисковик', ['Яндекс','Google'], horizontal=True)
    engine_key = 'yandex' if engine_label=='Яндекс' else 'google'
    sel_date = st.selectbox('Дата', all_dates, format_func=lambda d: d.strftime('%d.%m.%Y'))
    competitors = [d for d in all_domains if d != our]
    sel_comp = st.multiselect('Конкуренты', competitors, default=competitors[:10])
    show_domains = [our] + sel_comp
    st.divider()
    hide_brand = st.toggle('Скрыть брендовые запросы', value=True)
    st.divider()
    st.caption(f'Дат в базе: {len(all_dates)}')
    st.caption(f'Запросов: {df_all["query"].nunique()}')
    st.caption(f'Обновлено: {max(all_dates).strftime("%d.%m.%Y")}')

date_str = str(sel_date)

# ── Данные ────────────────────────────────────────────────────────────────
df_vis, total_q, our_stats = get_visibility_table(csv_path, engine_key, date_str, hide_brand)
df_our_pos = get_our_positions(csv_path, engine_key, date_str, hide_brand)

vis_cur = our_stats.get('Видимость', 0)
top3    = our_stats.get('Топ 1–3', 0)
top10   = our_stats.get('Топ 4–10', 0)
top50   = our_stats.get('Топ 21–50', 0) + our_stats.get('Топ 11–20', 0) + top10 + top3
not_found = total_q - top50

# ── Заголовок и КПИ ───────────────────────────────────────────────────────
st.title('💡 Светлюкс — Видимость в поисковиках')
st.subheader(f'{engine_label} · {sel_date.strftime("%d.%m.%Y")} · {total_q} запросов')

c1,c2,c3,c4 = st.columns(4)
for col, val, label in [
    (c1, f'{vis_cur:.1f}%', 'Видимость svetlux.ru'),
    (c2, top3,              'Запросов в Топ 1–3'),
    (c3, top10,             'Запросов в Топ 4–10'),
    (c4, not_found,         'Не в Топ-50'),
]:
    col.markdown(
        f'<div class="metric-card"><div class="metric-value">{val}</div>'
        f'<div class="metric-label">{label}</div></div>',
        unsafe_allow_html=True)

st.divider()

# ── Таблица + График ──────────────────────────────────────────────────────
col_l, col_r = st.columns(2, gap='large')

with col_l:
    st.subheader('🏆 Сравнение видимости')
    df_show = df_vis[df_vis['Домен'].isin(show_domains)].copy()
    df_show['Видимость'] = df_show['Видимость'].map(lambda x: f'{x:.1f}%')
    st.dataframe(df_show, height=420)

with col_r:
    st.subheader('📊 Видимость — столбчатая диаграмма')
    df_bar = df_vis[df_vis['Домен'].isin(show_domains)].sort_values('Видимость')
    df_bar['Видимость_num'] = df_bar['Видимость']
    fig = px.bar(df_bar, x='Видимость_num', y='Домен', orientation='h',
                 color='Домен', color_discrete_map=DOMAIN_COLORS,
                 text='Видимость_num',
                 labels={'Видимость_num':'Видимость, %','Домен':''})
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(height=420, showlegend=False,
                      margin=dict(l=0,r=70,t=10,b=0),
                      plot_bgcolor='white', paper_bgcolor='white',
                      xaxis=dict(ticksuffix='%'))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Позиции svetlux.ru ────────────────────────────────────────────────────
st.subheader('🔍 Позиции svetlux.ru по запросам')

col_f1, col_f2 = st.columns([2,1])
with col_f1:
    search = st.text_input('Поиск по запросу', placeholder='люстра')
with col_f2:
    pos_limit = st.select_slider('Показать позиции',
        options=['Топ 3','Топ 10','Топ 20','Топ 50','Все'], value='Топ 50')

limits = {'Топ 3':3,'Топ 10':10,'Топ 20':20,'Топ 50':50,'Все':999}
df_pos = df_our_pos.copy()
if search:
    df_pos = df_pos[df_pos['query'].str.contains(search.lower(), na=False)]
df_pos = df_pos[df_pos['position'] <= limits[pos_limit]]
df_pos.columns = ['Запрос','Позиция']
df_pos['Позиция'] = df_pos['Позиция'].apply(lambda x: int(x) if pd.notna(x) else '—')
df_pos = df_pos.reset_index(drop=True)
df_pos.index += 1

st.dataframe(df_pos, height=450)
st.caption(f'Показано: {len(df_pos)} запросов')

st.divider()
st.caption('Данные: XMLRiver.Parser · Топ-50 · Москва · positions_export.csv')
