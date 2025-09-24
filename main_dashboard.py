# main_dashboard.py - Based on your working version
import streamlit as st
import subprocess
import sys
import os
import time
import threading

def is_running_on_cloud():
    return os.environ.get('STREAMLIT_SERVER_ENVIRONMENT') == 'production'

def main():
    st.set_page_config(
        page_title="Social Media Extractor Dashboard",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Cloud warning
    if is_running_on_cloud():
        st.warning("🌐 Running on Streamlit Cloud - Some features may be limited")
    
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
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0;">🔍 Social Media Data Extractor</h1>
        <p style="margin:0; opacity: 0.9;">Developed by [Refat]</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🚀 Launch Extractors")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="platform-card" style="border-left-color: #0077B5;">
            <h3>💼 LinkedIn Extractor</h3>
            <ul>
                <li>No login required</li>
                <li>Profile, company, and post analysis</li>
                <li>Quick data extraction</li>
                <li>AI-powered insights</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Launch LinkedIn Extractor", key="linkedin_btn", use_container_width=True):
            if is_running_on_cloud():
                st.info("🔒 Multi-app launching not available in cloud")
            else:
                st.info("Run locally: streamlit run linkdin.py")
    
    with col2:
        st.markdown("""
        <div class="platform-card" style="border-left-color: #1877F2;">
            <h3>📘 Facebook Extractor</h3>
            <ul>
                <li>Manual login required</li>
                <li>Group post extraction</li>
                <li>Works with private groups</li>
                <li>AI conversation analysis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Launch Facebook Extractor", key="facebook_btn", use_container_width=True):
            if is_running_on_cloud():
                st.info("🔒 Multi-app launching not available in cloud")
            else:
                st.info("Run locally: streamlit run facebook.py")
    
    with col3:
        st.markdown("""
        <div class="platform-card" style="border-left-color: #FF6B35;">
            <h3>🔥 Facebook Extractor 2.0</h3>
            <ul>
                <li>Enhanced Facebook data extraction</li>
                <li>More powerful algorithms</li>
                <li>Faster processing speed</li>
                <li>Advanced AI analysis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Launch Facebook Extractor 2.0", key="facebook_pro_btn", use_container_width=True):
            if is_running_on_cloud():
                st.info("🔒 Multi-app launching not available in cloud")
            else:
                st.info("Run locally: streamlit run let.py")
    
    with col4:
        st.markdown("""
        <div class="platform-card" style="border-left-color: #4CAF50;">
            <h3>🌐 Website Extractor</h3>
            <ul>
                <li>Extract data from any website</li>
                <li>URL-based content extraction</li>
                <li>Text and data scraping</li>
                <li>AI-powered content analysis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Launch Website Extractor", key="website_btn", use_container_width=True):
            if is_running_on_cloud():
                st.info("🔒 Multi-app launching not available in cloud")
            else:
                st.info("Run locally: streamlit run website.py")
    
    # Package test section
    with st.expander("🔧 Package Status Check"):
        st.write("Testing if all packages import correctly:")
        
        packages_to_test = [
            ("streamlit", "st"),
            ("requests", "requests"),
            ("bs4", "BeautifulSoup"),
            ("python_dotenv", "dotenv"),
            ("PyPDF2", "PyPDF2"),
            ("langchain", "langchain"),
            ("sentence_transformers", "SentenceTransformer"),
            ("faiss", "faiss"),
            ("ollama", "ollama")
        ]
        
        for package, import_name in packages_to_test:
            try:
                if package == "bs4":
                    from bs4 import BeautifulSoup
                elif package == "python_dotenv":
                    from dotenv import load_dotenv
                elif package == "sentence_transformers":
                    from sentence_transformers import SentenceTransformer
                else:
                    __import__(package)
                st.success(f"✅ {package}")
            except ImportError as e:
                st.error(f"❌ {package}: {str(e)}")

if __name__ == "__main__":
    main()
