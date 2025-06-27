import streamlit as st
import pandas as pd

st.set_page_config(page_title="Revisión de Carga Académica", layout="wide")

if st.button("🔄 Reiniciar conversación"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

@st.cache_data
def cargar_datos():
    return pd.read_csv("Datos_Roster_V2.csv")

df = cargar_datos()
df.columns = df.columns.str.strip()

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

if 'Carga Co.' in df.columns:
    coordinadores = df[df['Carga Co.'].notnull()][['UF', 'Grupo', 'Profesor', 'Correo']].copy()
    coordinadores = coordinadores.rename(columns={'Profesor': 'Coordinador','Correo': 'Correo Coordinador'})
    df = df.merge(coordinadores, on=['UF', 'Grupo'], how='left')

st.title("🤖 Chatbot de Revisión de Carga Académica")

if 'step' not in st.session_state:
    st.session_state.step = 1

if st.session_state.step == 1:
    with st.form("nombre_form"):
        nombre = st.text_input("👋 Hola Profesor, por favor indícame tu nombre para iniciar la revisión de tu carga académica:")
        submitted = st.form_submit_button("Continuar ➡️")
        if submitted and nombre:
            st.session_state.nombre = nombre
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    with st.form("nomina_form"):
        nomina = st.text_input(f"Gracias {st.session_state.nombre}, ahora indícame tu número de nómina (ej. L01234567):")
        submitted = st.form_submit_button("Continuar ➡️")
        if submitted and nomina:
            st.session_state.nomina = nomina.strip()
            st.session_state.step = 3
            st.rerun()

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
        datos_profesor['Grupo'] = datos_profesor['Grupo'].fillna('').apply(lambda x: str(int(x)) if isinstance(x, float) else str(x))

        columnas = ['UF', 'Grupo', 'Nombre de UF', 'Inglés', 'Tipo de UF', '% de Resp', 'UDCs', 'Periodo', 'Horario', 'Coordinador de Bloque']
        columnas_existentes = [col for col in columnas if col in datos_profesor.columns]

        st.write("✅ Aquí está tu carga académica para el semestre:")
        st.dataframe(datos_profesor[columnas_existentes], use_container_width=True)

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

        st.success("Para confirmar tu carga académica y enviar tus comentarios, por favor da clic en el siguiente botón. Se abrirá un formulario de Microsoft Forms para capturar tu confirmación y observaciones de forma ordenada.")

        st.markdown("""
        <a href='https://forms.office.com/r/MAFjP70biu' target='_blank'>
            <button style="background-color:#003366; color:white; padding:12px 24px; border:none; border-radius:6px; font-size:16px; cursor:pointer;">
                📝 Ir al formulario para confirmar carga y enviar comentarios
            </button>
        </a>
        """, unsafe_allow_html=True)
