import streamlit as st
import pandas as pd
from datetime import datetime
import os
import re
import unicodedata
from weasyprint import HTML

# --- CONSTANTES Y CONFIGURACIONES ---
ARCHIVO_DATOS = "Datos_Roster_V2.csv"
ARCHIVO_RESPUESTAS = "confirmaciones_respuestas.csv"

# Estilo PDF (extraído y adaptado del código que diste)
ESTILO_PDF = """
<style>
  @page {
    size: A4 landscape;
    margin: 1cm;
  }
  body {
    font-family: Verdana, Segoe UI, sans-serif;
    font-size: 10px;
  }
  h1 {
    text-align: center;
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 0;
  }
  h2 {
    text-align: center;
    font-size: 14px;
    font-weight: normal;
    margin-top: 5px;
    margin-bottom: 15px;
  }
  .info-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 15px;
    font-size: 12px;
  }
  .info-row div {
    width: 48%;
  }
  table.tabla-centro {
    border-collapse: collapse;
    width: 100%;
    table-layout: auto;
    font-size: 10px;
    margin-bottom: 20px;
  }
  .tabla-centro th, .tabla-centro td {
    border: 1px solid #ccc;
    padding: 6px;
    text-align: center;
    word-wrap: break-word;
  }
  .tabla-centro th {
    background-color: #003366;
    color: white;
  }
  .resumen-container {
    display: flex;
    gap: 20px;
    margin-top: 15px;
    font-size: 12px;
  }
  .card {
    background-color: #f0f8ff;
    border-left: 5px solid #003366;
    padding: 10px 15px;
    flex: 1;
    border-radius: 5px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    text-align: center;
  }
  .card strong {
    display: block;
    font-size: 12px;
    color: #003366;
    margin-bottom: 3px;
  }
  .card span {
    font-size: 16px;
    font-weight: bold;
    color: #000;
  }
</style>
"""

# --- FUNCIONES AUXILIARES ---

def limpiar_nombre(nombre):
    nombre = unicodedata.normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('utf-8')
    nombre = re.sub(r'[^\w\s-]', '', nombre)
    nombre = re.sub(r'\s+', '_', nombre.strip())
    return nombre

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

def cargar_datos():
    try:
        df = pd.read_csv(ARCHIVO_DATOS)
        df.columns = df.columns.str.strip()
        df["Tipo de UF"] = df["UF"].apply(clasificar_tipo_uf)
        # Agregar coordinadores
        if "Carga Co." in df.columns:
            coord = df[df["Carga Co."].notnull()][["UF", "Grupo", "Profesor", "Correo"]].copy()
            coord = coord.rename(columns={"Profesor":"Coordinador","Correo":"Correo Coordinador"})
            df = df.merge(coord, on=["UF","Grupo"], how="left")
        return df
    except FileNotFoundError:
        st.error(f"⚠️ No se encontró el archivo {ARCHIVO_DATOS}. Por favor súbelo al repositorio.")
        st.stop()

def mostrar_tabla_carga(df_profesor):
    df_profesor["Carga Co."] = pd.to_numeric(df_profesor.get("Carga Co.", 0), errors="coerce").fillna(0)
    df_profesor["UDCs"] = pd.to_numeric(df_profesor.get("UDCs", 0), errors="coerce").fillna(0)

    total_carga_co = round(df_profesor["Carga Co."].sum(), 2)
    total_udcs = round(df_profesor["UDCs"].sum(), 2)
    udcs_totales = round(total_udcs + total_carga_co, 2)

    def mostrar_coordinador(row):
        if row["Tipo de UF"] in ["Bloque", "Concentración"]:
            return f"{row.get('Coordinador', '')} ({row.get('Correo Coordinador', '')})"
        return ""

    df_profesor["Coordinador de Bloque"] = df_profesor.apply(mostrar_coordinador, axis=1)
    df_profesor["Grupo"] = df_profesor["Grupo"].fillna("").apply(
        lambda x: str(int(x)) if isinstance(x, float) else str(x)
    )

    columnas = [
        "UF", "Grupo", "Nombre de UF", "Inglés", "Tipo de UF",
        "% de Resp", "UDCs", "Periodo", "Horario", "Coordinador de Bloque"
    ]

    resultado = df_profesor[columnas]

    st.subheader("📋 Esta es tu carga académica asignada:")
    st.dataframe(resultado, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("📘 Total UDCs Docente", f"{total_udcs}")
    col2.metric("👥 Total UDCs Coordinación", f"{total_carga_co}")
    col3.metric("📊 UDCs Totales", f"{udcs_totales}")

    return resultado, total_udcs, total_carga_co, udcs_totales

def generar_pdf_html(nomina, nombre_profesor, df_profesor):
    fecha_actual = datetime.now().strftime("%d/%m/%Y")

    df_profesor["Carga Co."] = pd.to_numeric(df_profesor.get("Carga Co.", 0), errors="coerce").fillna(0)
    df_profesor["UDCs"] = pd.to_numeric(df_profesor.get("UDCs", 0), errors="coerce").fillna(0)

    total_carga_co = round(df_profesor["Carga Co."].sum(), 2)
    total_udcs = round(df_profesor["UDCs"].sum(), 2)
    udcs_totales = round(total_udcs + total_carga_co, 2)

    def mostrar_coordinador(row):
        if row["Tipo de UF"] in ["Bloque", "Concentración"]:
            return f"{row.get('Coordinador', '')} ({row.get('Correo Coordinador', '')})"
        return ""

    df_profesor["Coordinador de Bloque"] = df_profesor.apply(mostrar_coordinador, axis=1)
    df_profesor["Grupo"] = df_profesor["Grupo"].fillna("").apply(
        lambda x: str(int(x)) if isinstance(x, float) else str(x)
    )

    columnas = [
        "UF", "Grupo", "Nombre de UF", "Inglés", "Tipo de UF",
        "% de Resp", "UDCs", "Periodo", "Horario", "Coordinador de Bloque"
    ]
    resultado = df_profesor[columnas]
    tabla_html = resultado.to_html(index=False, escape=False, na_rep='', classes='tabla-centro')

    resumen_html = f"""
    <div class="resumen-container">
      <div class="card">
        <strong>Total UDCs Docente</strong>
        <span>{total_udcs}</span>
      </div>
      <div class="card">
        <strong>Total UDCs Coordinación</strong>
        <span>{total_carga_co}</span>
      </div>
      <div class="card">
        <strong>UDCs Totales</strong>
        <span>{udcs_totales}</span>
      </div>
    </div>
    """

    encabezado_html = f"""
    <h1>Carga Académica Agosto-Diciembre 2025</h1>
    <h2>Departamento de Mecánica y Materiales Avanzados</h2>
    <div class="info-row">
      <div>
        <b>Número de Nómina:</b> {nomina}<br>
        <b>Nombre de Profesor:</b> {nombre_profesor}
      </div>
      <div style="text-align: right;">
        <b>Fecha de liberación:</b> {fecha_actual}
      </div>
    </div>
    """

    html_completo = ESTILO_PDF + encabezado_html + tabla_html + resumen_html
    return html_completo

# --- MAIN ---

st.title("🤖 Confirmación de Carga Académica")

# Botón reiniciar conversación siempre visible
if st.button("🔄 Reiniciar conversación"):
    st.session_state.clear()
    st.experimental_rerun()

# Inicializar variables de sesión para pasos
if "paso" not in st.session_state:
    st.session_state.paso = 1
if "nombre" not in st.session_state:
    st.session_state.nombre = ""
if "nomina" not in st.session_state:
    st.session_state.nomina = ""
if "confirmacion" not in st.session_state:
    st.session_state.confirmacion = None
if "comentarios" not in st.session_state:
    st.session_state.comentarios = ""

# Paso 1: Pedir nombre
if st.session_state.paso == 1:
    nombre_input = st.text_input("Hola Profesor, estoy aquí para ayudarte a revisar tu carga académica para este próximo semestre.\n\nPor favor, dime tu nombre:")
    if nombre_input.strip():
        st.session_state.nombre = nombre_input.strip()
        st.session_state.paso = 2
        st.experimental_rerun()

# Paso 2: Pedir número de nómina
elif st.session_state.paso == 2:
    nomina_input = st.text_input(f"Gracias {st.session_state.nombre}. Ahora por favor ingresa tu número de nómina (ej. L01234567):")
    if nomina_input.strip():
        st.session_state.nomina = nomina_input.strip()
        # Cargar datos y verificar nómina
        df = cargar_datos()
        datos_profesor = df[df["Nómina"] == st.session_state.nomina].copy()
        if datos_profesor.empty:
            st.warning("⚠️ No se encontraron asignaciones para esa nómina. Por favor verifica e intenta de nuevo.")
        else:
            st.session_state.datos_profesor = datos_profesor
            st.session_state.paso = 3
            st.experimental_rerun()

# Paso 3: Mostrar carga
elif st.session_state.paso == 3:
    st.write(f"Hola **{st.session_state.nombre}**, esta es tu carga académica asignada:")
    resultado, total_udcs, total_carga_co, udcs_totales = mostrar_tabla_carga(st.session_state.datos_profesor)

    # Paso 4: Confirmación (radio sin selección inicial)
    st.subheader("✅ Confirmación de carga")
    confirmacion = st.radio(
        "¿Confirmas tu carga académica asignada para este semestre?",
        ["Sí", "No"],
        index=-1,  # No seleccionado inicialmente
        key="confirmacion_radio"
    )

    if confirmacion:
        st.session_state.confirmacion = confirmacion
        st.session_state.paso = 4
        st.experimental_rerun()

# Paso 4: Comentarios
elif st.session_state.paso == 4:
    if st.session_state.confirmacion == "Sí":
        st.info("✅ Gracias por confirmar tu carga, apreciamos mucho tu dedicación y colaboración en este proceso. Mucho éxito para este semestre.")
        placeholder = "Si tienes algún comentario adicional, puedes indicarlo aquí."
    else:
        st.warning("⚠️ Lamentamos que tu carga actual no sea de tu agrado. Por favor explícanos qué parte de tu carga presenta una limitación para poder revisarla.")
        placeholder = "Por favor detalla las limitaciones que observas en tu carga."

    comentarios_input = st.text_area(
        "En caso de tener algún comentario, duda o sugerencia respecto a tu carga académica asignada, por favor indícalo a continuación:",
        placeholder=placeholder,
        value=st.session_state.comentarios,
        key="comentarios_textarea"
    )

    if st.button("📨 Enviar confirmación"):
        if comentarios_input.strip() == "" and st.session_state.confirmacion == "No":
            st.error("Por favor indica al menos una explicación o comentario para que podamos ayudarte.")
        else:
            # Guardar respuestas en CSV
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            nueva_fila = pd.DataFrame([{
                "Fecha Hora": fecha_hora,
                "Nómina": st.session_state.nomina,
                "Nombre Profesor": st.session_state.nombre,
                "Confirmación": st.session_state.confirmacion,
                "Comentarios": comentarios_input.strip()
            }])
            if not os.path.exists(ARCHIVO_RESPUESTAS):
                nueva_fila.to_csv(ARCHIVO_RESPUESTAS, index=False)
            else:
                nueva_fila.to_csv(ARCHIVO_RESPUESTAS, mode='a', header=False, index=False)

            st.success("✅ Tu confirmación y comentarios se han registrado correctamente. ¡Gracias por tu tiempo!")

            # Guardar para PDF
            st.session_state.comentarios = comentarios_input.strip()
            st.session_state.paso = 5
            st.experimental_rerun()

# Paso 5: Generar PDF y ofrecer descarga
elif st.session_state.paso == 5:
    html_pdf = generar_pdf_html(
        st.session_state.nomina,
        st.session_state.nombre,
        st.session_state.datos_profesor
    )
    # Generar PDF en memoria
    pdf_bytes = HTML(string=html_pdf).write_pdf()

    st.success("📄 Aquí puedes descargar un PDF con tu carga académica asignada.")

    st.download_button(
        label="⬇️ Descargar PDF de mi carga académica",
        data=pdf_bytes,
        file_name=f"Reporte_{st.session_state.nomina}_{limpiar_nombre(st.session_state.nombre)}.pdf",
        mime="application/pdf"
    )
