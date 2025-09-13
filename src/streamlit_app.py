import os
import sys
import json
from typing import List, Dict, Any

import streamlit as st
import re

# Optional deps used by dashboard table; app works without them
try:
    import pandas as pd  # noqa: F401
except Exception:
    pd = None  # type: ignore

# Ensure imports work whether launched from repo root or backend dir
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Backend imports
from pipeline.classifier import classify_ticket
from pipeline.rag import RAGPipeline


# ------------------------
# Page setup and utilities
# ------------------------
st.set_page_config(
    page_title="Atlan AI Support Copilot",
    page_icon="🤖",
    layout="wide",
)


PRIMARY_TAGS_DIRECT_ANSWER = {"How-to", "Product", "Best practices", "API/SDK", "SSO"}


def load_classified_tickets() -> List[Dict[str, Any]]:
    data_path = os.path.join(os.path.dirname(__file__), "data", "classified_tickets.json")
    if not os.path.exists(data_path):
        return []
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_classified_tickets(tickets: List[Dict[str, Any]]) -> bool:
    data_path = os.path.join(os.path.dirname(__file__), "data", "classified_tickets.json")
    try:
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def sentiment_to_icon_text(sentiment: str) -> str:
    s = (sentiment or "").strip().lower()
    mapping = {
        "angry": "😠 Angry",
        "frustrated": "😟 Frustrated",
        "curious": "🤔 Curious",
        "neutral": "😐 Neutral",
        "positive": "🙂 Positive",
    }
    return mapping.get(s, sentiment or "Unknown")


def priority_to_color(priority: str) -> str:
    p = (priority or "").lower()
    if p.startswith("p0"):
        return "#ef4444"  # red
    if p.startswith("p1"):
        return "#f59e0b"  # orange
    return "#6b7280"  # gray for P2/unknown


def render_badge(text: str, bg: str = "#eef2ff", fg: str = "#4338ca") -> str:
    return (
        f'<span style="display:inline-block;padding:4px 10px;border-radius:9999px;'
        f'background:{bg};color:{fg};font-size:12px;margin-right:6px;margin-bottom:6px;">{text}</span>'
    )


def render_priority_badge(priority: str) -> str:
    color = priority_to_color(priority)
    fg = "#111827"
    return (
        f'<span style="display:inline-block;padding:4px 10px;border-radius:8px;'
        f'background:{color};color:white;font-weight:600;font-size:12px;">{priority}</span>'
    )


def render_card(title: str, body_md: str) -> None:
    st.markdown(
        f"""
        <div style='border:1px solid #e5e7eb;border-radius:12px;padding:16px;background:white;'>
            <div style='font-weight:700;font-size:16px;margin-bottom:8px;color:#111827;'>{title}</div>
            <div style='color:#111827;'>
                {body_md}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def strip_sources_from_answer(answer_text: str) -> str:
    """Remove any embedded Sources sections from an LLM answer to avoid duplication."""
    if not answer_text:
        return ""
    # Common markers for sources sections
    markers = ["\nSources:", "\nSource:", "\n**Sources:**", "\n**Source:**", "\n📚 Sources:"]
    cut_idx = None
    for m in markers:
        idx = answer_text.lower().find(m.lower())
        if idx != -1:
            cut_idx = idx
            break
    return answer_text[:cut_idx].rstrip() if cut_idx is not None else answer_text


def format_answer_points(answer_text: str) -> str:
    """Render answer as a bold summary followed by clean bullet points, removing stray markdown."""
    cleaned = strip_sources_from_answer(answer_text or "")

    def sanitize_line(text: str) -> str:
        # Remove markdown bullets and leading symbols
        text = re.sub(r"^\s*([*\-•]+)\s+", "", text)
        # Remove markdown emphasis (bold/italic)
        text = re.sub(r"\*\*|__|\*", "", text)
        # Remove backticks
        text = text.replace("`", "")
        # Trim enclosing quotes only (not inner apostrophes)
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        return text.strip()

    lines_raw = [ln for ln in cleaned.splitlines() if ln.strip()]
    lines = [sanitize_line(ln.strip()) for ln in lines_raw if sanitize_line(ln.strip())]
    if not lines:
        return ""
    summary = lines[0]
    bullets = lines[1:]
    bullets_html = ""
    if bullets:
        items = "".join([f"<li style='margin:6px 0;line-height:1.5;'>{ln}</li>" for ln in bullets])
        bullets_html = f"<ul style='margin:6px 0 0 18px;padding:0;'>{items}</ul>"
    return f"<div style='font-weight:600;margin-bottom:4px;'>{summary}</div>{bullets_html}"


# ------------------------
# Title
# ------------------------
st.markdown(
    """
    <div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>
        <span style='font-size:28px;'>🤖</span>
        <h1 style='margin:0;font-size:28px;color:#2563eb;'>Atlan AI Support Copilot</h1>
    </div>
    <div style='color:#4b5563;margin-top:-8px;margin-bottom:16px;'>Clean, modern internal helpdesk assistant</div>
    """,
    unsafe_allow_html=True,
)

tab_dashboard, tab_agent = st.tabs(["Bulk Classification Dashboard", "Interactive AI Agent"])


# ------------------------
# Bulk Classification Dashboard
# ------------------------
with tab_dashboard:
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # Quick add/classify a new ticket into the dataset
    with st.expander("Add and Classify a New Ticket"):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            new_subject = st.text_input("Ticket Subject", placeholder="Connecting Snowflake to Atlan - required permissions?")
        with col_b:
            new_id = st.text_input("Ticket ID (optional)", placeholder="TCK-1001")
        new_body = st.text_area("Ticket Body", placeholder="Provide steps, errors, or details here...", height=120)
        submit_new = st.button("Classify and Add to Dashboard")
        if submit_new and new_subject.strip() and new_body.strip():
            # Classify and append
            result = classify_ticket(new_body.strip())
            if "error" in result:
                st.error(f"Classification failed: {result['error']}")
            else:
                tickets_existing = load_classified_tickets()
                # Create a simple numeric id if not provided
                assigned_id = new_id.strip() if new_id.strip() else str(len(tickets_existing) + 1)
                new_ticket = {
                    "id": assigned_id,
                    "subject": new_subject.strip(),
                    "body": new_body.strip(),
                    "classification": result,
                }
                tickets_existing.append(new_ticket)
                if save_classified_tickets(tickets_existing):
                    st.success("Ticket classified and added to the dashboard.")
                else:
                    st.error("Failed to save the updated tickets file.")

    tickets = load_classified_tickets()
    # Filters row
    if tickets:
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        with col_f1:
            filter_id = st.text_input("Filter by ID", placeholder="TICKET-245 or 12")
        with col_f2:
            filter_sentiment = st.selectbox(
                "Filter by Sentiment",
                options=["All", "Angry", "Frustrated", "Curious", "Neutral", "Positive"],
                index=0,
            )
        with col_f3:
            filter_priority = st.selectbox(
                "Filter by Priority",
                options=["All", "P0 (High)", "P1 (Medium)", "P2 (Low)"],
                index=0,
            )

        def match_filters(ticket: Dict[str, Any]) -> bool:
            tid = str(ticket.get("id") or ticket.get("ticket_id") or "")
            classification = ticket.get("classification", {}) or {}
            sentiment = str(classification.get("sentiment", ""))
            priority = str(classification.get("priority", ""))

            ok_id = True
            if filter_id.strip():
                ok_id = filter_id.strip().lower() in tid.lower()

            ok_sent = True
            if filter_sentiment != "All":
                ok_sent = sentiment.lower() == filter_sentiment.lower()

            ok_pri = True
            if filter_priority != "All":
                ok_pri = priority.lower().startswith(filter_priority.split()[0].lower())

            return ok_id and ok_sent and ok_pri

        tickets = [t for t in tickets if match_filters(t)]
    if not tickets:
        st.info("No pre-analyzed tickets found. Generate `data/classified_tickets.json` to populate this dashboard.")
    else:
        for t in tickets:
            ticket_id = t.get("id") or t.get("ticket_id") or t.get("Ticket ID") or ""
            subject = t.get("subject") or t.get("title") or t.get("Ticket Subject") or "Untitled Ticket"
            body_text = t.get("body") or t.get("description") or ""
            classification = t.get("classification", {}) or {}
            topic_tags = classification.get("topic_tags", []) or []
            sentiment = classification.get("sentiment", "")
            priority = classification.get("priority", "")

            # If no ID present, try to extract mentioned ID like TICKET-245 from subject/body
            if not ticket_id:
                m = re.search(r"\b[A-Z]{2,}-\d+\b", f"{subject}\n{body_text}")
                ticket_id = m.group(0) if m else "—"

            badges_html = "".join([render_badge(str(tag)) for tag in topic_tags])
            sentiment_text = sentiment_to_icon_text(sentiment)
            priority_html = render_priority_badge(priority or "P2 (Low)")

            body = (
                f"<div style='display:flex;flex-direction:column;gap:8px;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<div style='font-weight:600;font-size:15px;'>{subject}</div>"
                f"<div style='font-size:12px;color:#6b7280;'>ID: {ticket_id}</div>"
                f"</div>"
                f"<div>{badges_html}</div>"
                f"<div style='white-space:pre-wrap;color:#374151;background:#f9fafb;border:1px solid #e5e7eb;padding:10px;border-radius:8px;'>"
                f"{body_text}"
                f"</div>"
                f"<div style='display:flex;gap:16px;align-items:center;color:#374151;'>"
                f"<span><strong>Sentiment:</strong> {sentiment_text}</span>"
                f"<span><strong>Priority:</strong> {priority_html}</span>"
                f"</div>"
                f"</div>"
            )
            render_card("Ticket", body)
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)


# ------------------------
# Interactive AI Agent
# ------------------------
with tab_agent:
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # Input Area
    col_ch, col_btn = st.columns([4, 1])
    with col_ch:
        channel = st.selectbox(
            "Channel",
            options=["Email", "WhatsApp", "Voice", "Live chat", "Other"],
            index=0,
        )
    with col_btn:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        # placeholder to align button
    user_input = st.text_area(
        label="New ticket or question",
        placeholder="Submit a new ticket or ask a question...",
        height=160,
        label_visibility="collapsed",
    )
    analyze = st.button("Analyze and Respond", type="primary")

    if analyze and user_input.strip():
        with st.spinner("Analyzing ticket and preparing response..."):
            classification = classify_ticket(user_input.strip())

        # Internal Analysis Card
        if "error" in classification:
            render_card("Internal AI Analysis", f"<div style='color:#b91c1c;'>Error: {classification['error']}</div>")
        else:
            topic_tags = classification.get("topic_tags", []) or []
            sentiment = classification.get("sentiment", "")
            priority = classification.get("priority", "")

            badges_html = "".join([render_badge(str(tag)) for tag in topic_tags])
            sentiment_text = sentiment_to_icon_text(sentiment)
            priority_html = render_priority_badge(priority or "P2 (Low)")

            internal_md = (
                f"<div style='display:flex;flex-direction:column;gap:8px;'>"
                f"<div style='color:#6b7280;font-size:12px;'>Channel: {channel}</div>"
                f"<div><strong>Topic Tags:</strong> {badges_html}</div>"
                f"<div><strong>Sentiment:</strong> {sentiment_text}</div>"
                f"<div><strong>Priority:</strong> {priority_html}</div>"
                f"</div>"
            )
            render_card("Internal AI Analysis", internal_md)

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # Final Response Card
        if "error" in classification:
            render_card("Generated Response for Customer", "We couldn't analyze this ticket right now. Please try again later.")
        else:
            topic_tags_upper = {str(t).strip() for t in classification.get("topic_tags", [])}
            should_answer_directly = any(tag in PRIMARY_TAGS_DIRECT_ANSWER for tag in topic_tags_upper)

            if should_answer_directly:
                try:
                    if "rag_pipeline" not in st.session_state:
                        st.session_state["rag_pipeline"] = RAGPipeline()
                    rag = st.session_state["rag_pipeline"]
                    with st.spinner("Generating answer with knowledge base..."):
                        # Slight hinting by appending preferred domains into the query for retrieval bias
                        hint = " Prefer official documentation from docs.atlan.com and developer.atlan.com."
                        rag_result = rag.get_rag_answer(user_input.strip() + hint)
                except Exception as e:
                    rag_result = {"error": f"RAG pipeline error: {str(e)}"}

                if "error" in rag_result:
                    render_card(
                        "Generated Response for Customer",
                        f"<div style='color:#b91c1c;'>Unable to generate an answer. {rag_result['error']}</div>",
                    )
                else:
                    answer_text = rag_result.get("answer", "")
                    sources = rag_result.get("sources", []) or []

                    structured_answer = format_answer_points(answer_text)

                    sources_html = ""
                    if sources:
                        items = "".join([f"<li style='margin:4px 0;'><a href='{s}' target='_blank' rel='noopener noreferrer'>{s}</a></li>" for s in sources])
                        sources_html = f"<div style='margin-top:8px;'><strong>📚 Sources:</strong><ol style='margin:6px 0 0 18px;'>{items}</ol></div>"

                    render_card(
                        "Generated Response for Customer",
                        f"<div>{structured_answer}</div>{sources_html}",
                    )
            else:
                routed_topic = next(iter(topic_tags_upper), "General")
                routing_msg = (
                    f"This ticket has been classified as a '{routed_topic}' issue and has been routed to the appropriate team."
                )
                render_card("Generated Response for Customer", routing_msg)


