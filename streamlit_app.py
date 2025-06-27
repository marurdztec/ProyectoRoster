import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Revisión de Carga Académica", layout="wide")

# --- Botón para reiniciar conversación ---
if st.button("🔄 Reiniciar conversación"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.experimental_rerun()

# --- Cargar archivo de carga académica ---
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

# --- Conversación paso a paso ---
st.title("🤖 Chatbot de Revisión de Carga Académica")

if 'step' not in st.session_state:
    st.session_state.step = 1

if st.session_state.step == 1:
    st.write("👋 Hola Profesor, estoy aquí para ayudarte a revisar tu carga académica para este próximo semestre.")
    nombre = st.text_input("Por favor, indícame tu nombre:")
    if nombre:
        st.session_state.nombre = nombre
        if st.button("➡️ Continuar"):
            st.session_state.step = 2

elif st.session_state.step == 2:
    nomina = st.text_input(f"Gracias {st.session_state.nombre}, ahora por favor indícame tu número de nómina (ej. L01234567):")
    if nomina:
        st.session_state.nomina = nomina.strip()
        if st.button("➡️ Continuar"):
            st.session_state.step = 3

elif st.session_state.step == 3:
    datos_profesor = df[df['Nómina'] == st.session_state.nomina].copy()
    if datos_profesor.empty:
        st.error("❌ No se encontraron asignaciones para ese número de nómina.")
    else:
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

        st.write("✅ Aquí está tu carga académica:")
        columnas_existentes = [col for col in columnas if col in datos_profesor.columns]
        st.dataframe(datos_profesor[columnas_existentes], use_container_width=True)

        st.write(f"**Total UDCs Docente:** {total_udcs} | **Total UDCs Coordinación:** {total_carga_co} | **UDCs Totales:** {udcs_totales}")

        confirmacion = st.radio(
            "¿Confirmas tu carga asignada para este semestre?",
            options=["Sí", "No"],
            index=None
        )
        if confirmacion:
            st.session_state.confirmacion = confirmacion
            if st.button("➡️ Continuar"):
                st.session_state.step = 4

elif st.session_state.step == 4:
    if st.session_state.confirmacion == "Sí":
        st.success("✅ Gracias por confirmar tu carga. Apreciamos mucho tu dedicación y colaboración en este proceso. ¡Mucho éxito para este semestre!")
        comentarios = st.text_area(
            "Si tienes algún comentario adicional, por favor indícalo aquí:"
        )
    else:
        st.warning("⚠️ Lamentamos que tu carga no sea de tu agrado.")
        comentarios = st.text_area(
            "Por favor, explícame qué parte de tu carga presenta una limitación para poder aceptarla:"
        )
    if st.button("➡️ Finalizar"):
        st.session_state.comentarios = comentarios
        st.session_state.step = 5

elif st.session_state.step == 5:
    st.success("✅ Gracias por tus comentarios, se registraron correctamente.")

    datos_profesor = df[df['Nómina'] == st.session_state.nomina].copy()

    columnas = ['UF', 'Grupo', 'Nombre de UF', 'Inglés', 'Tipo de UF',
                '% de Resp', 'UDCs', 'Periodo', 'Horario', 'Coordinador de Bloque']
    columnas_existentes = [col for col in columnas if col in datos_profesor.columns]
    tabla_html = datos_profesor[columnas_existentes].to_html(index=False, classes='tabla-centro', border=1)

    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    nombre_profesor = st.session_state.nombre

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
    <h2>{nombre_profesor} | Nómina: {st.session_state.nomina}</h2>
    <p>Fecha de descarga: {fecha_actual}</p>
    {tabla_html}
    </body>
    </html>
    """

    buffer = BytesIO()
    buffer.write(html_completo.encode())
    buffer.seek(0)

    st.download_button(
        label="📄 Descargar carga académica (HTML imprimible)",
        data=buffer,
        file_name=f"Carga_{st.session_state.nomina}_{nombre_profesor.replace(' ', '_')}.html",
        mime="text/html"
    )
