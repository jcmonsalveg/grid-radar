import streamlit as st
import pandas as pd
import numpy as np
import requests
import io
from scipy.stats import linregress

st.set_page_config(
    page_title="Grid Radar",
    page_icon="<د",
    layout="wide",
    initial_sidebar_state="expanded"
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap');
:root{--navy:#0E1A3C;--blue:#336BF6;--green:#00C896;--red:#FF4B4B;--yellow:#FFD166;
      --bg:#F4F6FB;--card:#FFFFFF;--border:#E2E8F0;--text:#1A202C;--muted:#718096;}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);}
.main-header{background:linear-gradient(135deg,#0E1A3C 0%,#1a2d6b 100%);padding:2rem 2.5rem;
    border-radius:16px;margin-bottom:2rem;display:flex;align-items:center;gap:1.5rem;}
.main-header h1{font-family:'Space Mono',monospace;font-size:1.6rem;color:#fff;margin:0;}
.main-header p{color:rgba(255,255,255,0.6);margin:0;font-size:0.85rem;}
.badge-user{background:rgba(51,107,246,0.2);border:1px solid rgba(51,107,246,0.4);
    color:#93BBFF;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-family:'Space Mono',monospace;}
.step-card{background:#fff;border:1px solid var(--border);border-radius:12px;padding:1.5rem;margin-bottom:1rem;}
.step-title{font-family:'Space Mono',monospace;font-size:0.85rem;color:var(--blue);
    text-transform:uppercase;letter-spacing:1px;margin-bottom:0.75rem;}
.metric-box{background:var(--bg);border-radius:8px;padding:1rem;text-align:center;}
.metric-val{font-family:'Space Mono',monospace;font-size:1.3rem;font-weight:700;color:var(--navy);}
.metric-lbl{font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-top:4px;}
.alert-ok{background:#E6FBF4;border-left:4px solid #00C896;padding:1rem;border-radius:8px;color:#065f46;margin:1rem 0;}
.alert-fail{background:#FFF0F0;border-left:4px solid #FF4B4B;padding:1rem;border-radius:8px;color:#7f1d1d;margin:1rem 0;}
.sem-verde{background:#E6FBF4;border:2px solid #00C896;border-radius:8px;padding:0.75rem;text-align:center;font-weight:700;color:#065f46;}
.sem-amarillo{background:#FFFBEA;border:2px solid #FFD166;border-radius:8px;padding:0.75rem;text-align:center;font-weight:700;color:#78350f;}
.sem-rojo{background:#FFF0F0;border:2px solid #FF4B4B;border-radius:8px;padding:0.75rem;text-align:center;font-weight:700;color:#7f1d1d;}
div[data-testid="stSidebar"]{background:#0E1A3C;}
div[data-testid="stSidebar"] *{color:white !important;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

API_BASE = "https://soytraderconsciente.com/diarioconsciente/api/gr"

def verificar_token(token):
    try:
        r = requests.get(f"{API_BASE}/verify_token.php", params={"token": token}, timeout=5)
        return r.json()
    except:
        return {"valid": False, "error": "Error de conexion"}

def verificar_sesion(session_token):
    try:
        r = requests.get(f"{API_BASE}/verify_session.php", params={"session_token": session_token}, timeout=5)
        return r.json()
    except:
        return {"valid": False, "error": "Error de conexion"}

def check_auth():
    params = st.query_params
    if "session_token" in st.session_state:
        data = verificar_sesion(st.session_state["session_token"])
        if not data.get("valid"):
            st.session_state.clear()
            st.rerun()
    elif "token" in params:
        data = verificar_token(params["token"])
        if data.get("valid"):
            st.session_state["session_token"] = data["session_token"]
            st.session_state["user_id"]       = data["user_id"]
            st.session_state["email"]         = data["email"]
            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"Acceso denegado: {data.get('error','')}")
            st.markdown("[Volver a Diario Consciente](https://soytraderconsciente.com/diarioconsciente)")
            st.stop()
    else:
        st.error("Acceso no autorizado.")
        st.markdown("[Volver a Diario Consciente](https://soytraderconsciente.com/diarioconsciente)")
        st.stop()

def mbox(val, lbl, color="#0E1A3C"):
    return f"<div class='metric-box'><div class='metric-val' style='color:{color};'>{val}</div><div class='metric-lbl'>{lbl}</div></div>"

NOMBRES_FECHA = ["date","time","fecha","datetime","timestamp","dates","bar","bartime",
                 "gmt time","gmt_time","local time","local_time","<date>","<time>",
                 "date time","date_time","periodo","period","datetime64"]

def parsear_fecha(serie):
    for fmt in ["%Y%m%d %H:%M:%S.%f","%Y%m%d %H:%M:%S","%Y%m%d",
                "%Y-%m-%d %H:%M:%S","%Y-%m-%d","%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y","%m/%d/%Y","%d.%m.%Y","%Y.%m.%d %H:%M","%Y.%m.%d"]:
        try: return pd.to_datetime(serie, format=fmt)
        except: continue
    try: return pd.to_datetime(serie, format="mixed", dayfirst=False)
    except: return None

def cargar_csv(archivo):
    contenido = archivo.read().decode("utf-8", errors="replace")
    pl = contenido.split("\n")[0]
    sep = ";" if ";" in pl else ("\t" if "\t" in pl else ",")
    df_raw = pd.read_csv(io.StringIO(contenido), sep=sep, on_bad_lines="skip", skipinitialspace=True)
    df_raw.columns = df_raw.columns.str.strip()
    col_map = {}
    for col in df_raw.columns:
        cl = col.lower().strip()
        if cl in NOMBRES_FECHA or any(n in cl for n in NOMBRES_FECHA):
            if "date" not in col_map.values(): col_map[col] = "date"
        elif cl in ["open","apertura"]:    col_map[col] = "open"
        elif cl in ["high","alto","max"]:  col_map[col] = "high"
        elif cl in ["low","bajo","min"]:   col_map[col] = "low"
        elif cl in ["close","cierre"]:     col_map[col] = "close"
    df_raw = df_raw.rename(columns=col_map)
    if any(c not in df_raw.columns for c in ["date","open","high","low","close"]):
        return None, f"Columnas faltantes. Encontradas: {list(df_raw.columns)}"
    fechas = parsear_fecha(df_raw["date"].astype(str))
    if fechas is None: return None, "No se pudo parsear la fecha."
    df_raw["date"] = fechas
    df = df_raw[["date","open","high","low","close"]].copy()
    for c in ["open","high","low","close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open","high","low","close"])
    df = df.sort_values("date").reset_index(drop=True)
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

def calcular_metricas_mensuales(df, nombre_par):
    df = df.copy()
    df["mes"]  = df["date"].dt.month
    df["anio"] = df["date"].dt.year
    df["retorno"] = df["close"].pct_change()
    tr = pd.concat([df["high"]-df["low"],
                    (df["high"]-df["close"].shift(1)).abs(),
                    (df["low"]-df["close"].shift(1)).abs()], axis=1).max(axis=1)
    df["atr_pct"]  = tr.rolling(14).mean() / df["close"] * 100
    df["adx"]      = calcular_adx_arr(df["high"].values, df["low"].values, df["close"].values)
    df["vol_hist"] = df["retorno"].rolling(22).std() * np.sqrt(22) * 100
    MESES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
             7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
    atr_anual = df["atr_pct"].dropna().mean()
    vol_anual = df["vol_hist"].dropna().mean()
    resultados = []
    for mes in range(1,13):
        dm = df[df["mes"]==mes].copy()
        if len(dm) < 10: continue
        er_list=[];adx_list=[];atr_list=[];vol_list=[];dir_list=[]
        for anio in dm["anio"].unique():
            d = dm[dm["anio"]==anio]
            if len(d) < 5: continue
            desp = abs(d["close"].iloc[-1]-d["close"].iloc[0])
            mov  = d["close"].diff().abs().sum()
            er_list.append(desp/mov if mov>0 else 0)
            adx_v = d["adx"].dropna().mean()
            if not np.isnan(adx_v): adx_list.append(adx_v)
            atr_v = d["atr_pct"].dropna().mean()
            if not np.isnan(atr_v): atr_list.append(atr_v)
            vol_v = d["vol_hist"].dropna().mean()
            if not np.isnan(vol_v): vol_list.append(vol_v)
            vu=(d["close"]>d["open"]).sum(); vd=(d["close"]<d["open"]).sum(); tot=vu+vd
            dir_list.append(max(vu,vd)/tot if tot>0 else 0.5)
        if not er_list: continue
        er  = np.mean(er_list)
        adx = np.mean(adx_list) if adx_list else 25
        atr = np.mean(atr_list) if atr_list else atr_anual
        vol = np.mean(vol_list) if vol_list else vol_anual
        dir_ = np.mean(dir_list)
        puntos = 0
        if er < 0.25: puntos+=0
        elif er < 0.40: puntos+=1
        elif er < 0.55: puntos+=2
        else: puntos+=3
        if adx < 20: puntos+=0
        elif adx < 28: puntos+=1
        elif adx < 36: puntos+=2
        else: puntos+=3
        if atr < atr_anual*0.8: puntos+=0
        elif atr < atr_anual*1.2: puntos+=1
        elif atr < atr_anual*1.5: puntos+=2
        else: puntos+=3
        if dir_ < 0.60: puntos+=0
        elif dir_ < 0.68: puntos+=1
        elif dir_ < 0.75: puntos+=2
        else: puntos+=3
        if vol < vol_anual*0.8: puntos+=0
        elif vol < vol_anual*1.2: puntos+=1
        elif vol < vol_anual*1.5: puntos+=2
        else: puntos+=3
        if puntos <= 3: sem="="
        elif puntos <= 7: sem="="
        else: sem="=4"
        resultados.append({
            "par":par_nombre,"mes_num":mes,"mes":MESES[mes],
            "er":round(er,3),"adx":round(adx,1),"atr_pct":round(atr,3),
            "vol_hist":round(vol,2),"dir_velas":round(dir_,2),
            "puntos":puntos,"semaforo":sem,
        })
    return pd.DataFrame(resultados)

check_auth()

with st.sidebar:
    st.title("<د Grid Radar")
    st.caption("Trader Consciente")
    st.divider()
    seleccion = st.radio("", ["< Inicio","= Como funciona","= Analisis de pares"],
                         label_visibility="collapsed")
    st.divider()
    st.caption(st.session_state.get("email",""))
    if st.button("Cerrar sesion", use_container_width=True):
        st.session_state.clear(); st.rerun()

email = st.session_state.get("email","")

def page_header(t, s, e="<د"):
    st.markdown(f"""<div class='main-header'>
        <div style='font-size:2.5rem;'>{e}</div>
        <div style='flex:1;'><h1>{t}</h1><p>{s}</p></div>
        <div class='badge-user'>=d {email}</div>
    </div>""", unsafe_allow_html=True)

if seleccion == "< Inicio":
    page_header("Grid Radar","Detecta cuando es seguro operar robots Grid y Martingala")
    st.markdown("""<div class='step-card'>
        <div style='font-size:0.95rem;color:#2D3748;line-height:1.7;'>
        <strong>Grid Radar</strong> analiza datos historicos OHLC de cualquier par y te dice
        exactamente en que meses es seguro tener activos tus robots de cobertura
        (Grid y Martingala), cuando reducir el lotaje, y cuando apagarlos para proteger tu cuenta.<br><br>
        El analisis se basa en <strong>5 metricas cientificas</strong> que miden
        la lateralizacion y volatilidad del mercado mes a mes.
        </div></div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown("<div class='step-card' style='text-align:center;'><div style='font-size:2rem;'>=</div><strong>1. Sube tus datos</strong><br><span style='font-size:0.82rem;color:#718096;'>CSV con datos OHLC D1 de uno o varios pares</span></div>", unsafe_allow_html=True)
    with c2: st.markdown("<div class='step-card' style='text-align:center;'><div style='font-size:2rem;'>=</div><strong>2. Analisis automatico</strong><br><span style='font-size:0.82rem;color:#718096;'>5 metricas calculadas mes a mes para cada par</span></div>", unsafe_allow_html=True)
    with c3: st.markdown("<div class='step-card' style='text-align:center;'><div style='font-size:2rem;'>=ئ</div><strong>3. Semaforo de riesgo</strong><br><span style='font-size:0.82rem;color:#718096;'>Verde Seguro  Amarillo Precaucion  Rojo No operar</span></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Usa el menu de la izquierda para navegar.")

elif seleccion == "= Como funciona":
    page_header("Como funciona Grid Radar","Entiende que mide cada metrica y por que importa","=")
    metricas = [
        ("= Efficiency Ratio (ER)",
         "Mide que tan eficiente fue el movimiento del precio: si fue en linea recta (tendencia) o de forma caotica (rango lateral).",
         "ER = Desplazamiento neto del mes / Suma de todos los movimientos diarios",
         "El precio empezo en 1.0800 y termino en 1.0900 ! se desplazo 100 pips netos.\nPero dia a dia sumo 800 pips de movimiento total.\nER = 100 / 800 = 0.125 ! muy lateral '",
         "ER < 0.25   ! = Lateral perfecto\nER 0.25-0.40 ! = Algo de direccion\nER > 0.40   ! =4 Tendencia",
         "Un grid gana cuando el precio va y vuelve. Si el ER es alto, el precio se fue en una direccion y no regreso   el grid acumula posiciones perdedoras sin cerrar."),
        ("= ADX   Average Directional Index",
         "Mide la fuerza de la tendencia sin importar la direccion. No dice si sube o baja   solo que tan fuerte es el movimiento direccional.",
         "Compara el movimiento alcista (+DI) vs bajista (-DI). Cuando uno domina claramente, el ADX sube.",
         "ADX = 15 ! mercado sin direccion clara ! Grid seguro '\nADX = 45 ! tendencia fuerte en marcha ! Grid en peligro =4",
         "ADX < 20  ! = Sin tendencia\nADX 20-28 ! = Tendencia debil\nADX > 28  ! =4 Tendencia fuerte",
         "Si el ADX esta bajo, el mercado lateraliza. Si sube, algo se mueve con fuerza y el grid esta en riesgo."),
        ("= ATR Normalizado (%)",
         "El rango promedio de movimiento diario como porcentaje del precio. Mide que tan grandes son las velas.",
         "ATR% = Average True Range / Precio de cierre  100",
         "Oro a $2.000 con ATR de $20 ! ATR% = 1.0%\nEURUSD a 1.0800 con ATR 0.0050 ! ATR% = 0.46%\nPermite comparar cualquier activo en la misma escala.",
         "ATR% bajo (< 80% del promedio anual)  ! = Velas pequenas\nATR% medio (80-120%)                  ! = Normal\nATR% alto (> 150% del promedio anual)  ! =4 Velas grandes",
         "Con velas grandes el grid necesita niveles mas separados y mas capital. Meses de ATR alto requieren mas margen para sobrevivir."),
        ("=o Porcentaje de velas en la misma direccion",
         "De todos los dias del mes, que porcentaje cerraron en la misma direccion (todos bajando o todos subiendo).",
         "% direccion = max(velas alcistas, velas bajistas) / total de velas del mes",
         "Un mes de 22 dias: 17 bajistas y 5 alcistas ! 77% bajistas ! tendencia clara =4\nUn mes con 12 bajistas y 10 alcistas ! 55% ! equilibrio =",
         "< 60% en una direccion ! = Equilibrio\n60-68%                ! = Sesgo leve\n> 68%                 ! =4 Tendencia clara",
         "Si la mayoria de velas van en la misma direccion, el precio esta caminando sostenidamente y el grid acumula perdidas."),
        ("= Volatilidad Historica Mensual",
         "La dispersion estadistica de los retornos diarios ese mes. Que tan impredecibles fueron los movimientos de cierre a cierre.",
         "Vol = Desviacion estandar de retornos diarios  "22 (anualizada al mes)",
         "Vol baja ! retornos consistentes ! Grid tranquilo '\nVol alta ! retornos bruscos e impredecibles ! Grid en peligro =4\n(Diferente al ATR: mide dispersion de cierres, no tamano de velas)",
         "Vol < 80% promedio anual  ! =\nVol 80-120%              ! =\nVol > 150% promedio anual ! =4",
         "Alta volatilidad historica significa movimientos bruscos e impredecibles. El grid necesita predecibilidad para funcionar bien."),
    ]
    for nombre,que,formula,ejemplo,umbral,por_que in metricas:
        with st.expander(nombre, expanded=False):
            st.markdown(f"""
            <div class='step-card'><div class='step-title'>Que mide</div><div style='font-size:0.85rem;color:#4A5568;'>{que}</div></div>
            <div class='step-card'><div class='step-title'>Formula</div><pre style='font-size:0.8rem;'>{formula}</pre>
            <div class='step-title' style='margin-top:0.75rem;'>Ejemplo</div><pre style='font-size:0.8rem;'>{ejemplo}</pre></div>
            <div class='step-card'><div class='step-title'>Umbrales del semaforo</div><pre style='font-size:0.8rem;'>{umbral}</pre></div>
            <div class='step-card'><div class='step-title'>Por que importa para Grid/Martingala</div><div style='font-size:0.85rem;color:#4A5568;'>{por_que}</div></div>
            """, unsafe_allow_html=True)
    st.markdown("""<div class='step-card'>
        <div style='font-weight:700;font-size:0.95rem;margin-bottom:1rem;'>=ئ Como se combinan en el semaforo</div>
        <div style='font-size:0.88rem;color:#4A5568;line-height:1.7;'>
        Cada metrica da entre 0 y 3 puntos segun su nivel de riesgo. La suma total determina el color:<br><br>
        <strong>= VERDE (0-3 puntos):</strong> Condiciones optimas. Opera con tu lotaje normal.<br><br>
        <strong>= AMARILLO (4-7 puntos):</strong> Hay algo de direccion. Reduce el lotaje a la mitad.<br><br>
        <strong>=4 ROJO (8-15 puntos):</strong> Tendencia fuerte historica. No encender el robot este mes.
        </div></div>""", unsafe_allow_html=True)

elif seleccion == "= Analisis de pares":
    page_header("Analisis de Pares","Sube tus datos y obtn el semaforo de riesgo","=")
    st.markdown("""<div class='step-card'>
        <div style='font-size:0.88rem;color:#4A5568;'>
        Sube uno o varios archivos CSV con datos OHLC en timeframe <strong>D1</strong>.
        La app analiza cada par por separado y los compara entre si.<br><br>
        <strong>Requisitos:</strong> Minimo 3 anos de datos  Columnas Open, High, Low, Close  Formato CSV
        </div></div>""", unsafe_allow_html=True)

    archivos = st.file_uploader("Selecciona uno o varios archivos CSV", type=["csv"],
                                 accept_multiple_files=True)
    if not archivos:
        st.info("Sube al menos un archivo CSV para comenzar.")
    else:
        pares_data = {}
        for archivo in archivos:
            nombre = archivo.name.replace(".csv","").replace("_D1","").replace("_d1","").replace("_","").upper()
            df, error = cargar_csv(archivo)
            if error:
                st.markdown(f"<div class='alert-fail'>Error en {nombre}: {error}</div>", unsafe_allow_html=True)
            else:
                pares_data[nombre] = df
                st.markdown(f"<div class='alert-ok'>' {nombre}   {len(df):,} barras ({df['date'].min().strftime('%Y-%m-%d')} al {df['date'].max().strftime('%Y-%m-%d')})</div>", unsafe_allow_html=True)

        if pares_data and st.button("= Analizar todos los pares", use_container_width=True, type="primary"):
            todos = []
            prog  = st.progress(0, text="Analizando...")
            for i, (nombre, df) in enumerate(pares_data.items()):
                prog.progress((i+1)/len(pares_data), text=f"Analizando {nombre}...")
                df = df.copy()
                df["mes"]  = df["date"].dt.month
                df["anio"] = df["date"].dt.year
                df["retorno"] = df["close"].pct_change()
                tr = pd.concat([df["high"]-df["low"],
                                (df["high"]-df["close"].shift(1)).abs(),
                                (df["low"]-df["close"].shift(1)).abs()], axis=1).max(axis=1)
                df["atr_pct"]  = tr.rolling(14).mean() / df["close"] * 100
                df["adx"]      = calcular_adx_arr(df["high"].values, df["low"].values, df["close"].values)
                df["vol_hist"] = df["retorno"].rolling(22).std() * np.sqrt(22) * 100
                atr_anual = df["atr_pct"].dropna().mean()
                vol_anual = df["vol_hist"].dropna().mean()
                MESES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
                         7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
                for mes in range(1,13):
                    dm = df[df["mes"]==mes].copy()
                    if len(dm) < 10: continue
                    er_l=[];adx_l=[];atr_l=[];vol_l=[];dir_l=[]
                    for anio in dm["anio"].unique():
                        d = dm[dm["anio"]==anio]
                        if len(d) < 5: continue
                        desp=abs(d["close"].iloc[-1]-d["close"].iloc[0])
                        mov=d["close"].diff().abs().sum()
                        er_l.append(desp/mov if mov>0 else 0)
                        av=d["adx"].dropna().mean()
                        if not np.isnan(av): adx_l.append(av)
                        av2=d["atr_pct"].dropna().mean()
                        if not np.isnan(av2): atr_l.append(av2)
                        av3=d["vol_hist"].dropna().mean()
                        if not np.isnan(av3): vol_l.append(av3)
                        vu=(d["close"]>d["open"]).sum(); vd=(d["close"]<d["open"]).sum(); tot=vu+vd
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
                    sem="=" if p<=3 else ("=" if p<=7 else "=4")
                    todos.append({"par":nombre,"mes_num":mes,"mes":MESES[mes],
                                  "er":round(er,3),"adx":round(adx,1),"atr_pct":round(atr,3),
                                  "vol_hist":round(vol,2),"dir_velas":round(dir_,2),
                                  "puntos":p,"semaforo":sem})
            prog.progress(1.0, text="' Completado")
            st.session_state["gr_res"]   = pd.DataFrame(todos)
            st.session_state["gr_pares"] = list(pares_data.keys())

        if "gr_res" in st.session_state:
            df_total = st.session_state["gr_res"]
            pares    = st.session_state["gr_pares"]
            MESES_C  = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
                        7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='step-title'>=ئ Semaforo por mes y par</div>", unsafe_allow_html=True)
            pivot = df_total.pivot_table(index="par", columns="mes_num", values="semaforo", aggfunc="first")
            pivot.columns = [MESES_C.get(c,str(c)) for c in pivot.columns]
            st.dataframe(pivot, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='step-title'>= Recomendaciones por par</div>", unsafe_allow_html=True)

            for par in pares:
                dp = df_total[df_total["par"]==par].sort_values("mes_num")
                mv = dp[dp["semaforo"]=="="]["mes"].tolist()
                ma = dp[dp["semaforo"]=="="]["mes"].tolist()
                mr = dp[dp["semaforo"]=="=4"]["mes"].tolist()
                with st.expander(f"= {par}", expanded=True):
                    c1,c2,c3 = st.columns(3)
                    with c1: st.markdown(f"<div class='sem-verde'>= SEGUROS ({len(mv)})<br><small>{', '.join(mv) or 'Ninguno'}</small></div>", unsafe_allow_html=True)
                    with c2: st.markdown(f"<div class='sem-amarillo'>= PRECAUCION ({len(ma)})<br><small>{', '.join(ma) or 'Ninguno'}</small></div>", unsafe_allow_html=True)
                    with c3: st.markdown(f"<div class='sem-rojo'>=4 NO OPERAR ({len(mr)})<br><small>{', '.join(mr) or 'Ninguno'}</small></div>", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if mv: st.markdown(f"<div class='alert-ok'>' <strong>Enciende tu robot en:</strong> {', '.join(mv)}<br><small>El par historicamente lateraliza estos meses.</small></div>", unsafe_allow_html=True)
                    if ma: st.markdown(f"<div style='background:#FFFBEA;border-left:4px solid #FFD166;padding:1rem;border-radius:8px;margin:0.5rem 0;'>& <strong>Reduce el lotaje a la mitad en:</strong> {', '.join(ma)}<br><small>Hay algo de direccion. Opera con mas margen.</small></div>", unsafe_allow_html=True)
                    if mr: st.markdown(f"<div class='alert-fail'>=ث <strong>No enciendas el robot en:</strong> {', '.join(mr)}<br><small>Tendencia fuerte historica. Alto riesgo de quema.</small></div>", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.dataframe(dp[["mes","semaforo","er","adx","atr_pct","vol_hist","dir_velas"]].rename(
                        columns={"mes":"Mes","semaforo":"Semaforo","er":"ER","adx":"ADX",
                                 "atr_pct":"ATR%","vol_hist":"Vol%","dir_velas":"Dir Velas"}
                    ).style.format({"ER":"{:.3f}","ADX":"{:.1f}","ATR%":"{:.3f}%","Vol%":"{:.2f}%","Dir Velas":"{:.0%}"}),
                    use_container_width=True, hide_index=True)

            if len(pares) > 1:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<div class='step-title'>& Comparativa entre pares</div>", unsafe_allow_html=True)
                comp = []
                for par in pares:
                    dp = df_total[df_total["par"]==par]
                    comp.append({"Par":par,
                                 "= Meses seguros":(dp["semaforo"]=="=").sum(),
                                 "= Precaucion":(dp["semaforo"]=="=").sum(),
                                 "=4 Peligrosos":(dp["semaforo"]=="=4").sum(),
                                 "ER promedio":round(dp["er"].mean(),3),
                                 "ADX promedio":round(dp["adx"].mean(),1)})
                df_comp = pd.DataFrame(comp).sort_values("= Meses seguros", ascending=False)
                st.dataframe(df_comp, use_container_width=True, hide_index=True)
                mejor = df_comp.iloc[0]["Par"]; peor = df_comp.iloc[-1]["Par"]
                st.markdown(f"<div class='alert-ok'>< <strong>{mejor}</strong> es el par mas seguro para Grid con {df_comp.iloc[0]['= Meses seguros']} meses verdes al ao. <strong>{peor}</strong> es el mas peligroso con {df_comp.iloc[-1]['=4 Peligrosos']} meses rojos.</div>", unsafe_allow_html=True)