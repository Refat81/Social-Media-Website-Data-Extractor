# let_deploy.py
import streamlit as st
import time
from bs4 import BeautifulSoup
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from langchain_community.llms import HuggingFaceHub
import re
import requests
import os
from datetime import datetime
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Facebook Extractor 2.0", page_icon="📘", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .main-header { background: linear-gradient(135deg, #FF6B35, #FF8E53); color: white; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; text-align: center; }
    .stButton>button { background-color: #1877F2; color: white; border: none; border-radius: 4px; padding: 8px 16px; width: 100%; }
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
            model_kwargs={"temperature": 0.7, "max_length": 512}
        )
        return llm
    except Exception as e:
        st.error(f"❌ HuggingFace error: {e}")
        return None

class FacebookGroupExtractor:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.is_logged_in = False
        
    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            st.info("🔄 Setting up Chrome browser...")
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 25)
            st.success("✅ Chrome browser setup completed!")
            return True
        except Exception as e:
            st.error(f"❌ Failed to setup Chrome: {str(e)}")
            return False
    
    def manual_login(self):
        try:
            st.info("🔓 Opening Facebook for manual login...")
            self.driver.get("https://www.facebook.com")
            time.sleep(3)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            st.success("✅ Facebook opened successfully!")
            st.info("""
            **📝 Manual Login Instructions:**
            1. Browser window opened with Facebook
            2. Manually login to your account
            3. Complete any security checks
            4. Return here and click 'I'm Logged In'
            """)
            return True
        except Exception as e:
            st.error(f"❌ Failed to open Facebook: {str(e)}")
            return False
    
    def check_login_status(self):
        try:
            current_url = self.driver.current_url.lower()
            login_success_urls = ["facebook.com/home", "facebook.com/groups", "facebook.com/marketplace"]
            if any(url in current_url for url in login_success_urls):
                self.is_logged_in = True
                return True
            
            login_indicators = ["//a[@aria-label='Profile']", "//div[@aria-label='Account']", "//span[contains(text(), 'Menu')]"]
            for indicator in login_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    for element in elements:
                        if element.is_displayed():
                            self.is_logged_in = True
                            return True
                except:
                    continue
            return False
        except Exception as e:
            logger.error(f"Login check error: {str(e)}")
            return False
    
    def extract_group_data(self, group_url: str, max_scrolls: int = 10) -> dict:
        try:
            if not self.is_logged_in:
                return {"error": "Not logged in. Please login first.", "status": "error"}
            
            st.info(f"🌐 Accessing group: {group_url}")
            self.driver.get(group_url)
            time.sleep(5)
            
            # Extract group info
            group_info = self._extract_group_info()
            posts_data = self._scroll_and_extract_posts(max_scrolls)
            
            return {
                "group_info": group_info,
                "posts": posts_data,
                "extraction_time": datetime.now().isoformat(),
                "total_posts": len(posts_data),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            return {"error": f"Extraction failed: {str(e)}", "status": "error"}
    
    def _extract_group_info(self) -> dict:
        group_info = {}
        try:
            name_selectors = ["//h1", "//h2", "//h3", "//title"]
            for selector in name_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        name = element.text.strip()
                        if name and len(name) > 3:
                            group_info["name"] = name
                            break
                    if "name" in group_info:
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Group info extraction failed: {str(e)}")
        return group_info
    
    def _scroll_and_extract_posts(self, max_scrolls: int) -> List[dict]:
        all_posts = []
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for scroll_iteration in range(max_scrolls):
            current_posts = self._extract_posts_from_current_page()
            for post in current_posts:
                if not self._is_duplicate_post(post, all_posts):
                    all_posts.append(post)
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        return all_posts
    
    def _extract_posts_from_current_page(self) -> List[dict]:
        posts = []
        strategies = [
            ("//div[@role='article']", "article"),
            ("//div[contains(@data-pagelet, 'Feed')]//div", "feed"),
            ("//div[contains(@class, 'userContent')]", "userContent")
        ]
        
        for xpath, source in strategies:
            posts.extend(self._extract_by_xpath(xpath, source))
        
        return posts
    
    def _extract_by_xpath(self, xpath: str, source: str) -> List[dict]:
        posts = []
        try:
            elements = self.driver.find_elements(By.XPATH, xpath)
            for element in elements:
                try:
                    post_text = element.text.strip()
                    if self._is_valid_post(post_text):
                        post_data = {
                            "content": post_text,
                            "source": source,
                            "timestamp": datetime.now().isoformat(),
                            "has_comments": False,
                            "reactions": 0
                        }
                        posts.append(post_data)
                except:
                    continue
        except:
            pass
        return posts
    
    def _is_valid_post(self, text: str) -> bool:
        if not text or len(text) < 30:
            return False
        excluded_phrases = ['facebook', 'login', 'sign up', 'password', 'menu', 'navigation']
        text_lower = text.lower()
        if any(phrase in text_lower for phrase in excluded_phrases):
            return False
        words = text.split()
        return len(words) >= 5
    
    def _is_duplicate_post(self, new_post: dict, existing_posts: List[dict]) -> bool:
        new_content = new_post.get("content", "")[:100]
        for existing_post in existing_posts:
            existing_content = existing_post.get("content", "")[:100]
            similarity = self._calculate_similarity(new_content, existing_content)
            if similarity > 0.7:
                return True
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0.0
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def process_group_data(group_data: dict):
    if not group_data or "posts" not in group_data or not group_data["posts"]:
        return None, []
    
    all_text = f"Group: {group_data.get('group_info', {}).get('name', 'Unknown')}\n\n"
    all_text += f"Total Posts: {len(group_data['posts'])}\n\n"
    
    for i, post in enumerate(group_data["posts"]):
        content = post.get("content", "")
        all_text += f"--- Post {i+1} ---\n"
        all_text += f"Content: {content}\n\n"
    
    splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(all_text)
    documents = [Document(page_content=chunk) for chunk in chunks]
    
    try:
        embeddings = get_embeddings()
        if embeddings is None:
            return None, []
        vectorstore = FAISS.from_documents(documents, embeddings)
        return vectorstore, chunks
    except Exception as e:
        st.error(f"Vector store creation failed: {e}")
        return None, []

def create_chatbot(vectorstore):
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
        st.error(f"Failed to create chatbot: {str(e)}")
        return None

def main():
    st.markdown("""
    <div class="main-header">
        <h1>🔥 Facebook Group Extractor 2.0</h1>
        <p>Professional Version - Powered by HuggingFace</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("← Back to Main Dashboard", use_container_width=True):
        st.info("Return to main dashboard")
        return
    
    if not st.session_state.get('hf_api_key'):
        st.error("❌ API Key not configured. Please go back to main dashboard.")
        return
    
    # Initialize session state
    if "extractor" not in st.session_state:
        st.session_state.extractor = None
    if "login_status" not in st.session_state:
        st.session_state.login_status = "not_started"
    if "group_data" not in st.session_state:
        st.session_state.group_data = None
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Sidebar
    with st.sidebar:
        st.success("✅ HuggingFace API Active")
        
        # Login section
        st.subheader("🔐 Facebook Login")
        
        if st.session_state.login_status == "not_started":
            if st.button("🚪 Start Manual Login", type="primary", use_container_width=True):
                with st.spinner("Setting up browser..."):
                    extractor = FacebookGroupExtractor()
                    if extractor.setup_driver():
                        st.session_state.extractor = extractor
                        if extractor.manual_login():
                            st.session_state.login_status = "in_progress"
                            st.rerun()
        
        elif st.session_state.login_status == "in_progress":
            st.info("🔄 Login in progress...")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ I'm Logged In", type="primary"):
                    if st.session_state.extractor and st.session_state.extractor.check_login_status():
                        st.session_state.login_status = "completed"
                        st.success("✅ Login successful!")
                        st.rerun()
            with col2:
                if st.button("❌ Cancel"):
                    if st.session_state.extractor:
                        st.session_state.extractor.close()
                    st.session_state.login_status = "not_started"
                    st.rerun()
        
        elif st.session_state.login_status == "completed":
            st.success("✅ Logged in to Facebook")
        
        # Group extraction
        st.subheader("📝 Group Information")
        group_url = st.text_input("Facebook Group URL", placeholder="https://www.facebook.com/groups/groupname/")
        max_scrolls = st.slider("Number of scrolls", 5, 20, 10)
        
        if st.button("🚀 Extract Group Data", type="primary", use_container_width=True):
            if st.session_state.login_status != "completed":
                st.error("❌ Please login to Facebook first")
            elif not group_url or "facebook.com/groups/" not in group_url:
                st.error("❌ Please enter a valid Facebook group URL")
            else:
                with st.spinner("🌐 Extracting group data..."):
                    group_data = st.session_state.extractor.extract_group_data(group_url, max_scrolls)
                    if group_data.get("status") == "success":
                        st.session_state.group_data = group_data
                        vectorstore, chunks = process_group_data(group_data)
                        if vectorstore:
                            st.session_state.chatbot = create_chatbot(vectorstore)
                            st.session_state.chat_history = []
                            st.success(f"✅ Successfully extracted {len(group_data['posts'])} posts!")
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📊 Status")
        
        if st.session_state.login_status == "not_started":
            st.info("🔐 Start manual login to begin")
        elif st.session_state.login_status == "in_progress":
            st.warning("🔄 Complete login in the browser")
        elif st.session_state.login_status == "completed":
            st.success("✅ Ready to extract group data")
            
            if st.session_state.group_data:
                group_info = st.session_state.group_data.get("group_info", {})
                posts = st.session_state.group_data.get("posts", [])
                
                st.subheader("🏷️ Group Info")
                if group_info.get("name"):
                    st.write(f"**Name:** {group_info['name']}")
                st.write(f"**Posts Extracted:** {len(posts)}")
    
    with col2:
        st.header("💬 Chat")
        
        if st.session_state.chatbot and st.session_state.group_data:
            for i, chat in enumerate(st.session_state.chat_history):
                with st.chat_message("user"):
                    st.write(chat["question"])
                with st.chat_message("assistant"):
                    st.write(chat["answer"])
            
            user_question = st.chat_input("Ask about the group...")
            if user_question:
                with st.chat_message("user"):
                    st.write(user_question)
                with st.chat_message("assistant"):
                    with st.spinner("🤔 Analyzing..."):
                        try:
                            response = st.session_state.chatbot.invoke({"question": user_question})
                            answer = response.get("answer", "No response generated.")
                            st.write(answer)
                            st.session_state.chat_history.append({
                                "question": user_question,
                                "answer": answer
                            })
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.info("📊 Extract group data first to start chatting")

if __name__ == "__main__":
    main()
