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
from langchain_community.llms.ollama import Ollama
import re
import requests
import subprocess
import os
import json
from datetime import datetime
from typing import List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FacebookGroupExtractor:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.is_logged_in = False
        
    def setup_driver(self):
        """Setup Chrome driver for manual login"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 25)
            return True
        except Exception as e:
            st.error(f"Failed to setup driver: {str(e)}")
            return False
    
    def manual_login(self):
        """Open Facebook for manual login"""
        try:
            st.info("🔓 Opening Facebook for manual login...")
            self.driver.get("https://www.facebook.com")
            time.sleep(3)
            
            # Handle cookies
            self._handle_cookies()
            
            st.success("✅ Facebook opened successfully!")
            st.info("""
            **Please manually login to Facebook:**
            1. Enter your email/phone and password
            2. Complete any security checks if needed
            3. Wait until you're fully logged in
            4. Return to this app and click 'I'm Logged In'
            """)
            
            return True
            
        except Exception as e:
            st.error(f"Failed to open Facebook: {str(e)}")
            return False
    
    def check_login_status(self):
        """Check if user is logged in"""
        try:
            # Check for login indicators
            login_indicators = [
                "//a[@aria-label='Profile']",
                "//div[@aria-label='Account']",
                "//span[contains(text(), 'Menu')]",
                "//div[contains(@aria-label, 'Facebook')]"
            ]
            
            for indicator in login_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element.is_displayed():
                        self.is_logged_in = True
                        return True
                except:
                    continue
            
            # Check URL for login success
            current_url = self.driver.current_url
            if "facebook.com/home" in current_url or "facebook.com/?sk" in current_url:
                self.is_logged_in = True
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Login check error: {str(e)}")
            return False
    
    def extract_group_data(self, group_url: str, max_scrolls: int = 10) -> dict:
        """Extract data from Facebook group after manual login"""
        try:
            if not self.is_logged_in:
                return {"error": "Not logged in. Please login first.", "status": "error"}
            
            st.info(f"🌐 Accessing group: {group_url}")
            
            # Clean the URL
            if '?' in group_url:
                group_url = group_url.split('?')[0]
            
            self.driver.get(group_url)
            time.sleep(5)
            
            # Check if we have access to the group
            if not self._verify_group_access():
                return {"error": "Cannot access group. Check if URL is correct and you have permissions.", "status": "error"}
            
            # Extract group info
            group_info = self._extract_group_info()
            
            # Scroll and extract posts
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
    
    def _handle_cookies(self):
        """Handle cookie consent"""
        try:
            cookie_selectors = [
                "button[data-testid='cookie-policy-manage-dialog-accept-button']",
                "button[data-cookiebanner='accept_button']",
                "button[title*='cookie' i]",
                "button[title*='allow' i]",
                "//button[contains(., 'Allow')]",
                "//button[contains(., 'Accept')]"
            ]
            
            for selector in cookie_selectors:
                try:
                    if selector.startswith("//"):
                        element = self.driver.find_element(By.XPATH, selector)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    element.click()
                    time.sleep(2)
                    break
                except:
                    continue
        except:
            pass
    
    def _verify_group_access(self) -> bool:
        """Verify we can access the group"""
        try:
            # Check for group-specific elements
            group_indicators = [
                "//div[contains(@data-pagelet, 'Group')]",
                "//div[contains(@aria-label, 'Group')]",
                "//h1[contains(., 'Group')]",
                "//div[@role='main']"
            ]
            
            for indicator in group_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element.is_displayed():
                        return True
                except:
                    continue
            
            # Check for access denied messages
            denied_indicators = [
                "//*[contains(text(), 'content isn't available')]",
                "//*[contains(text(), 'not available')]",
                "//*[contains(text(), 'access')]",
                "//*[contains(text(), 'permission')]"
            ]
            
            page_text = self.driver.page_source.lower()
            if any(indicator in page_text for indicator in ['not available', 'content unavailable', 'access denied']):
                return False
                
            return "groups" in self.driver.current_url
            
        except:
            return False
    
    def _extract_group_info(self) -> dict:
        """Extract group information"""
        group_info = {}
        try:
            # Get group name
            name_selectors = [
                "//h1",
                "//div[contains(@class, 'groupName')]",
                "//span[contains(@class, 'groupName')]",
                "//title"
            ]
            
            for selector in name_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    name = element.text.strip()
                    if name and len(name) > 3:
                        group_info["name"] = name
                        break
                except:
                    continue
            
            # Get member count
            member_selectors = [
                "//*[contains(text(), 'members')]",
                "//*[contains(text(), 'Members')]",
                "//div[contains(@class, 'memberCount')]"
            ]
            
            for selector in member_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    member_text = element.text
                    if 'members' in member_text.lower():
                        group_info["member_count"] = member_text
                        break
                except:
                    continue
            
            # Get group description
            desc_selectors = [
                "//div[contains(@class, 'description')]",
                "//div[contains(@class, 'about')]",
                "//div[contains(@data-ad-comet-preview, 'message')]"
            ]
            
            for selector in desc_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    desc = element.text.strip()
                    if desc:
                        group_info["description"] = desc
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Group info extraction failed: {str(e)}")
        
        return group_info
    
    def _scroll_and_extract_posts(self, max_scrolls: int) -> List[dict]:
        """Scroll and extract posts with multiple strategies"""
        all_posts = []
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for scroll_iteration in range(max_scrolls):
            st.info(f"📜 Scrolling... ({scroll_iteration + 1}/{max_scrolls})")
            
            # Extract posts from current view
            current_posts = self._extract_posts_from_current_page()
            
            # Add new posts
            for post in current_posts:
                if not self._is_duplicate_post(post, all_posts):
                    all_posts.append(post)
            
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(4)
            
            # Check if we've reached the end
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                st.success("✅ Reached end of content")
                break
            last_height = new_height
        
        return all_posts
    
    def _extract_posts_from_current_page(self) -> List[dict]:
        """Extract posts using multiple strategies"""
        posts = []
        
        # Strategy 1: Look for article elements (main posts)
        posts.extend(self._extract_by_xpath("//div[@role='article']", "article"))
        
        # Strategy 2: Look for story elements
        posts.extend(self._extract_by_xpath("//div[contains(@data-pagelet, 'Feed')]//div", "feed"))
        
        # Strategy 3: Look for user content
        posts.extend(self._extract_by_xpath("//div[contains(@class, 'userContent')]", "userContent"))
        
        # Strategy 4: Look for posts with substantial text
        posts.extend(self._extract_text_rich_elements())
        
        return posts
    
    def _extract_by_xpath(self, xpath: str, source: str) -> List[dict]:
        """Extract posts using XPath selector"""
        posts = []
        try:
            elements = self.driver.find_elements(By.XPATH, xpath)
            
            for i, element in enumerate(elements):
                try:
                    # Get the entire post text
                    post_text = element.text.strip()
                    
                    if self._is_valid_post(post_text):
                        # Try to get more structured data
                        post_data = self._parse_structured_post(element, post_text, source)
                        posts.append(post_data)
                        
                except Exception as e:
                    logger.debug(f"Error extracting element {i}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.warning(f"XPath {source} failed: {str(e)}")
        
        return posts
    
    def _extract_text_rich_elements(self) -> List[dict]:
        """Extract elements with substantial text content"""
        posts = []
        try:
            # Look for divs with substantial text
            elements = self.driver.find_elements(By.XPATH, "//div[string-length(text()) > 100]")
            
            for element in elements:
                try:
                    text = element.text.strip()
                    if self._is_valid_post(text):
                        posts.append({
                            "content": text,
                            "source": "text_rich",
                            "timestamp": datetime.now().isoformat(),
                            "has_comments": "comment" in text.lower()[:200]
                        })
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Text-rich extraction failed: {str(e)}")
        
        return posts
    
    def _parse_structured_post(self, element, text: str, source: str) -> dict:
        """Parse post with structured data"""
        post_data = {
            "content": text,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "has_comments": False,
            "reactions": 0
        }
        
        try:
            # Check for comments
            comment_indicators = [
                "//*[contains(text(), 'comment')]",
                "//*[contains(text(), 'Comment')]"
            ]
            
            for indicator in comment_indicators:
                try:
                    comments = element.find_elements(By.XPATH, indicator)
                    if comments:
                        post_data["has_comments"] = True
                        break
                except:
                    continue
            
            # Check for reactions
            reaction_indicators = [
                "//*[contains(text(), 'Like')]",
                "//*[contains(text(), 'Reaction')]"
            ]
            
            # Try to extract reaction count
            reaction_text = text.lower()
            if 'like' in reaction_text or 'reaction' in reaction_text:
                # Simple regex to find numbers near reaction words
                reaction_match = re.search(r'(\d+)\s*(like|reaction)', reaction_text)
                if reaction_match:
                    post_data["reactions"] = int(reaction_match.group(1))
                    
        except Exception as e:
            logger.debug(f"Structured parsing failed: {str(e)}")
        
        return post_data
    
    def _is_valid_post(self, text: str) -> bool:
        """Check if text is a valid post"""
        if not text or len(text) < 50:
            return False
        
        # Exclude navigation and UI text
        excluded_phrases = [
            'facebook', 'login', 'sign up', 'password', 'email',
            'cookie', 'privacy', 'terms', 'menu', 'navigation',
            'home', 'search', 'notification', 'messenger', 'watch',
            'marketplace', 'groups', 'pages', 'events'
        ]
        
        text_lower = text.lower()
        if any(phrase in text_lower for phrase in excluded_phrases):
            return False
        
        # Check for reasonable word count
        words = text.split()
        if len(words) < 8:
            return False
        
        return True
    
    def _is_duplicate_post(self, new_post: dict, existing_posts: List[dict]) -> bool:
        """Check if post is duplicate"""
        new_content = new_post.get("content", "")[:150]
        
        for existing_post in existing_posts:
            existing_content = existing_post.get("content", "")[:150]
            similarity = self._calculate_similarity(new_content, existing_content)
            if similarity > 0.8:  # 80% similarity
                return True
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

def check_ollama_running():
    """Check if Ollama is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    """Start Ollama service"""
    try:
        if os.name == 'nt':  # Windows
            subprocess.Popen(['ollama', 'serve'], creationflags=subprocess.CREATE_NO_WINDOW)
        else:  # Linux/Mac
            subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
        return check_ollama_running()
    except Exception as e:
        st.error(f"Failed to start Ollama: {e}")
        return False

def get_available_models():
    """Get list of available Ollama models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [model['name'] for model in models]
    except:
        return ["llama2", "mistral", "gemma", "llama3"]

def process_group_data(group_data: dict):
    """Process extracted group data for chatbot"""
    if not group_data or "posts" not in group_data or not group_data["posts"]:
        return None, []
    
    # Combine all posts into a single text
    all_text = f"Group: {group_data.get('group_info', {}).get('name', 'Unknown')}\n\n"
    all_text += f"Total Posts Extracted: {len(group_data['posts'])}\n\n"
    
    for i, post in enumerate(group_data["posts"]):
        content = post.get("content", "")
        source = post.get("source", "unknown")
        has_comments = post.get("has_comments", False)
        reactions = post.get("reactions", 0)
        
        all_text += f"--- Post {i+1} ---\n"
        all_text += f"Source: {source}\n"
        all_text += f"Reactions: {reactions}\n"
        all_text += f"Has Comments: {has_comments}\n"
        all_text += f"Content: {content}\n\n"
    
    # Split into chunks
    splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    
    chunks = splitter.split_text(all_text)
    documents = [Document(page_content=chunk) for chunk in chunks]
    
    # Create vector store
    embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(documents, embeddings)
    
    return vectorstore, chunks

def create_chatbot(vectorstore, model_name: str):
    """Create conversational chatbot"""
    try:
        llm = Ollama(
            model=model_name,
            base_url="http://localhost:11434",
            temperature=0.7,
            top_k=40,
            top_p=0.9,
            num_predict=512
        )
        
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            memory=memory,
            return_source_documents=True,
            output_key="answer"
        )
        
        return chain
    except Exception as e:
        st.error(f"Failed to create chatbot: {str(e)}")
        return None

def clear_chat_history():
    """Clear chat history and recreate chatbot with fresh memory"""
    if "vectorstore" in st.session_state and st.session_state.vectorstore:
        # Recreate chatbot with fresh memory
        model_name = st.session_state.get("current_model", "llama2")
        st.session_state.chatbot = create_chatbot(st.session_state.vectorstore, model_name)
        st.session_state.chat_history = []
        st.success("🔄 Chat history cleared! You can now ask questions with a fresh conversation.")
    else:
        st.error("❌ No extracted data found. Please extract group data first.")

def main():
    st.set_page_config(
        page_title="Facebook Group Analyzer with Manual Login",
        page_icon="📘",
        layout="wide"
    )
    
    st.title("📘 Facebook Group Data Extractor & Chatbot")
    st.markdown("Manual login required for private groups - Works with both public and private groups")
    
    # Initialize session state
    if "extractor" not in st.session_state:
        st.session_state.extractor = None
    if "login_status" not in st.session_state:
        st.session_state.login_status = "not_started"  # not_started, in_progress, completed, failed
    if "group_data" not in st.session_state:
        st.session_state.group_data = None
    if "vectorstore" not in st.session_state:
        st.session_state.vectorstore = None
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_model" not in st.session_state:
        st.session_state.current_model = "llama2"
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Ollama status
        st.subheader("🤖 Ollama Status")
        if check_ollama_running():
            st.success("✅ Ollama is running")
        else:
            st.error("❌ Ollama is not running")
            if st.button("🔄 Start Ollama"):
                if start_ollama():
                    st.success("✅ Ollama started successfully")
                    st.rerun()
                else:
                    st.error("❌ Failed to start Ollama")
        
        # Model selection
        available_models = get_available_models()
        model_name = st.selectbox(
            "Select AI Model",
            available_models,
            index=0 if available_models else 0,
            key="model_selector"
        )
        
        # Store current model
        st.session_state.current_model = model_name
        
        # Login section
        st.subheader("🔐 Facebook Login")
        
        if st.session_state.login_status == "not_started":
            if st.button("🚪 Start Manual Login", type="primary", use_container_width=True):
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
                    else:
                        st.error("❌ Login not detected. Please make sure you're logged in.")
            with col2:
                if st.button("❌ Cancel Login"):
                    if st.session_state.extractor:
                        st.session_state.extractor.close()
                    st.session_state.login_status = "not_started"
                    st.rerun()
        
        elif st.session_state.login_status == "completed":
            st.success("✅ Logged in to Facebook")
            if st.button("🚪 Logout & Restart"):
                if st.session_state.extractor:
                    st.session_state.extractor.close()
                st.session_state.login_status = "not_started"
                st.session_state.group_data = None
                st.session_state.vectorstore = None
                st.session_state.chatbot = None
                st.session_state.chat_history = []
                st.rerun()
        
        # Group extraction section
        st.subheader("📝 Group Information")
        group_url = st.text_input(
            "Facebook Group URL",
            placeholder="https://www.facebook.com/groups/groupname/",
            help="Works with both public and private groups"
        )
        
        # Extraction settings
        st.subheader("⚙️ Extraction Settings")
        max_scrolls = st.slider("Number of scrolls", 5, 20, 10)
        
        if st.button("🚀 Extract Group Data", type="primary", use_container_width=True):
            if st.session_state.login_status != "completed":
                st.error("❌ Please login to Facebook first")
            elif not group_url or "facebook.com/groups/" not in group_url:
                st.error("❌ Please enter a valid Facebook group URL")
            elif not check_ollama_running():
                st.error("❌ Ollama is not running")
            else:
                with st.spinner("🌐 Extracting group data... This may take a few minutes."):
                    group_data = st.session_state.extractor.extract_group_data(group_url, max_scrolls)
                    
                    if group_data.get("status") == "success" and group_data.get("posts"):
                        st.session_state.group_data = group_data
                        
                        # Process for chatbot
                        vectorstore, chunks = process_group_data(group_data)
                        if vectorstore:
                            st.session_state.vectorstore = vectorstore
                            st.session_state.chatbot = create_chatbot(vectorstore, model_name)
                            st.session_state.chat_history = []
                            st.success(f"✅ Successfully extracted {len(group_data['posts'])} posts!")
                        else:
                            st.error("❌ Failed to process group data")
                    else:
                        error_msg = group_data.get("error", "Unknown error")
                        st.error(f"❌ Extraction failed: {error_msg}")
        
        # Chat management section
        if st.session_state.chatbot and st.session_state.group_data:
            st.subheader("💬 Chat Management")
            if st.button("🗑️ Clear Chat History", type="secondary", use_container_width=True):
                clear_chat_history()
                st.rerun()
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📊 Login & Extraction Status")
        
        if st.session_state.login_status == "not_started":
            st.info("""
            ## 🔐 Manual Login Required
            
            **How it works:**
            1. Click 'Start Manual Login' in the sidebar
            2. A browser window will open with Facebook
            3. **Manually login** to your Facebook account
            4. Complete any security checks if needed
            5. Return here and click 'I'm Logged In'
            
            **Benefits:**
            - Works with both public and private groups
            - No need to enter password in this app
            - Handles 2FA and security checks
            - More reliable than automated login
            """)
            
        elif st.session_state.login_status == "in_progress":
            st.warning("""
            ## 🔄 Login in Progress
            
            **Please complete these steps:**
            1. ✅ Browser window should be open with Facebook
            2. 🔄 **Manually login** to your Facebook account
            3. ✅ Wait until you see your Facebook home page
            4. 🔄 Return here and click **'I'm Logged In'**
            
            **Troubleshooting:**
            - If browser didn't open, check popup blockers
            - Make sure you're fully logged into Facebook
            - If you see security checks, complete them first
            """)
            
        elif st.session_state.login_status == "completed":
            st.success("""
            ## ✅ Login Successful!
            
            You can now:
            1. Enter a Facebook group URL in the sidebar
            2. Adjust extraction settings
            3. Click 'Extract Group Data'
            4. Chat with the extracted content
            """)
            
            if st.session_state.group_data:
                group_info = st.session_state.group_data.get("group_info", {})
                posts = st.session_state.group_data.get("posts", [])
                
                st.subheader("🏷️ Group Information")
                if group_info:
                    for key, value in group_info.items():
                        if value:
                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                
                st.subheader(f"📝 Posts Extracted: {len(posts)}")
                
                for i, post in enumerate(posts[:3]):
                    with st.expander(f"Post {i+1}"):
                        content = post.get("content", "")
                        st.text_area(f"Content {i+1}", content, height=150, key=f"post_{i}")
                        st.caption(f"Source: {post.get('source', 'unknown')} | Reactions: {post.get('reactions', 0)}")
    
    with col2:
        st.header("💬 Chat with Group Data")
        
        # Chat management button at the top
        if st.session_state.chatbot and st.session_state.group_data:
            col_clear, col_info = st.columns([1, 3])
            with col_clear:
                if st.button("🗑️ Clear History", key="clear_top"):
                    clear_chat_history()
                    st.rerun()
            with col_info:
                st.caption("Clear conversation history while keeping extracted data")
        
        if st.session_state.chatbot and st.session_state.group_data:
            # Display chat history
            for i, chat in enumerate(st.session_state.chat_history):
                with st.chat_message("user"):
                    st.write(chat["question"])
                with st.chat_message("assistant"):
                    st.write(chat["answer"])
            
            # Chat input
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
                            
                            st.session_state.chat_history.append({
                                "question": user_question,
                                "answer": answer
                            })
                            
                        except Exception as e:
                            error_msg = f"Error: {str(e)}"
                            st.error(error_msg)
            
            if not st.session_state.chat_history:
                st.subheader("💡 Suggested Questions")
                suggestions = [
                    "What are the main topics discussed in this group?",
                    "Summarize the most active discussions",
                    "What kind of content gets the most engagement?",
                    "Are there any common questions or problems?",
                    "What's the overall tone of the group?"
                ]
                
                for suggestion in suggestions:
                    if st.button(suggestion, key=suggestion):
                        st.info(f"Type: '{suggestion}' in the chat input above")
                        
        elif st.session_state.login_status == "completed":
            st.info("📊 Extract group data first to start chatting")
        else:
            st.info("🔐 Login to Facebook to get started")

if __name__ == "__main__":
    main()