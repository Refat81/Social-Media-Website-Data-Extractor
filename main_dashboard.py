import streamlit as st
import linkdin_hf
import let_hf


HUGGINGFACE_API_KEY = "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"


st.set_page_config(page_title="AI Dashboard", page_icon="🤖", layout="wide")


st.title("🤖 AI Dashboard")


col1, col2 = st.columns(2)


with col1:
st.header("💼 LinkedIn Analyzer")
if st.button("Launch LinkedIn Analyzer"):
linkdin_hf.main(HUGGINGFACE_API_KEY)


with col2:
st.header("📘 Facebook Group Extractor")
if st.button("Launch Facebook Extractor"):
let_hf.main(HUGGINGFACE_API_KEY)

import streamlit as st
import subprocess
import sys
import os
import webbrowser
import time
import threading
import requests

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
                "--browser.serverAddress", "localhost",
                "--server.enableCORS", "false",
                "--server.enableXsrfProtection", "false"
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running {app_file}: {e}")

    thread = threading.Thread(target=run_app, daemon=True)
    thread.start()
    return thread

def check_hf_key():
    # Warn if no key present
    hf_key = None
    try:
        hf_key = st.secrets["huggingface"]["api_key"]
    except Exception:
        hf_key = os.environ.get("HUGGINGFACE_API_KEY")
    return bool(hf_key)

def main():
    st.set_page_config(
        page_title="Social Media & Website Extractor Dashboard",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
    <style>
        .stApp { background-color: #0e1117; color: white; }
        .main-header { background: linear-gradient(135deg, #1a2a6c, #b21f1f); color: white; padding: 2rem; border-radius: 10px; text-align: center; margin-bottom: 2rem; }
        .platform-card { background-color: #262730; padding: 1.5rem; border-radius: 10px; border-left: 4px solid; margin: 1rem 0; height: 320px; display: flex; flex-direction: column; justify-content: space-between; }
        .linkedin-card { border-left-color: #0077B5; }
        .facebook-card { border-left-color: #1877F2; }
        .facebook-pro-card { border-left-color: #FF6B35; }
        .feature-list { margin: 1rem 0; padding-left: 1.5rem; flex-grow: 1; }
        .status-box { background-color: #1a1a2e; padding: 1rem; border-radius: 5px; margin: 0.5rem 0; min-height: 120px; }
        .pro-badge { background: linear-gradient(45deg, #FF6B35, #FF8E53); color: white; padding: 0.2rem 0.5rem; border-radius: 12px; font-size: 0.8rem; font-weight: bold; margin-left: 0.5rem; }
        .button-container { margin-top: auto; padding-top: 1rem; }
        .status-container { min-height: 180px; display: flex; flex-direction: column; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0;">🔍 Social Media Data Extractor</h1>
        <p style="margin:0; opacity: 0.9;">Developed by [Refat]</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("Choose between LinkedIn and Facebook extractors based on your needs.")

    # API key status
    hf_ok = check_hf_key()
    if hf_ok:
        st.success("🔑 Hugging Face API key found (using Hugging Face for online models).")
    else:
        st.error("⚠️ No Hugging Face API key detected. Add it to Streamlit secrets as `[huggingface] api_key = \"hf_...\"` or set HUGGINGFACE_API_KEY env var.")

    # Initialize session state
    if 'linkedin_port' not in st.session_state:
        st.session_state.linkedin_port = None
    if 'facebook_port' not in st.session_state:
        st.session_state.facebook_port = None
    if 'facebook_pro_port' not in st.session_state:
        st.session_state.facebook_pro_port = None

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
                <li>AI-powered insights (Hugging Face)</li>
            </ul>
            <div class="button-container"></div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 Launch LinkedIn Extractor", key="linkedin_btn", use_container_width=True):
            if os.path.exists("linkdin.py"):
                port = get_available_port(8601)
                st.session_state.linkedin_port = port
                with st.spinner(f"Starting LinkedIn extractor on port {port}..."):
                    run_streamlit_app_in_thread("linkdin.py", port)
                    time.sleep(5)
                    webbrowser.open_new_tab(f"http://localhost:{port}")
                    st.success(f"✅ LinkedIn extractor launched on port {port}!")
                    st.session_state.linkedin_launched = True
            else:
                st.error("❌ linkdin.py file not found!")

    with col2:
        st.markdown("""
        <div class="platform-card facebook-card">
            <h3>📘 Facebook Extractor</h3>
            <ul class="feature-list">
                <li>Manual login required</li>
                <li>Group post extraction</li>
                <li>Works with private groups</li>
                <li>AI conversation analysis (Hugging Face)</li>
            </ul>
            <div class="button-container"></div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 Launch Facebook Extractor", key="facebook_btn", use_container_width=True):
            if os.path.exists("facebook.py"):
                port = get_available_port(8701)
                st.session_state.facebook_port = port
                with st.spinner(f"Starting Facebook extractor on port {port}..."):
                    run_streamlit_app_in_thread("facebook.py", port)
                    time.sleep(5)
                    webbrowser.open_new_tab(f"http://localhost:{port}")
                    st.success(f"✅ Facebook extractor launched on port {port}!")
                    st.session_state.facebook_launched = True
            else:
                st.error("❌ facebook.py file not found!")

    with col3:
        st.markdown("""
        <div class="platform-card facebook-pro-card">
            <h3>🔥 Facebook Extractor 2.0 <span class="pro-badge">PRO</span></h3>
            <ul class="feature-list">
                <li>Enhanced Facebook data extraction</li>
                <li>Faster processing speed</li>
                <li>Advanced AI analysis (Hugging Face)</li>
            </ul>
            <div class="button-container"></div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 Launch Facebook Extractor 2.0", key="facebook_pro_btn", use_container_width=True):
            if os.path.exists("let.py"):
                port = get_available_port(8801)
                st.session_state.facebook_pro_port = port
                with st.spinner(f"Starting Facebook Extractor 2.0 on port {port}..."):
                    run_streamlit_app_in_thread("let.py", port)
                    time.sleep(5)
                    webbrowser.open_new_tab(f"http://localhost:{port}")
                    st.success(f"✅ Facebook Extractor 2.0 launched on port {port}!")
                    st.session_state.facebook_pro_launched = True
            else:
                st.error("❌ let.py file not found!")

    st.markdown("---")
    st.subheader("🔄 Current Status")

    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        st.markdown("### 💼 LinkedIn Extractor")
        if st.session_state.linkedin_port:
            st.markdown(f"""
            <div class="status-container">
                <div class="status-box">
                    ✅ <strong>Running on:</strong> http://localhost:{st.session_state.linkedin_port}<br>
                    📁 <strong>File:</strong> linkdin.py
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 Restart LinkedIn", key="restart_linkedin", use_container_width=True):
                st.session_state.linkedin_port = None
                st.rerun()
        else:
            st.info("💤 Not running - Click launch button to start")

    with status_col2:
        st.markdown("### 📘 Facebook Extractor")
        if st.session_state.facebook_port:
            st.markdown(f"""
            <div class="status-container">
                <div class="status-box">
                    ✅ <strong>Running on:</strong> http://localhost:{st.session_state.facebook_port}<br>
                    📁 <strong>File:</strong> facebook.py
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 Restart Facebook", key="restart_facebook", use_container_width=True):
                st.session_state.facebook_port = None
                st.rerun()
        else:
            st.info("💤 Not running - Click launch button to start")

    with status_col3:
        st.markdown("### 🔥 Facebook Extractor 2.0")
        if st.session_state.facebook_pro_port:
            st.markdown(f"""
            <div class="status-container">
                <div class="status-box">
                    ✅ <strong>Running on:</strong> http://localhost:{st.session_state.facebook_pro_port}<br>
                    📁 <strong>File:</strong> let.py
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 Restart Facebook 2.0", key="restart_facebook_pro", use_container_width=True):
                st.session_state.facebook_pro_port = None
                st.rerun()
        else:
            st.info("💤 Not running - Click launch button to start")

    st.markdown("---")
    st.subheader("🔧 System Check")

    if st.button("Check System Status", use_container_width=True):
        linkedin_exists = os.path.exists("linkdin.py")
        facebook_exists = os.path.exists("facebook.py")
        let_exists = os.path.exists("let.py")
        hf_ok = check_hf_key()

        st.markdown("### 📁 File Status")
        check_col1, check_col2, check_col3 = st.columns(3)
        with check_col1:
            if linkedin_exists:
                st.success("✅ linkdin.py found (LinkedIn extractor)")
            else:
                st.error("❌ linkdin.py not found!")
        with check_col2:
            if facebook_exists:
                st.success("✅ facebook.py found (Facebook extractor)")
            else:
                st.error("❌ facebook.py not found!")
        with check_col3:
            if let_exists:
                st.success("✅ let.py found (Facebook Extractor 2.0)")
            else:
                st.error("❌ let.py not found!")

        st.markdown("### 🤖 Hugging Face Status")
        if hf_ok:
            st.success("✅ Hugging Face API key configured")
        else:
            st.warning("⚠️ Hugging Face API key missing - AI features will not work")

        st.markdown("### 🌐 Port Status")
        dashboard_port = 8501
        st.info(f"Dashboard running on: http://localhost:{dashboard_port}")

        ports_to_check = [8501, 8601, 8701, 8801, 8602, 8702, 8802]
        port_cols = st.columns(3)
        for i, port in enumerate(ports_to_check):
            col_index = i % 3
            with port_cols[col_index]:
                if check_port_in_use(port):
                    st.info(f"Port {port}: 🔴 In use")
                else:
                    st.info(f"Port {port}: 🟢 Available")

    with st.expander("📋 Usage Instructions", expanded=False):
        st.markdown("""
        ## Quick Start Guide

        **1. Start the Dashboard:**
        ```bash
        streamlit run main_dashboard.py
        ```

        **2. Secrets (Hugging Face):**
        Add to Streamlit secrets or env var:
        ```toml
        [huggingface]
        api_key = "hf_your_key_here"
        ```

        **3. Recommended Workflow:**
        - Start the extractor you need from this dashboard.
        - For online deployment, use Hugging Face models (no Ollama required).

        **4. Troubleshooting:**
        - If AI features don't work, check your Hugging Face key.
        - Ensure required .py files exist in the same folder.
        """)

    with st.expander("🔍 Files in Current Directory", expanded=False):
        st.write("**Python files found:**")
        python_files = [f for f in os.listdir('.') if f.endswith('.py')]
        file_cols = st.columns(2)
        for i, file in enumerate(sorted(python_files)):
            col_index = i % 2
            with file_cols[col_index]:
                file_size = os.path.getsize(file)
                status = "✅" if file in ["linkdin.py", "facebook.py", "main_dashboard.py", "let.py"] else "📄"
                st.write(f"{status} {file} ({file_size} bytes)")

if __name__ == "__main__":
    main()

