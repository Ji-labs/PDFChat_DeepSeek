import streamlit as st
from PyPDF2 import PdfReader
from langchain_deepseek import ChatDeepSeek  # Using DeepSeek now after installation
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
import os

os.environ["DEEPSEEK_API_KEY"] = st.secrets.get("DEEPSEEK_API_KEY", "")

st.set_page_config(page_title="Chat with PDF", page_icon="📚")
st.title("Chat with your PDF 📚")

if "conversation" not in st.session_state:
    st.session_state.conversation = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "processComplete" not in st.session_state:
    st.session_state.processComplete = None

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            st.warning(f"Error reading PDF: {e}")
    return text

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1500, chunk_overlap=300, length_function=len)
    return text_splitter.split_text(text)

def get_conversation_chain(vectorstore):
    llm = ChatDeepSeek(model="deepseek-chat", api_key=os.environ["DEEPSEEK_API_KEY"])
    template = """You are an expert PDF assistant. Use the following context to answer questions accurately.\nProvide clear, concise responses. If unsure, say so.\n\n{context}\nQuestion: {question}\nAnswer:"""
    prompt = PromptTemplate(input_variables=['context', 'question'], template=template)
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    return ConversationalRetrievalChain.from_llm(llm=llm, retriever=vectorstore.as_retriever(), memory=memory, combine_docs_chain_kwargs={'prompt': prompt})

def process_docs(pdf_docs):
    if not pdf_docs:
        st.error("Please upload PDF files to begin.")
        return False
    try:
        import sentence_transformers  # Ensure sentence-transformers is installed
        raw_text = get_pdf_text(pdf_docs)
        text_chunks = get_text_chunks(raw_text)
        embeddings = HuggingFaceEmbeddings()
        vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
        st.session_state.conversation = get_conversation_chain(vectorstore)
        st.session_state.processComplete = True
        return True
    except ImportError:
        st.error("Could not import sentence_transformers. Please install it with `pip install sentence-transformers`.")
        return False
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return False

with st.sidebar:
    st.subheader("Your Documents")
    pdf_docs = st.file_uploader("Upload your PDFs here", type="pdf", accept_multiple_files=True)
    if st.button("Process") and pdf_docs:
        with st.spinner("Processing your PDFs..."):
            if process_docs(pdf_docs):
                st.success("Processing complete!")

if st.session_state.processComplete:
    user_question = st.chat_input("Ask a question about your documents:")
    if user_question:
        try:
            with st.spinner("Thinking..."):
                response = st.session_state.conversation({"question": user_question})
                st.session_state.chat_history.append(("You", user_question))
                st.session_state.chat_history.append(("Bot", response["answer"]))
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.write(message)
else:
    st.write("👈 Upload PDFs to begin chatting!")
