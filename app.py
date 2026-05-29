import streamlit as st
import pandas as pd
import numpy as np
import requests
import io

st.set_page_config(page_title='Grid Radar', page_icon='🎯', layout='wide')

API_BASE = 'https://juancarlosmonsalveg.com/diarioconsciente/api/gr'

def verificar_token(token):
    try:
        r = requests.get(f'{API_BASE}/verify_token.php', params={'token': token}, timeout=10)
        return r.json()
    except:
        return {'valid': False, 'error': 'Error de conexion'}

def verificar_sesion(session_token):
    try:
        r = requests.get(f'{API_BASE}/verify_session.php', params={'session_token': session_token}, timeout=10)
        return r.json()
    except:
        return {'valid': False, 'error': 'Error de conexion'}

def check_auth():
    params = st.query_params
    if 'session_token' in st.session_state:
        data = verificar_sesion(st.session_state['session_token'])
        if not data.get('valid'):
            st.session_state.clear()
            st.rerun()
    elif 'token' in params:
        data = verificar_token(params['token'])
        if data.get('valid'):
            st.session_state['session_token'] = data['session_token']
            st.session_state['user_id']       = data['user_id']
            st.session_state['email']         = data['email']
            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"Acceso denegado: {data.get('error','')}")
            st.markdown('[Volver a Diario Consciente](https://juancarlosmonsalveg.com/diarioconsciente)')
            st.stop()
    else:
        st.error('Acceso no autorizado.')
        st.markdown('[Volver a Diario Consciente](https://juancarlosmonsalveg.com/diarioconsciente)')
        st.stop()

NOMBRES_FECHA = ['date','time','fecha','datetime','timestamp','bar','bartime','gmt time','gmt_time','<date>','<time>','date_time','periodo','period']

def parsear_fecha(serie):
    for fmt in ['%Y%m%d %H:%M:%S.%f','%Y%m%d %H:%M:%S','%Y%m%d','%Y-%m-%d %H:%M:%S','%Y-%m-%d','%d/%m/%Y %H:%M:%S','%d/%m/%Y','%m/%d/%Y','%d.%m.%Y','%Y.%m.%d %H:%M','%Y.%m.%d']:
        try: return pd.to_datetime(serie, format=fmt)
        except: continue
    try: return pd.to_datetime(serie, format='mixed', dayfirst=False)
    except: return None

def cargar_csv(archivo):
    contenido = archivo.read().decode('utf-8', errors='replace')
    pl = contenido.split('\n')[0]
    sep = ';' if ';' in pl else ('\t' if '\t' in pl else ',')
    df_raw = pd.read_csv(io.StringIO(contenido), sep=sep, on_bad_lines='skip', skipinitialspace=True)
    df_raw.columns = df_raw.columns.str.strip()
    col_map = {}
    for col in df_raw.columns:
        cl = col.lower().strip()
        if cl in NOMBRES_FECHA or any(n in cl for n in NOMBRES_FECHA):
            if 'date' not in col_map.values(): col_map[col] = 'date'
        elif cl in ['open','apertura']:    col_map[col] = 'open'
        elif cl in ['high','alto','max']:  col_map[col] = 'high'
        elif cl in ['low','bajo','min']:   col_map[col] = 'low'
        elif cl in ['close','cierre']:     col_map[col] = 'close'
    df_raw = df_raw.rename(columns=col_map)
    if any(c not in df_raw.columns for c in ['date','open','high','low','close']):
        return None, f"Columnas faltantes. Encontradas: {list(df_raw.columns)}"
    fechas = parsear_fecha(df_raw['date'].astype(str))
    if fechas is None: return None, 'No se pudo parsear la fecha.'
    df_raw['date'] = fechas
    df = df_raw[['date','open','high','low','close']].copy()
    for c in ['open','high','low','close']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['open','high','low','close'])
    df = df.sort_values('date').reset_index(drop=True)
    return df, None

def calcular_adx_arr(high, low, close, period=14):
    h,l,c = np.array(high),np.array(low),np.array(close)
    n=len(c); adx=np.full(n,np.nan); dx=np.zeros(n); str_=spdm=smdm=0.0
    for i in range(1,period):
        tr=max(h[i],c[i-1])-min(l[i],c[i-1]); up=h[i]-h[i-1]; dn=l[i-1]-l[i]
        str_+=tr; spdm+=max(up,0.0) if up>dn else 0.0; smdm+=max(dn,0.0) if dn>up else 0.0
    for i in range(period,n):
        tr=max(h[i],c[i-1])-min(l[i],c[i-1]); up=h[i]-h[i-1]; dn=l[i-1]-l[i]
        pdm=up if(up>dn and up>0) else 0.0; mdm=dn if(dn>up and dn>0) else 0.0
        str_=(str_*(period-1)+tr)/period; spdm=(spdm*(period-1)+pdm)/period; smdm=(smdm*(period-1)+mdm)/period
        pi=100*spdm/str_ if str_>0 else 0.0; mi=100*smdm/str_ if str_>0 else 0.0
        ds=pi+mi; dx[i]=100*abs(pi-mi)/ds if ds>0 else 0.0
    sdx=dx[period]
    for i in range(period+1,n): sdx=(sdx*(period-1)+dx[i])/period; adx[i]=sdx
    return adx

check_auth()

with st.sidebar:
    st.title('Grid Radar')
    st.caption('Trader Consciente')
    st.divider()
    seleccion = st.radio('', ['Inicio','Como funciona','Analisis de pares'], label_visibility='collapsed')
    st.divider()
    st.caption(st.session_state.get('email',''))
    if st.button('Cerrar sesion', use_container_width=True):
        st.session_state.clear(); st.rerun()

email = st.session_state.get('email','')

def ph(t, s, e='🎯'):
    st.markdown(f'## {e} {t}')
    st.caption(s)
    st.markdown(f'**Usuario:** {email}')
    st.divider()

if seleccion == 'Inicio':
    ph('Grid Radar','Detecta cuando es seguro operar robots Grid y Martingala')
    st.markdown('**Grid Radar** analiza datos historicos OHLC y te dice en que meses es seguro tener activos tus robots de cobertura, cuando reducir el lotaje, y cuando apagarlos.')
    c1,c2,c3 = st.columns(3)
    with c1:
        st.info('📁 **1. Sube tus datos**\n\nCSV con datos OHLC D1 de uno o varios pares')
    with c2:
        st.info('🔍 **2. Analisis automatico**\n\n5 metricas calculadas mes a mes para cada par')
    with c3:
        st.info('🚦 **3. Semaforo de riesgo**\n\nVerde Seguro / Amarillo Precaucion / Rojo No operar')
    st.info('Usa el menu de la izquierda para navegar.')

elif seleccion == 'Como funciona':
    ph('Como funciona Grid Radar','Entiende que mide cada metrica','📖')
    with st.expander('Efficiency Ratio (ER)', expanded=False):
        st.markdown('**Que mide:** Que tan eficiente fue el movimiento del precio: si fue en linea recta (tendencia) o caotico (lateral).')
        st.code('ER = Desplazamiento neto del mes / Suma de todos los movimientos diarios\nER < 0.25 = Verde (lateral) | ER 0.25-0.40 = Amarillo | ER > 0.40 = Rojo (tendencia)')
        st.markdown('**Por que importa:** El grid gana cuando el precio va y vuelve. ER alto significa que el precio se fue sin regresar.')
    with st.expander('ADX - Average Directional Index', expanded=False):
        st.markdown('**Que mide:** La fuerza de la tendencia. No dice si sube o baja, solo que tan fuerte es el movimiento.')
        st.code('ADX < 20 = Verde (sin tendencia) | ADX 20-28 = Amarillo | ADX > 28 = Rojo (tendencia fuerte)')
        st.markdown('**Por que importa:** Si el ADX esta bajo el mercado lateraliza. Si sube, el grid acumula perdidas.')
    with st.expander('ATR Normalizado', expanded=False):
        st.markdown('**Que mide:** El rango promedio de movimiento diario como porcentaje del precio. Que tan grandes son las velas.')
        st.code('ATR% = Average True Range / Precio de cierre x 100\nBajo (menor 80% promedio) = Verde | Medio = Amarillo | Alto (mayor 150%) = Rojo')
        st.markdown('**Por que importa:** Meses de ATR alto requieren mas capital de respaldo en el grid.')
    with st.expander('Porcentaje de velas en la misma direccion', expanded=False):
        st.markdown('**Que mide:** Que porcentaje de dias del mes cerraron en la misma direccion.')
        st.code('menor 60% = Verde | 60-68% = Amarillo | mayor 68% = Rojo')
        st.markdown('**Por que importa:** Si la mayoria de velas van en la misma direccion el precio camina sostenidamente.')
    with st.expander('Volatilidad Historica Mensual', expanded=False):
        st.markdown('**Que mide:** La dispersion estadistica de los retornos diarios. Que tan impredecibles fueron los movimientos.')
        st.code('Vol = Desviacion estandar de retornos diarios x raiz(22)\nBaja (menor 80%) = Verde | Media = Amarillo | Alta (mayor 150%) = Rojo')
        st.markdown('**Por que importa:** Alta volatilidad significa movimientos bruscos. El grid necesita predecibilidad.')
    st.info('**Semaforo combinado:** Cada metrica da 0-3 puntos.\n\n🟢 VERDE (0-3): Opera con lotaje normal.\n\n🟡 AMARILLO (4-7): Reduce el lotaje a la mitad.\n\n🔴 ROJO (8-15): No encender el robot.')

elif seleccion == 'Analisis de pares':
    ph('Analisis de Pares','Sube tus datos y obten el semaforo de riesgo','📊')
    st.info('Sube uno o varios archivos CSV con datos OHLC en timeframe D1. Minimo 3 anos de datos recomendados.')
    archivos = st.file_uploader('Selecciona uno o varios archivos CSV', type=['csv'], accept_multiple_files=True)
    if not archivos:
        st.info('Sube al menos un archivo CSV para comenzar.')
    else:
        pares_data = {}
        for archivo in archivos:
            nombre = archivo.name.replace('.csv','').replace('_D1','').replace('_d1','').replace('_','').upper()
            df, error = cargar_csv(archivo)
            if error:
                st.error(f'Error en {nombre}: {error}')
            else:
                pares_data[nombre] = df
                st.success(f'{nombre} cargado - {len(df):,} barras ({df["date"].min().strftime("%Y-%m-%d")} al {df["date"].max().strftime("%Y-%m-%d")})')
        if pares_data and st.button('Analizar todos los pares', use_container_width=True, type='primary'):
            todos = []
            prog  = st.progress(0, text='Analizando...')
            MESES = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
            for idx, (nombre, df) in enumerate(pares_data.items()):
                prog.progress((idx+1)/len(pares_data), text=f'Analizando {nombre}...')
                df = df.copy()
                df['mes']  = df['date'].dt.month
                df['anio'] = df['date'].dt.year
                df['retorno'] = df['close'].pct_change()
                tr = pd.concat([df['high']-df['low'],(df['high']-df['close'].shift(1)).abs(),(df['low']-df['close'].shift(1)).abs()], axis=1).max(axis=1)
                df['atr_pct']  = tr.rolling(14).mean() / df['close'] * 100
                df['adx']      = calcular_adx_arr(df['high'].values, df['low'].values, df['close'].values)
                df['vol_hist'] = df['retorno'].rolling(22).std() * np.sqrt(22) * 100
                atr_anual = df['atr_pct'].dropna().mean()
                vol_anual = df['vol_hist'].dropna().mean()
                for mes in range(1,13):
                    dm = df[df['mes']==mes].copy()
                    if len(dm) < 10: continue
                    er_l=[];adx_l=[];atr_l=[];vol_l=[];dir_l=[]
                    for anio in dm['anio'].unique():
                        d = dm[dm['anio']==anio]
                        if len(d) < 5: continue
                        desp=abs(d['close'].iloc[-1]-d['close'].iloc[0])
                        mov=d['close'].diff().abs().sum()
                        er_l.append(desp/mov if mov>0 else 0)
                        av=d['adx'].dropna().mean()
                        if not np.isnan(av): adx_l.append(av)
                        av2=d['atr_pct'].dropna().mean()
                        if not np.isnan(av2): atr_l.append(av2)
                        av3=d['vol_hist'].dropna().mean()
                        if not np.isnan(av3): vol_l.append(av3)
                        vu=(d['close']>d['open']).sum(); vd=(d['close']<d['open']).sum(); tot=vu+vd
                        dir_l.append(max(vu,vd)/tot if tot>0 else 0.5)
                    if not er_l: continue
                    er=np.mean(er_l); adx=np.mean(adx_l) if adx_l else 25
                    atr=np.mean(atr_l) if atr_l else atr_anual
                    vol=np.mean(vol_l) if vol_l else vol_anual
                    dir_=np.mean(dir_l)
                    p=0
                    if er>=0.40: p+=3
                    elif er>=0.25: p+=1
                    if adx>=36: p+=3
                    elif adx>=28: p+=2
                    elif adx>=20: p+=1
                    if atr>=atr_anual*1.5: p+=3
                    elif atr>=atr_anual*1.2: p+=2
                    elif atr>=atr_anual*0.8: p+=1
                    if dir_>=0.75: p+=3
                    elif dir_>=0.68: p+=2
                    elif dir_>=0.60: p+=1
                    if vol>=vol_anual*1.5: p+=3
                    elif vol>=vol_anual*1.2: p+=2
                    elif vol>=vol_anual*0.8: p+=1
                    sem='🟢' if p<=3 else ('🟡' if p<=7 else '🔴')
                    todos.append({'par':nombre,'mes_num':mes,'mes':MESES[mes],'er':round(er,3),'adx':round(adx,1),'atr_pct':round(atr,3),'vol_hist':round(vol,2),'dir_velas':round(dir_,2),'puntos':p,'semaforo':sem})
            prog.progress(1.0, text='Completado')
            st.session_state['gr_res']   = pd.DataFrame(todos)
            st.session_state['gr_pares'] = list(pares_data.keys())
        if 'gr_res' in st.session_state:
            df_total = st.session_state['gr_res']
            pares    = st.session_state['gr_pares']
            MESES_C  = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
            st.divider()
            st.subheader('Semaforo por mes y par')
            pivot = df_total.pivot_table(index='par', columns='mes_num', values='semaforo', aggfunc='first')
            pivot.columns = [MESES_C.get(c,str(c)) for c in pivot.columns]
            st.dataframe(pivot, use_container_width=True)
            st.divider()
            st.subheader('Recomendaciones por par')
            for par in pares:
                dp = df_total[df_total['par']==par].sort_values('mes_num')
                mv = dp[dp['semaforo']=='🟢']['mes'].tolist()
                ma = dp[dp['semaforo']=='🟡']['mes'].tolist()
                mr = dp[dp['semaforo']=='🔴']['mes'].tolist()
                with st.expander(f'Par: {par}', expanded=True):
                    c1,c2,c3 = st.columns(3)
                    with c1: st.success(f'🟢 SEGUROS ({len(mv)})\n{chr(10).join(mv) or "Ninguno"}')
                    with c2: st.warning(f'🟡 PRECAUCION ({len(ma)})\n{chr(10).join(ma) or "Ninguno"}')
                    with c3: st.error(f'🔴 NO OPERAR ({len(mr)})\n{chr(10).join(mr) or "Ninguno"}')
                    if mv: st.success(f'Enciende tu robot en: {chr(44).join(mv)}')
                    if ma: st.warning(f'Reduce el lotaje a la mitad en: {chr(44).join(ma)}')
                    if mr: st.error(f'No enciendas el robot en: {chr(44).join(mr)}')
                    st.dataframe(dp[['mes','semaforo','er','adx','atr_pct','vol_hist','dir_velas']].rename(columns={'mes':'Mes','semaforo':'Semaforo','er':'ER','adx':'ADX','atr_pct':'ATR pct','vol_hist':'Vol pct','dir_velas':'Dir Velas'}).style.format({'ER':'{:.3f}','ADX':'{:.1f}','ATR pct':'{:.3f}','Vol pct':'{:.2f}','Dir Velas':'{:.0%}'}), use_container_width=True, hide_index=True)
            if len(pares) > 1:
                st.divider()
                st.subheader('Comparativa entre pares')
                comp = []
                for par in pares:
                    dp = df_total[df_total['par']==par]
                    comp.append({'Par':par,'Meses seguros':(dp['semaforo']=='🟢').sum(),'Precaucion':(dp['semaforo']=='🟡').sum(),'Peligrosos':(dp['semaforo']=='🔴').sum(),'ER promedio':round(dp['er'].mean(),3),'ADX promedio':round(dp['adx'].mean(),1)})
                df_comp = pd.DataFrame(comp).sort_values('Meses seguros', ascending=False)
                st.dataframe(df_comp, use_container_width=True, hide_index=True)
                mejor = df_comp.iloc[0]['Par']; peor = df_comp.iloc[-1]['Par']
                st.success(f'{mejor} es el par mas seguro para Grid con {df_comp.iloc[0]["Meses seguros"]} meses verdes. {peor} es el mas peligroso con {df_comp.iloc[-1]["Peligrosos"]} meses rojos.')
