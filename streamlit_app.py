import streamlit as st
import pandas as pd
from datetime import datetime
import os
import unicodedata
import re

# --- Función para limpiar nombre para PDF ---
def limpiar_nombre(nombre):
    nombre = unicodedata.normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('utf-8')
    nombre = re.sub(r'[^\w\s-]', '', nombre)
    nombre = re.sub(r'\s+', '_', nombre.strip())
    return nombre

# --- Cargar datos CSV ---
@st.cache_data
def cargar_datos():
    df = pd.read_csv("Datos_Roster_V2.csv")
    df.columns = df.columns.str.strip()
    return df

df = cargar_datos()

# --- Clasificar tipo de UF ---
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

df['Tipo de UF'] = df['UF'].apply(clasificar_tipo_uf)

# --- Detectar coordinadores por Carga Co. ---
if 'Carga Co.' in df.columns:
    coordinadores = df[df['Carga Co.'].notnull()][['UF', 'Grupo', 'Profesor', 'Correo']].copy()
    coordinadores = coordinadores.rename(columns={
        'Profesor': 'Coordinador',
        'Correo': 'Correo Coordinador'
    })
    df = df.merge(coordinadores, on=['UF', 'Grupo'], how='left')
else:
    st.warning("No se encontró la columna 'Carga Co.' en el archivo CSV.")

# --- Inicializar estado ---
if 'step' not in st.session_state:
    st.session_state.step = 0
if 'nombre_profesor' not in st.session_state:
    st.session_state.nombre_profesor = ''
if 'nomina' not in st.session_state:
    st.session_state.nomina = ''
if 'confirmacion' not in st.session_state:
    st.session_state.confirmacion = None
if 'comentarios' not in st.session_state:
    st.session_state.comentarios = ''

# --- Función para resetear ---
def reset_conversacion():
    st.session_state.step = 0
    st.session_state.nombre_profesor = ''
    st.session_state.nomina = ''
    st.session_state.confirmacion = None
    st.session_state.comentarios = ''
    st.experimental_rerun = lambda: None  # Se elimina rerun para evitar errores, si quieres quitar del todo

st.sidebar.button("Reiniciar conversación", on_click=reset_conversacion)

st.title("Chatbot para revisión de carga académica")

if st.session_state.step == 0:
    st.write("Hola Profesor, estoy aquí para ayudarte a revisar tu carga académica para este próximo semestre.")
    nombre = st.text_input("Por favor, dime tu nombre:")
    if st.button("Continuar") and nombre.strip() != "":
        st.session_state.nombre_profesor = nombre.strip()
        st.session_state.step = 1

elif st.session_state.step == 1:
    st.write(f"Hola, {st.session_state.nombre_profesor}! Por favor, ingresa tu número de nómina (ej. L01234567):")
    nomina = st.text_input("Número de nómina:")
    if st.button("Continuar") and nomina.strip() != "":
        st.session_state.nomina = nomina.strip()
        # Validar si existe nómina en df
        if st.session_state.nomina not in df['Nómina'].values:
            st.error("No se encontraron asignaciones para esa nómina.")
        else:
            st.session_state.step = 2

elif st.session_state.step == 2:
    datos_profesor = df[df['Nómina'] == st.session_state.nomina].copy()
    if datos_profesor.empty:
        st.error("No se encontraron asignaciones para esa nómina.")
        st.session_state.step = 1  # Volver a pedir nomina
    else:
        # Nombre real del profesor (del csv)
        nombre_real = datos_profesor['Profesor'].iloc[0]
        st.write(f"Carga académica para: **{nombre_real}**")
        
        # Procesar columnas numéricas
        datos_profesor['Carga Co.'] = pd.to_numeric(datos_profesor.get('Carga Co.', 0), errors='coerce').fillna(0)
        datos_profesor['UDCs'] = pd.to_numeric(datos_profesor.get('UDCs', 0), errors='coerce').fillna(0)

        total_carga_co = round(datos_profesor['Carga Co.'].sum(), 2)
        total_udcs = round(datos_profesor['UDCs'].sum(), 2)
        udcs_totales = round(total_udcs + total_carga_co, 2)

        def mostrar_coordinador(row):
            if row['Tipo de UF'] in ['Bloque', 'Concentración']:
                return f"{row.get('Coordinador', '')} ({row.get('Correo Coordinador', '')})"
            return ""

        datos_profesor['Coordinador de Bloque'] = datos_profesor.apply(mostrar_coordinador, axis=1)

        datos_profesor['Grupo'] = datos_profesor['Grupo'].fillna('').apply(
            lambda x: str(int(x)) if isinstance(x, float) else str(x)
        )

        columnas = [
            'UF', 'Grupo', 'Nombre de UF', 'Inglés', 'Tipo de UF',
            '% de Resp', 'UDCs', 'Periodo', 'Horario', 'Coordinador de Bloque'
        ]
        tabla_mostrar = datos_profesor[columnas]

        st.dataframe(tabla_mostrar, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total UDCs Docente", total_udcs)
        col2.metric("Total UDCs Coordinación", total_carga_co)
        col3.metric("UDCs Totales", udcs_totales)

        st.session_state.nombre_profesor = nombre_real

        if st.button("Confirmar carga asignada"):
            st.session_state.confirmacion = True
            st.session_state.step = 3

        if st.button("No confirmo la carga asignada"):
            st.session_state.confirmacion = False
            st.session_state.step = 3

elif st.session_state.step == 3:
    if st.session_state.confirmacion:
        st.success("Gracias por confirmar tu carga, apreciamos mucho tu dedicación y colaboración en este proceso. Mucho éxito para este semestre.")
    else:
        st.warning("Lamento que no sea de tu agrado, por favor explícanos qué parte de tu carga presenta una limitación para poder aceptarla.")

    comentarios = st.text_area("Por favor, si tienes algún comentario, duda o sugerencia relacionada con tu carga académica, compártelo aquí:")

    if st.button("Enviar comentarios y finalizar"):
        # Guardar respuestas en CSV local
        archivo_confirmaciones = "confirmaciones_respuestas.csv"

        # Crear dataframe de respuesta
        df_respuesta = pd.DataFrame([{
            'FechaHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Nómina': st.session_state.nomina,
            'Profesor': st.session_state.nombre_profesor,
            'Confirmó carga': st.session_state.confirmacion,
            'Comentarios': comentarios
        }])

        if os.path.exists(archivo_confirmaciones):
            df_existente = pd.read_csv(archivo_confirmaciones)
            df_final = pd.concat([df_existente, df_respuesta], ignore_index=True)
        else:
            df_final = df_respuesta

        df_final.to_csv(archivo_confirmaciones, index=False)

        st.success("Tus respuestas han sido registradas correctamente.")

        st.session_state.comentarios = comentarios
        st.session_state.step = 4

elif st.session_state.step == 4:
    st.write(f"Profesor: **{st.session_state.nombre_profesor}**")
    st.write("Aquí puedes descargar un PDF con tu carga académica.")

    datos_profesor = df[df['Nómina'] == st.session_state.nomina].copy()

    # Preparar datos para PDF
    datos_profesor['Carga Co.'] = pd.to_numeric(datos_profesor.get('Carga Co.', 0), errors='coerce').fillna(0)
    datos_profesor['UDCs'] = pd.to_numeric(datos_profesor.get('UDCs', 0), errors='coerce').fillna(0)

    total_carga_co = round(datos_profesor['Carga Co.'].sum(), 2)
    total_udcs = round(datos_profesor['UDCs'].sum(), 2)
    udcs_totales = round(total_udcs + total_carga_co, 2)

    def mostrar_coordinador(row):
        if row['Tipo de UF'] in ['Bloque', 'Concentración']:
            return f"{row.get('Coordinador', '')} ({row.get('Correo Coordinador', '')})"
        return ""

    datos_profesor['Coordinador de Bloque'] = datos_profesor.apply(mostrar_coordinador, axis=1)
    datos_profesor['Grupo'] = datos_profesor['Grupo'].fillna('').apply(
        lambda x: str(int(x)) if isinstance(x, float) else str(x)
    )
    columnas_pdf = [
        'UF', 'Grupo', 'Nombre de UF', 'Inglés', 'Tipo de UF',
        '% de Resp', 'UDCs', 'Periodo', 'Horario', 'Coordinador de Bloque'
    ]
    tabla_pdf = datos_profesor[columnas_pdf]

    # Estilo para el PDF
    estilo = """
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

    from weasyprint import HTML
    import tempfile

    # Crear contenido HTML para PDF
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    encabezado_html = f"""
    <h1>Carga Académica Agosto-Diciembre 2025</h1>
    <h2>Departamento Mecánica y Materiales Avanzados</h2>
    <div class="info-row">
      <div>
        <b>Número de Nómina:</b> {st.session_state.nomina}<br>
        <b>Nombre de Profesor:</b> {st.session_state.nombre_profesor}
      </div>
      <div style="text-align: right;">
        <b>Fecha de liberación:</b> {fecha_actual}
      </div>
    </div>
    """

    tabla_html = tabla_pdf.to_html(index=False, escape=False, na_rep='', classes='tabla-centro')
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

    html_completo = estilo + encabezado_html + tabla_html + resumen_html

    # Botón para generar y descargar PDF
    if st.button("Descargar PDF con mi carga académica"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            HTML(string=html_completo).write_pdf(tmp_pdf.name)
            tmp_pdf.flush()
            pdf_bytes = open(tmp_pdf.name, "rb").read()
            st.download_button(
                label="Haz clic aquí para descargar tu PDF",
                data=pdf_bytes,
                file_name=f"Reporte_{st.session_state.nomina}_{limpiar_nombre(st.session_state.nombre_profesor)}.pdf",
                mime="application/pdf",
            )

st.write("---")
st.sidebar.write("© 2025 Departamento de Mecánica y Materiales Avanzados")
