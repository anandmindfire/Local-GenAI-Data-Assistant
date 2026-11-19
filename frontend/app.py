"""Streamlit presentation layer for Local GenAI Data Assistant.

Communicates with the FastAPI backend exclusively over HTTP REST.
Maintains clean separation of concerns: no agent logic in frontend callbacks.
"""

import os
import uuid

import httpx
import pandas as pd
import streamlit as st

# Configure Page
st.set_page_config(
    page_title="Local GenAI Data Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API Base URL from environment (defaults to local docker port)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")


def init_session_state() -> None:
    """Initialize session state variables for chat history and session tracking."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:16]}"


init_session_state()


def fetch_health_status() -> dict:
    """Fetch backend readiness probe."""
    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.get(f"{API_BASE_URL}/health")
            if resp.status_code == 200:
                return resp.json()
            return {"status": "degraded", "dependencies": {}}
    except Exception as e:
        return {"status": "unreachable", "error": str(e), "dependencies": {}}


def fetch_documents() -> list[dict]:
    """Fetch list of indexed documents."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{API_BASE_URL}/documents?page=1&page_size=50")
            if resp.status_code == 200:
                return resp.json().get("items", [])
            return []
    except Exception:
        return []


def upload_document(file) -> dict:
    """Upload and ingest a document via the FastAPI backend."""
    try:
        files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{API_BASE_URL}/documents/ingest", files=files)
            return resp.json()
    except Exception as e:
        return {"success": False, "error": {"message": str(e)}}


def send_chat_message(message: str, conversation_id: str) -> dict:
    """Send natural language query to FastAPI /chat orchestrator."""
    payload = {"message": message, "conversation_id": conversation_id}
    with httpx.Client(timeout=600.0) as client:
        resp = client.post(f"{API_BASE_URL}/chat", json=payload)
        return resp.json()


# ==============================================================================
# SIDEBAR: System Status, Document Management & Controls
# ==============================================================================
with st.sidebar:
    st.title("🤖 Local Data Assistant")
    st.caption("Privacy-First RAG & NL2SQL Assistant")

    st.divider()

    # Session Controls
    st.subheader("💬 Session")
    st.write(f"**ID:** `{st.session_state.conversation_id}`")
    if st.button("➕ New Conversation", width="stretch"):
        st.session_state.messages = []
        st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:16]}"
        st.rerun()

    st.divider()

    # Backend Health Probe
    st.subheader("🔌 System Status")
    health = fetch_health_status()
    if health.get("status") == "ok":
        st.success("● Backend Online (Healthy)")
        deps = health.get("dependencies", {})
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Database", "Ready" if deps.get("database") else "Down")
            st.metric("Ollama LLM", "Ready" if deps.get("ollama") else "Down")
        with col2:
            st.metric("Qdrant", "Ready" if deps.get("qdrant") else "Down")
            st.metric("Embedding", "Ready" if deps.get("embedding_model_available") else "Missing")
    else:
        st.error(f"● Backend Disconnected ({health.get('status', 'Offline')})")
        if "error" in health:
            st.caption(health["error"])

    st.divider()

    # Document Upload Section
    st.subheader("📄 Upload Document")
    uploaded_file = st.file_uploader(
        "Supported formats: PDF, DOCX, TXT, MD",
        type=["pdf", "docx", "txt", "md"],
        help="Upload enterprise policies or guides to index into Qdrant",
    )
    if uploaded_file is not None:
        if st.button("Index Document", type="primary", width="stretch"):
            with st.spinner(f"Ingesting '{uploaded_file.name}' into vector database..."):
                res = upload_document(uploaded_file)
                if res.get("status") in ("created", "skipped"):
                    st.success(f"{res.get('message', 'Document indexed successfully.')}")
                    st.rerun()
                else:
                    err_msg = res.get("error", {}).get("message", "Ingestion failed.")
                    st.error(f"Error: {err_msg}")

    # Indexed Documents List
    st.subheader("📚 Indexed Documents")
    docs = fetch_documents()
    if docs:
        for doc in docs:
            st.caption(
                f"• **{doc['filename']}** ({doc['chunk_count']} chunks, {doc['file_type'].upper()})"
            )
    else:
        st.caption("No documents indexed yet.")

    st.divider()

    # Quick Prompt Examples
    st.subheader("💡 Example Prompts")
    example_prompts = [
        "What is the company annual leave policy?",
        "Which are the top five customers by revenue?",
        "What is our customer refund policy, and how much was refunded in total?",
        "Which products have stock below 10?",
    ]
    for prompt in example_prompts:
        if st.button(prompt, key=f"ex_{prompt[:15]}", width="stretch"):
            st.session_state.pending_prompt = prompt
            st.rerun()


# ==============================================================================
# MAIN VIEW: Conversational Interface
# ==============================================================================
st.title("Local GenAI Data Assistant")
st.markdown(
    "Interact with unstructured enterprise documents and structured PostgreSQL databases seamlessly using local models."
)

# Display Existing Chat Messages
for msg in st.session_state.messages:
    role = msg["role"]
    with st.chat_message(role):
        st.markdown(msg["content"])

        # Display rich artifacts for assistant messages
        if role == "assistant":
            # Display Intent Badge
            intent = msg.get("intent")
            if intent == "document":
                st.caption("🏷️ **Intent: Document RAG**")
            elif intent == "sql":
                st.caption("🏷️ **Intent: Relational Database SQL**")
            elif intent == "combined":
                st.caption("🏷️ **Intent: Multi-Source Parallel (RAG + SQL)**")

            # Display SQL Results Table
            sql_results = msg.get("sql_results")
            if sql_results and isinstance(sql_results, list) and len(sql_results) > 0:
                with st.expander(
                    f"📊 Relational SQL Results ({len(sql_results)} rows)", expanded=True
                ):
                    df = pd.DataFrame(sql_results)
                    st.dataframe(df, width="stretch")

            # Display Source References
            sources = msg.get("sources")
            if sources and isinstance(sources, list) and len(sources) > 0:
                with st.expander(
                    f"📑 Referenced Document Sources ({len(sources)} citations)", expanded=False
                ):
                    for i, src in enumerate(sources, 1):
                        filename = src.get("filename", "Unknown")
                        page = src.get("page_number")
                        page_str = f", Page {page}" if page else ""
                        score = src.get("score")
                        score_str = f" (Relevance: {score:.2f})" if score else ""
                        st.markdown(f"**[{i}] {filename}**{page_str}{score_str}")

            # Display Technical Execution Metadata
            metadata = msg.get("execution_metadata", {})
            if metadata:
                with st.expander("⚙️ Execution Metadata & Audit", expanded=False):
                    sql_duration = metadata.get("sql_duration_ms")
                    if sql_duration:
                        st.write(f"• **Database Query Execution Time:** `{sql_duration:.2f} ms`")
                    rag_conf = metadata.get("rag_confidence")
                    if rag_conf:
                        st.write(f"• **RAG Confidence:** `{rag_conf}`")


# Handle Prompt Input (either from chat_input or pre-selected example prompt)
user_prompt = st.chat_input(
    "Ask a question about company policies, customers, orders, or products..."
)
if "pending_prompt" in st.session_state and st.session_state.pending_prompt:
    user_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_prompt:
    # 1. Render & Save User Message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Render Assistant Response with Execution Status
    with st.chat_message("assistant"):
        with st.status("Executing workflow with local models...", expanded=True) as status:
            st.write("🔍 Analyzing query intent & executing local pipeline...")
            try:
                response_data = send_chat_message(
                    message=user_prompt,
                    conversation_id=st.session_state.conversation_id,
                )

                if not response_data.get("answer"):
                    err = response_data.get("error", {}).get("message", "Unknown error occurred.")
                    status.update(label="Workflow failed", state="error", expanded=False)
                    st.error(f"Error: {err}")
                else:
                    detected_intent = response_data.get("intent", "general")
                    if detected_intent == "document":
                        status.update(
                            label="Document RAG query completed", state="complete", expanded=False
                        )
                    elif detected_intent == "sql":
                        status.update(
                            label="SQL Agent query completed", state="complete", expanded=False
                        )
                    elif detected_intent == "combined":
                        status.update(
                            label="Parallel multi-source query completed",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        status.update(label="Response generated", state="complete", expanded=False)

                    # Display Answer
                    answer = response_data.get("answer", "")
                    st.markdown(answer)

                    # Display Intent Badge
                    if detected_intent == "document":
                        st.caption("🏷️ **Intent: Document RAG**")
                    elif detected_intent == "sql":
                        st.caption("🏷️ **Intent: Relational Database SQL**")
                    elif detected_intent == "combined":
                        st.caption("🏷️ **Intent: Multi-Source Parallel (RAG + SQL)**")

                    # Display SQL Results Table
                    sql_results = response_data.get("sql_results")
                    if sql_results and isinstance(sql_results, list) and len(sql_results) > 0:
                        with st.expander(
                            f"📊 Relational SQL Results ({len(sql_results)} rows)", expanded=True
                        ):
                            df = pd.DataFrame(sql_results)
                            st.dataframe(df, width="stretch")

                    # Display Sources
                    sources = response_data.get("sources")
                    if sources and isinstance(sources, list) and len(sources) > 0:
                        with st.expander(
                            f"📑 Referenced Document Sources ({len(sources)} citations)",
                            expanded=False,
                        ):
                            for i, src in enumerate(sources, 1):
                                filename = src.get("filename", "Unknown")
                                page = src.get("page_number")
                                page_str = f", Page {page}" if page else ""
                                score = src.get("score")
                                score_str = f" (Relevance: {score:.2f})" if score else ""
                                st.markdown(f"**[{i}] {filename}**{page_str}{score_str}")

                    # Display Metadata
                    metadata = response_data.get("execution_metadata", {})
                    if metadata:
                        with st.expander("⚙️ Execution Metadata & Audit", expanded=False):
                            sql_duration = metadata.get("sql_duration_ms")
                            if sql_duration:
                                st.write(
                                    f"• **Database Query Execution Time:** `{sql_duration:.2f} ms`"
                                )
                            rag_conf = metadata.get("rag_confidence")
                            if rag_conf:
                                st.write(f"• **RAG Confidence:** `{rag_conf}`")

                    # Save assistant message to session state
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "intent": detected_intent,
                            "sql_results": sql_results,
                            "sources": sources,
                            "execution_metadata": metadata,
                        }
                    )

            except Exception as e:
                status.update(label="Connection error", state="error", expanded=False)
                st.error(f"Failed to communicate with FastAPI backend: {e}")
