import streamlit as st
import requests
from bs4 import BeautifulSoup
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
from langchain.llms import HuggingFaceHub
import re
import time
import os

# Page config
st.set_page_config(
    page_title="LinkedIn AI Analyzer",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Minimal styling (kept from original)
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .main-header { background: #0077b5; color: white; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; text-align: center; }
    .user-message { border-left: 4px solid #0077b5; padding: 12px; margin: 8px 0; color: white; }
    .assistant-message { border-left: 4px solid #00a0dc; padding: 12px; margin: 8px 0; color: white; }
</style>
""", unsafe_allow_html=True)

def get_hf_key():
    try:
        return st.secrets["huggingface"]["api_key"]
    except Exception:
        return os.environ.get("HUGGINGFACE_API_KEY")

def check_hf_key():
    return bool(get_hf_key())

def extract_linkedin_data(url, data_type):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return f"❌ Failed to access page (Status: {response.status_code}). The page may be private or require login."

        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        paragraphs = text.split('.')
        meaningful_content = [p.strip() for p in paragraphs if len(p.strip()) > 50]
        if not meaningful_content:
            return "❌ No meaningful content found. This might be a private page or require LinkedIn login."

        if data_type == "profile":
            header = f"👤 LINKEDIN PROFILE: {url}\n\n"
        elif data_type == "company":
            header = f"🏢 LINKEDIN COMPANY: {url}\n\n"
        else:
            header = f"📝 LINKEDIN POST: {url}\n\n"

        result = header + "📋 EXTRACTED CONTENT:\n\n"
        for i, content in enumerate(meaningful_content[:10], 1):
            result += f"{i}. {content}\n\n"
        result += f"\n✅ Extracted blocks: {len(meaningful_content)}\n"
        result += f"Total chars: {len(text)}\n"
        return result
    except Exception as e:
        return f"❌ Error extracting data: {str(e)}"

def get_text_chunks(text):
    if not text.strip():
        return []
    splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len)
    return splitter.split_text(text)

def get_vectorstore(text_chunks):
    if not text_chunks:
        return None
    documents = [Document(page_content=chunk) for chunk in text_chunks]
    embeddings = SentenceTransformerEmbeddings(model_name='all-MiniLM-L6-v2')
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore

def create_conversation_chain(vectorstore, model_name="meta-llama/Llama-2-7b-chat-hf"):
    if vectorstore is None:
        return None
    hf_key = get_hf_key()
    if not hf_key:
        st.error("Hugging Face API key not configured. Add it to Streamlit secrets as `[huggingface] api_key = \"hf_...\"`.")
        return None

    llm = HuggingFaceHub(repo_id=model_name, huggingfacehub_api_token=hf_key, model_kwargs={
        "temperature": 0.7, "max_new_tokens": 512, "top_p": 0.9
    })

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")
    chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=vectorstore.as_retriever(search_kwargs={"k": 3}), memory=memory, return_source_documents=True, output_key="answer")
    return chain

def display_message(role, content):
    if role == "user":
        st.markdown(f"<div class='user-message'><strong>👤 You:</strong><br>{content}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='assistant-message'><strong>🤖 Assistant:</strong><br>{content}</div>", unsafe_allow_html=True)

def main():
    st.markdown("<div class='main-header'><h1>💼 LinkedIn AI Analyzer</h1><p>Extract and analyze LinkedIn data with Hugging Face models</p></div>", unsafe_allow_html=True)

    if "conversation" not in st.session_state: st.session_state.conversation = None
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "processed" not in st.session_state: st.session_state.processed = False
    if "extracted_data" not in st.session_state: st.session_state.extracted_data = ""
    if "data_type" not in st.session_state: st.session_state.data_type = "profile"

    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        if check_hf_key():
            st.success("✅ Hugging Face key found")
        else:
            st.error("❌ Hugging Face key missing")
            st.info("Add your key in Streamlit secrets as `[huggingface] api_key = \"hf_...\"` or env var HUGGINGFACE_API_KEY")

        model_name = st.selectbox("🤖 Select Model", [
            "meta-llama/Llama-2-7b-chat-hf",
            "HuggingFaceH4/zephyr-7b-beta",
            "mistralai/Mistral-7B-Instruct-v0.2"
        ], index=0)

        data_type = st.selectbox("📊 Content Type", ["profile", "company", "post"])
        linkedin_url = st.text_input("🌐 LinkedIn URL", placeholder="https://www.linkedin.com/in/username/")

        if st.button("🚀 Extract & Analyze"):
            if not check_hf_key():
                st.error("Hugging Face API key not set.")
            elif not linkedin_url.strip():
                st.warning("Please enter a LinkedIn URL")
            else:
                with st.spinner("🔄 Extracting..."):
                    progress = st.progress(0)
                    extracted_data = extract_linkedin_data(linkedin_url, data_type)
                    progress.progress(33)
                    if extracted_data and not extracted_data.startswith("❌"):
                        chunks = get_text_chunks(extracted_data)
                        progress.progress(66)
                        if chunks:
                            vectorstore = get_vectorstore(chunks)
                            conversation = create_conversation_chain(vectorstore, model_name=model_name)
                            progress.progress(100)
                            if conversation:
                                st.session_state.conversation = conversation
                                st.session_state.processed = True
                                st.session_state.extracted_data = extracted_data
                                st.session_state.data_type = data_type
                                st.session_state.chat_history = []
                                st.success(f"✅ Ready to analyze {len(chunks)} content chunks.")
                                st.session_state.chat_history.append({"role": "assistant", "content": f"I've analyzed this LinkedIn {data_type}. What would you like to know?"})
                            else:
                                st.error("❌ Failed to initialize conversation (model or key issue).")
                        else:
                            st.error("❌ No meaningful content could be extracted from the page.")
                    else:
                        st.error(extracted_data)
                    progress.empty()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 💬 Analysis Chat")
        for i, chat in enumerate(st.session_state.chat_history):
            if chat["role"] == "user":
                display_message("user", chat["content"])
            else:
                if chat["content"]:
                    display_message("assistant", chat["content"])
                else:
                    with st.spinner("🤔 Analyzing..."):
                        try:
                            if st.session_state.conversation:
                                response = st.session_state.conversation.invoke({"question": st.session_state.chat_history[i-1]["content"]})
                                answer = response.get("answer", "I couldn't generate a response.")
                                st.session_state.chat_history[i]["content"] = answer
                                st.rerun()
                        except Exception as e:
                            st.session_state.chat_history[i]["content"] = f"❌ Error: {str(e)}"
                            st.rerun()

        if st.session_state.processed:
            user_input = st.chat_input("Ask about the LinkedIn data...")
            if user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": ""})
                st.rerun()
        else:
            st.info("👋 To get started: add HF key, enter a public LinkedIn URL, and click 'Extract & Analyze'.")

    with col2:
        if st.session_state.processed:
            st.markdown("### 📊 Data Overview")
            data = st.session_state.extracted_data
            chunks = get_text_chunks(data)
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Content Type", st.session_state.data_type.title())
                st.metric("Text Chunks", len(chunks))
            with c2:
                st.metric("Characters", f"{len(data):,}")
                st.metric("Words", f"{len(data.split()):,}")
            with st.expander("📋 View Extracted Data", expanded=False):
                st.text_area("Raw Data", data, height=200, label_visibility="collapsed")

if __name__ == "__main__":
    main()
