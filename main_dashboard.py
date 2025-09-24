# main_dashboard.py - Cloud Optimized Version
import streamlit as st
import os
import sys

# Check if running on Streamlit Cloud
def is_running_on_cloud():
    return os.environ.get('STREAMLIT_SERVER_ENVIRONMENT') == 'production'

# Try to import required packages with fallbacks
def check_dependencies():
    missing_deps = []
    
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        missing_deps.append("beautifulsoup4")
    
    try:
        import pandas as pd
    except ImportError:
        missing_deps.append("pandas")
    
    try:
        import ollama
    except ImportError:
        missing_deps.append("ollama")
    
    return missing_deps

def main():
    st.set_page_config(
        page_title="Social Media & Website Extractor Dashboard",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Check dependencies first
    missing_deps = check_dependencies()
    
    # Cloud detection
    if is_running_on_cloud():
        st.sidebar.success("🌐 Running on Streamlit Cloud")
    else:
        st.sidebar.info("💻 Running Locally")
    
    # Show dependency warnings
    if missing_deps:
        st.error(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        st.info("""
        **Please add these to your requirements.txt and redeploy:**
        ```
        requests>=2.31.0
        beautifulsoup4>=4.12.0
        pandas>=2.1.0
        ollama>=0.1.0
        ```
        """)
    
    # Custom CSS
    st.markdown("""
    <style>
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
    }
    .cloud-info {
        background: #1a2a6c;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0;">🔍 Social Media & Website Data Extractor</h1>
        <p style="margin:0; opacity: 0.9;">Streamlit Cloud Deployment</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Cloud information
    st.markdown("""
    <div class="cloud-info">
        <h4>📦 Deployment Status</h4>
        <p><strong>Current Environment:</strong> Streamlit Cloud</p>
        <p><strong>Multi-app launching:</strong> Not available in cloud</p>
        <p><strong>Solution:</strong> Deploy each extractor as separate apps</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Extractors overview
    st.markdown("## 📊 Available Extractors")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="platform-card" style="border-left-color: #0077B5;">
            <h3>💼 LinkedIn Extractor</h3>
            <ul>
                <li>Profile analysis</li>
                <li>Company data</li>
                <li>Post extraction</li>
                <li>AI insights</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View LinkedIn Extractor", key="linkedin", use_container_width=True):
            if is_running_on_cloud():
                st.info("Deploy as separate app: `linkdin.py`")
            else:
                st.info("Run locally: `streamlit run linkdin.py`")
    
    with col2:
        st.markdown("""
        <div class="platform-card" style="border-left-color: #1877F2;">
            <h3>📘 Facebook Extractor</h3>
            <ul>
                <li>Group posts</li>
                <li>Private groups</li>
                <li>Conversation analysis</li>
                <li>AI processing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View Facebook Extractor", key="facebook", use_container_width=True):
            if is_running_on_cloud():
                st.info("Deploy as separate app: `facebook.py`")
            else:
                st.info("Run locally: `streamlit run facebook.py`")
    
    with col3:
        st.markdown("""
        <div class="platform-card" style="border-left-color: #FF6B35;">
            <h3>🔥 Facebook 2.0</h3>
            <ul>
                <li>Enhanced extraction</li>
                <li>Advanced algorithms</li>
                <li>Better performance</li>
                <li>Extended features</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View Facebook 2.0", key="facebook_pro", use_container_width=True):
            if is_running_on_cloud():
                st.info("Deploy as separate app: `let.py`")
            else:
                st.info("Run locally: `streamlit run let.py`")
    
    with col4:
        st.markdown("""
        <div class="platform-card" style="border-left-color: #4CAF50;">
            <h3>🌐 Website Extractor</h3>
            <ul>
                <li>Any website data</li>
                <li>URL processing</li>
                <li>Content extraction</li>
                <li>Batch operations</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View Website Extractor", key="website", use_container_width=True):
            if is_running_on_cloud():
                st.info("Deploy as separate app: `website.py`")
            else:
                st.info("Run locally: `streamlit run website.py`")
    
    # Deployment guide
    with st.expander("🚀 Deployment Instructions", expanded=True):
        st.markdown("""
        ## How to Fix Your Current Deployment
        
        ### 1. Add Missing Files to GitHub:
        ```bash
        # Create .streamlit folder
        mkdir .streamlit
        
        # Create config.toml
        echo '[server]
        headless = true
        enableCORS = false
        enableXsrfProtection = false' > .streamlit/config.toml
        
        # Create packages.txt
        echo 'chromium-browser
        chromium-chromedriver' > packages.txt
        ```
        
        ### 2. Update requirements.txt:
        ```txt
        streamlit>=1.28.0
        requests>=2.31.0
        beautifulsoup4>=4.12.0
        python-dotenv>=1.0.0
        PyPDF2>=3.0.0
        langchain>=0.0.350
        sentence-transformers>=2.2.0
        faiss-cpu>=1.7.0
        ollama>=0.1.0
        selenium>=4.15.0
        webdriver-manager>=4.0.0
        pandas>=2.1.0
        ```
        
        ### 3. Redeploy on Streamlit Cloud:
        - Go to share.streamlit.io
        - Find your app
        - Click "Manage app" → "Settings" → "Redeploy"
        """
        )
    
    # File status check
    with st.expander("🔍 Current File Status"):
        files = [
            "main_dashboard.py", "linkdin.py", "facebook.py", 
            "let.py", "website.py", "requirements.txt",
            ".streamlit/config.toml", "packages.txt"
        ]
        
        for file in files:
            if os.path.exists(file):
                st.success(f"✅ {file}")
            else:
                st.error(f"❌ {file} - MISSING")
    
    # Quick fix section
    if missing_deps:
        st.markdown("---")
        st.error("## 🚨 Immediate Action Required")
        st.markdown("""
        Your app is missing critical dependencies. Please:
        
        1. **Update your requirements.txt** with the dependencies above
        2. **Add the missing files** to your GitHub repository
        3. **Redeploy** your Streamlit app
        """)

if __name__ == "__main__":
    main()
