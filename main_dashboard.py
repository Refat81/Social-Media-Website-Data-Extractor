# main_dashboard.py
import streamlit as st
import subprocess
import sys
import os
import webbrowser
import time
import threading

def check_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('localhost', port)) == 0

def get_available_port(start_port: int = 8601) -> int:
    port = start_port
    while check_port_in_use(port):
        port += 1
    return port

def run_streamlit_app_in_thread(app_file: str, port: int):
    def run_app():
        try:
            subprocess.run([
                sys.executable, "-m", "streamlit", "run", 
                app_file, 
                "--server.port", str(port),
                "--server.headless", "true",
                "--browser.serverAddress", "localhost"
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running {app_file}: {e}")
    
    thread = threading.Thread(target=run_app, daemon=True)
    thread.start()
    return thread

def main():
    st.set_page_config(
        page_title="Social Media Data Extractor",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
    <style>
        .stApp { background-color: #0e1117; color: white; }
        .main-header { background: linear-gradient(135deg, #1a2a6c, #b21f1f); color: white; padding: 2rem; border-radius: 10px; text-align: center; margin-bottom: 2rem; }
        .platform-card { background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid; margin: 1rem 0; height: 280px; }
        .linkedin-card { border-left-color: #0077B5; }
        .facebook-card { border-left-color: #1877F2; }
        .facebook-pro-card { border-left-color: #FF6B35; }
        .feature-list { margin: 1rem 0; padding-left: 1.5rem; flex-grow: 1; }
        .api-key-section { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem; }
        .status-box { background-color: #1a1a2e; padding: 1rem; border-radius: 5px; margin: 0.5rem 0; min-height: 120px; }
    </style>
    """, unsafe_allow_html=True)
    
    # API Key Section
    st.markdown("""
    <div class="api-key-section">
        <h2 style="margin:0; color:white;">🔑 HuggingFace API Key Required</h2>
        <p style="margin:0; color:white; opacity:0.9;">Get FREE API key from: <a href="https://huggingface.co/settings/tokens" target="_blank" style="color:white; text-decoration:underline;">huggingface.co/settings/tokens</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    # API Configuration
    hf_api_key = st.text_input(
        "🤗 Enter Your HuggingFace API Key",
        type="password",
        placeholder="hf_xxxxxxxxxxxxxxxx",
        help="Get FREE API key from huggingface.co/settings/tokens"
    )
    
    # Store API key
    if hf_api_key:
        st.session_state.hf_api_key = hf_api_key
        st.success("✅ HuggingFace API Key saved! You can now launch extractors.")
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0;">🔍 Social Media Data Extractor</h1>
        <p style="margin:0; opacity: 0.9;">100% Free - No Local Setup Required</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'linkedin_port' not in st.session_state:
        st.session_state.linkedin_port = None
    if 'facebook_port' not in st.session_state:
        st.session_state.facebook_port = None
    if 'facebook_pro_port' not in st.session_state:
        st.session_state.facebook_pro_port = None
    
    # Platform selection
    st.markdown("## 🚀 Launch Extractors")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="platform-card linkedin-card">
            <h3>💼 LinkedIn Extractor</h3>
            <ul class="feature-list">
                <li>No login required</li>
                <li>Profile, company, and post analysis</li>
                <li>Quick data extraction</li>
                <li>AI-powered insights</li>
                <li>100% Free</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Launch LinkedIn Extractor", key="linkedin_btn", use_container_width=True):
            if not st.session_state.get('hf_api_key'):
                st.error("❌ Please enter your HuggingFace API Key first")
            else:
                if os.path.exists("linkdin_deploy.py"):
                    port = get_available_port(8601)
                    st.session_state.linkedin_port = port
                    with st.spinner(f"Starting LinkedIn extractor..."):
                        run_streamlit_app_in_thread("linkdin_deploy.py", port)
                        time.sleep(3)
                        webbrowser.open_new_tab(f"http://localhost:{port}")
                        st.success(f"✅ LinkedIn extractor launched!")
                else:
                    st.error("❌ linkdin_deploy.py file not found!")

    with col2:
        st.markdown("""
        <div class="platform-card facebook-card">
            <h3>📘 Facebook Extractor</h3>
            <ul class="feature-list">
                <li>Manual login required</li>
                <li>Group post extraction</li>
                <li>Works with private groups</li>
                <li>AI conversation analysis</li>
                <li>100% Free</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Launch Facebook Extractor", key="facebook_btn", use_container_width=True):
            if not st.session_state.get('hf_api_key'):
                st.error("❌ Please enter your HuggingFace API Key first")
            else:
                if os.path.exists("facebook_deploy.py"):
                    port = get_available_port(8701)
                    st.session_state.facebook_port = port
                    with st.spinner(f"Starting Facebook extractor..."):
                        run_streamlit_app_in_thread("facebook_deploy.py", port)
                        time.sleep(3)
                        webbrowser.open_new_tab(f"http://localhost:{port}")
                        st.success(f"✅ Facebook extractor launched!")
                else:
                    st.error("❌ facebook_deploy.py file not found!")
    
    with col3:
        st.markdown("""
        <div class="platform-card facebook-pro-card">
            <h3>🔥 Facebook Extractor 2.0</h3>
            <ul class="feature-list">
                <li>Enhanced Facebook data extraction</li>
                <li>More powerful algorithms</li>
                <li>Faster processing speed</li>
                <li>Advanced AI analysis</li>
                <li>100% Free</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Launch Facebook Extractor 2.0", key="facebook_pro_btn", use_container_width=True):
            if not st.session_state.get('hf_api_key'):
                st.error("❌ Please enter your HuggingFace API Key first")
            else:
                if os.path.exists("let_deploy.py"):
                    port = get_available_port(8801)
                    st.session_state.facebook_pro_port = port
                    with st.spinner(f"Starting Facebook Extractor 2.0..."):
                        run_streamlit_app_in_thread("let_deploy.py", port)
                        time.sleep(3)
                        webbrowser.open_new_tab(f"http://localhost:{port}")
                        st.success(f"✅ Facebook Extractor 2.0 launched!")
                else:
                    st.error("❌ let_deploy.py file not found!")
    
    # Status
    st.markdown("---")
    st.subheader("🔄 Current Status")
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        st.markdown("### 💼 LinkedIn")
        if st.session_state.linkedin_port:
            st.success(f"✅ Running on port {st.session_state.linkedin_port}")
        else:
            st.info("💤 Not running")
    
    with status_col2:
        st.markdown("### 📘 Facebook")
        if st.session_state.facebook_port:
            st.success(f"✅ Running on port {st.session_state.facebook_port}")
        else:
            st.info("💤 Not running")
    
    with status_col3:
        st.markdown("### 🔥 Facebook 2.0")
        if st.session_state.facebook_pro_port:
            st.success(f"✅ Running on port {st.session_state.facebook_pro_port}")
        else:
            st.info("💤 Not running")
    
    # Instructions
    with st.expander("📋 How to Use", expanded=True):
        st.markdown("""
        1. **Get FREE API Key:**
           - Go to https://huggingface.co/settings/tokens
           - Create account (FREE)
           - Click "New token" 
           - Copy your token (starts with hf_)
        
        2. **Enter API Key above**
        
        3. **Click any extractor to launch**
        
        4. **For Streamlit Cloud:**
           - Add this to Secrets:
           ```
           HUGGINGFACEHUB_API_TOKEN = "your_token_here"
           ```
        """)

if __name__ == "__main__":
    main()
