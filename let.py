import streamlit as st
import time
from bs4 import BeautifulSoup
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import SentenceTransformerEmbeddings
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
from langchain.llms import HuggingFaceHub
import re
import requests
import subprocess
import os
import json
from datetime import datetime
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_hf_key():
    try:
        return st.secrets["huggingface"]["api_key"]
    except Exception:
        return os.environ.get("HUGGINGFACE_API_KEY")

def check_hf_key():
    return bool(get_hf_key())

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
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--window-size=1200,800")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                logger.warning(f"webdriver_manager failed: {e}. Trying system chrome.")
                self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 25)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
        except Exception as e:
            logger.error(f"setup_driver error: {e}")
            return False

    def manual_login(self):
        try:
            self.driver.get("https://www.facebook.com")
            time.sleep(3)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._handle_cookies()
            return True
        except Exception as e:
            logger.error(f"manual_login error: {e}")
            return False

    def check_login_status(self):
        try:
            current_url = self.driver.current_url.lower()
            login_success_urls = ["facebook.com/home", "facebook.com/?sk", "facebook.com/groups", "facebook.com/marketplace"]
            if any(url in current_url for url in login_success_urls):
                self.is_logged_in = True
                return True
            page_source = self.driver.page_source.lower()
            if any(word in page_source for word in ['news feed', 'notification', 'messenger', 'profile']):
                self.is_logged_in = True
                return True
            return False
        except Exception as e:
            logger.error(f"check_login_status error: {e}")
            return False

    def extract_group_data(self, group_url: str, max_scrolls: int = 10) -> dict:
        try:
            if not self.is_logged_in:
                return {"error": "Not logged in. Please login first.", "status": "error"}
            group_url = self._clean_group_url(group_url)
            if not group_url:
                return {"error": "Invalid group URL", "status": "error"}
            self.driver.get(group_url)
            time.sleep(5)
            access_result = self._verify_group_access()
            if not access_result["success"]:
                return {"error": access_result["message"], "status": "error"}
            group_info = self._extract_group_info()
            posts_data = self._scroll_and_extract_posts(max_scrolls)
            return {"group_info": group_info, "posts": posts_data, "extraction_time": datetime.now().isoformat(), "total_posts": len(posts_data), "status": "success"}
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return {"error": f"Extraction failed: {str(e)}", "status": "error"}

    def _clean_group_url(self, url: str) -> str:
        if not url or "facebook.com/groups/" not in url:
            return ""
        url = url.split('?')[0].split('#')[0]
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url

    def _handle_cookies(self):
        try:
            time.sleep(2)
            cookie_selectors = [
                "button[data-testid='cookie-policy-manage-dialog-accept-button']",
                "button[data-cookiebanner='accept_button']",
                "//button[contains(., 'Accept')]",
                "//button[contains(., 'Allow')]",
            ]
            for selector in cookie_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            time.sleep(1)
                            return
                except:
                    continue
        except Exception as e:
            logger.debug(f"Cookie handling failed: {e}")

    def _verify_group_access(self) -> dict:
        try:
            current_url = self.driver.current_url.lower()
            if "login" in current_url or "log in" in self.driver.page_source.lower():
                return {"success": False, "message": "Login required or session expired"}
            group_indicators = ["//div[contains(@data-pagelet, 'Group')]", "//div[contains(@aria-label, 'Group')]", "//h1"]
            for indicator in group_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    if elements:
                        return {"success": True, "message": "Group access verified"}
                except:
                    continue
            page_text = self.driver.page_source.lower()
            denied_indicators = ["content isn't available", "you must be a member", "you don't have permission"]
            for indicator in denied_indicators:
                if indicator in page_text:
                    return {"success": False, "message": f"Access denied: {indicator}"}
            if "groups" in current_url:
                return {"success": True, "message": "URL indicates group access"}
            return {"success": False, "message": "Cannot verify group access"}
        except Exception as e:
            return {"success": False, "message": f"Access verification error: {str(e)}"}

    def _extract_group_info(self) -> dict:
        group_info = {}
        try:
            name_selectors = ["//h1", "//h2", "//div[@role='heading']", "//title"]
            for selector in name_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        name = element.text.strip()
                        if name and 3 < len(name) < 100:
                            group_info["name"] = name
                            break
                    if "name" in group_info:
                        break
                except:
                    continue
            member_selectors = ["//*[contains(text(), 'members')]", "//*[contains(text(), 'Members')]", "//div[contains(@class, 'memberCount')]"]
            for selector in member_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        txt = element.text
                        if any(word in txt.lower() for word in ['member', 'people', 'follow']):
                            group_info["member_count"] = txt
                            break
                    if "member_count" in group_info:
                        break
                except:
                    continue
            desc_selectors = ["//div[contains(@class, 'description')]", "//div[contains(@class, 'about')]"]
            for selector in desc_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        desc = element.text.strip()
                        if desc and len(desc) > 10:
                            group_info["description"] = desc
                            break
                    if "description" in group_info:
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Group info extraction failed: {e}")
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
            ("//div[contains(@class, 'userContent')]", "userContent"),
        ]
        for xpath, source in strategies:
            posts.extend(self._extract_by_xpath(xpath, source))
        if len(posts) < 3:
            posts.extend(self._extract_text_rich_elements())
        return posts

    def _extract_by_xpath(self, xpath: str, source: str) -> List[dict]:
        posts = []
        try:
            elements = self.driver.find_elements(By.XPATH, xpath)
            for element in elements:
                try:
                    post_text = element.text.strip()
                    if self._is_valid_post(post_text):
                        post_data = self._parse_structured_post(element, post_text, source)
                        posts.append(post_data)
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"XPath extraction failed: {e}")
        return posts

    def _extract_text_rich_elements(self) -> List[dict]:
        posts = []
        try:
            elements = self.driver.find_elements(By.XPATH, "//div[string-length(text()) > 50]")
            for element in elements:
                try:
                    text = element.text.strip()
                    if self._is_valid_post(text):
                        posts.append({"content": text, "source": "text_rich", "timestamp": datetime.now().isoformat(), "has_comments": "comment" in text.lower()[:200]})
                except:
                    continue
        except Exception as e:
            logger.debug(f"Text-rich extraction failed: {e}")
        return posts

    def _parse_structured_post(self, element, text: str, source: str) -> dict:
        post_data = {"content": text, "source": source, "timestamp": datetime.now().isoformat(), "has_comments": False, "reactions": 0}
        try:
            text_lower = text.lower()
            if any(word in text_lower for word in ['comment', 'reply', 'response']):
                post_data["has_comments"] = True
            reaction_match = re.search(r'(\d+)\s*(like|reaction|love|wow|haha|sad|angry)', text_lower)
            if reaction_match:
                post_data["reactions"] = int(reaction_match.group(1))
            elif 'like' in text_lower:
                post_data["reactions"] = 1
        except Exception:
            pass
        return post_data

    def _is_valid_post(self, text: str) -> bool:
        if not text or len(text) < 30:
            return False
        excluded_phrases = ['facebook', 'login', 'sign up', 'password', 'email', 'cookie', 'privacy', 'terms', 'menu', 'notification', 'messenger']
        text_lower = text.lower()
        if any(phrase in text_lower for phrase in excluded_phrases):
            return False
        words = text.split()
        if len(words) < 5:
            return False
        return True

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
    all_text += f"Description: {group_data.get('group_info', {}).get('description', 'No description')}\n\n"
    all_text += f"Member Count: {group_data.get('group_info', {}).get('member_count', 'Unknown')}\n\n"
    all_text += f"Total Posts Extracted: {len(group_data['posts'])}\n\n"
    all_text += f"Extraction Time: {group_data.get('extraction_time', 'Unknown')}\n\n"
    for i, post in enumerate(group_data["posts"]):
        content = post.get("content", "")
        source = post.get("source", "unknown")
        has_comments = post.get("has_comments", False)
        reactions = post.get("reactions", 0)
        timestamp = post.get("timestamp", "")
        all_text += f"--- Post {i+1} ---\nSource: {source}\nReactions: {reactions}\nHas Comments: {has_comments}\nTimestamp: {timestamp}\nContent: {content}\n\n"
    splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len)
    chunks = splitter.split_text(all_text)
    documents = [Document(page_content=chunk) for chunk in chunks]
    try:
        embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(documents, embeddings)
        return vectorstore, chunks
    except Exception as e:
        st.error(f"Vector store creation failed: {e}")
        return None, []

def create_chatbot(vectorstore, model_name: str = "meta-llama/Llama-2-7b-chat-hf"):
    if vectorstore is None:
        return None
    hf_key = get_hf_key()
    if not hf_key:
        st.error("Hugging Face API key not configured.")
        return None
    llm = HuggingFaceHub(repo_id=model_name, huggingfacehub_api_token=hf_key, model_kwargs={"temperature":0.7, "max_new_tokens":512, "top_p":0.9})
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")
    chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=vectorstore.as_retriever(search_kwargs={"k": 3}), memory=memory, return_source_documents=True, output_key="answer")
    return chain

def clear_chat_history():
    if "vectorstore" in st.session_state and st.session_state.vectorstore:
        model_name = st.session_state.get("current_model", "meta-llama/Llama-2-7b-chat-hf")
        st.session_state.chatbot = create_chatbot(st.session_state.vectorstore, model_name)
        st.session_state.chat_history = []
        st.success("🔄 Chat history cleared!")
    else:
        st.error("❌ No extracted data found. Please extract group data first.")

def main():
    st.set_page_config(page_title="Facebook Group Analyzer with Manual Login", page_icon="📘", layout="wide")
    st.title("📘 Facebook Group Data Extractor & Chatbot (Hugging Face)")
    if "extractor" not in st.session_state: st.session_state.extractor = None
    if "login_status" not in st.session_state: st.session_state.login_status = "not_started"
    if "group_data" not in st.session_state: st.session_state.group_data = None
    if "vectorstore" not in st.session_state: st.session_state.vectorstore = None
    if "chatbot" not in st.session_state: st.session_state.chatbot = None
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "current_model" not in st.session_state: st.session_state.current_model = "meta-llama/Llama-2-7b-chat-hf"

    with st.sidebar:
        st.header("🔧 Configuration")
        st.subheader("🤖 Hugging Face Status")
        if check_hf_key():
            st.success("✅ Hugging Face key found")
            available_models = [
                "meta-llama/Llama-2-7b-chat-hf",
                "HuggingFaceH4/zephyr-7b-beta",
                "mistralai/Mistral-7B-Instruct-v0.2"
            ]
            model_name = st.selectbox("Select AI Model", available_models, index=0, key="model_selector")
            st.session_state.current_model = model_name
        else:
            st.error("❌ Hugging Face key not found")
            if st.button("Show instructions to add key"):
                st.info("Add `HUGGINGFACE_API_KEY` env var or add `[huggingface] api_key = \"hf_...\"` in Streamlit secrets.")

        st.subheader("🔐 Facebook Login")
        if st.session_state.login_status == "not_started":
            if st.button("🚪 Start Manual Login", type="primary", use_container_width=True):
                extractor = FacebookGroupExtractor()
                if extractor.setup_driver():
                    st.session_state.extractor = extractor
                    if extractor.manual_login():
                        st.session_state.login_status = "in_progress"
                        st.experimental_rerun()
                    else:
                        st.error("Failed to open Facebook")
                else:
                    st.error("Failed to setup browser")
        elif st.session_state.login_status == "in_progress":
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ I'm Logged In", type="primary", use_container_width=True):
                    if st.session_state.extractor and st.session_state.extractor.check_login_status():
                        st.session_state.login_status = "completed"
                        st.success("✅ Login successful!")
                        st.experimental_rerun()
                    else:
                        st.error("❌ Login not detected.")
            with col2:
                if st.button("❌ Cancel Login", type="secondary", use_container_width=True):
                    if st.session_state.extractor:
                        st.session_state.extractor.close()
                    st.session_state.login_status = "not_started"
                    st.experimental_rerun()
        elif st.session_state.login_status == "completed":
            st.success("✅ Logged in to Facebook")
            if st.button("🚪 Logout & Restart", type="secondary", use_container_width=True):
                if st.session_state.extractor:
                    st.session_state.extractor.close()
                st.session_state.login_status = "not_started"
                st.session_state.group_data = None
                st.session_state.vectorstore = None
                st.session_state.chatbot = None
                st.session_state.chat_history = []
                st.experimental_rerun()

        st.subheader("📝 Group Information")
        group_url = st.text_input("Facebook Group URL", placeholder="https://www.facebook.com/groups/groupname/")
        max_scrolls = st.slider("Number of scrolls", 5, 20, 10)

        if st.button("🚀 Extract Group Data", type="primary", use_container_width=True):
            if st.session_state.login_status != "completed":
                st.error("❌ Please login to Facebook first")
            elif not group_url or "facebook.com/groups/" not in group_url:
                st.error("❌ Please enter a valid Facebook group URL")
            elif not check_hf_key():
                st.error("❌ Hugging Face API key not set")
            else:
                with st.spinner("🌐 Extracting group data..."):
                    group_data = st.session_state.extractor.extract_group_data(group_url, max_scrolls)
                    if group_data.get("status") == "success" and group_data.get("posts"):
                        st.session_state.group_data = group_data
                        vectorstore, chunks = process_group_data(group_data)
                        if vectorstore:
                            st.session_state.vectorstore = vectorstore
                            st.session_state.chatbot = create_chatbot(vectorstore, st.session_state.current_model)
                            st.session_state.chat_history = []
                            st.success(f"✅ Successfully extracted {len(group_data['posts'])} posts!")
                        else:
                            st.error("❌ Failed to process group data")
                    else:
                        error_msg = group_data.get("error", "Unknown error")
                        st.error(f"❌ Extraction failed: {error_msg}")

        if st.session_state.chatbot and st.session_state.group_data:
            st.subheader("💬 Chat Management")
            if st.button("🗑️ Clear Chat History", type="secondary", use_container_width=True):
                clear_chat_history()
                st.experimental_rerun()

    # Main area
    col1, col2 = st.columns([1, 1])
    with col1:
        st.header("📊 Login & Extraction Status")
        if st.session_state.login_status == "not_started":
            st.info("Click 'Start Manual Login' in the sidebar to begin.")
        elif st.session_state.login_status == "in_progress":
            st.warning("Complete manual login in the opened browser and then click 'I'm Logged In'.")
        elif st.session_state.login_status == "completed":
            st.success("✅ Login Successful!")
            if st.session_state.group_data:
                group_info = st.session_state.group_data.get("group_info", {})
                for key, value in group_info.items():
                    if value:
                        st.write(f"**{key.replace('_',' ').title()}:** {value}")
                posts = st.session_state.group_data.get("posts", [])
                st.subheader(f"📝 Posts Extracted: {len(posts)}")
                for i, post in enumerate(posts[:3]):
                    with st.expander(f"Post {i+1} Sample", expanded=i==0):
                        content = post.get("content", "")
                        if len(content) > 500:
                            content = content[:500] + "..."
                        st.text_area(f"Content {i+1}", content, height=150, key=f"post_{i}")

    with col2:
        st.header("💬 Chat with Group Data")
        if st.session_state.chatbot and st.session_state.group_data:
            for i, chat in enumerate(st.session_state.chat_history):
                with st.chat_message("user"):
                    st.write(chat["question"])
                with st.chat_message("assistant"):
                    st.write(chat["answer"])
            user_question = st.chat_input("Ask about the group content...")
            if user_question:
                with st.chat_message("user"):
                    st.write(user_question)
                with st.chat_message("assistant"):
                    with st.spinner("🤔 Analyzing..."):
                        try:
                            response = st.session_state.chatbot.invoke({"question": user_question})
                            answer = response.get("answer", "I couldn't generate a response.")
                            st.write(answer)
                            st.session_state.chat_history.append({"question": user_question, "answer": answer})
                        except Exception as e:
                            st.error(f"Error: {e}")
            if not st.session_state.chat_history:
                st.subheader("💡 Suggested Questions")
                suggestions = [
                    "What are the main topics discussed in this group?",
                    "Summarize the most active discussions",
                    "What kind of content gets the most engagement?"
                ]
                for suggestion in suggestions:
                    if st.button(suggestion, key=suggestion):
                        st.info(f"Type: '{suggestion}' in the chat input above")
        elif st.session_state.login_status == "completed":
            st.info("Extract group data first to start chatting")
        else:
            st.info("Login to Facebook to get started")

if __name__ == "__main__":
    main()
