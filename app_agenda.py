import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="ERP Agenda & Equipos Inteligente", layout="wide", page_icon="📊")

DB_FILE = "agenda_trabajos.csv"
DB_ELIMINADOS = "agenda_eliminados.csv"

# Columnas extendidas con gestión de personal y tiempos detallados
COLUMNS = ["ID", "Trabajo", "Cliente", "VIP", "Urgencia", "Impacto", "Fecha_Entrega", "Estado", "Cobrado", "Gastos", "Tiempo_Horas", "Dias_Invertidos", "Num_Trabajadores"]

# Inicializar archivos
for file in [DB_FILE, DB_ELIMINADOS]:
    if not os.path.exists(file):
        pd.DataFrame(columns=COLUMNS if file == DB_FILE else COLUMNS + ["Fecha_Eliminacion"]).to_csv(file, index=False)

def cargar_datos(file_path):
    df = pd.read_csv(file_path)
    for col in ["Cobrado", "Gastos", "Tiempo_Horas", "Dias_Invertidos", "Num_Trabajadores"]:
        if col not in df.columns: df[col] = 0.0 if col != "Num_Trabajadores" else 1
    df["Cobrado"] = df["Cobrado"].fillna(0.0)
    df["Gastos"] = df["Gastos"].fillna(0.0)
    df["Tiempo_Horas"] = df["Tiempo_Horas"].fillna(0.0)
    df["Dias_Invertidos"] = df["Dias_Invertidos"].fillna(0.0)
    df["Num_Trabajadores"] = df["Num_Trabajadores"].fillna(1).astype(int)
    if "Fecha_Entrega" in df.columns:
        df["Fecha_Entrega"] = pd.to_datetime(df["Fecha_Entrega"], format='mixed', errors='coerce').fillna(pd.Timestamp(datetime.now().date()))
    return df

def guardar_datos(df, file_path):
    df.to_csv(file_path, index=False)

df = cargar_datos(DB_FILE)

st.title("📊 SISTEMA CENTRAL DE OPERACIONES, EQUIPOS Y FINANZAS")

# --- INDICADORES MÉTRICOS ---
df_pendientes_count = len(df[df["Estado"].isin(["Pendiente", "Aceptado"])])
df_hechos_count = len(df[df["Estado"] == "Completado"])
total_beneficio = (df["Cobrado"] - df["Gastos"]).sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Trabajos Activos ⏳", df_pendientes_count)
m2.metric("Trabajos Completados ✅", df_hechos_count)
m3.metric("Beneficio Neto Total 💰", f"${total_beneficio:,.2f}")
m4.metric("Personal Activo Asignado 👥", int(df[df["Estado"] == "Aceptado"]["Num_Trabajadores"].sum()))

# --- MÓDULO 1: AGREGAR TRABAJO ---
with st.expander("➕ REGISTRAR NUEVO TRABAJO O PEDIDO", expanded=False):
    with st.form("nuevo_trabajo"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre del Trabajo / Proyecto:")
            cliente = st.text_input("Cliente:")
            vip = st.checkbox("¿Cliente VIP? ⭐")
        with c2:
            urgencia = st.slider("Urgencia (1 al 5):", 1, 5, 3)
            impacto = st.slider("Impacto Económico Inicial (1 al 5):", 1, 5, 3)
            fecha = st.date_input("Fecha Límite Próxima:", datetime.now())
        
        if st.form_submit_button("AGENDAR E INICIAR TRAZABILIDAD"):
            if nombre and cliente:
                nuevo_id = int(df["ID"].max() + 1) if len(df) > 0 else 100
                nueva_fila = {
                    "ID": nuevo_id, "Trabajo": nombre, "Cliente": cliente, "VIP": "Sí" if vip else "No",
                    "Urgencia": urgencia, "Impacto": impacto, "Fecha_Entrega": fecha.strftime("%Y-%m-%d"),
                    "Estado": "Pendiente", "Cobrado": 0.0, "Gastos": 0.0, "Tiempo_Horas": 0.0, "Dias_Invertidos": 0.0, "Num_Trabajadores": 1
                }
                df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
                guardar_datos(df, DB_FILE)
                st.success("¡Agendado con éxito!")
                st.rerun()

# --- FORMULARIO DE CIERRE FINANCIERO Y PERSONAL ---
if "completar_id" in st.session_state:
    st.warning(f"📝 Liquidación y Tiempos para el Trabajo ID #{st.session_state['completar_id']}")
    with st.form("cierre_operativo"):
        f1, f2 = st.columns(2)
        with f1:
            cobrado_val = st.number_input("Monto Cobrado Final ($):", min_value=0.0, step=100.0)
            gastos_val = st.number_input("Gastos Reales en Materiales ($):", min_value=0.0, step=50.0)
        with f2:
            trabajadores_val = st.number_input("Cantidad de Trabajadores Asignados:", min_value=1, step=1, value=1)
            horas_val = st.number_input("Total Horas Acumuladas del Equipo:", min_value=0.0, step=1.0)
            dias_val = st.number_input("Días de Duración del Trabajo:", min_value=0.0, step=1.0)
        
        if st.form_submit_button("COMPLETAR Y REGISTRAR EN HISTORIAL"):
            df.loc[df["ID"] == st.session_state["completar_id"], ["Estado", "Cobrado", "Gastos", "Tiempo_Horas", "Dias_Invertidos", "Num_Trabajadores"]] = ["Completado", cobrado_val, gastos_val, horas_val, dias_val, trabajadores_val]
            guardar_datos(df, DB_FILE)
            del st.session_state["completar_id"]
            st.success("¡Datos consolidados en el balance financiero general!")
            st.rerun()

# --- MÓDULO 2: TRABAJOS ACTIVOS ---
df_activos = df[df["Estado"].isin(["Pendiente", "Aceptado"])].copy()
if not df_activos.empty:
    hoy = pd.Timestamp(datetime.now().date())
    df_activos["Dias_Restantes"] = (df_activos["Fecha_Entrega"] - hoy).dt.days
    df_activos["Score"] = (df_activos["Urgencia"] * 1.5) + (df_activos["Impacto"] * 1.5) - (df_activos["Dias_Restantes"] * 0.2) + (df_activos["Estado"].apply(lambda x: 3.0 if x == "Aceptado" else 0.0))
    df_activos = df_activos.sort_values(by="Score", ascending=False)

    st.subheader("🔥 BANDEJA OPERATIVA (Por Prioridad)")
    for idx, row in df_activos.iterrows():
        with st.container():
            col_info, col_accion = st.columns([0.6, 0.4])
            with col_info:
                st.markdown(f"### {row['Trabajo']} - Cliente: {row['Cliente']} " + ("⭐ [VIP]" if row["VIP"] == "Sí" else ""))
                st.caption(f"Fase: **{row['Estado'].upper()}** | 📅 Límite: {row['Fecha_Entrega'].strftime('%d/%m/%Y')} ({row['Dias_Restantes']} días restantes) | 👥 Personal Inicial: {row['Num_Trabajadores']}")
            with col_accion:
                st.write("")
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    if row["Estado"] == "Pendiente" and st.button("Aceptar 👍", key=f"ac_{row['ID']}"):
                        df.loc[df["ID"] == row["ID"], "Estado"] = "Aceptado"
                        guardar_datos(df, DB_FILE)
                        st.rerun()
                with b2:
                    if st.button("Hecho ✅", key=f"hc_{row['ID']}"):
                        st.session_state["completar_id"] = row["ID"]
                        st.rerun()
                with b3:
                    if st.button("Cancelar ❌", key=f"cn_{row['ID']}"):
                        df.loc[df["ID"] == row["ID"], "Estado"] = "Cancelado"
                        guardar_datos(df, DB_FILE)
                        st.rerun()
                with b4:
                    if st.button("Eliminar 🗑️", key=f"el_{row['ID']}"):
                        # Mover a eliminados por auditoría
                        df_el = cargar_datos(DB_ELIMINADOS)
                        fila_eliminar = df[df["ID"] == row["ID"]].copy()
                        fila_eliminar["Fecha_Eliminacion"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        df_el = pd.concat([df_el, fila_eliminar], ignore_index=True)
                        guardar_datos(df_el, DB_ELIMINADOS)
                        # Quitar de la agenda principal
                        df = df[df["ID"] != row["ID"]]
                        guardar_datos(df, DB_FILE)
                        st.rerun()
            st.markdown("---")

# --- MÓDULO 3: BALANCE GRÁFICO AVANZADO ---
st.markdown("## 📊 RENDIMIENTO FINANCIERO Y EFICIENCIA DE EQUIPOS")
df_historico = df[df["Estado"] == "Completado"].copy()

if not df_historico.empty:
    df_historico["Beneficio_Neto"] = df_historico["Cobrado"] - df_historico["Gastos"]
    df_historico["Rendimiento_Por_Trabajador"] = df_historico.apply(lambda r: r["Beneficio_Neto"] / r["Num_Trabajadores"] if r["Num_Trabajadores"] > 0 else r["Beneficio_Neto"], axis=1)
    
    g1, g2 = st.columns(2)
    with g1:
        st.write("### 💰 Margen Neto por Proyecto")
        st.bar_chart(df_historico.set_index("Trabajo")[["Beneficio_Neto", "Gastos"]])
    with g2:
        st.write("### 👥 Rentabilidad por Integrante del Equipo ($ / Persona)")
        st.line_chart(df_historico.set_index("Trabajo")["Rendimiento_Por_Trabajador"])
else:
    st.info("📊 Las gráficas se generarán automáticamente cuando completes proyectos.")

# --- MÓDULO 4: PANELES DE HISTORIAL COMPLETO ---
st.markdown("## 📂 CENTRO DE ARCHIVO E HISTORIALES")
t1, t2, t3 = st.tabs(["✅ TRABAJOS REALIZADOS", "❌ TRABAJOS CANCELADOS", "🗑️ AUDITORÍA DE ELIMINADOS"])

with t1:
    df_comp = df[df["Estado"] == "Completado"]
    if not df_comp.empty:
        st.dataframe(df_comp[["ID", "Trabajo", "Cliente", "Cobrado", "Gastos", "Tiempo_Horas", "Dias_Invertidos", "Num_Trabajadores"]])
        # Botón de descarga para contabilidad
        st.download_button("Descargar Registro Completo (Excel/CSV)", df_comp.to_csv(index=False), "Historico_Realizados.csv", "text/csv")
    else: st.write("No hay registros en esta sección.")

with t2:
    df_canc = df[df["Estado"] == "Cancelado"]
    st.dataframe(df_canc[["ID", "Trabajo", "Cliente", "Fecha_Entrega"]]) if not df_canc.empty else st.write("Sin trabajos cancelados.")

with t3:
    df_elim = cargar_datos(DB_ELIMINADOS)
    st.dataframe(df_elim[["ID", "Trabajo", "Cliente", "Fecha_Eliminacion"]]) if not df_elim.empty else st.write("El registro de eliminados está limpio.")
