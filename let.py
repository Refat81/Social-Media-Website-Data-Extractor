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
from langchain_community.llms.ollama import Ollama
import re
import requests
import subprocess
import os
import json
from datetime import datetime
from typing import List
import logging
import sys

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
        try:
            chrome_options = Options()
            
            # Essential options for stability
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # UI options for better visibility
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--window-size=1200,800")
            
            # Disable extensions and popups
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-popup-blocking")
            
            # Bypass automation detection
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User agent to mimic real browser
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            st.info("🔄 Setting up Chrome browser...")
            
            # Use webdriver_manager to handle driver automatically
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                st.warning(f"Webdriver manager failed, trying direct Chrome: {e}")
                # Fallback to system Chrome
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 25)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            st.success("✅ Chrome browser setup completed!")
            return True
            
        except Exception as e:
            st.error(f"❌ Failed to setup Chrome driver: {str(e)}")
            st.info("💡 Make sure Chrome is installed on your system.")
            return False
    
    def manual_login(self):
        """Open Facebook for manual login"""
        try:
            st.info("🔓 Opening Facebook for manual login...")
            
            # Open Facebook
            self.driver.get("https://www.facebook.com")
            time.sleep(3)
            
            # Wait for page to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Handle cookies with better detection
            self._handle_cookies()
            
            st.success("✅ Facebook opened successfully!")
            st.info("""
            **📝 Manual Login Instructions:**
            
            1. **Browser Window**: A Chrome window should now be open with Facebook
            2. **Login Steps**:
               - Enter your email/phone in the login form
               - Enter your password
               - Complete any security checks (2FA if enabled)
            3. **Verification**: Wait until you see your Facebook news feed
            4. **Return to App**: Come back here and click '✅ I'm Logged In'
            
            **🛠️ Troubleshooting:**
            - If no browser opens, check popup blockers
            - If login fails, try again or check credentials
            - For security checks, complete them in the browser
            """)
            
            return True
            
        except Exception as e:
            st.error(f"❌ Failed to open Facebook: {str(e)}")
            return False
    
    def check_login_status(self):
        """Check if user is logged in with multiple verification methods"""
        try:
            # Check current URL first
            current_url = self.driver.current_url.lower()
            
            # URLs that indicate successful login
            login_success_urls = [
                "facebook.com/home",
                "facebook.com/?sk",
                "facebook.com/groups",
                "facebook.com/marketplace",
                "facebook.com/watch"
            ]
            
            if any(url in current_url for url in login_success_urls):
                self.is_logged_in = True
                return True
            
            # Check for login indicators in page elements
            login_indicators = [
                "//a[@aria-label='Profile' or contains(@href, '/me/')]",
                "//div[@aria-label='Account']",
                "//span[contains(text(), 'Menu')]",
                "//div[contains(@aria-label, 'Facebook')]",
                "//a[contains(@href, 'logout')]",
                "//div[contains(text(), 'Welcome')]"
            ]
            
            for indicator in login_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    for element in elements:
                        if element.is_displayed():
                            self.is_logged_in = True
                            return True
                except:
                    continue
            
            # Check for login form (indicating NOT logged in)
            try:
                login_form = self.driver.find_elements(By.ID, "loginform")
                if login_form:
                    return False
            except:
                pass
            
            # Final check - look for any personalized content
            page_source = self.driver.page_source.lower()
            if any(word in page_source for word in ['news feed', 'notification', 'messenger', 'profile']):
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
            
            # Clean and validate URL
            group_url = self._clean_group_url(group_url)
            if not group_url:
                return {"error": "Invalid group URL", "status": "error"}
            
            # Navigate to group
            self.driver.get(group_url)
            time.sleep(5)
            
            # Wait for group page to load
            try:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except:
                pass
            
            # Check if we have access to the group
            access_result = self._verify_group_access()
            if not access_result["success"]:
                return {"error": access_result["message"], "status": "error"}
            
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
    
    def _clean_group_url(self, url: str) -> str:
        """Clean and validate group URL"""
        if not url or "facebook.com/groups/" not in url:
            return ""
        
        # Remove query parameters and fragments
        url = url.split('?')[0].split('#')[0]
        
        # Ensure it's a proper URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        return url
    
    def _handle_cookies(self):
        """Handle cookie consent with improved detection"""
        try:
            # Wait a moment for cookie dialog to appear
            time.sleep(2)
            
            cookie_selectors = [
                "button[data-testid='cookie-policy-manage-dialog-accept-button']",
                "button[data-cookiebanner='accept_button']",
                "button[title*='cookie' i]",
                "button[title*='allow' i]",
                "//button[contains(., 'Allow')]",
                "//button[contains(., 'Accept')]",
                "//button[contains(., 'Allow all cookies')]",
                "//button[contains(., 'Accept All')]"
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
                            time.sleep(2)
                            logger.info("✅ Cookie consent handled")
                            return
                except:
                    continue
        except Exception as e:
            logger.debug(f"Cookie handling failed: {str(e)}")
    
    def _verify_group_access(self) -> dict:
        """Verify we can access the group with detailed feedback"""
        try:
            current_url = self.driver.current_url.lower()
            
            # Check if we're still on login page or redirected
            if "login" in current_url or "log in" in self.driver.page_source.lower():
                return {"success": False, "message": "Login required or session expired"}
            
            # Check for group-specific elements
            group_indicators = [
                "//div[contains(@data-pagelet, 'Group')]",
                "//div[contains(@aria-label, 'Group')]",
                "//h1[contains(., 'Group')]",
                "//div[@role='main']//article",
                "//div[contains(@class, 'group')]"
            ]
            
            for indicator in group_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    if elements:
                        return {"success": True, "message": "Group access verified"}
                except:
                    continue
            
            # Check for access denied messages
            page_text = self.driver.page_source.lower()
            denied_indicators = [
                "content isn't available",
                "not available",
                "access denied",
                "you must be a member",
                "this content isn't available",
                "you don't have permission"
            ]
            
            for indicator in denied_indicators:
                if indicator in page_text:
                    return {"success": False, "message": f"Access denied: {indicator}"}
            
            # Final URL check
            if "groups" in current_url and "view=groups" not in current_url:
                return {"success": True, "message": "URL indicates group access"}
                
            return {"success": False, "message": "Cannot verify group access"}
            
        except Exception as e:
            return {"success": False, "message": f"Access verification error: {str(e)}"}
    
    def _extract_group_info(self) -> dict:
        """Extract group information with improved selectors"""
        group_info = {}
        try:
            # Get group name with multiple selectors
            name_selectors = [
                "//h1",
                "//h2",
                "//h3",
                "//div[@role='heading']",
                "//title",
                "//span[contains(@class, 'groupName')]",
                "//div[contains(@class, 'groupName')]"
            ]
            
            for selector in name_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        name = element.text.strip()
                        if name and len(name) > 3 and len(name) < 100:
                            group_info["name"] = name
                            break
                    if "name" in group_info:
                        break
                except:
                    continue
            
            # Get member count
            member_selectors = [
                "//*[contains(text(), 'members')]",
                "//*[contains(text(), 'Members')]",
                "//*[contains(text(), 'people')]",
                "//div[contains(@class, 'memberCount')]"
            ]
            
            for selector in member_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        member_text = element.text
                        if any(word in member_text.lower() for word in ['member', 'people', 'follow']):
                            group_info["member_count"] = member_text
                            break
                    if "member_count" in group_info:
                        break
                except:
                    continue
            
            # Get group description
            desc_selectors = [
                "//div[contains(@class, 'description')]",
                "//div[contains(@class, 'about')]",
                "//div[contains(@data-ad-comet-preview, 'message')]",
                "//div[contains(@class, 'groupDescription')]"
            ]
            
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
            logger.warning(f"Group info extraction failed: {str(e)}")
        
        return group_info
    
    def _scroll_and_extract_posts(self, max_scrolls: int) -> List[dict]:
        """Scroll and extract posts with multiple strategies"""
        all_posts = []
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        
        st.info(f"📜 Starting to scroll and extract posts...")
        
        for scroll_iteration in range(max_scrolls):
            scroll_attempts += 1
            
            # Extract posts from current view
            current_posts = self._extract_posts_from_current_page()
            new_posts_count = 0
            
            # Add new posts
            for post in current_posts:
                if not self._is_duplicate_post(post, all_posts):
                    all_posts.append(post)
                    new_posts_count += 1
            
            progress_text = f"📜 Scroll {scroll_iteration + 1}/{max_scrolls} - Found {new_posts_count} new posts (Total: {len(all_posts)})"
            st.info(progress_text)
            
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Reduced wait time
            
            # Check if we've reached the end
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                st.success("✅ Reached end of content")
                break
            last_height = new_height
            
            # Small progress indicator
            if scroll_iteration % 2 == 0:
                st.write(f"🔄 Progress: {scroll_iteration + 1}/{max_scrolls} scrolls completed")
        
        st.success(f"✅ Extraction completed! Found {len(all_posts)} total posts.")
        return all_posts
    
    def _extract_posts_from_current_page(self) -> List[dict]:
        """Extract posts using multiple strategies"""
        posts = []
        
        # Multiple extraction strategies
        strategies = [
            ("//div[@role='article']", "article"),
            ("//div[contains(@data-pagelet, 'Feed')]//div", "feed"),
            ("//div[contains(@class, 'userContent')]", "userContent"),
            ("//div[contains(@class, 'story')]", "story"),
            ("//div[contains(@data-ad-preview, 'message')]", "preview")
        ]
        
        for xpath, source in strategies:
            posts.extend(self._extract_by_xpath(xpath, source))
        
        # Fallback: text-rich elements
        if len(posts) < 3:
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
            logger.debug(f"XPath {source} failed: {str(e)}")
        
        return posts
    
    def _extract_text_rich_elements(self) -> List[dict]:
        """Extract elements with substantial text content"""
        posts = []
        try:
            # Look for divs with substantial text
            elements = self.driver.find_elements(By.XPATH, "//div[string-length(text()) > 50]")
            
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
            logger.debug(f"Text-rich extraction failed: {str(e)}")
        
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
            # Check for comments in the text
            text_lower = text.lower()
            if any(word in text_lower for word in ['comment', 'reply', 'response']):
                post_data["has_comments"] = True
            
            # Try to extract reaction count
            reaction_match = re.search(r'(\d+)\s*(like|reaction|love|wow|haha|sad|angry)', text_lower)
            if reaction_match:
                post_data["reactions"] = int(reaction_match.group(1))
            elif 'like' in text_lower:
                post_data["reactions"] = 1  # Default to 1 if likes mentioned but no count
                    
        except Exception as e:
            logger.debug(f"Structured parsing failed: {str(e)}")
        
        return post_data
    
    def _is_valid_post(self, text: str) -> bool:
        """Check if text is a valid post"""
        if not text or len(text) < 30:  # Reduced minimum length
            return False
        
        # Exclude navigation and UI text
        excluded_phrases = [
            'facebook', 'login', 'sign up', 'password', 'email',
            'cookie', 'privacy', 'terms', 'menu', 'navigation',
            'home', 'search', 'notification', 'messenger', 'watch',
            'marketplace', 'groups', 'pages', 'events', 'create post'
        ]
        
        text_lower = text.lower()
        if any(phrase in text_lower for phrase in excluded_phrases):
            return False
        
        # Check for reasonable word count
        words = text.split()
        if len(words) < 5:  # Reduced minimum words
            return False
        
        return True
    
    def _is_duplicate_post(self, new_post: dict, existing_posts: List[dict]) -> bool:
        """Check if post is duplicate using content similarity"""
        new_content = new_post.get("content", "")[:100]  # First 100 chars for comparison
        
        for existing_post in existing_posts:
            existing_content = existing_post.get("content", "")[:100]
            similarity = self._calculate_similarity(new_content, existing_content)
            if similarity > 0.7:  # 70% similarity threshold
                return True
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
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
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

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
        st.info("🔄 Starting Ollama service...")
        
        if os.name == 'nt':  # Windows
            subprocess.Popen(['ollama', 'serve'], creationflags=subprocess.CREATE_NO_WINDOW)
        else:  # Linux/Mac
            subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait longer for Ollama to start
        time.sleep(8)
        return check_ollama_running()
    except Exception as e:
        st.error(f"Failed to start Ollama: {e}")
        return False

def get_available_models():
    """Get list of available Ollama models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [model['name'] for model in models]
    except:
        pass
    
    # Default fallback models
    return ["llama2", "mistral", "gemma", "llama3", "codellama"]

def process_group_data(group_data: dict):
    """Process extracted group data for chatbot"""
    if not group_data or "posts" not in group_data or not group_data["posts"]:
        return None, []
    
    # Combine all posts into a single text
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
        
        all_text += f"--- Post {i+1} ---\n"
        all_text += f"Source: {source}\n"
        all_text += f"Reactions: {reactions}\n"
        all_text += f"Has Comments: {has_comments}\n"
        all_text += f"Timestamp: {timestamp}\n"
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
    try:
        embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(documents, embeddings)
        return vectorstore, chunks
    except Exception as e:
        st.error(f"Vector store creation failed: {e}")
        return None, []

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
        st.session_state.login_status = "not_started"
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
            
            # Model selection
            available_models = get_available_models()
            if available_models:
                model_name = st.selectbox(
                    "Select AI Model",
                    available_models,
                    index=0,
                    key="model_selector"
                )
                st.session_state.current_model = model_name
            else:
                st.warning("No models found. Please install models in Ollama.")
        else:
            st.error("❌ Ollama is not running")
            if st.button("🔄 Start Ollama"):
                if start_ollama():
                    st.success("✅ Ollama started successfully")
                    st.rerun()
                else:
                    st.error("❌ Failed to start Ollama")
        
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
                        else:
                            st.error("Failed to open Facebook")
                    else:
                        st.error("Failed to setup browser")
        
        elif st.session_state.login_status == "in_progress":
            st.info("🔄 Login in progress...")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ I'm Logged In", type="primary", use_container_width=True):
                    if st.session_state.extractor and st.session_state.extractor.check_login_status():
                        st.session_state.login_status = "completed"
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Login not detected. Please make sure you're logged in and try again.")
            with col2:
                if st.button("❌ Cancel Login", type="secondary", use_container_width=True):
                    if st.session_state.extractor:
                        st.session_state.extractor.close()
                    st.session_state.login_status = "not_started"
                    st.rerun()
        
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
                            st.session_state.chatbot = create_chatbot(vectorstore, st.session_state.current_model)
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
            3. ✅ Wait until you see your Facebook news feed
            4. 🔄 Return here and click **'I'm Logged In'**
            
            **🛠️ Troubleshooting:**
            - If no browser opens, check popup blockers
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
                else:
                    st.write("No group information extracted")
                
                st.subheader(f"📝 Posts Extracted: {len(posts)}")
                
                # Show sample posts
                for i, post in enumerate(posts[:3]):
                    with st.expander(f"Post {i+1} Sample", expanded=i==0):
                        content = post.get("content", "")
                        # Truncate long content
                        if len(content) > 500:
                            content = content[:500] + "..."
                        st.text_area(f"Content {i+1}", content, height=150, key=f"post_{i}")
                        st.caption(f"Source: {post.get('source', 'unknown')} | Reactions: {post.get('reactions', 0)}")
    
    with col2:
        st.header("💬 Chat with Group Data")
        
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