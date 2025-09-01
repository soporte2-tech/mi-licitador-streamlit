import streamlit as st
import io
from PyPDF2 import PdfReader
import google.generativeai as genai
import json
import re
import base64

# --- Configuración de la clave de API (MODIFICAR AQUÍ) ---
# Reemplaza "TU_CLAVE_API_AQUÍ" con tu clave real de la API de Google Gemini.
GEMINI_API_KEY = "AIzaSyDcMQfWzddVSITX8lGtaoEPTit1l24DAeo"

# --- Funciones de procesamiento (basadas en tu código) ---
def process_files(uploaded_files):
    """Extrae texto de una lista de archivos subidos (.docx y .pdf)."""
    textos = []
    if not uploaded_files:
        return ""
    for uploaded_file in uploaded_files:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        if file_extension == 'docx':
            try:
                doc = Document(io.BytesIO(uploaded_file.getvalue()))
                full_text = []
                for para in doc.paragraphs:
                    full_text.append(para.text)
                textos.append('\n'.join(full_text))
            except Exception as e:
                st.warning(f"No se pudo procesar el archivo DOCX: {uploaded_file.name}. Error: {e}")
                continue
        elif file_extension == 'pdf':
            try:
                reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
                full_text = []
                for page in reader.pages:
                    full_text.append(page.extract_text())
                textos.append('\n'.join(full_text))
            except Exception as e:
                st.warning(f"No se pudo procesar el archivo PDF: {uploaded_file.name}. Error: {e}")
                continue
    return '\n\n'.join(textos)

def create_prompt_structure(pliegos_text, plantilla_text=""):
    """Crea el prompt para generar la estructura de la memoria técnica."""
    prompt = f"""
    Eres un experto en licitaciones públicas y redacción de memorias técnicas. Tu tarea es analizar los siguientes pliegos de una licitación y generar una propuesta de estructura para la memoria técnica que debe presentarse. La estructura debe ser lo más detallada posible, con secciones y subsecciones que reflejen los requisitos del pliego.

    Tu respuesta debe ser un objeto JSON con la siguiente estructura:
    {{
      "secciones": [
        {{
          "nombre": "Nombre de la Sección",
          "objetivo": "Breve descripción de lo que se debe desarrollar en esta sección.",
          "subsecciones": [
            {{
              "nombre": "Nombre de la Subsección",
              "objetivo": "Breve descripción de los puntos clave a desarrollar aquí."
            }}
          ]
        }}
      ]
    }}

    Considera los siguientes pliegos de la licitación:
    ---
    {pliegos_text}
    ---
    """
    if plantilla_text:
        prompt += f"""
        También, si se proporciona, utiliza esta plantilla como referencia para estructurar la respuesta, incorporando su formato y secciones si son pertinentes:
        ---
        {plantilla_text}
        ---
        """
    return prompt

def create_prompt_questions(pliegos_text):
    """Crea el prompt para generar una lista de preguntas guía."""
    prompt = f"""
    Eres un experto en licitaciones públicas. A partir del siguiente pliego de una licitación, genera un listado de preguntas concisas que un redactor debe responder en la memoria técnica para garantizar que cubre todos los requisitos clave.

    El listado debe ser directo y sin explicaciones adicionales. Cada pregunta debe ir en una línea separada.
    Si una pregunta requiere que el usuario suba un archivo, añade la etiqueta [FILE] al final de la pregunta.

    Pliegos:
    ---
    {pliegos_text}
    ---
    """
    return prompt

def generate_doc(structure, questions):
    """Genera un documento Word con la estructura y las preguntas."""
    document = Document()
    document.add_heading('Análisis de Licitación', level=1)
    document.add_heading('Estructura Propuesta para la Memoria Técnica', level=2)
    
    for section in structure.get("secciones", []):
        document.add_heading(section.get("nombre", "Sección sin nombre"), level=3)
        document.add_paragraph(f'Objetivo: {section.get("objetivo", "Sin objetivo definido.")}')
        for sub in section.get("subsecciones", []):
            document.add_paragraph(f'- {sub.get("nombre", "Subsección sin nombre")}: {sub.get("objetivo", "Sin objetivo definido.")}')

    document.add_page_break()
    document.add_heading('Preguntas Guía para la Redacción', level=2)
    for q in questions:
        document.add_paragraph(f'- {q}')

    doc_stream = io.BytesIO()
    document.save(doc_stream)
    doc_stream.seek(0)
    return doc_stream

# --- Lógica y Estructura de la aplicación Streamlit ---

st.set_page_config(
    page_title="Generador de Memorias Técnicas",
    page_icon="📝",
    layout="wide"
)

# --- Estilo CSS para la aplicación ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
        color: #1a237e;
    }
    .main-header {
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a237e;
        margin-bottom: 0.5rem;
    }
    .main-subheader {
        text-align: center;
        font-size: 1.1rem;
        color: #37474f;
        margin-bottom: 2rem;
    }
    .stButton>button {
        background-color: #3f51b5;
        color: white;
        font-size: 1.1rem;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        border: none;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #303f9f;
        transform: translateY(-2px);
    }
    .question-container {
        background-color: #e8eaf6;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        color: #1a237e;
        margin-bottom: 1rem;
    }
    .progress-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 1.5rem;
    }
    .progress-bar {
        height: 10px;
        background-color: #e0e0e0;
        border-radius: 5px;
        flex-grow: 1;
        margin-right: 1rem;
    }
    .progress-bar-fill {
        height: 100%;
        background-color: #3f51b5;
        border-radius: 5px;
        transition: width 0.5s ease;
    }
    [data-testid="stFileUploadDropzone"] {
        border-radius: 10px;
        border: 2px dashed #90caf9;
        background-color: #e3f2fd;
    }
    .stSuccess {
        background-color: #e8f5e9;
        color: #388e3c;
        border-left: 5px solid #388e3c;
        padding: 10px;
        border-radius: 5px;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Flujo de la aplicación ---
if 'step' not in st.session_state:
    st.session_state.step = "upload"
    st.session_state.questions = []
    st.session_state.current_question_index = 0
    st.session_state.show_download_button = False

if st.session_state.step == "upload":
    st.markdown('<div class="main-header">Generador de Memorias Técnicas</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subheader">Analiza tus pliegos y obtén una guía profesional para tu cliente.</div>', unsafe_allow_html=True)
    
    st.header("1. Sube tus documentos")
    pliegos_files = st.file_uploader(
        'Pliegos de la licitación (.docx o .pdf) (Obligatorio)',
        type=['docx', 'pdf'],
        accept_multiple_files=True
    )
    plantilla_file = st.file_uploader(
        'Plantilla de la memoria (.docx o .pdf) (Opcional)',
        type=['docx', 'pdf']
    )

    if st.button('Analizar Documentos', use_container_width=True):
        if not pliegos_files:
            st.error("⚠️ Por favor, sube al menos un archivo de pliegos.")
        elif GEMINI_API_KEY == "TU_CLAVE_API_AQUÍ":
            st.error("⚠️ Por favor, introduce tu Clave de API en el código.")
        else:
            with st.spinner("Analizando documentos... Esto puede tardar unos minutos."):
                try:
                    genai.configure(api_key=GEMINI_API_KEY)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    pliegos_text = process_files(pliegos_files)
                    plantilla_text = process_files([plantilla_file]) if plantilla_file else ""

                    # Generar Estructura
                    prompt_structure = create_prompt_structure(pliegos_text, plantilla_text)
                    response_structure = model.generate_content(prompt_structure)
                    structure_json_str = re.sub(r'```json\n|```', '', response_structure.text).strip()
                    structure = json.loads(structure_json_str)

                    # Generar Preguntas
                    prompt_questions = create_prompt_questions(pliegos_text)
                    response_questions = model.generate_content(prompt_questions)
                    questions = response_questions.text.split('\n')
                    questions = [q.strip() for q in questions if q.strip()]

                    # Generar documento y guardar en el estado de la sesión
                    st.session_state.docx_stream = generate_doc(structure, questions)
                    st.session_state.questions = questions
                    st.session_state.step = "results"
                    st.session_state.show_download_button = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Ocurrió un error inesperado: {e}")

if st.session_state.step == "results":
    st.markdown('<div class="main-header">Análisis Completado</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subheader">El informe de análisis se ha generado con éxito.</div>', unsafe_allow_html=True)
    st.success("✅ ¡Análisis completado! Tu archivo .docx está listo para ser descargado.")
    
    if st.session_state.show_download_button:
        st.download_button(
            label="Descargar Informe de Análisis",
            data=st.session_state.docx_stream,
            file_name="Informe_Analisis.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.session_state.show_download_button = False  # Para que no se muestre de nuevo al recargar
    
    if st.button('Continuar a la Sesión de Preguntas', use_container_width=True):
        st.session_state.step = "questions"
        st.rerun()

if st.session_state.step == "questions":
    st.header("Sesión de Preguntas para el Cliente")
    
    questions = st.session_state.questions
    current_index = st.session_state.current_question_index
    
    # Barra de progreso y contador
    progress = (current_index + 1) / len(questions) if len(questions) > 0 else 0
    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-bar">
            <div class="progress-bar-fill" style="width: {progress * 100}%;"></div>
        </div>
        <span>{current_index + 1}/{len(questions)}</span>
    </div>
    """, unsafe_allow_html=True)

    # Contenedor de la pregunta
    current_question = questions[current_index]
    is_file_upload_needed = "[FILE]" in current_question
    question_text = current_question.replace("[FILE]", "").strip()
    
    st.markdown(f'<div class="question-container">{question_text}</div>', unsafe_allow_html=True)
    
    if is_file_upload_needed:
        st.file_uploader("Sube el archivo aquí:", type=['jpg', 'jpeg', 'png', 'pdf', 'docx'], key=f"file_uploader_{current_index}")
    
    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if current_index > 0:
            if st.button('⬅️ Anterior', use_container_width=True):
                st.session_state.current_question_index -= 1
                st.rerun()
    with col_next:
        if current_index < len(questions) - 1:
            if st.button('Siguiente ➡️', use_container_width=True):
                st.session_state.current_question_index += 1
                st.rerun()
        elif current_index == len(questions) - 1:
            st.success("¡Has respondido a todas las preguntas!")
            if st.button('Volver a empezar', use_container_width=True):
                st.session_state.clear()

                st.rerun()
