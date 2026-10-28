
import os
import io
import time
import random

import streamlit as st
import pymupdf

from docx import Document
from google import genai
from google.genai import errors


# Connect to Gemini
api_key = os.getenv("GEMINI_API_KEY")

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
            stream=data,
            filetype="pdf"
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

    # Read the document
    try:
        document_text = read_document(uploaded_file)

    except Exception as e:
        st.error(f"Document reading error: {e}")
        st.stop()

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

        # Check API key
        if not api_key:
            st.error(
                "GEMINI_API_KEY is missing. "
                "Please set your API key in the Terminal."
            )
            st.stop()

        # Limit document text for beginner version
        context = document_text[:40000]

        # Create prompt for Gemini
        prompt = f"""
        You are a helpful AI document assistant.

        Answer the user's question using only
        the information in the document below.

        Explain the answer in simple language.

        If the answer is not available in the
        document, say:
        "I could not find that in the document."

        DOCUMENT:
        {context}

        QUESTION:
        {question}
        """

        # Connect to Gemini and generate answer
        try:
            client = genai.Client(api_key=api_key)

            # Retry up to 3 times if Gemini is busy
            for attempt in range(3):

                try:
                    with st.spinner(
                        "Gemini is reading your document..."
                    ):
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=prompt
                        )

                    break

                except errors.ServerError as e:

                    # Retry only temporary server errors
                    if e.code not in (500, 502, 503, 504):
                        raise

                    if attempt == 2:
                        raise

                    wait_time = (2 ** attempt) + random.uniform(0, 1)

                    st.warning(
                        "Gemini is busy. "
                        "Trying again automatically..."
                    )

                    time.sleep(wait_time)

            answer = (
                response.text
                or "Gemini did not return an answer."
            )

        except errors.ClientError as e:
            st.error(f"Gemini API error: {e}")
            st.stop()

        except errors.ServerError as e:
            st.error(
                "Gemini is temporarily unavailable. "
                "Please try again after a few minutes."
            )
            st.stop()

        except Exception as e:
            st.error(f"Unexpected error: {e}")
            st.stop()

        # Display Gemini's answer
        with st.chat_message("assistant"):
            st.write(answer)

        # Save answer in chat history
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

else:
    st.info("Please upload a document first.")
