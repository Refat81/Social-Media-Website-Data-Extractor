# website_chatbot_advanced.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time
from typing import List, Dict, Tuple, Set
import json
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from datetime import datetime
import os

class AdvancedWebsiteChatbot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.extracted_data = {}
        self.chat_history = []
        self.visited_urls = set()
        self.url_scores = {}
        self.content_cache = {}
        
    def call_ollama_api(self, prompt: str, model: str = 'llama2', max_retries: int = 3) -> str:
        """Enhanced Ollama API call with retry logic and better error handling"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    'http://localhost:11434/api/generate',
                    json={
                        'model': model,
                        'prompt': prompt,
                        'stream': False,
                        'options': {
                            'temperature': 0.3,
                            'top_p': 0.9,
                            'num_ctx': 4096  # Increased context window
                        }
                    },
                    timeout=180
                )
                response.raise_for_status()
                result = response.json()
                return result.get('response', 'No response from AI model').strip()
                
            except requests.exceptions.ConnectionError:
                if attempt == max_retries - 1:
                    return "Error: Could not connect to Ollama. Please make sure Ollama is running on port 11434."
                time.sleep(2)
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    return "Error: Request timeout. The AI model is taking too long to respond."
                time.sleep(3)
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    return f"Error calling Ollama API: {str(e)}"
                time.sleep(1)
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"Unexpected error: {str(e)}"
                time.sleep(1)
        return "Error: Max retries exceeded"

    def is_valid_url(self, url: str) -> bool:
        """Enhanced URL validation"""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False
            
            # Check for common file extensions to avoid non-HTML content
            invalid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.png', '.zip', '.exe']
            if any(url.lower().endswith(ext) for ext in invalid_extensions):
                return False
                
            return True
        except:
            return False

    def calculate_url_score(self, url: str, link_text: str = "") -> float:
        """Calculate priority score for URL crawling"""
        score = 0.0
        
        # Penalize URLs with query parameters (likely dynamic content)
        if '?' in url:
            score -= 0.3
            
        # Penalize long URLs
        if len(url) > 100:
            score -= 0.2
            
        # Boost URLs with important keywords in path
        important_keywords = ['about', 'contact', 'services', 'products', 'blog', 'article', 'news']
        if any(keyword in url.lower() for keyword in important_keywords):
            score += 0.5
            
        # Boost URLs with meaningful link text
        if link_text:
            text_length = len(link_text.strip())
            if text_length > 10 and text_length < 100:
                score += 0.3
                
        return score

    def extract_website_content(self, url: str, max_pages: int = 50, depth: int = 2) -> Dict:
        """Advanced website content extraction with multi-threading and intelligent crawling"""
        try:
            self.visited_urls.clear()
            self.url_scores.clear()
            self.content_cache.clear()
            
            # Validate and normalize URL
            if not self.is_valid_url(url):
                raise ValueError("Invalid URL provided")
                
            # Ensure URL has scheme
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            st.info(f"🚀 Starting extraction of up to {max_pages} pages from {url}...")
            
            # Extract main page first
            main_content = self._extract_single_page(url)
            if not main_content:
                raise Exception("Failed to extract main page content")
                
            website_data = {
                'main_url': url,
                'title': main_content['title'],
                'meta_description': main_content['meta_description'],
                'main_content': main_content['content'],
                'links': [],
                'pages': {},
                'structure': {},
                'extraction_time': datetime.now().isoformat(),
                'total_pages': 1,
                'content_stats': {
                    'total_chars': len(main_content['content']),
                    'avg_content_length': len(main_content['content']),
                    'pages_with_content': 1
                }
            }
            
            self.visited_urls.add(url)
            
            # Extract links from main page and score them
            main_links = self._extract_links_with_scoring(BeautifulSoup(main_content['raw_html'], 'html.parser'), url)
            website_data['links'] = main_links
            
            # Multi-threaded extraction of additional pages
            if max_pages > 1:
                additional_pages = self._crawl_additional_pages(main_links, max_pages - 1, depth)
                website_data['pages'] = additional_pages
                website_data['total_pages'] = 1 + len(additional_pages)
                
                # Calculate content statistics
                total_chars = len(main_content['content'])
                for page_content in additional_pages.values():
                    total_chars += len(page_content.get('content', ''))
                    
                website_data['content_stats']['total_chars'] = total_chars
                website_data['content_stats']['avg_content_length'] = total_chars / website_data['total_pages']
                website_data['content_stats']['pages_with_content'] = website_data['total_pages']
            
            # Generate site structure
            website_data['structure'] = self._generate_site_structure(website_data)
            
            return website_data
            
        except Exception as e:
            st.error(f"Error extracting website content: {str(e)}")
            return None

    def _crawl_additional_pages(self, links: List[Dict], max_pages: int, depth: int) -> Dict:
        """Crawl additional pages using multi-threading with depth control"""
        pages = {}
        urls_to_crawl = [(link['url'], 1) for link in links if link['url'] not in self.visited_urls]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {}
            
            while urls_to_crawl and len(pages) < max_pages:
                # Get next batch of URLs
                current_batch = urls_to_crawl[:10]
                urls_to_crawl = urls_to_crawl[10:]
                
                # Submit tasks
                for url, current_depth in current_batch:
                    if url not in self.visited_urls and len(pages) < max_pages:
                        future = executor.submit(self._extract_single_page, url)
                        future_to_url[future] = (url, current_depth)
                
                # Process completed tasks
                for future in as_completed(future_to_url):
                    url, current_depth = future_to_url[future]
                    try:
                        content = future.result(timeout=30)
                        if content and content['content']:
                            pages[url] = content
                            self.visited_urls.add(url)
                            
                            # Extract links for next depth level if within limit
                            if current_depth < depth and len(pages) < max_pages:
                                soup = BeautifulSoup(content['raw_html'], 'html.parser')
                                new_links = self._extract_links_with_scoring(soup, url)
                                for link in new_links:
                                    if link['url'] not in self.visited_urls and len(pages) + len(urls_to_crawl) < max_pages:
                                        urls_to_crawl.append((link['url'], current_depth + 1))
                        
                    except Exception as e:
                        st.warning(f"Failed to extract {url}: {str(e)}")
                    
                    # Remove processed future
                    del future_to_url[future]
                
                # Be polite - delay between batches
                time.sleep(1)
        
        return pages

    def _extract_single_page(self, url: str) -> Dict:
        """Extract content from a single page with enhanced error handling"""
        try:
            # Check cache first
            url_hash = hashlib.md5(url.encode()).hexdigest()
            if url_hash in self.content_cache:
                return self.content_cache[url_hash]
                
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Extract metadata
            title = soup.title.string if soup.title else 'No title'
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta_desc.get('content', '') if meta_desc else ''
            
            # Enhanced content extraction
            content = self._extract_meaningful_content(soup)
            
            result = {
                'url': url,
                'title': title,
                'meta_description': meta_description,
                'content': content,
                'raw_html': str(soup),
                'content_length': len(content),
                'status': 'success'
            }
            
            # Cache the result
            self.content_cache[url_hash] = result
            return result
            
        except Exception as e:
            return {
                'url': url,
                'title': 'Error',
                'meta_description': '',
                'content': f'Error extracting content: {str(e)}',
                'raw_html': '',
                'content_length': 0,
                'status': 'error'
            }

    def _extract_links_with_scoring(self, soup, base_url: str) -> List[Dict]:
        """Extract and score internal links"""
        internal_links = set()
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if not href or href.startswith(('javascript:', 'mailto:', 'tel:')):
                continue
                
            full_url = urljoin(base_url, href)
            
            # Normalize URL
            parsed = urlparse(full_url)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized_url += '?' + parsed.query
                
            # Check if it's an internal link and valid
            if (parsed.netloc == base_domain and 
                self.is_valid_url(normalized_url) and
                normalized_url not in self.visited_urls):
                
                link_text = link.get_text(strip=True)
                score = self.calculate_url_score(normalized_url, link_text)
                
                internal_links.add((normalized_url, score, link_text))
        
        # Convert to list of dictionaries and sort by score
        links_list = [{'url': url, 'score': score, 'link_text': text} 
                     for url, score, text in internal_links]
        links_list.sort(key=lambda x: x['score'], reverse=True)
        
        return links_list

    def _extract_meaningful_content(self, soup) -> str:
        """Advanced content extraction focusing on meaningful text"""
        # Priority content areas
        content_selectors = [
            'main', 'article', '.content', '#content', '.main-content',
            '#main-content', '.post-content', '.entry-content',
            '.article-content', '.blog-content', '.page-content',
            '[role="main"]', '.main', '.body'
        ]
        
        # Try priority content areas first
        for selector in content_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = self._clean_text(element.get_text())
                if len(text) > 200:  # Substantial content
                    return text
        
        # Fallback: try to find the largest text block
        body = soup.find('body')
        if body:
            # Remove navigation and other non-content elements
            for unwanted in body.select('nav, header, footer, aside, .sidebar, .navigation'):
                unwanted.decompose()
            
            text = self._clean_text(body.get_text())
            if len(text) > 100:
                return text
        
        return self._clean_text(soup.get_text())

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Replace multiple whitespaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        # Remove excessive line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text

    def _generate_site_structure(self, website_data: Dict) -> Dict:
        """Generate hierarchical site structure"""
        structure = {
            'main_page': website_data['main_url'],
            'sections': {},
            'page_count': website_data['total_pages'],
            'depth': 1
        }
        
        # Group pages by path segments
        for url in [website_data['main_url']] + list(website_data['pages'].keys()):
            parsed = urlparse(url)
            path_segments = [seg for seg in parsed.path.split('/') if seg]
            
            current_level = structure['sections']
            for segment in path_segments:
                if segment not in current_level:
                    current_level[segment] = {'pages': [], 'subsections': {}}
                current_level = current_level[segment]['subsections']
            
            # Add page to appropriate section
            # Implementation simplified for brevity
            
        return structure

    def summarize_website_content(self, website_data: Dict) -> str:
        """Create comprehensive summary with content analysis"""
        try:
            # Prepare optimized content for summarization
            content_chunks = self._prepare_content_chunks(website_data)
            
            prompt = f"""
            Please provide a comprehensive analysis of this website with the following structure:

            WEBSITE OVERVIEW:
            - Main purpose and primary focus
            - Target audience and value proposition
            - Key themes and topics covered

            CONTENT ANALYSIS:
            - Summary of main services/products/information
            - Key features and differentiators
            - Content depth and quality assessment

            STRUCTURAL ANALYSIS:
            - Website organization and navigation patterns
            - Content coverage across different pages
            - Notable sections and their purposes

            KEY FINDINGS:
            - Most important information extracted
            - Potential use cases and applications
            - Overall quality assessment

            Website URL: {website_data['main_url']}
            Title: {website_data['title']}
            Total Pages Analyzed: {website_data['total_pages']}
            Total Content: {website_data['content_stats']['total_chars']} characters

            CONTENT:
            {content_chunks}

            Please provide a detailed, well-structured analysis.
            """
            
            return self.call_ollama_api(prompt)
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def _prepare_content_chunks(self, website_data: Dict, max_chunk_size: int = 3000) -> str:
        """Prepare content chunks for AI processing"""
        all_content = []
        
        # Main page content
        main_content = website_data['main_content']
        if len(main_content) > max_chunk_size:
            main_content = main_content[:max_chunk_size] + "... [truncated]"
        all_content.append(f"MAIN PAGE: {main_content}")
        
        # Additional pages content (prioritized by length and relevance)
        page_contents = []
        for url, page_data in website_data['pages'].items():
            if page_data.get('content'):
                page_contents.append((len(page_data['content']), url, page_data['content']))
        
        # Sort by content length (longer content likely more important)
        page_contents.sort(reverse=True)
        
        for i, (length, url, content) in enumerate(page_contents[:10]):  # Top 10 pages
            if len(content) > max_chunk_size:
                content = content[:max_chunk_size] + "... [truncated]"
            all_content.append(f"PAGE {i+1} ({url}): {content}")
        
        return "\n\n".join(all_content)

    def answer_question(self, question: str, website_data: Dict, chat_history: List) -> str:
        """Enhanced question answering with context optimization"""
        try:
            # Prepare optimized context
            context = self._prepare_qa_context(question, website_data, chat_history)
            
            prompt = f"""
            Based EXCLUSIVELY on the provided website content, answer the user's question.
            
            GUIDELINES:
            - Only use information from the provided content
            - If information is not available, clearly state this
            - Be specific, accurate, and cite relevant sections when possible
            - Maintain a helpful and professional tone
            - If the question requires inference, base it strictly on available content
            
            WEBSITE CONTEXT:
            {context}
            
            USER QUESTION: {question}
            
            CHAT HISTORY (for context):
            {self._format_chat_history(chat_history[-4:])}
            
            Answer:
            """
            
            return self.call_ollama_api(prompt)
            
        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def _prepare_qa_context(self, question: str, website_data: Dict, chat_history: List) -> str:
        """Prepare optimized context for Q&A based on question relevance"""
        # Simple keyword matching for context selection (could be enhanced with embeddings)
        question_lower = question.lower()
        
        relevant_content = []
        
        # Check main content
        main_content = website_data['main_content'].lower()
        if any(keyword in question_lower for keyword in ['main', 'purpose', 'about', 'what is']):
            relevant_content.append(f"MAIN PAGE: {website_data['main_content'][:2000]}")
        
        # Add main page content (always include some)
        relevant_content.append(f"MAIN CONTEXT: {website_data['main_content'][:1500]}")
        
        # Add relevant pages based on keyword matching
        for url, page_data in website_data['pages'].items():
            page_content = page_data.get('content', '').lower()
            content_keywords = ['service', 'product', 'contact', 'about', 'price', 'feature']
            if any(keyword in question_lower and keyword in page_content for keyword in content_keywords):
                relevant_content.append(f"RELEVANT PAGE ({url}): {page_data.get('content', '')[:1000]}")
        
        # Limit total context size
        total_context = "\n\n".join(relevant_content)
        if len(total_context) > 8000:
            total_context = total_context[:8000] + "... [context truncated]"
            
        return total_context

    def _format_chat_history(self, history: List) -> str:
        """Format chat history for context"""
        if not history:
            return "No recent conversation history."
            
        formatted = []
        for msg in history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)

def main():
    st.set_page_config(
        page_title="🌐 Advanced Website AI Analyzer",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Dark theme CSS matching LinkedIn AI Analyzer
    st.markdown("""
    <style>
        /* Dark background for entire app */
        .stApp {
            background-color: #0e1117;
            color: white;
        }
        
        /* Sidebar dark background */
        .css-1d391kg {
            background-color: #262730;
        }
        
        /* Main content area */
        .main .block-container {
            background-color: #0e1117;
            color: white;
        }
        
        /* All text white */
        body {
            color: white !important;
        }
        
        /* Chat messages - transparent with white text */
        .user-message {
            background-color: transparent;
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 4px solid #0077b5;
            color: white;
        }
        
        .assistant-message {
            background-color: transparent;
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 4px solid #00a0dc;
            color: white;
        }
        
        /* Remove all white backgrounds from Streamlit components */
        .stTextInput>div>div>input {
            background-color: #262730;
            color: white;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 10px;
        }
        
        /* Buttons */
        .stButton>button {
            background-color: #0077b5;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 500;
            width: 100%;
        }
        
        /* Metric containers - dark */
        [data-testid="metric-container"] {
            background-color: #262730;
            color: white;
            border: 1px solid #555;
            padding: 10px;
            border-radius: 5px;
        }
        
        /* Expander - dark */
        .streamlit-expanderHeader {
            background-color: #262730;
            color: white;
        }
        
        .streamlit-expanderContent {
            background-color: #262730;
            color: white;
        }
        
        /* Text area - dark */
        .stTextArea textarea {
            background-color: #262730;
            color: white;
        }
        
        /* Select boxes - dark */
        .stSelectbox>div>div>select {
            background-color: #262730;
            color: white;
        }
        
        /* Progress bar */
        .stProgress > div > div > div > div {
            background-color: #0077b5;
        }
        
        /* Success/Error messages - dark */
        .stSuccess {
            background-color: #1a3a1a;
            color: #90ee90;
        }
        
        .stError {
            background-color: #3a1a1a;
            color: #ff6b6b;
        }
        
        .stWarning {
            background-color: #3a3a1a;
            color: #ffff90;
        }
        
        .stInfo {
            background-color: #1a3a3a;
            color: #90ffff;
        }
        
        /* Header */
        .main-header {
            background: #0077b5;
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            text-align: center;
        }
        
        /* Make all text white */
        h1, h2, h3, h4, h5, h6, p, div, span {
            color: white !important;
        }
        
        /* Chat input */
        .stChatInput>div>div>textarea {
            background-color: #262730;
            color: white;
        }
        
        /* Custom status panels for dark theme */
        .status-success {
            background-color: #1a3a1a;
            border: 1px solid #2e7d32;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            color: #90ee90;
        }
        
        .status-warning {
            background-color: #3a3a1a;
            border: 1px solid #b0a429;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            color: #ffff90;
        }
        
        .status-error {
            background-color: #3a1a1a;
            border: 1px solid #c62828;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            color: #ff6b6b;
        }
        
        /* Dataframe styling for dark theme */
        .dataframe {
            background-color: #262730 !important;
            color: white !important;
        }
        
        .dataframe th {
            background-color: #0077b5 !important;
            color: white !important;
        }
        
        .dataframe td {
            background-color: #262730 !important;
            color: white !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🌐 Advanced Website AI Analyzer</h1>
        <p>Extract and analyze website data with AI-powered insights</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check Ollama status
    ollama_running = check_ollama_status()
    
    # Initialize chatbot and session state
    initialize_session_state()
    
    # Sidebar
    render_sidebar(ollama_running)
    
    # Main content
    render_main_content(ollama_running)

def check_ollama_status() -> bool:
    """Check if Ollama is running"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        return response.status_code == 200
    except:
        return False

def initialize_session_state():
    """Initialize session state variables"""
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = AdvancedWebsiteChatbot()
    if 'website_data' not in st.session_state:
        st.session_state.website_data = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'summary' not in st.session_state:
        st.session_state.summary = None
    if 'extraction_progress' not in st.session_state:
        st.session_state.extraction_progress = 0
    if 'current_status' not in st.session_state:
        st.session_state.current_status = "Ready"

def render_sidebar(ollama_running: bool):
    """Render the sidebar content with dark theme"""
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        
        # Ollama status
        if ollama_running:
            st.success("✅ Ollama is running")
        else:
            st.error("❌ Ollama not detected")
            st.info("Please start Ollama: `ollama serve`")
        
        website_url = st.text_input(
            "🌐 Website URL:",
            placeholder="https://example.com",
            help="Enter the full website URL to analyze"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_pages = st.slider(
                "📄 Max Pages:",
                min_value=1,
                max_value=50,
                value=15,
                help="Maximum number of pages to extract (1-50)"
            )
        
        with col2:
            crawl_depth = st.slider(
                "📊 Crawl Depth:",
                min_value=1,
                max_value=3,
                value=2,
                help="How deep to crawl internal links"
            )
        
        if st.button("🚀 Extract & Analyze", use_container_width=True, type="primary"):
            if website_url:
                if st.session_state.chatbot.is_valid_url(website_url):
                    start_extraction(website_url, max_pages, crawl_depth, ollama_running)
                else:
                    st.error("❌ Please enter a valid URL")
            else:
                st.error("❌ Please enter a website URL")
        
        st.markdown("---")
        render_status_panel(ollama_running)
        st.markdown("---")
        render_ai_models_panel()

def start_extraction(url: str, max_pages: int, depth: int, ollama_running: bool):
    """Start the website extraction process"""
    with st.spinner("🔄 Starting extraction..."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Update progress
        def update_progress(progress, status):
            progress_bar.progress(progress)
            status_text.text(f"Status: {status}")
        
        update_progress(10, "Initializing crawler...")
        
        # Extract website content
        website_data = st.session_state.chatbot.extract_website_content(url, max_pages, depth)
        
        if website_data:
            update_progress(80, "Processing extracted content...")
            st.session_state.website_data = website_data
            
            # Generate summary if Ollama is running
            if ollama_running:
                update_progress(90, "Generating AI summary...")
                st.session_state.summary = st.session_state.chatbot.summarize_website_content(website_data)
            else:
                st.session_state.summary = "⚠️ AI summary not available - Ollama is not running"
            
            update_progress(100, "Extraction completed!")
            st.session_state.chat_history = []
            st.success("✅ Website data extracted successfully!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Failed to extract website data")

def render_status_panel(ollama_running: bool):
    """Render the status information panel with dark theme"""
    st.markdown("### 📊 Status Panel")
    
    if st.session_state.website_data:
        st.markdown("""
        <div class="status-success">
            <h4>✅ Website Data Loaded</h4>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Pages", st.session_state.website_data['total_pages'])
            st.metric("Content Size", f"{st.session_state.website_data['content_stats']['total_chars']:,} chars")
        
        with col2:
            st.metric("Links Found", len(st.session_state.website_data['links']))
            avg_length = st.session_state.website_data['content_stats']['avg_content_length']
            st.metric("Avg Page Length", f"{int(avg_length):,} chars")
        
        if st.button("🔄 New Extraction", use_container_width=True):
            reset_extraction()
    else:
        st.markdown("""
        <div class="status-warning">
            <h4>💤 Ready for Extraction</h4>
            <p>Enter a URL above to start analyzing a website</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🤖 AI Status")
    if ollama_running:
        st.success("✅ Ollama Connected")
        st.info("AI features are enabled and ready")
    else:
        st.error("❌ Ollama Not Detected")
        st.code("ollama serve", language="bash")
        st.warning("AI features will be disabled")

def render_ai_models_panel():
    """Render AI models information panel"""
    st.markdown("### 🧠 AI Models")
    st.info("""
    **Current Model:** LLaMA 2
    **Capabilities:**
    - Website summarization
    - Intelligent Q&A
    - Content analysis
    - Context understanding
    """)

def reset_extraction():
    """Reset the extraction state"""
    st.session_state.website_data = None
    st.session_state.summary = None
    st.session_state.chat_history = []
    st.rerun()

def render_main_content(ollama_running: bool):
    """Render the main content area with dark theme"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_summary_panel()
    
    with col2:
        render_chat_panel(ollama_running)
    
    # Advanced analytics
    if st.session_state.website_data:
        render_analytics_panel()

def render_summary_panel():
    """Render the website summary panel"""
    st.markdown("### 📋 Website Analysis")
    
    if st.session_state.website_data:
        # Metrics overview
        st.markdown("#### 📊 Content Metrics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pages Analyzed", st.session_state.website_data['total_pages'])
        with col2:
            st.metric("Total Content", f"{st.session_state.website_data['content_stats']['total_chars']:,} chars")
        with col3:
            st.metric("Extraction Time", st.session_state.website_data['extraction_time'][:10])
        
        # AI Summary
        st.markdown("#### 🤖 AI Analysis")
        if st.session_state.summary:
            st.write(st.session_state.summary)
        else:
            st.info("No AI analysis available. Content extraction completed successfully.")
        
        # Content preview
        with st.expander("🔍 View Detailed Content Analysis"):
            render_content_analysis()
    else:
        st.info("👆 Enter a website URL to start analysis")

def render_content_analysis():
    """Render detailed content analysis"""
    if not st.session_state.website_data:
        return
    
    # Page content overview
    st.write("**📄 Page Content Overview:**")
    pages_data = []
    
    # Main page
    pages_data.append({
        'Page': 'Main Page',
        'URL': st.session_state.website_data['main_url'],
        'Content Length': len(st.session_state.website_data['main_content']),
        'Status': '✅'
    })
    
    # Additional pages
    for i, (url, content) in enumerate(st.session_state.website_data['pages'].items()):
        pages_data.append({
            'Page': f'Page {i+1}',
            'URL': url,
            'Content Length': content.get('content_length', 0),
            'Status': content.get('status', '❓')
        })
    
    df = pd.DataFrame(pages_data)
    st.dataframe(df, use_container_width=True)
    
    # Content distribution
    st.write("**📈 Content Distribution:**")
    content_lengths = [len(st.session_state.website_data['main_content'])]
    content_lengths.extend([page.get('content_length', 0) for page in st.session_state.website_data['pages'].values()])
    
    chart_data = pd.DataFrame({
        'Page Type': ['Main Page'] + [f'Page {i+1}' for i in range(len(content_lengths)-1)],
        'Content Length': content_lengths
    })
    
    st.bar_chart(chart_data.set_index('Page Type'))

def render_chat_panel(ollama_running: bool):
    """Render the chat interface panel with LinkedIn-style messaging"""
    st.markdown("### 💬 Chat with Website")
    
    if st.session_state.website_data:
        # Display chat history
        for i, chat in enumerate(st.session_state.chat_history):
            if chat["role"] == "user":
                display_message("user", chat["content"])
            elif chat["role"] == "assistant":
                if chat["content"]:  # Only display if there's content
                    display_message("assistant", chat["content"])
                else:
                    # Process pending assistant messages
                    with st.spinner("🤔 Analyzing..."):
                        try:
                            if st.session_state.website_data:
                                response = st.session_state.chatbot.answer_question(
                                    st.session_state.chat_history[i-1]["content"],
                                    st.session_state.website_data,
                                    st.session_state.chat_history
                                )
                                st.session_state.chat_history[i]["content"] = response
                                st.rerun()
                        except Exception as e:
                            st.session_state.chat_history[i]["content"] = f"❌ Error: {str(e)}"
                            st.rerun()
        
        # Chat input
        if ollama_running:
            user_input = st.chat_input("Ask about the website content...")
            
            if user_input:
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input
                })
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": ""
                })
                st.rerun()
        
        # Quick questions in sidebar style
        st.markdown("---")
        st.markdown("#### 🚀 Quick Questions")
        
        quick_questions = [
            "What's the main purpose of this website?",
            "What are the key services or products?",
            "Who is the target audience?",
            "What makes this website unique?",
            "Summarize the main content"
        ]
        
        for question in quick_questions:
            if st.button(question, key=f"quick_{question}", use_container_width=True):
                process_question(question)
        
        if st.session_state.chat_history and st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
        
        if not ollama_running:
            st.warning("⚠️ AI features disabled - Ollama is not running")
        
    else:
        st.info("👆 Extract a website first to start chatting!")

def display_message(role: str, content: str):
    """Display a chat message with LinkedIn-style formatting"""
    if role == "user":
        st.markdown(f"""
        <div class="user-message">
            <strong>👤 You:</strong><br>{content}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="assistant-message">
            <strong>🤖 Assistant:</strong><br>{content}
        </div>
        """, unsafe_allow_html=True)

def process_question(question: str):
    """Process a user question"""
    if question.strip() and st.session_state.website_data:
        # Add user question to history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': question
        })
        
        # Add empty assistant message placeholder
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': ""
        })
        
        st.rerun()

def render_analytics_panel():
    """Render advanced analytics panel"""
    with st.expander("📈 Advanced Analytics", expanded=False):
        st.markdown("#### 🔍 Deep Content Analysis")
        
        if st.session_state.website_data:
            # Content statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Characters", f"{st.session_state.website_data['content_stats']['total_chars']:,}")
            
            with col2:
                st.metric("Average Page Length", f"{int(st.session_state.website_data['content_stats']['avg_content_length']):,}")
            
            with col3:
                st.metric("Content Coverage", f"{st.session_state.website_data['content_stats']['pages_with_content']}/{st.session_state.website_data['total_pages']} pages")
            
            # URL analysis
            st.write("**🌐 URL Structure Analysis:**")
            st.json({
                "main_url": st.session_state.website_data['main_url'],
                "total_pages_crawled": st.session_state.website_data['total_pages'],
                "internal_links_found": len(st.session_state.website_data['links']),
                "crawl_depth": "Multi-level" if len(st.session_state.website_data['pages']) > 5 else "Shallow"
            })

if __name__ == "__main__":
    main()