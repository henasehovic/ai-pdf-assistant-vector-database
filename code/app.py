import streamlit as st
import requests
from streamlit_extras.colored_header import colored_header
import json

# Configuration
FASTAPI_BASE_URL = "http://127.0.0.1:8000"
st.set_page_config(
    page_title="PDF AI Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'

# Custom CSS
st.markdown("""
    <style>
        /* Navbar styles */
        .navbar {
            position: sticky;
            top: 0;
            z-index: 100;
            background-color: #2c3e50;
            padding: 10px 0;
            margin: -10px 0 20px 0;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .nav-link {
            color: white !important;
            padding: 10px 15px;
            text-decoration: none !important;
            font-weight: 500;
            border-radius: 5px;
            margin: 0 5px;
            transition: background-color 0.3s;
        }
        
        .nav-link:hover {
            background-color: #34495e;
        }
        
        .nav-link.active {
            background-color: #3498db;
        }
        
        /* Main content styles */
        .main {
            background-color: #f8f9fa;
        }
        
        .stButton>button {
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
        }
        
        .stTextInput>div>div>input {
            border-radius: 8px;
            padding: 8px 12px;
        }
        
        .stFileUploader>div>div>div>button {
            border-radius: 8px;
            padding: 8px 12px;
        }
        
        .stExpander {
            border-radius: 8px;
            border: 1px solid rgba(49, 51, 63, 0.2);
        }
        
        .success-box {
            padding: 16px;
            background-color: #e6f7e6;
            border-radius: 8px;
            border-left: 4px solid #2ecc71;
            margin-bottom: 16px;
        }
        
        .user-info {
            background-color: #black;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            margin-bottom: 16px;
        }
        
        .auth-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 30px;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            color: black;
            text-align: center;
            font-weight: 900;
            font-size: 20px;
        }
        
        .auth-title {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 30px;
        }
    </style>
""", unsafe_allow_html=True)

def login_page():
    """Display login page"""
    st.markdown('<div class="auth-container"> Welcome to the PDF Sumerizer', unsafe_allow_html=True)
    st.markdown('<h2 class="auth-title">🔐 Login to PDF AI Assistant</h2>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns(2)
        with col1:
            login_button = st.form_submit_button("🚀 Login", use_container_width=True)
        with col2:
            if st.form_submit_button("📝 Register", use_container_width=True):
                st.session_state.current_page = 'register'
                st.rerun()
    
    if login_button:
        if not username or not password:
            st.error("Please fill in all fields")
            return
            
        try:
            response = requests.post(f"{FASTAPI_BASE_URL}/login/", 
                                   json={"username": username, "password": password})
            
            if response.status_code == 200:
                login_data = response.json()
                st.session_state.logged_in = True
                st.session_state.user_data = login_data['user']
                st.success("✅ Login successful!")
                st.balloons()
                st.rerun()
            else:
                error_detail = response.json().get('detail', 'Login failed')
                st.error(f"❌ {error_detail}")
                
        except requests.exceptions.ConnectionError:
            st.error("🔌 Could not connect to the backend service")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def register_page():
    """Display registration page"""
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<h2 class="auth-title">📝 Register for PDF AI Assistant</h2>', unsafe_allow_html=True)
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("First Name*", placeholder="Enter your first name")
            username = st.text_input("Username*", placeholder="Choose a username (3-20 chars)")
            password = st.text_input("Password*", type="password", placeholder="Min 6 characters")
            
        with col2:
            surname = st.text_input("Last Name*", placeholder="Enter your last name")
            email = st.text_input("Email*", placeholder="Enter your email address")
            telephone = st.text_input("Phone (Optional)", placeholder="Enter your phone number")
        
        st.markdown("*Required fields")
        
        col1, col2 = st.columns(2)
        with col1:
            register_button = st.form_submit_button("🎉 Register", use_container_width=True)
        with col2:
            if st.form_submit_button("🔙 Back to Login", use_container_width=True):
                st.session_state.current_page = 'login'
                st.rerun()
    
    if register_button:
        # Validate required fields
        if not all([name, surname, username, email, password]):
            st.error("Please fill in all required fields")
            return
            
        try:
            user_data = {
                "name": name,
                "surname": surname,
                "username": username,
                "email": email,
                "password": password,
                "telephone": telephone if telephone else None
            }
            
            response = requests.post(f"{FASTAPI_BASE_URL}/register/", json=user_data)
            
            if response.status_code == 201:
                st.success("✅ Registration successful! You can now login.")
                st.balloons()
                st.session_state.current_page = 'login'
                st.rerun()
            else:
                error_detail = response.json().get('detail', 'Registration failed')
                st.error(f"❌ {error_detail}")
                
        except requests.exceptions.ConnectionError:
            st.error("🔌 Could not connect to the backend service")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def main_app():
    """Main PDF AI Assistant application"""
    
    # User info in sidebar
    with st.sidebar:
        st.markdown(
            f'<div class="user-info">'
            f'<strong>👤 Welcome, {st.session_state.user_data["name"]} {st.session_state.user_data["surname"]}!</strong><br>'
            f'<small>Username: {st.session_state.user_data["username"]}</small><br>'
            f'<small>Email: {st.session_state.user_data["email"]}</small>'
            f'</div>', 
            unsafe_allow_html=True
        )
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_data = None
            st.session_state.current_page = 'login'
            st.rerun()
        
        st.image("https://cdn-icons-png.flaticon.com/512/337/337946.png", 
                 width=150,
                 caption="PDF AI Assistant")
        st.title("PDF AI Assistant")
        st.markdown("""
        **Instructions:**
        1. Upload your PDF document
        2. Choose an analysis option
        3. Get insights from your document
        """)
        st.markdown("---")
        st.markdown("Built using Streamlit, FastAPI, and Gemini")

    # Navbar
    st.markdown("""
        <div class="navbar">
            <center>
                <a href="#upload-your-pdf" class="nav-link">📤 Upload PDF</a>
                <a href="#document-summary" class="nav-link">📝 Full Summary</a>
                <a href="#topic-analysis" class="nav-link">🔎 Topic Analysis</a>
                <a href="#ask-question" class="nav-link">❓ Ask Question</a>
                <a href="#database-inspection" class="nav-link">🔍 Database</a>
            </center>
        </div>
    """, unsafe_allow_html=True)

    # Main Content
    st.markdown('<a id="upload-your-pdf"></a>', unsafe_allow_html=True)
    colored_header(
        label="📤 1. Upload Your PDF",
        description="",
        color_name="blue-70"
    )
    uploaded_file = st.file_uploader(
        "Choose a PDF file", 
        type="pdf", 
        key="pdf_uploader",
        help="Upload the PDF you want to analyze"
    )

    if uploaded_file:
        if st.button("✨ Process PDF", key="process_pdf_button"):
            with st.spinner("Processing your PDF... This may take a moment"):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                try:
                    response = requests.post(f"{FASTAPI_BASE_URL}/upload-and-process-pdf/", files=files)
                    if response.status_code == 200:
                        st.success("✅ PDF processed successfully!")
                        st.balloons()
                        with st.expander("View Processing Details"):
                            st.json(response.json())
                    else:
                        st.error(f"Error processing PDF: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Could not connect to the backend service")

    st.divider()

    # Document Summary
    st.markdown('<a id="document-summary"></a>', unsafe_allow_html=True)
    colored_header(
        label="📝 2. Document Summary",
        description="Get a comprehensive summary of the entire document",
        color_name="blue-70"
    )

    if st.button("🔍 Generate Full Summary", key="full_summary_button"):
        with st.spinner("Generating summary... Please wait"):
            try:
                response = requests.post(f"{FASTAPI_BASE_URL}/summarize-pdf/")
                if response.status_code == 200:
                    summary_data = response.json()
                    with st.container(border=True):
                        st.markdown("### 📋 Summary")
                        st.write(summary_data.get("summary", "No summary available."))
                        st.caption(f"Summarized from {summary_data.get('summarized_chunks_count', 0)} document sections")
                elif response.status_code == 404:
                    st.warning("No PDF found. Please upload a PDF first")
                else:
                    st.error(f"Error generating summary: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Could not connect to the backend service")

    st.divider()

    # Topic Analysis
    st.markdown('<a id="topic-analysis"></a>', unsafe_allow_html=True)
    colored_header(
        label="🔎 3. Topic Analysis",
        description="Get insights about specific topics within your document",
        color_name="blue-70"
    )

    topic_query = st.text_input(
        "Enter a topic or question:", 
        key="topic_query_input",
        placeholder="e.g., 'What are the key findings?'"
    )

    if st.button("🧠 Analyze Topic", key="topic_summary_button"):
        if topic_query:
            with st.spinner(f"Analyzing topic: '{topic_query}'..."):
                try:
                    response = requests.post(f"{FASTAPI_BASE_URL}/summarize-topic/", json={"topic_query": topic_query})
                    if response.status_code == 200:
                        summary_data = response.json()
                        with st.container(border=True):
                            st.markdown(f"### 📌 Analysis of: '{topic_query}'")
                            st.write(summary_data.get("summary", "No summary available."))
                            
                            st.markdown("#### 📚 Relevant Sections")
                            if summary_data.get('retrieved_chunks_info'):
                                for chunk_info in summary_data['retrieved_chunks_info']:
                                    with st.expander(f"📄 Page {chunk_info['metadata'].get('page_number', 'N/A')}"):
                                        st.write(chunk_info['chunk_preview'])
                            else:
                                st.write("No specific sections were used for this analysis.")
                    elif response.status_code == 404:
                        st.warning("No relevant content found for this topic")
                    else:
                        st.error(f"Error generating topic analysis: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Could not connect to the backend service")
        else:
            st.warning("Please enter a topic to analyze")

    st.divider()

    # Question Answering
    st.markdown('<a id="ask-question"></a>', unsafe_allow_html=True)
    colored_header(
        label="❓ 4. Ask a Question",
        description="Get precise answers about your document's content",
        color_name="blue-70"
    )

    question_input = st.text_input(
        "Enter your question:", 
        key="qa_question_input",
        placeholder="e.g., 'What is the main conclusion?'"
    )

    if st.button("💡 Get Answer", key="get_answer_button"):
        if question_input:
            with st.spinner(f"Finding answer to: '{question_input}'..."):
                try:
                    response = requests.post(f"{FASTAPI_BASE_URL}/ask-pdf/", json={"question": question_input})
                    if response.status_code == 200:
                        answer_data = response.json()
                        with st.container(border=True):
                            st.markdown("### 💬 Answer")
                            st.write(answer_data.get("answer", "No answer available."))
                            
                            st.markdown("#### 📖 Supporting Content")
                            if answer_data.get('retrieved_chunks_info'):
                                for chunk_info in answer_data['retrieved_chunks_info']:
                                    with st.expander(f"📄 Page {chunk_info['metadata'].get('page_number', 'N/A')}"):
                                        st.write(chunk_info['chunk_preview'])
                            else:
                                st.write("No specific content was used for this answer.")
                    elif response.status_code == 400:
                        st.error(f"Input error: {response.json().get('detail', 'Please provide a valid question.')}")
                    elif response.status_code == 404:
                        st.warning(f"Information not found: {response.json().get('detail', 'No relevant content found.')}")
                    else:
                        st.error(f"Error getting answer: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Could not connect to the backend service")
        else:
            st.warning("Please enter a question")

    st.divider()

    # Database Inspection
    st.markdown('<a id="database-inspection"></a>', unsafe_allow_html=True)
    colored_header(
        label="🔍 5. Database Inspection",
        description="View the stored document chunks and metadata",
        color_name="blue-70"
    )

    if st.button("🛠️ Inspect Database", key="inspect_db_button"):
        with st.spinner("Retrieving database information..."):
            try:
                response = requests.get(f"{FASTAPI_BASE_URL}/inspect-db-collection/")
                if response.status_code == 200:
                    db_info = response.json()
                    with st.container(border=True):
                        st.metric("Total Document Chunks", db_info.get("total_items_in_collection", 0))
                        
                        st.markdown("#### Sample Chunks")
                        if db_info.get('sample_documents'):
                            for doc in db_info['sample_documents']:
                                with st.expander(f"📄 ID: {doc.get('id')} (Page {doc['metadata'].get('page_number', 'N/A')})"):
                                    st.write(doc.get('document_preview'))
                        else:
                            st.write("No documents found in the database.")
                else:
                    st.error(f"Error inspecting database: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Could not connect to the backend service")

    # Footer
    st.markdown("---")
    st.caption("© 2024 PDF AI Assistant | Built with Streamlit, FastAPI, and Google Gemini")

# Main App Logic
def main():
    """Main application controller"""
    
    # Show login/register pages if not logged in
    if not st.session_state.logged_in:
        if st.session_state.current_page == 'login':
            login_page()
        elif st.session_state.current_page == 'register':
            register_page()
    else:
        # Show main application if logged in
        main_app()

if __name__ == "__main__":
    main()