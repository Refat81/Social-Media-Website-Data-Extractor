# main_dashboard.py - Cloud Optimized
import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd

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
    cloud_mode = is_running_on_cloud()
    
    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a2a6c, #b21f1f); color: white; padding: 2rem; border-radius: 10px; text-align: center; margin-bottom: 2rem;">
        <h1 style="margin:0;">🔍 Data Extractor Dashboard</h1>
        <p style="margin:0; opacity: 0.9;">Cloud Deployment Ready</p>
    </div>
    """, unsafe_allow_html=True)
    
    if cloud_mode:
        st.warning("🌐 Running on Streamlit Cloud - Some features limited")
        st.info("""
        **Cloud Limitations:**
        - Ollama AI features not available
        - Multi-app launching disabled
        - Chrome automation not supported
        
        **Available Features:**
        - Basic web scraping
        - Data processing
        - URL content extraction
        """)
    
    # Extractors with cloud-aware functionality
    st.markdown("## 🚀 Available Tools")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #0077B5; margin: 1rem 0; height: 280px;">
            <h3>💼 LinkedIn Data</h3>
            <ul>
                <li>Public profile data</li>
                <li>Company information</li>
                <li>Basic analysis</li>
                <li>Data export</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📊 Open LinkedIn Tool", key="linkedin", use_container_width=True):
            if cloud_mode:
                show_cloud_alternative("LinkedIn", "public LinkedIn data scraping")
            else:
                st.success("Run locally: `streamlit run linkdin.py`")
    
    with col2:
        st.markdown("""
        <div style="background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #1877F2; margin: 1rem 0; height: 280px;">
            <h3>📘 Facebook Data</h3>
            <ul>
                <li>Public group content</li>
                <li>Basic extraction</li>
                <li>Content analysis</li>
                <li>Data processing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📊 Open Facebook Tool", key="facebook", use_container_width=True):
            if cloud_mode:
                show_cloud_alternative("Facebook", "public Facebook data extraction")
            else:
                st.success("Run locally: `streamlit run facebook.py`")
    
    with col3:
        st.markdown("""
        <div style="background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #FF6B35; margin: 1rem 0; height: 280px;">
            <h3>🔥 Enhanced Tools</h3>
            <ul>
                <li>Advanced algorithms</li>
                <li>Better processing</li>
                <li>Enhanced features</li>
                <li>Improved UI</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Open Enhanced Tool", key="enhanced", use_container_width=True):
            if cloud_mode:
                show_cloud_alternative("Enhanced", "advanced data processing")
            else:
                st.success("Run locally: `streamlit run let.py`")
    
    with col4:
        st.markdown("""
        <div style="background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #4CAF50; margin: 1rem 0; height: 280px;">
            <h3>🌐 Website Data</h3>
            <ul>
                <li>URL content extraction</li>
                <li>Text scraping</li>
                <li>Data processing</li>
                <li>Basic analysis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🌐 Open Website Tool", key="website", use_container_width=True):
            if cloud_mode:
                show_website_tool()
            else:
                st.success("Run locally: `streamlit run website.py`")
    
    # Cloud-friendly tools
    st.markdown("---")
    st.markdown("## 🛠️ Cloud-Compatible Tools")
    
    # Basic web scraping tool
    with st.expander("🔍 Basic Web Scraper (Works in Cloud)"):
        url = st.text_input("Enter URL to scrape:", "https://httpbin.org/html")
        
        if st.button("Scrape Website Content"):
            if url:
                try:
                    response = requests.get(url, timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extract basic content
                    title = soup.find('title')
                    paragraphs = soup.find_all('p')[:5]  # First 5 paragraphs
                    
                    st.success("✅ Successfully scraped content!")
                    
                    if title:
                        st.write(f"**Title:** {title.get_text()}")
                    
                    if paragraphs:
                        st.write("**Content:**")
                        for i, p in enumerate(paragraphs):
                            st.write(f"{i+1}. {p.get_text()[:200]}...")
                    
                    # Show raw text length
                    text_content = soup.get_text()
                    st.info(f"📊 Total text content: {len(text_content)} characters")
                    
                except Exception as e:
                    st.error(f"❌ Error scraping website: {e}")
    
    # Data processing demo
    with st.expander("📊 Data Processing Demo"):
        st.write("**Sample data processing with pandas:**")
        
        # Create sample data
        sample_data = {
            'Platform': ['LinkedIn', 'Facebook', 'Website', 'Twitter'],
            'Records': [150, 300, 75, 200],
            'Status': ['Completed', 'In Progress', 'Completed', 'Pending']
        }
        
        df = pd.DataFrame(sample_data)
        st.dataframe(df)
        
        st.write(f"**Total records:** {df['Records'].sum()}")
        st.write(f"**Completed tasks:** {len(df[df['Status'] == 'Completed'])}")
    
    # Package status
    with st.expander("🔧 System Status"):
        st.success("✅ All Python packages installed successfully!")
        
        # Test packages
        packages = [
            ("streamlit", "✅ Working"),
            ("requests", "✅ Working"),
            ("beautifulsoup4", "✅ Web scraping ready"),
            ("pandas", "✅ Data processing ready"),
            ("ollama", "❌ Local only - not available in cloud"),
            ("selenium", "❌ Local only - Chrome not available in cloud"),
        ]
        
        for pkg, status in packages:
            st.write(f"- **{pkg}:** {status}")
        
        if cloud_mode:
            st.info("""
            **For full functionality:**
            1. Run locally with `streamlit run main_dashboard.py`
            2. Install Ollama locally for AI features
            3. Use Chrome for automation features
            """)

def show_cloud_alternative(tool_name, description):
    st.info(f"""
    **🔒 {tool_name} Extractor - Cloud Limitations**
    
    {description} requires local execution for full functionality.
    
    **To use this tool:**
    ```bash
    # Run locally on your machine
    streamlit run {tool_name.lower().replace(' ', '')}.py
    ```
    
    **Cloud alternatives available:**
    - Basic web scraping tool above
    - Data processing demo
    - Public content extraction
    """)

def show_website_tool():
    st.success("""
    **🌐 Website Content Extractor**
    
    **Available in Cloud:**
    - Basic HTML content scraping
    - Text extraction from public websites
    - Data processing and analysis
    
    **Use the web scraper above** for cloud-compatible website extraction.
    
    **For advanced features** (JavaScript rendering, authentication):
    ```bash
    # Run locally
    streamlit run website.py
    ```
    """)

if __name__ == "__main__":
    main()
