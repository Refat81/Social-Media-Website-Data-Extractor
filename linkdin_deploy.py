# linkdin_deploy.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_core.documents import Document
from langchain_community.llms import HuggingFaceHub
import re
import time

# Configure the page
st.set_page_config(
    page_title="LinkedIn AI Analyzer",
    page_icon="💼",
    layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .main-header { background: #0077B5; color: white; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; text-align: center; }
    .stButton>button { background-color: #0077b5; color: white; border: none; border-radius: 4px; padding: 8px 16px; width: 100%; }
    .stTextInput>div>div>input { background-color: #262730; color: white; border: 1px solid #555; }
    .stSelectbox>div>div>select { background-color: #262730; color: white; }
    .stTextArea textarea { background-color: #262730; color: white; }
</style>
""", unsafe_allow_html=True)

def get_embeddings():
    try:
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        return embeddings
    except Exception as e:
        st.error(f"❌ Failed to load embeddings: {e}")
        return None

def get_llm():
    api_key = st.session_state.get('hf_api_key')
    if not api_key:
        st.error("❌ HuggingFace API Key not found")
        return None
    
    try:
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large",
            huggingfacehub_api_token=api_key,
            model_kwargs={"temperature": 0.7, "max_length": 500}
        )
        return llm
    except Exception as e:
        st.error(f"❌ HuggingFace error: {e}")
        return None

def extract_linkedin_data(url, data_type):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return f"❌ Failed to access page (Status: {response.status_code})"
        
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
            return "❌ No meaningful content found."
        
        if data_type == "profile":
            result = "👤 LINKEDIN PROFILE DATA\n\n"
        elif data_type == "company":
            result = "🏢 LINKEDIN COMPANY DATA\n\n"
        else:
            result = "📝 LINKEDIN POST DATA\n\n"
        
        result += f"🔗 URL: {url}\n"
        result += "="*50 + "\n\n"
        
        for i, content in enumerate(meaningful_content[:10], 1):
            result += f"{i}. {content}\n\n"
        
        result += "="*50 + "\n"
        result += f"✅ Extracted {len(meaningful_content)} content blocks\n"
        
        return result
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_text_chunks(text):
    if not text.strip():
        return []
    splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200)
    return splitter.split_text(text)

def get_vectorstore(text_chunks):
    if not text_chunks:
        return None
    documents = [Document(page_content=chunk) for chunk in text_chunks]
    embeddings = get_embeddings()
    if embeddings is None:
        return None
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore

def get_conversation_chain(vectorstore):
    if vectorstore is None:
        return None
    try:
        llm = get_llm()
        if llm is None:
            return None
        
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            memory=memory,
            return_source_documents=True
        )
        return chain
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None

def main():
    st.markdown("""
    <div class="main-header">
        <h1>💼 LinkedIn AI Analyzer</h1>
        <p>Free Version - Powered by HuggingFace</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("← Back to Main Dashboard", use_container_width=True):
        st.info("Return to main dashboard")
        return
    
    if not st.session_state.get('hf_api_key'):
        st.error("❌ API Key not configured. Please go back to main dashboard.")
        return
    
    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "processed" not in st.session_state:
        st.session_state.processed = False
    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = ""
    
    # Sidebar
    with st.sidebar:
        st.success("✅ HuggingFace API Active")
        
        data_type = st.selectbox("📊 Content Type", ["profile", "company", "post"])
        
        url_placeholder = {
            "profile": "https://www.linkedin.com/in/username/",
            "company": "https://www.linkedin.com/company/companyname/", 
            "post": "https://www.linkedin.com/posts/username_postid/"
        }
        
        linkedin_url = st.text_input("🌐 LinkedIn URL", placeholder=url_placeholder[data_type])
        
        if st.button("🚀 Extract & Analyze", type="primary"):
            if not linkedin_url.strip():
                st.warning("Please enter a LinkedIn URL")
            else:
                with st.spinner("🔄 Extracting data..."):
                    extracted_data = extract_linkedin_data(linkedin_url, data_type)
                    
                    if extracted_data and not extracted_data.startswith("❌"):
                        chunks = get_text_chunks(extracted_data)
                        if chunks:
                            vectorstore = get_vectorstore(chunks)
                            conversation = get_conversation_chain(vectorstore)
                            if conversation:
                                st.session_state.conversation = conversation
                                st.session_state.processed = True
                                st.session_state.extracted_data = extracted_data
                                st.session_state.chat_history = []
                                st.success(f"✅ Ready to analyze {len(chunks)} content chunks!")
                            else:
                                st.error("❌ Failed to initialize AI")
                        else:
                            st.error("❌ No content extracted")
                    else:
                        st.error(extracted_data)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 💬 Chat")
        
        for i, chat in enumerate(st.session_state.chat_history):
            if chat["role"] == "user":
                st.markdown(f"**👤 You:** {chat['content']}")
            elif chat["role"] == "assistant":
                if chat["content"]:
                    st.markdown(f"**🤖 Assistant:** {chat['content']}")
        
        if st.session_state.processed:
            user_input = st.chat_input("Ask about the LinkedIn data...")
            if user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with st.spinner("🤔 Analyzing..."):
                    try:
                        if st.session_state.conversation:
                            response = st.session_state.conversation.invoke({"question": user_input})
                            answer = response.get("answer", "No response generated.")
                            st.session_state.chat_history.append({"role": "assistant", "content": answer})
                            st.rerun()
                    except Exception as e:
                        st.session_state.chat_history.append({"role": "assistant", "content": f"❌ Error: {str(e)}"})
                        st.rerun()
        else:
            st.info("👋 Enter a LinkedIn URL and click 'Extract & Analyze' to start")
    
    with col2:
        if st.session_state.processed:
            st.markdown("### 📊 Overview")
            data = st.session_state.extracted_data
            chunks = get_text_chunks(data)
            
            st.metric("Content Type", data_type.title())
            st.metric("Text Chunks", len(chunks))
            st.metric("Characters", f"{len(data):,}")

if __name__ == "__main__":
    main()
