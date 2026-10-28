
import os
import io
import streamlit as st
import pymupdf

from docx import Document
from google import genai

# Connect to Gemini
api_key = st.secrets.get("GEMINI_API_KEY")

# Create our webpage
st.title("My AI Document Chatbot")
st.write("Upload a document and ask questions!")

# Upload PDF, Word, or text documents
uploaded_file = st.file_uploader(
    "Choose a document",
    type=["pdf", "docx", "txt"]
)

# Function to read the uploaded document
def read_document(file):
    data = file.getvalue()

    if file.name.lower().endswith(".pdf"):
        text = ""
        with pymupdf.open(
            stream=data, filetype="pdf"
        ) as pdf:
            for page in pdf:
                text += page.get_text() + "\n"

        return text

    elif file.name.lower().endswith(".docx"):
        doc = Document(io.BytesIO(data))
        return "\n".join(
            paragraph.text
            for paragraph in doc.paragraphs
        )

    else:
        return data.decode("utf-8")

# Remember chat messages
if "messages" not in st.session_state:
    st.session_state.messages = []

if uploaded_file is not None:

    # Reset chat when document changes
    file_id = (
        uploaded_file.name,
        uploaded_file.size,
        hash(uploaded_file.getvalue())
    )

    if st.session_state.get("file_id") != file_id:
        st.session_state.file_id = file_id
        st.session_state.messages = []

    document_text = read_document(uploaded_file)

    if not document_text.strip():
        st.warning("No readable text found.")
        st.stop()

    st.success("Document uploaded successfully!")

    # Display previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Ask a question
    question = st.chat_input(
        "Ask something about your document"
    )

    if question:
        with st.chat_message("user"):
            st.write(question)

        st.session_state.messages.append({
            "role": "user",
            "content": question
        })

        if not api_key:
            st.error("GEMINI_API_KEY is missing.")
            st.stop()

        # Limit text for this beginner version
        context = document_text[:40000]

        prompt = f"""
        You are a helpful document assistant.

        Answer using only the document below.
        If the answer is not in the document,
        say "I could not find that in the document."

        DOCUMENT:
        {context}

        QUESTION:
        {question}
        """

        try:
            client = genai.Client(api_key=api_key)

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )

            answer = response.text or "No answer returned."

        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

        with st.chat_message("assistant"):
            st.write(answer)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

else:
    st.info("Please upload a document first.")
