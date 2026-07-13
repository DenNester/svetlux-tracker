import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

st.set_page_config(page_title='Светлюкс — Видимость', page_icon='💡', layout='wide')

st.markdown("""<style>
.metric-card{background:#f8f9fa;border-radius:10px;padding:14px 18px;
             border-left:4px solid #1F4E79;margin-bottom:8px;}
.metric-value{font-size:1.7rem;font-weight:700;color:#1F4E79;line-height:1.2;}
.metric-label{font-size:0.8rem;color:#666;margin-top:3px;}
.metric-delta-pos{color:#28a745;font-size:0.85rem;font-weight:600;}
.metric-delta-neg{color:#dc3545;font-size:0.85rem;font-weight:600;}
.metric-delta-neu{color:#888;font-size:0.85rem;}
.section-title{font-size:1.1rem;font-weight:600;color:#1F4E79;margin-bottom:8px;}
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

REQUIRED_SUMMARY_COLS = ['check_date','engine','domain','hide_brand','total_queries',
                         'visibility_weighted','top3','top10','top11_50','top1_50',
                         'not_found','avg_position','median_position','unique_urls']
REQUIRED_POSITIONS_COLS = ['check_date','engine','query','position']

@st.cache_data
def load_summary():
    for p in [Path(__file__).parent/'visibility_summary.csv', Path('visibility_summary.csv')]:
        if p.exists():
            df = pd.read_csv(str(p), encoding='utf-8-sig')
            df.columns = df.columns.str.strip()
            missing = [c for c in REQUIRED_SUMMARY_COLS if c not in df.columns]
            if missing:
                st.error(
                    f'❌ В visibility_summary.csv не хватает колонок: **{", ".join(missing)}**.\n\n'
                    f'Колонки, которые реально есть в файле: {", ".join(df.columns)}\n\n'
                    f'Похоже, в репозитории на GitHub лежит не та версия файла — проверь, '
                    f'что закоммичен актуальный CSV с этими колонками.'
                )
                st.stop()
            df['check_date'] = pd.to_datetime(df['check_date']).dt.date
            if df['hide_brand'].dtype != bool:
                df['hide_brand'] = df['hide_brand'].astype(str).str.strip().str.lower().map(
                    {'true': True, 'false': False, '1': True, '0': False,
                     'истина': True, 'ложь': False}
                )
            return df
    return None

@st.cache_data
def load_positions():
    for p in [Path(__file__).parent/'svetlux_positions.csv', Path('svetlux_positions.csv')]:
        if p.exists():
            df = pd.read_csv(str(p), encoding='utf-8-sig')
            df.columns = df.columns.str.strip()
            missing = [c for c in REQUIRED_POSITIONS_COLS if c not in df.columns]
            if missing:
                st.error(
                    f'❌ В svetlux_positions.csv не хватает колонок: **{", ".join(missing)}**.\n\n'
                    f'Колонки, которые реально есть в файле: {", ".join(df.columns)}'
                )
                st.stop()
            df['check_date'] = pd.to_datetime(df['check_date']).dt.date
            df['position'] = pd.to_numeric(df['position'], errors='coerce')
            return df
    return pd.DataFrame()

df_sum = load_summary()
df_pos = load_positions()

if df_sum is None:
    st.error('Файл visibility_summary.csv не найден.')
    st.stop()

all_dates   = sorted(df_sum['check_date'].unique(), reverse=True)
all_domains = sorted(df_sum['domain'].unique().tolist())
our = 'svetlux.ru'

# Автоцвет для доменов, которых нет в DOMAIN_COLORS — чтобы не ломать консистентность графиков
_FALLBACK_PALETTE = px.colors.qualitative.Set3
_unmapped = [d for d in all_domains if d not in DOMAIN_COLORS]
for i, d in enumerate(_unmapped):
    DOMAIN_COLORS[d] = _FALLBACK_PALETTE[i % len(_FALLBACK_PALETTE)]

# ── Сайдбар ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('⚙️ Настройки')
    engine_label = st.radio('Поисковик', ['Яндекс','Google'], horizontal=True)
    engine_key   = 'yandex' if engine_label=='Яндекс' else 'google'

    st.markdown('**Текущая дата**')
    sel_date = st.selectbox('Дата просмотра', all_dates,
                            format_func=lambda d: d.strftime('%d.%m.%Y'),
                            key='main_date')

    st.markdown('**Дата сравнения**')
    cmp_options = ['Предыдущее измерение'] + [d.strftime('%d.%m.%Y') for d in all_dates if d != sel_date]
    if len(cmp_options) == 1:
        st.caption('Пока только 1 дата в базе — сравнивать не с чем.')
        cmp_date = None
    else:
        cmp_choice = st.selectbox('Сравнить с', cmp_options, key='cmp_date')
        if cmp_choice == 'Предыдущее измерение':
            prev_list = [d for d in all_dates if d < sel_date]
            cmp_date  = prev_list[0] if prev_list else None
        else:
            cmp_date = pd.to_datetime(cmp_choice, format='%d.%m.%Y').date()

    st.divider()
    if st.button('🔄 Обновить данные', use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    competitors = [d for d in all_domains if d != our]
    sel_comp    = st.multiselect('Конкуренты', competitors, default=competitors)
    show_domains = [our] + sel_comp

    st.divider()
    hide_brand = st.toggle('Скрыть брендовые запросы', value=True)
    st.divider()
    st.caption(f'Измерений в базе: {len(all_dates)}')
    st.caption(f'Последнее: {max(all_dates).strftime("%d.%m.%Y")}')
    if cmp_date:
        st.caption(f'Сравнение с: {cmp_date.strftime("%d.%m.%Y")}')

# ── Фильтр данных ─────────────────────────────────────────────────────────
def get_slice(date):
    if date is None:
        return df_sum.iloc[0:0].copy()  # пусто, но с теми же колонками — не ломает our_val
    return df_sum[(df_sum['check_date']==date) &
                  (df_sum['engine']==engine_key) &
                  (df_sum['hide_brand']==hide_brand)].copy()

df_cur  = get_slice(sel_date)
df_cmp  = get_slice(cmp_date)

def our_val(df, col, default=None):
    if 'domain' not in df.columns or col not in df.columns:
        return default
    row = df[df['domain']==our]
    return row[col].iloc[0] if len(row) else default

total_q  = our_val(df_cur, 'total_queries', 0)
vis_cur  = our_val(df_cur, 'visibility_weighted', 0.0)
top3_cur = our_val(df_cur, 'top3', 0)
top10_cur= our_val(df_cur, 'top10', 0)
top1150  = our_val(df_cur, 'top11_50', 0)
top150   = our_val(df_cur, 'top1_50', 0)
nf_cur   = our_val(df_cur, 'not_found', 0)
avg_cur  = our_val(df_cur, 'avg_position')
med_cur  = our_val(df_cur, 'median_position')
url_cur  = our_val(df_cur, 'unique_urls', 0)
cov_cur  = (top150 / total_q * 100) if total_q else 0.0

vis_cmp  = our_val(df_cmp, 'visibility_weighted')
top3_cmp = our_val(df_cmp, 'top3')
top10_cmp= our_val(df_cmp, 'top10')
top1150c = our_val(df_cmp, 'top11_50')
avg_cmp  = our_val(df_cmp, 'avg_position')
med_cmp  = our_val(df_cmp, 'median_position')
top150c  = our_val(df_cmp, 'top1_50')
total_qc = our_val(df_cmp, 'total_queries')
cov_cmp  = (top150c / total_qc * 100) if (top150c is not None and total_qc) else None

def delta_badge(cur, prev, fmt='.1f', invert=False):
    """Returns HTML badge with delta"""
    if prev is None or cur is None: return ''
    try: d = float(cur) - float(prev)
    except: return ''
    if abs(d) < 0.05: return ' <span class="metric-delta-neu">→ 0</span>'
    positive = d > 0
    if invert: positive = not positive
    cls  = 'metric-delta-pos' if positive else 'metric-delta-neg'
    arrow = '▲' if d > 0 else '▼'
    val  = abs(d)
    s    = f'{val:{fmt}}' if '.' in fmt else str(int(val))
    return f' <span class="{cls}">{arrow}{s}</span>'

# ── Заголовок ─────────────────────────────────────────────────────────────
st.title('💡 Светлюкс — Видимость в поисковиках')
cmp_label = f' (vs {cmp_date.strftime("%d.%m")})' if cmp_date else ''
st.subheader(f'{engine_label} · {sel_date.strftime("%d.%m.%Y")}{cmp_label} · {total_q} запросов')

# ── КПИ строка 1: основные ────────────────────────────────────────────────
c1,c2,c3,c4 = st.columns(4)
kpi1 = [
    (c1, f'{vis_cur:.1f}%', delta_badge(vis_cur, vis_cmp), 'Видимость (взвеш.)'),
    (c2, top3_cur,  delta_badge(top3_cur, top3_cmp, fmt='d'),   'Топ 1–3'),
    (c3, top10_cur, delta_badge(top10_cur, top10_cmp, fmt='d'),  'Топ 1–10'),
    (c4, top1150,   delta_badge(top1150, top1150c, fmt='d'),     'Топ 11–50'),
]
for col, val, d, label in kpi1:
    col.markdown(
        f'<div class="metric-card"><div class="metric-value">{val}{d}</div>'
        f'<div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

# ── КПИ строка 2: позиции и охват ─────────────────────────────────────────
c5,c6,c7,c8,c9 = st.columns(5)
kpi2 = [
    (c5, f'{avg_cur:.1f}' if avg_cur else '—',
         delta_badge(avg_cur, avg_cmp, invert=True), 'Средняя позиция'),
    (c6, f'{med_cur:.1f}' if med_cur else '—',
         delta_badge(med_cur, med_cmp, invert=True), 'Медианная позиция'),
    (c7, f'{cov_cur:.1f}%', delta_badge(cov_cur, cov_cmp), 'Покрытие в Топ-50'),
    (c8, url_cur, '', 'URL в выдаче'),
    (c9, nf_cur,  '', 'Не в Топ-50'),
]
for col, val, d, label in kpi2:
    col.markdown(
        f'<div class="metric-card"><div class="metric-value">{val}{d}</div>'
        f'<div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

st.divider()

# ── Таблица + Бар ─────────────────────────────────────────────────────────
st.subheader('🏆 Сравнение конкурентов')
df_show = df_cur[df_cur['domain'].isin(show_domains)].copy()
if len(df_cmp):
    df_show = df_show.merge(
        df_cmp[['domain','visibility_weighted','top3','top10','top11_50']].rename(
            columns={'visibility_weighted':'v_c','top3':'t3c','top10':'t10c','top11_50':'t1150c'}),
        on='domain', how='left')
    df_show['Δ Вид.'] = (df_show['visibility_weighted']-df_show['v_c']).round(1).map(
        lambda x: f'+{x:.1f}' if pd.notna(x) and x>0 else (f'{x:.1f}' if pd.notna(x) else '—'))
    df_show['Δ Т1-3'] = (df_show['top3']-df_show['t3c']).map(
        lambda x: f'+{int(x)}' if pd.notna(x) and x>0 else (f'{int(x)}' if pd.notna(x) else '—'))
    df_show['Δ Т1-10'] = (df_show['top10']-df_show['t10c']).map(
        lambda x: f'+{int(x)}' if pd.notna(x) and x>0 else (f'{int(x)}' if pd.notna(x) else '—'))

df_show = df_show.sort_values('visibility_weighted', ascending=False).reset_index(drop=True)
df_show.index += 1

base_cols = ['domain','visibility_weighted','top3','top10','top11_50','avg_position','median_position','unique_urls']
delta_cols = ['Δ Вид.','Δ Т1-3','Δ Т1-10'] if len(df_cmp) else []

df_out = df_show[base_cols + delta_cols].rename(columns={
    'domain':'Домен','visibility_weighted':'Видимость',
    'top3':'Топ 1–3','top10':'Топ 1–10','top11_50':'Топ 11–50',
    'avg_position':'Ср.поз','median_position':'Мед.поз','unique_urls':'URL'})
df_out['Видимость'] = df_out['Видимость'].map(lambda x: f'{x:.1f}%')
df_out['Ср.поз']   = df_out['Ср.поз'].map(lambda x: f'{x:.1f}' if pd.notna(x) else '—')
df_out['Мед.поз']  = df_out['Мед.поз'].map(lambda x: f'{x:.1f}' if pd.notna(x) else '—')

def _highlight_our_row(row):
    is_ours = row['Домен'] == our
    style = 'font-weight: 700; background-color: #EAF2FB;' if is_ours else ''
    return [style] * len(row)

# st.table рендерит полностью, без внутреннего скролла, и поддерживает жирный шрифт через Styler
st.table(df_out.style.apply(_highlight_our_row, axis=1))
st.download_button(
    '⬇️ Экспорт таблицы (CSV)',
    data=df_out.to_csv(index=False).encode('utf-8-sig'),
    file_name=f'svetlux_comparison_{sel_date}.csv',
    mime='text/csv',
    key='dl_comparison',
)

st.subheader('📊 Видимость')
df_bar = df_cur[df_cur['domain'].isin(show_domains)].sort_values('visibility_weighted', ascending=False)
domain_order_top_to_bottom = df_bar['domain'].tolist()
domain_order_bottom_to_top = domain_order_top_to_bottom[::-1]  # для оси Y: первый элемент внизу

fig = px.bar(df_bar, x='visibility_weighted', y='domain', orientation='h',
             color='domain', color_discrete_map=DOMAIN_COLORS,
             text='visibility_weighted',
             labels={'visibility_weighted':'Видимость, %','domain':''})
fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')

# Наибольшая видимость — сверху; наш домен — жирным в подписи и с обводкой столбца
tick_labels = [f'<b>{d}</b>' if d == our else d for d in domain_order_bottom_to_top]
fig.update_yaxes(tickmode='array', tickvals=domain_order_bottom_to_top, ticktext=tick_labels,
                  categoryorder='array', categoryarray=domain_order_bottom_to_top)
for tr in fig.data:
    if tr.name == our:
        tr.marker.line.width = 2
        tr.marker.line.color = '#000000'

fig.update_layout(height=max(300, len(show_domains)*24+60), showlegend=False,
                  margin=dict(l=0,r=70,t=10,b=0),
                  plot_bgcolor='white', paper_bgcolor='white',
                  xaxis=dict(ticksuffix='%'))
st.plotly_chart(fig, use_container_width=True)

# ── Динамика ──────────────────────────────────────────────────────────────
hist_dates = sorted([d for d in all_dates if d <= sel_date])
if len(hist_dates) >= 2:
    st.divider()
    st.subheader('📈 Динамика по датам измерений')

    mask_h = ((df_sum['check_date'].isin(hist_dates)) &
              (df_sum['engine']==engine_key) &
              (df_sum['hide_brand']==hide_brand))
    df_hist = df_sum[mask_h].copy()

    tab_vis, tab_ranges, tab_pos = st.tabs([
        '📉 Видимость', '📊 Диапазоны позиций', '📍 Средняя / медианная позиция'
    ])

    with tab_vis:
        df_hv = df_hist[df_hist['domain'].isin(show_domains)].rename(
            columns={'check_date':'Дата','domain':'Домен','visibility_weighted':'Видимость'})
        fig_v = px.line(df_hv, x='Дата', y='Видимость', color='Домен',
                        color_discrete_map=DOMAIN_COLORS, markers=True,
                        labels={'Видимость':'Видимость, %','Дата':''})
        fig_v.update_traces(line_width=2, marker_size=7)
        for tr in fig_v.data:
            if tr.name == our: tr.line.width=4; tr.marker.size=9
        fig_v.update_layout(height=380, margin=dict(l=0,r=0,t=10,b=0),
                            plot_bgcolor='white', paper_bgcolor='white',
                            yaxis=dict(ticksuffix='%'),
                            legend=dict(orientation='h',y=1.12,x=0,font=dict(size=9)))
        st.plotly_chart(fig_v, use_container_width=True)

    with tab_ranges:
        st.markdown('**Динамика по диапазонам позиций — светлюкс.ru**')
        df_our_hist = df_hist[df_hist['domain']==our].sort_values('check_date')
        if len(df_our_hist) >= 2:
            fig_r = go.Figure()
            for col, name, color in [
                ('top3',    'Топ 1–3',   '#C6EFCE'),
                ('top10',   'Топ 1–10',  '#FFEB9C'),
                ('top11_50','Топ 11–50', '#FCE4D6'),
                ('not_found','Не в топ-50','#F2F2F2'),
            ]:
                fig_r.add_trace(go.Bar(
                    x=df_our_hist['check_date'].astype(str),
                    y=df_our_hist[col],
                    name=name,
                    marker_color=color,
                    marker_line_color='#CCCCCC',
                    marker_line_width=0.5,
                ))
            fig_r.update_layout(
                barmode='stack', height=380,
                margin=dict(l=0,r=0,t=10,b=0),
                plot_bgcolor='white', paper_bgcolor='white',
                legend=dict(orientation='h',y=1.12,x=0),
                xaxis_title='', yaxis_title='Запросов',
            )
            st.plotly_chart(fig_r, use_container_width=True)

        st.markdown('**Сравнение конкурентов по диапазонам (текущая дата)**')
        sel_range = st.selectbox('Диапазон', ['Топ 1–3','Топ 1–10','Топ 11–50'],
                                 key='range_sel')
        range_col = {'Топ 1–3':'top3','Топ 1–10':'top10','Топ 11–50':'top11_50'}[sel_range]
        df_rc = df_cur[df_cur['domain'].isin(show_domains)].sort_values(range_col, ascending=False)
        fig_rc = px.bar(df_rc, x=range_col, y='domain', orientation='h',
                        color='domain', color_discrete_map=DOMAIN_COLORS,
                        text=range_col, labels={range_col:'Запросов','domain':''})
        fig_rc.update_traces(textposition='outside')
        fig_rc.update_layout(height=max(250, len(show_domains)*22+50), showlegend=False,
                              margin=dict(l=0,r=50,t=10,b=0),
                              plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(fig_rc, use_container_width=True)

    with tab_pos:
        st.markdown('**Динамика средней и медианной позиции — светлюкс.ru**')
        df_our_hist = df_hist[df_hist['domain']==our].sort_values('check_date')
        if len(df_our_hist) >= 2:
            fig_p = go.Figure()
            fig_p.add_trace(go.Scatter(
                x=df_our_hist['check_date'].astype(str),
                y=df_our_hist['avg_position'],
                name='Средняя позиция',
                mode='lines+markers',
                line=dict(color='#E8543A', width=2),
                marker=dict(size=8),
            ))
            fig_p.add_trace(go.Scatter(
                x=df_our_hist['check_date'].astype(str),
                y=df_our_hist['median_position'],
                name='Медианная позиция',
                mode='lines+markers',
                line=dict(color='#1F4E79', width=2, dash='dot'),
                marker=dict(size=8),
            ))
            fig_p.update_layout(
                height=320, margin=dict(l=0,r=0,t=10,b=0),
                plot_bgcolor='white', paper_bgcolor='white',
                yaxis=dict(autorange='reversed', title='Позиция (чем меньше — тем лучше)'),
                legend=dict(orientation='h', y=1.12, x=0),
            )
            st.plotly_chart(fig_p, use_container_width=True)
            st.caption('Ось инвертирована: позиция 1 — вверху (лучше), позиция 50 — внизу.')
        else:
            st.info('Накопи хотя бы 2 измерения — тогда появится график динамики.')

st.divider()

# ── Позиции svetlux.ru ────────────────────────────────────────────────────
st.subheader('🔍 Позиции svetlux.ru по запросам')
if len(df_pos):
    mask_p = ((df_pos['check_date']==sel_date) & (df_pos['engine']==engine_key))
    if hide_brand and 'is_brand' in df_pos.columns:
        mask_p = mask_p & (~df_pos['is_brand'].fillna(False))
    df_p = df_pos[mask_p][['query','position']].sort_values('position').reset_index(drop=True)

    col_f1, col_f2 = st.columns([2,1])
    with col_f1:
        search = st.text_input('Поиск по запросу', placeholder='люстра')
    with col_f2:
        pos_limit = st.select_slider('Показать позиции',
            options=['Топ 3','Топ 10','Топ 20','Топ 50','Все'], value='Топ 50')

    lim = {'Топ 3':3,'Топ 10':10,'Топ 20':20,'Топ 50':50,'Все':999}[pos_limit]
    df_p = df_p[df_p['position']<=lim]
    if search:
        df_p = df_p[df_p['query'].str.contains(search.lower(), na=False)]
    df_p.columns = ['Запрос','Позиция']
    df_p['Позиция'] = df_p['Позиция'].apply(lambda x: int(x) if pd.notna(x) else '—')
    df_p.index = range(1, len(df_p)+1)
    st.dataframe(df_p, height=400)
    st.caption(f'Показано: {len(df_p)} запросов')
    st.download_button(
        '⬇️ Экспорт позиций (CSV)',
        data=df_p.to_csv(index=False).encode('utf-8-sig'),
        file_name=f'svetlux_positions_{sel_date}.csv',
        mime='text/csv',
        key='dl_positions',
    )

st.divider()
st.caption('Данные: XMLRiver.Parser · Топ-50 · Москва · Видимость взвешена по частотности Wordstat')
