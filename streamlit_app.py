import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import os

st.set_page_config(page_title="Revisión de Carga Académica", layout="wide")

# Botón para reiniciar conversación
if st.button("🔄 Reiniciar conversación"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_rerun()

# Cargar datos
@st.cache_data
def cargar_datos():
    return pd.read_csv("Datos_Roster_V2.csv")

df = cargar_datos()
df.columns = df.columns.str.strip()

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

df['Tipo de UF'] = df['UF'].apply(clasificar_tipo_uf)

# Detectar coordinadores
if 'Carga Co.' in df.columns:
    coordinadores = df[df['Carga Co.'].notnull()][['UF', 'Grupo', 'Profesor', 'Correo']].copy()
    coordinadores = coordinadores.rename(columns={
        'Profesor': 'Coordinador',
        'Correo': 'Correo Coordinador'
    })
    df = df.merge(coordinadores, on=['UF', 'Grupo'], how='left')

st.title("🤖 Chatbot de Revisión de Carga Académica")

if 'step' not in st.session_state:
    st.session_state.step = 1

# Paso 1: Captura nombre
if st.session_state.step == 1:
    with st.form("nombre_form"):
        nombre = st.text_input("👋 Hola Profesor, estoy aquí para ayudarte a revisar tu carga académica para este próximo semestre.\n\nPor favor, indícame tu nombre:")
        submitted = st.form_submit_button("Continuar ➡️")
        if submitted and nombre:
            st.session_state.nombre = nombre
            st.session_state.step = 2
            st.experimental_rerun()

# Paso 2: Captura nómina
elif st.session_state.step == 2:
    with st.form("nomina_form"):
        nomina = st.text_input(f"Gracias {st.session_state.nombre}, ahora por favor indícame tu número de nómina (ej. L01234567):")
        submitted = st.form_submit_button("Continuar ➡️")
        if submitted and nomina:
            st.session_state.nomina = nomina.strip()
            st.session_state.step = 3
            st.experimental_rerun()

# Paso 3: Mostrar carga
elif st.session_state.step == 3:
    datos_profesor = df[df['Nómina'] == st.session_state.nomina].copy()
    if datos_profesor.empty:
        st.error("❌ No se encontraron asignaciones para ese número de nómina.")
    else:
        nombre_profesor_csv = datos_profesor['Profesor'].iloc[0] if 'Profesor' in datos_profesor.columns else "Nombre no disponible"

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

        columnas = ['UF', 'Grupo', 'Nombre de UF', 'Inglés', 'Tipo de UF',
                    '% de Resp', 'UDCs', 'Periodo', 'Horario', 'Coordinador de Bloque']
        columnas_existentes = [col for col in columnas if col in datos_profesor.columns]

        # Eliminar columna 'index' si existe
        if 'index' in datos_profesor.columns:
            datos_profesor = datos_profesor.drop(columns=['index'])

        st.write("✅ Aquí está tu carga académica para el semestre:")
        st.dataframe(
            datos_profesor[columnas_existentes].reset_index(drop=True),
            use_container_width=True
        )

        st.write(f"""
        <div style='display:flex; gap:20px;'>
            <div style='background-color:#f0f8ff; padding:10px; border-left:5px solid #003366; flex:1; text-align:center;'>
                <b>Total UDCs Docente</b><br><span style='font-size:20px;'>{total_udcs}</span>
            </div>
            <div style='background-color:#f0f8ff; padding:10px; border-left:5px solid #003366; flex:1; text-align:center;'>
                <b>Total UDCs Coordinación</b><br><span style='font-size:20px;'>{total_carga_co}</span>
            </div>
            <div style='background-color:#f0f8ff; padding:10px; border-left:5px solid #003366; flex:1; text-align:center;'>
                <b>UDCs Totales</b><br><span style='font-size:20px;'>{udcs_totales}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("confirm_form"):
            confirmacion = st.radio("¿Confirmas tu carga asignada para este semestre?", options=["Sí", "No"], index=None)
            comentarios = st.text_area("Comentarios, dudas o sugerencias adicionales:")
            submitted = st.form_submit_button("Enviar respuesta ✅")
            if submitted and confirmacion:
                # Guardar en CSV de forma persistente, nunca borrando datos previos
                respuesta_df = pd.DataFrame([{
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Nombre": nombre_profesor_csv,
                    "Nómina": st.session_state.nomina,
                    "Confirmación": confirmacion,
                    "Comentarios": comentarios
                }])
                try:
                    if os.path.exists("confirmaciones_respuestas.csv"):
                        respuesta_df.to_csv("confirmaciones_respuestas.csv", mode='a', header=False, index=False, encoding='utf-8-sig')
                    else:
                        respuesta_df.to_csv("confirmaciones_respuestas.csv", index=False, encoding='utf-8-sig')
                    st.success("✅ Tu respuesta ha sido registrada correctamente. ¡Gracias por tu tiempo y colaboración!")
                except Exception as e:
                    st.error(f"❌ Ocurrió un error al guardar la respuesta: {e}")

                st.session_state.step = 4
                st.session_state.nombre_profesor_csv = nombre_profesor_csv
                st.session_state.datos_profesor_tabla = datos_profesor[columnas_existentes]
                st.session_state.total_udcs = total_udcs
                st.session_state.total_carga_co = total_carga_co
                st.session_state.udcs_totales = udcs_totales
                st.experimental_rerun()

# Paso 4: Descargar carga como HTML
elif st.session_state.step == 4:
    st.info("Si lo deseas, puedes descargar tu carga académica en formato imprimible para tus registros.")

    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    nomina = st.session_state.nomina
    nombre_profesor_csv = st.session_state.nombre_profesor_csv

    tabla_html = st.session_state.datos_profesor_tabla.to_html(index=False, classes='tabla-centro', border=1)

    resumen_html = f"""
    <div style='display:flex; gap:20px; margin-top:15px;'>
        <div style='background-color:#f0f8ff; padding:10px; border-left:5px solid #003366; flex:1; text-align:center;'>
            <b>Total UDCs Docente</b><br><span style='font-size:18px;'>{st.session_state.total_udcs}</span>
        </div>
        <div style='background-color:#f0f8ff; padding:10px; border-left:5px solid #003366; flex:1; text-align:center;'>
            <b>Total UDCs Coordinación</b><br><span style='font-size:18px;'>{st.session_state.total_carga_co}</span>
        </div>
        <div style='background-color:#f0f8ff; padding:10px; border-left:5px solid #003366; flex:1; text-align:center;'>
            <b>UDCs Totales</b><br><span style='font-size:18px;'>{st.session_state.udcs_totales}</span>
        </div>
    </div>
    """

    html_completo = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <title>Carga Académica</title>
    <style>
        body {{
            font-family: Verdana, sans-serif;
            margin: 40px;
        }}
        h1, h2 {{
            text-align: center;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 6px;
            text-align: center;
        }}
        th {{
            background-color: #003366;
            color: white;
        }}
    </style>
    </head>
    <body>
    <h1>Carga Académica Agosto-Diciembre 2025</h1>
    <h2>Departamento de Mecánica y Materiales Avanzados</h2>
    <p style='text-align:center;'><b>Profesor:</b> {nombre_profesor_csv} | <b>Nómina:</b> {nomina} | <b>Fecha:</b> {fecha_actual}</p>
    {tabla_html}
    {resumen_html}
    </body>
    </html>
    """

    buffer = BytesIO()
    buffer.write(html_completo.encode())
    buffer.seek(0)

    st.download_button(
        label="📄 Descargar carga académica (HTML imprimible)",
        data=buffer,
        file_name=f"Carga_{nomina}_{nombre_profesor_csv.replace(' ', '_')}.html",
        mime="text/html"
    )
