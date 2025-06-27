import streamlit as st
import pandas as pd
from io import StringIO

# Configuración de la página
st.set_page_config(page_title="Chatbot para Carga Académica AD25", layout="wide")

# Estilo CSS para mejorar visualización y scroll horizontal
st.markdown("""
    <style>
    .tabla-centro {
        border-collapse: collapse;
        width: 100%;
        font-family: Verdana, Segoe UI, sans-serif;
        font-size: 12px;
        margin-bottom: 20px;
        overflow-x: auto;
        display: block;
        white-space: nowrap;
    }
    .tabla-centro th, .tabla-centro td {
        border: 1px solid #ccc;
        padding: 8px;
        text-align: center;
    }
    .tabla-centro th {
        background-color: #003366;
        color: white;
    }
    .resumen-container {
        display: flex;
        gap: 20px;
        margin-top: 15px;
        font-family: Verdana, Segoe UI, sans-serif;
        font-size: 14px;
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
        font-size: 14px;
        color: #003366;
        margin-bottom: 3px;
    }
    .card span {
        font-size: 18px;
        font-weight: bold;
        color: #000;
    }
    .reiniciar-btn {
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Botón para reiniciar conversación arriba
if st.button("🔄 Reiniciar conversación", key="reiniciar", help="Borrar respuestas y empezar de nuevo", css_class="reiniciar-btn"):
    st.experimental_rerun()

# Cargar datos desde CSV local (o ruta que tengas)
@st.cache_data(show_spinner=False)
def cargar_datos():
    df = pd.read_csv("Datos_Roster_V2.csv")
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

    # Detectar coordinadores por Carga Co.
    if 'Carga Co.' in df.columns:
        coordinadores = df[df['Carga Co.'].notnull()][['UF', 'Grupo', 'Profesor', 'Correo']].copy()
        coordinadores = coordinadores.rename(columns={
            'Profesor': 'Coordinador',
            'Correo': 'Correo Coordinador'
        })
        df = df.merge(coordinadores, on=['UF', 'Grupo'], how='left')
    return df

df = cargar_datos()

st.title("Chatbot para Carga Académica AD25")
st.markdown("### Departamento Mecánica y Materiales Avanzados")
st.write("Hola Profesor, estoy aquí para ayudarte a revisar tu carga académica para este próximo semestre.")

# Usamos session_state para controlar pasos de la conversación
if "step" not in st.session_state:
    st.session_state.step = 1
if "nombre_profesor" not in st.session_state:
    st.session_state.nombre_profesor = ""
if "nomina" not in st.session_state:
    st.session_state.nomina = ""
if "datos_profesor" not in st.session_state:
    st.session_state.datos_profesor = pd.DataFrame()
if "confirma_carga" not in st.session_state:
    st.session_state.confirma_carga = None
if "comentarios" not in st.session_state:
    st.session_state.comentarios = ""

# Paso 1: Pedir nombre para saludo personalizado (opcional, solo para amabilidad)
if st.session_state.step == 1:
    nombre_input = st.text_input("Por favor, dime tu nombre:")
    if st.button("Continuar", key="btn1") and nombre_input.strip():
        st.session_state.nombre_profesor = nombre_input.strip()
        st.session_state.step = 2
        st.experimental_rerun()

if st.session_state.step >= 2:
    st.markdown(f"Hola **{st.session_state.nombre_profesor}**, por favor ingresa tu número de nómina (ejemplo: L01234567):")

# Paso 2: Pedir número de nómina
if st.session_state.step == 2:
    nomina_input = st.text_input("Número de nómina:")
    if st.button("Continuar", key="btn2") and nomina_input.strip():
        nomina_input = nomina_input.strip()
        # Filtrar datos para ese número de nómina
        datos_profesor = df[df['Nómina'] == nomina_input].copy()
        if datos_profesor.empty:
            st.error("No se encontraron asignaciones para esa nómina. Por favor verifica e intenta de nuevo.")
        else:
            st.session_state.nomina = nomina_input
            st.session_state.datos_profesor = datos_profesor
            # Guardar el nombre real del profesor del CSV
            st.session_state.nombre_profesor = datos_profesor['Profesor'].iloc[0]
            st.session_state.step = 3
            st.experimental_rerun()

# Paso 3: Mostrar carga y preguntar confirmación
if st.session_state.step == 3:
    datos_profesor = st.session_state.datos_profesor.copy()
    # Calcular totales
    datos_profesor['Carga Co.'] = pd.to_numeric(datos_profesor.get('Carga Co.', 0), errors='coerce').fillna(0)
    datos_profesor['UDCs'] = pd.to_numeric(datos_profesor.get('UDCs', 0), errors='coerce').fillna(0)
    total_carga_co = round(datos_profesor['Carga Co.'].sum(), 2)
    total_udcs = round(datos_profesor['UDCs'].sum(), 2)
    udcs_totales = round(total_udcs + total_carga_co, 2)

    # Crear columna Coordinador de Bloque
    def mostrar_coordinador(row):
        if row['Tipo de UF'] in ['Bloque', 'Concentración']:
            return f"{row.get('Coordinador', '')} ({row.get('Correo Coordinador', '')})"
        return ""
    datos_profesor['Coordinador de Bloque'] = datos_profesor.apply(mostrar_coordinador, axis=1)

    # Formatear columna Grupo
    datos_profesor['Grupo'] = datos_profesor['Grupo'].fillna('').apply(
        lambda x: str(int(x)) if isinstance(x, float) else str(x)
    )

    columnas = [
        'UF', 'Grupo', 'Nombre de UF', 'Inglés', 'Tipo de UF',
        '% de Resp', 'UDCs', 'Periodo', 'Horario', 'Coordinador de Bloque'
    ]
    tabla_mostrar = datos_profesor[columnas]

    st.markdown("#### Tu carga académica asignada:")
    # Mostrar tabla sin índice y con scroll horizontal limitado
    st.dataframe(tabla_mostrar, use_container_width=True, height=300)

    # Mostrar los recuadros con totales
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Total UDCs Docente**  \n{total_udcs}")
    c2.markdown(f"**Total UDCs Coordinación**  \n{total_carga_co}")
    c3.markdown(f"**UDCs Totales**  \n{udcs_totales}")

    st.markdown("¿Confirmas que esta carga asignada es correcta?")
    confirma = st.radio("", options=["Sí", "No"], index=-1, horizontal=True, key="confirma_radio")
    if st.button("Continuar", key="btn3") and confirma in ["Sí", "No"]:
        st.session_state.confirma_carga = confirma
        st.session_state.step = 4
        st.experimental_rerun()

# Paso 4: Comentarios dependiendo confirmación
if st.session_state.step == 4:
    if st.session_state.confirma_carga == "Sí":
        st.success("Gracias por confirmar tu carga, apreciamos mucho tu dedicación y colaboración en este proceso. Mucho éxito para este semestre.")
        st.session_state.comentarios = ""
        st.markdown("Si tienes algún comentario adicional, puedes escribirlo aquí (opcional):")
        comentarios_input = st.text_area("", value="", key="comentarios")
        if st.button("Finalizar", key="btn_fin1"):
            st.session_state.comentarios = comentarios_input.strip()
            # Guardar respuestas en CSV
            with open("confirmaciones_respuestas.csv", "a", encoding="utf-8") as f:
                f.write(f"{st.session_state.nomina},{st.session_state.nombre_profesor},{st.session_state.confirma_carga},{st.session_state.comentarios},{pd.Timestamp.now()}\n")
            st.success("Tus respuestas han sido registradas. ¡Gracias!")
            st.session_state.step = 5
            st.experimental_rerun()
    else:
        st.warning("Lamento que no sea de tu agrado, por favor explícame qué parte de tu carga presenta una limitación para poder aceptarla.")
        comentarios_input = st.text_area("", value=st.session_state.comentarios, key="comentarios_neg")
        if st.button("Enviar comentario", key="btn_fin2") and comentarios_input.strip():
            st.session_state.comentarios = comentarios_input.strip()
            # Guardar respuestas en CSV
            with open("confirmaciones_respuestas.csv", "a", encoding="utf-8") as f:
                f.write(f"{st.session_state.nomina},{st.session_state.nombre_profesor},{st.session_state.confirma_carga},{st.session_state.comentarios},{pd.Timestamp.now()}\n")
            st.success("Tus respuestas han sido registradas. ¡Gracias por tu colaboración!")
            st.session_state.step = 5
            st.experimental_rerun()

# Paso 5: Mostrar HTML imprimible con carga
if st.session_state.step == 5:
    datos_profesor = st.session_state.datos_profesor.copy()
    total_carga_co = round(pd.to_numeric(datos_profesor.get('Carga Co.', 0), errors='coerce').fillna(0).sum(), 2)
    total_udcs = round(pd.to_numeric(datos_profesor.get('UDCs', 0), errors='coerce').fillna(0).sum(), 2)
    udcs_totales = round(total_udcs + total_carga_co, 2)

    # Crear columna Coordinador de Bloque
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

    # Generar HTML imprimible
    estilo_html = """
    <style>
      @media print {
        body {
          font-family: Verdana, Segoe UI, sans-serif;
          font-size: 12px;
          margin: 1cm;
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
        table {
          border-collapse: collapse;
          width: 100%;
          font-size: 12px;
          margin-bottom: 20px;
        }
        th, td {
          border: 1px solid #ccc;
          padding: 6px;
          text-align: center;
          word-wrap: break-word;
        }
        th {
          background-color: #003366;
          color: white;
        }
        .resumen-container {
          display: flex;
          gap: 20px;
          margin-top: 15px;
          font-size: 14px;
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
          font-size: 14px;
          color: #003366;
          margin-bottom: 3px;
        }
        .card span {
          font-size: 18px;
          font-weight: bold;
          color: #000;
        }
      }
    </style>
    """

    html_carga = tabla_mostrar.to_html(index=False, classes='tabla-centro', border=1, escape=False)

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

    encabezado_html = """
    <h1>Chatbot para Carga Académica AD25</h1>
    <h2>Departamento Mecánica y Materiales Avanzados</h2>
    """

    html_final = estilo_html + encabezado_html + html_carga + resumen_html

    st.markdown("### Aquí está tu carga académica para imprimir o guardar como PDF:")
    st.markdown(html_final, unsafe_allow_html=True)
    st.info("Puedes usar el botón de imprimir de tu navegador (Ctrl+P o Cmd+P) para guardar esta página como PDF.")

    if st.button("Finalizar y Reiniciar"):
        st.session_state.clear()
        st.experimental_rerun()
