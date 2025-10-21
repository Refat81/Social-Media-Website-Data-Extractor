# main_dashboard.py
import streamlit as st
import subprocess
import sys
import os
import webbrowser
import time
import threading

def check_port_in_use(port: int) -> bool:
    """Check if a port is already in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('localhost', port)) == 0

def get_available_port(start_port: int = 8601) -> int:
    """Find an available port starting from start_port"""
    port = start_port
    while check_port_in_use(port):
        port += 1
    return port

def run_streamlit_app_in_thread(app_file: str, port: int):
    """Run Streamlit app in a separate thread"""
    def run_app():
        try:
            subprocess.run([
                sys.executable, "-m", "streamlit", "run", 
                app_file, 
                "--server.port", str(port),
                "--server.headless", "true",
                "--browser.serverAddress", "localhost",
                "--server.enableCORS", "false",
                "--server.enableXsrfProtection", "false"
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
    
    # Simple dark theme CSS
    st.markdown("""
    <style>
        .stApp {
            background-color: #0e1117;
            color: white;
        }
        
        .main-header {
            background: linear-gradient(135deg, #1a2a6c, #b21f1f);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .platform-card {
            background-color: #262730;
            padding: 1.5rem;
            border-radius: 10px;
            border-left: 4px solid;
            margin: 1rem 0;
            height: 280px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .linkedin-card {
            border-left-color: #0077B5;
        }
        
        .facebook-card {
            border-left-color: #1877F2;
        }
        
        .facebook-pro-card {
            border-left-color: #FF6B35;
        }
        
        .feature-list {
            margin: 1rem 0;
            padding-left: 1.5rem;
            flex-grow: 1;
        }
        
        .api-key-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        
        .status-box {
            background-color: #1a1a2e;
            padding: 1rem;
            border-radius: 5px;
            margin: 0.5rem 0;
            min-height: 120px;
        }
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
    col1, col2 = st.columns([2, 1])
    
    with col1:
        hf_api_key = st.text_input(
            "🤗 Enter Your HuggingFace API Key",
            type="password",
            placeholder="hf_xxxxxxxxxxxxxxxx",
            help="Get FREE API key from huggingface.co/settings/tokens"
        )
    
    with col2:
        st.markdown("### 📝 How to get key:")
        st.markdown("""
        1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
        2. Sign up/login (FREE)
        3. Click **New token**
        4. Name it (e.g., 'streamlit-app')
        5. Copy and paste here
        """)
    
    # Store API key in session state
    if hf_api_key:
        st.session_state.hf_api_key = hf_api_key
        st.success("✅ HuggingFace API Key saved! You can now launch extractors.")
    
    # Header section
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0;">🔍 Social Media Data Extractor</h1>
        <p style="margin:0; opacity: 0.9;">100% Free - No Ollama Required</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("All features work with your HuggingFace API key. No local setup needed!")
    
    # Initialize session state for tracking launched apps
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
                <li>100% Free with HuggingFace</li>
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
                    
                    with st.spinner(f"Starting LinkedIn extractor on port {port}..."):
                        run_streamlit_app_in_thread("linkdin_deploy.py", port)
                        time.sleep(3)
                        webbrowser.open_new_tab(f"http://localhost:{port}")
                        st.success(f"✅ LinkedIn extractor launched on port {port}!")
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
                <li>100% Free with HuggingFace</li>
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
                    
                    with st.spinner(f"Starting Facebook extractor on port {port}..."):
                        run_streamlit_app_in_thread("facebook_deploy.py", port)
                        time.sleep(3)
                        webbrowser.open_new_tab(f"http://localhost:{port}")
                        st.success(f"✅ Facebook extractor launched on port {port}!")
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
                <li>100% Free with HuggingFace</li>
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
                    
                    with st.spinner(f"Starting Facebook Extractor 2.0 on port {port}..."):
                        run_streamlit_app_in_thread("let_deploy.py", port)
                        time.sleep(3)
                        webbrowser.open_new_tab(f"http://localhost:{port}")
                        st.success(f"✅ Facebook Extractor 2.0 launched on port {port}!")
                else:
                    st.error("❌ let_deploy.py file not found!")
    
    # Show current status
    st.markdown("---")
    st.subheader("🔄 Current Status")
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        st.markdown("### 💼 LinkedIn Extractor")
        if st.session_state.linkedin_port:
            st.markdown(f"""
            <div class="status-box">
                ✅ <strong>Running on:</strong> http://localhost:{st.session_state.linkedin_port}<br>
                🔑 <strong>API Status:</strong> ✅ Active
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("💤 Not running - Configure API Key and click launch")
    
    with status_col2:
        st.markdown("### 📘 Facebook Extractor")
        if st.session_state.facebook_port:
            st.markdown(f"""
            <div class="status-box">
                ✅ <strong>Running on:</strong> http://localhost:{st.session_state.facebook_port}<br>
                🔑 <strong>API Status:</strong> ✅ Active
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("💤 Not running - Configure API Key and click launch")
    
    with status_col3:
        st.markdown("### 🔥 Facebook Extractor 2.0")
        if st.session_state.facebook_pro_port:
            st.markdown(f"""
            <div class="status-box">
                ✅ <strong>Running on:</strong> http://localhost:{st.session_state.facebook_pro_port}<br>
                🔑 <strong>API Status:</strong> ✅ Active
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("💤 Not running - Configure API Key and click launch")
    
    # Deployment Instructions
    with st.expander("🚀 Streamlit Cloud Deployment", expanded=True):
        st.markdown("""
        ## How to Deploy to Streamlit Cloud (FREE)
        
        **1. Get HuggingFace API Key (FREE):**
        - Go to: https://huggingface.co/settings/tokens
        - Create account (FREE, no credit card)
        - Click "New token"
        - Name it and copy the token
        
        **2. Deploy to Streamlit Cloud:**
        - Go to: https://share.streamlit.io
        - Connect your GitHub repository
        - Set main file to: `main_dashboard.py`
        
        **3. Set Secrets in Streamlit:**
        - In your Streamlit app dashboard
        - Go to "Settings" → "Secrets"
        - Add this:
        ```toml
        HUGGINGFACEHUB_API_TOKEN = "hf_xxxxxxxxxxxxxxxx"
        ```
        
        **4. That's it! Your app will be live at:**
        `https://your-app-name.streamlit.app`
        
        **Free Tier Limits:**
        - HuggingFace: 10,000 tokens/month FREE
        - Streamlit: Unlimited apps FREE
        - No credit card required
        """)
    
    # Cost Information
    with st.expander("💰 Cost Information"):
        st.markdown("""
        ## 100% Free Setup
        
        **HuggingFace API:**
        - ✅ 10,000 tokens per month FREE
        - ✅ No credit card required
        - ✅ Perfect for personal projects
        - ✅ Enough for hundreds of analyses
        
        **Streamlit Cloud:**
        - ✅ Unlimited apps FREE
        - ✅ No server costs
        - ✅ Automatic deployments
        
        **No Ollama Required:**
        - ✅ No local setup
        - ✅ No GPU required
        - ✅ Works on any device
        - ✅ Cloud-based AI
        """)

if __name__ == "__main__":
    main()
