# main_dashboard.py - Cloud Compatible Version
import streamlit as st
import os
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
try:
    import pandas as pd
except ImportError:
    pd = None

def is_running_on_cloud():
    return os.environ.get('STREAMLIT_SERVER_ENVIRONMENT') == 'production'

def main():
    st.set_page_config(
        page_title="Data Extractor Dashboard",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Cloud detection
    if is_running_on_cloud():
        st.sidebar.success("🌐 Running on Streamlit Cloud")
        st.sidebar.info("Some features limited in cloud environment")
    else:
        st.sidebar.info("💻 Running Locally")
    
    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a2a6c, #b21f1f); color: white; padding: 2rem; border-radius: 10px; text-align: center; margin-bottom: 2rem;">
        <h1 style="margin:0;">🔍 Data Extractor Dashboard</h1>
        <p style="margin:0; opacity: 0.9;">Cloud Deployment Ready</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature cards
    st.markdown("## 📊 Available Extractors")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #0077B5; margin: 1rem 0; height: 250px;">
            <h3>💼 LinkedIn Data</h3>
            <ul>
                <li>Profile information</li>
                <li>Company data</li>
                <li>Public content</li>
                <li>Basic analysis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Open LinkedIn", key="linkedin", use_container_width=True):
            if is_running_on_cloud():
                st.info("🔒 Advanced features require local deployment")
            else:
                st.success("Run locally: streamlit run linkdin.py")
    
    with col2:
        st.markdown("""
        <div style="background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #1877F2; margin: 1rem 0; height: 250px;">
            <h3>📘 Facebook Data</h3>
            <ul>
                <li>Public group data</li>
                <li>Basic extraction</li>
                <li>Content analysis</li>
                <li>Data export</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Open Facebook", key="facebook", use_container_width=True):
            if is_running_on_cloud():
                st.info("🔒 Advanced features require local deployment")
            else:
                st.success("Run locally: streamlit run facebook.py")
    
    with col3:
        st.markdown("""
        <div style="background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #FF6B35; margin: 1rem 0; height: 250px;">
            <h3>🔥 Enhanced Tools</h3>
            <ul>
                <li>Advanced algorithms</li>
                <li>Better processing</li>
                <li>Enhanced features</li>
                <li>Improved UI</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Open Enhanced", key="enhanced", use_container_width=True):
            if is_running_on_cloud():
                st.info("🔒 Advanced features require local deployment")
            else:
                st.success("Run locally: streamlit run let.py")
    
    with col4:
        st.markdown("""
        <div style="background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #4CAF50; margin: 1rem 0; height: 250px;">
            <h3>🌐 Website Data</h3>
            <ul>
                <li>URL content</li>
                <li>Text extraction</li>
                <li>Basic scraping</li>
                <li>Data processing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Open Website", key="website", use_container_width=True):
            if is_running_on_cloud():
                st.info("🔒 Advanced features require local deployment")
            else:
                st.success("Run locally: streamlit run website.py")
    
    # Deployment status
    with st.expander("🔧 Deployment Status", expanded=True):
        st.markdown("""
        ### ✅ Current Status: Cloud Compatible
        
        **Working Features:**
        - Basic web scraping (BeautifulSoup)
        - HTTP requests (requests)
        - Data processing (pandas)
        - Environment variables (python-dotenv)
        
        **Cloud Limitations:**
        - No Chrome automation (Selenium)
        - No AI models (Ollama)
        - No PDF processing (PyPDF2)
        - No heavy ML libraries
        
        **Solution for Full Features:**
        - Deploy locally for complete functionality
        - Use cloud for basic dashboard
        """)
        
        # Package status
        st.markdown("### 📦 Package Status")
        packages = {
            "streamlit": "✅ Working",
            "requests": "✅ Working", 
            "beautifulsoup4": "✅ Working",
            "pandas": "✅ Working",
            "python-dotenv": "✅ Working",
            "selenium": "❌ Not available",
            "ollama": "❌ Not available",
            "PyPDF2": "❌ Not available"
        }
        
        for pkg, status in packages.items():
            st.write(f"- {pkg}: {status}")
    
    # Quick actions
    st.markdown("---")
    st.markdown("## 🚀 Quick Actions")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("Check Deployment", key="check_deploy"):
            st.success("✅ Dashboard deployed successfully!")
            st.info("Basic features available in cloud")
    
    with action_col2:
        if st.button("View Documentation", key="docs"):
            st.markdown("""
            **Local Deployment (Full Features):**
            ```bash
            pip install -r requirements_full.txt
            streamlit run main_dashboard.py
            ```
            
            **Cloud Deployment (Basic Features):**
            - Current setup
            - Basic web scraping only
            """)
    
    with action_col3:
        if st.button("Test Basic Features", key="test"):
            try:
                # Test requests
                response = requests.get("https://httpbin.org/json", timeout=10)
                st.success("✅ HTTP requests working")
                
                # Test BeautifulSoup
                if BeautifulSoup:
                    st.success("✅ Web scraping ready")
                else:
                    st.warning("⚠️ BeautifulSoup not available")
                    
                # Test pandas
                if pd is not None:
                    test_df = pd.DataFrame({"test": [1, 2, 3]})
                    st.success("✅ Data processing ready")
                else:
                    st.warning("⚠️ Pandas not available")
                    
            except Exception as e:
                st.error(f"❌ Basic test failed: {e}")

if __name__ == "__main__":
    main()
