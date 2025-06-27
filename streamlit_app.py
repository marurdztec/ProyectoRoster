import streamlit as st
import pandas as pd
from datetime import datetime
import os

# -----------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------
ARCHIVO_RESPUESTAS = "confirmaciones_respuestas.csv"

# Crear archivo de respuestas si no existe
if not os.path.exists(ARCHIVO_RESPUESTAS):
    df_vacio = pd.DataFrame(columns=[
        "Fecha Hora", "Nómina", "Nombre Profesor", "Confirmación", "Comentarios"
    ])
    df_vacio.to_csv(ARCHIVO_RESPUESTAS, index=False)

# -----------------------------
# CARGA DEL CSV DE CARGA DOCENTE
# -----------------------------
@st.cache_data
def cargar_datos():
    df = pd.read_csv("Datos_Roster_V2.csv")
    df.columns = df.columns.str.strip()
    return df

df = cargar_datos()

# -----------------------------
# CLASIFICAR TIPO DE UF
# -----------------------------
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

# -----------------------------
# AGREGAR COORDINADORES
# -----------------------------
if "Carga Co." in df.columns:
    coordinadores = df[df["Carga Co."].notnull()][["UF", "Grupo", "Profesor", "Correo"]].copy()
    coordinadores = coordinadores.rename(columns={
        "Profesor": "Coordinador",
        "Correo": "Correo Coordinador"
    })
    df = df.merge(coordinadores, on=["UF", "Grupo"], how="left")

# -----------------------------
# INTERFAZ DE USUARIO
# -----------------------------
st.title("🤖 Confirmación de Carga Académica")

# Botón para reiniciar conversación siempre visible arriba
if st.button("🔄 Reiniciar conversación", key="reiniciar"):
    st.experimental_rerun()

st.markdown("👋 **Hola Profesor, estoy aquí para ayudarte a revisar tu carga académica para este próximo semestre.**")

nombre_profesor = st.text_input("Por favor indícame tu nombre:")

if nombre_profesor.strip() != "":
    nomina = st.text_input(f"Gracias {nombre_profesor}, ahora por favor ingresa tu número de nómina (ej. L01234567):")

    if nomina:
        datos_profesor = df[df["Nómina"] == nomina].copy()

        if datos_profesor.empty:
            st.warning("⚠️ No se encontraron asignaciones para esa nómina.")
        else:
            # Asegurar valores numéricos
            datos_profesor["Carga Co."] = pd.to_numeric(datos_profesor.get("Carga Co.", 0), errors="coerce").fillna(0)
            datos_profesor["UDCs"] = pd.to_numeric(datos_profesor.get("UDCs", 0), errors="coerce").fillna(0)

            total_carga_co = round(datos_profesor["Carga Co."].sum(), 2)
            total_udcs = round(datos_profesor["UDCs"].sum(), 2)
            udcs_totales = round(total_udcs + total_carga_co, 2)

            # Función para mostrar coordinador de bloque
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

            # Formatear columnas numéricas para evitar errores y mejorar visualización
            resultado = resultado.copy()
            if "UDCs" in resultado.columns:
                resultado["UDCs"] = pd.to_numeric(resultado["UDCs"], errors="coerce")
                resultado["UDCs"] = resultado["UDCs"].map(lambda x: f"{x:.2f}" if pd.notnull(x) else "")
            if "% de Resp" in resultado.columns:
                resultado["% de Resp"] = pd.to_numeric(resultado["% de Resp"], errors="coerce")
                resultado["% de Resp"] = resultado["% de Resp"].map(lambda x: f"{x:.2f}" if pd.notnull(x) else "")

            st.subheader("📋 Esta es tu carga académica asignada:")
            st.dataframe(resultado, use_container_width=True)

            # Mostrar recuadros de totales
            col1, col2, col3 = st.columns(3)
            col1.metric("📘 Total UDCs Docente", f"{total_udcs:.2f}")
            col2.metric("👥 Total UDCs Coordinación", f"{total_carga_co:.2f}")
            col3.metric("📊 UDCs Totales", f"{udcs_totales:.2f}")

            st.subheader("✅ Confirmación de carga")
            confirmacion = st.radio(
                "¿Confirmas tu carga académica asignada para este semestre?",
                ["Sí", "No"],
                horizontal=True,
                index=None  # Para que no haya opción seleccionada al inicio
            )

            comentario_placeholder = ""
            if confirmacion == "Sí":
                st.info("✅ Gracias por confirmar tu carga, apreciamos mucho tu dedicación y colaboración en este proceso. ¡Mucho éxito para este semestre!")
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

                # Guardar en CSV sin sobrescribir (modo append)
                if os.path.exists(ARCHIVO_RESPUESTAS):
                    nueva_fila.to_csv(ARCHIVO_RESPUESTAS, mode="a", header=False, index=False)
                else:
                    nueva_fila.to_csv(ARCHIVO_RESPUESTAS, mode="w", header=True, index=False)

                st.success("✅ Tu confirmación y comentarios se han registrado correctamente. ¡Gracias por tu tiempo!")

                # Generar HTML imprimible para descarga
                estilo = """
                <style>
                  body { font-family: Verdana, Segoe UI, sans-serif; font-size: 12px; }
                  h1 { text-align: center; font-weight: bold; }
                  h2 { text-align: center; margin-top: 0; margin-bottom: 20px; }
                  table { border-collapse: collapse; width: 100%; font-size: 10px; }
                  th, td { border: 1px solid #ccc; padding: 6px; text-align: center; word-wrap: break-word; }
                  th { background-color: #003366; color: white; }
                  .resumen-container { display: flex; gap: 15px; margin-top: 15px; font-size: 12px; }
                  .card { background-color: #f0f8ff; border-left: 5px solid #003366; padding: 10px 15px; flex: 1; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }
                  .card strong { display: block; font-size: 12px; color: #003366; margin-bottom: 3px; }
                  .card span { font-size: 16px; font-weight: bold; color: #000; }
                </style>
                """

                # Convertir tabla a HTML
                tabla_html = resultado.to_html(index=False, escape=False, na_rep='', classes='tabla-centro')

                resumen_html = f"""
                <div class="resumen-container">
                  <div class="card">
                    <strong>Total UDCs Docente</strong>
                    <span>{total_udcs:.2f}</span>
                  </div>
                  <div class="card">
                    <strong>Total UDCs Coordinación</strong>
                    <span>{total_carga_co:.2f}</span>
                  </div>
                  <div class="card">
                    <strong>UDCs Totales</strong>
                    <span>{udcs_totales:.2f}</span>
                  </div>
                </div>
                """

                encabezado_html = f"""
                <h1>Chatbot para Carga Académica AD25</h1>
                <h2>Departamento Mecánica y Materiales Avanzados</h2>
                <p><b>Profesor:</b> {nombre_profesor}</p>
                <p><b>Nómina:</b> {nomina}</p>
                <hr>
                """

                html_completo = estilo + encabezado_html + tabla_html + resumen_html

                st.markdown("---")
                st.markdown("### 🖨️ Vista previa para imprimir o guardar en PDF")
                st.markdown(html_completo, unsafe_allow_html=True)

