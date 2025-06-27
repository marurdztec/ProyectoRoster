import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Archivo CSV de salida para guardar respuestas
ARCHIVO_RESPUESTAS = "confirmaciones_respuestas.csv"

# Crear archivo si no existe
if not os.path.exists(ARCHIVO_RESPUESTAS):
    df_vacio = pd.DataFrame(columns=[
        "Fecha Hora", "Nómina", "Nombre Profesor", "Confirmación", "Comentarios"
    ])
    df_vacio.to_csv(ARCHIVO_RESPUESTAS, index=False)

# Función para cargar datos con caching
@st.cache_data
def cargar_datos():
    df = pd.read_csv("Datos_Roster_V2.csv")
    df.columns = df.columns.str.strip()
    return df

df = cargar_datos()

# Clasificar tipo de UF
def clasificar_tipo_uf(uf):
    if isinstance(uf, str):
        if uf.endswith("S"):
            return "Semana Tec"
        elif uf.endswith("B"):
            return "Bloque"
        elif uf.endswith("C"):
            return "Concentración"
        else:
            return "Materia"
    return "Desconocido"

df["Tipo de UF"] = df["UF"].apply(clasificar_tipo_uf)

# Agregar coordinadores si existe la columna
if "Carga Co." in df.columns:
    coordinadores = df[df["Carga Co."].notnull()][["UF", "Grupo", "Profesor", "Correo"]].copy()
    coordinadores = coordinadores.rename(columns={
        "Profesor": "Coordinador",
        "Correo": "Correo Coordinador"
    })
    df = df.merge(coordinadores, on=["UF", "Grupo"], how="left")

# --- Estilos CSS para tabla centrada y ancha ---
st.markdown(
    """
    <style>
    .tabla-centro th, .tabla-centro td {
        text-align: center !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Botón siempre visible para reiniciar sesión ---
if st.button("🔄 Reiniciar conversación", help="Borrar respuestas y empezar de nuevo"):
    st.session_state.clear()
    st.experimental_rerun()

# Título y bienvenida
st.title("🤖 Chatbot para Carga Académica AD25")
st.markdown("Departamento Mecánica y Materiales Avanzados")
st.markdown("👋 **Hola Profesor, estoy aquí para ayudarte a revisar tu carga académica para este próximo semestre.**")

# Inputs
nombre_profesor = st.text_input("Por favor indícame tu nombre:")

if nombre_profesor.strip():
    nomina = st.text_input(f"Gracias {nombre_profesor}, ahora por favor ingresa tu número de nómina (ej. L01234567):")

    if nomina:
        datos_profesor = df[df["Nómina"] == nomina].copy()

        if datos_profesor.empty:
            st.warning("⚠️ No se encontraron asignaciones para esa nómina.")
        else:
            # Procesar datos numéricos
            datos_profesor["Carga Co."] = pd.to_numeric(datos_profesor.get("Carga Co.", 0), errors="coerce").fillna(0)
            datos_profesor["UDCs"] = pd.to_numeric(datos_profesor.get("UDCs", 0), errors="coerce").fillna(0)

            total_carga_co = round(datos_profesor["Carga Co."].sum(), 2)
            total_udcs = round(datos_profesor["UDCs"].sum(), 2)
            udcs_totales = round(total_udcs + total_carga_co, 2)

            def mostrar_coordinador(row):
                if row["Tipo de UF"] in ["Bloque", "Concentración"]:
                    return f"{row.get('Coordinador', '')} ({row.get('Correo Coordinador', '')})"
                return ""

            datos_profesor["Coordinador de Bloque"] = datos_profesor.apply(mostrar_coordinador, axis=1)
            datos_profesor["Grupo"] = datos_profesor["Grupo"].fillna("").apply(
                lambda x: str(int(x)) if isinstance(x, float) else str(x)
            )

            columnas = [
                "UF", "Grupo", "Nombre de UF", "Inglés", "Tipo de UF",
                "% de Resp", "UDCs", "Periodo", "Horario", "Coordinador de Bloque"
            ]
            resultado = datos_profesor[columnas]

           # Formatear columnas numéricas para que tengan 2 decimales
            resultado = resultado.copy()
            if 'UDCs' in resultado.columns:
                resultado['UDCs'] = resultado['UDCs'].map('{:.2f}'.format)
            if '% de Resp' in resultado.columns:
                resultado['% de Resp'] = resultado['% de Resp'].map('{:.2f}'.format)

            st.subheader("📋 Esta es tu carga académica asignada:")
            st.dataframe(resultado, use_container_width=True)

            # Mostrar tabla sin índice, con scroll horizontal y ancho al 100%
            st.dataframe(resultado.style.set_table_attributes('class="tabla-centro"').set_precision(2), use_container_width=True)

            # Mostrar métricas en 3 columnas
            col1, col2, col3 = st.columns(3)
            col1.metric("📘 Total UDCs Docente", f"{total_udcs}")
            col2.metric("👥 Total UDCs Coordinación", f"{total_carga_co}")
            col3.metric("📊 UDCs Totales", f"{udcs_totales}")

            st.subheader("✅ Confirmación de carga")
            confirmacion = st.radio("¿Confirmas tu carga académica asignada para este semestre?", ["Sí", "No"], horizontal=True)

            comentario_placeholder = ""
            if confirmacion == "Sí":
                st.info("✅ Gracias por confirmar tu carga, apreciamos mucho tu dedicación y colaboración en este proceso. Mucho éxito para este semestre.")
                comentario_placeholder = "Si tienes algún comentario adicional, puedes indicarlo aquí."
            elif confirmacion == "No":
                st.warning("⚠️ Lamentamos que tu carga actual no sea de tu agrado. Por favor explícanos qué parte de tu carga presenta una limitación para poder revisarla.")
                comentario_placeholder = "Por favor detalla las limitaciones que observas en tu carga."

            comentarios = st.text_area(
                "En caso de tener algún comentario, duda o sugerencia respecto a tu carga académica asignada, por favor indícalo a continuación:",
                placeholder=comentario_placeholder
            )

            if st.button("📨 Enviar confirmación y comentarios"):
                fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                nueva_fila = pd.DataFrame([{
                    "Fecha Hora": fecha_hora,
                    "Nómina": nomina,
                    "Nombre Profesor": nombre_profesor,
                    "Confirmación": confirmacion,
                    "Comentarios": comentarios
                }])

                # Guardar en CSV, append sin encabezado
                nueva_fila.to_csv(ARCHIVO_RESPUESTAS, mode="a", header=False, index=False)

                st.success("✅ Tu confirmación y comentarios se han registrado correctamente. ¡Gracias por tu tiempo!")

