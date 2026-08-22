import json
import uuid
from typing import Any, Dict, Iterator, Optional, Tuple

import requests
import streamlit as st

from core.config import config


# ============================================================
# Streamlit configuration
# ============================================================

st.set_page_config(
    page_title="E-commerce Assistant",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Constants
# ============================================================

REQUEST_TIMEOUT = 60
STREAM_TIMEOUT = (10, 300)


# ============================================================
# Session state helpers
# ============================================================

def initialize_session_state() -> None:
    """Initialize all Streamlit session-state values."""

    defaults = {
        "session_id": str(uuid.uuid4()),
        "messages": [
            {
                "role": "assistant",
                "content": "Hello! How can I assist you today?",
            }
        ],
        "used_context": [],
        "latest_feedback": None,
        "show_feedback_box": False,
        "feedback_submission_status": None,
        "trace_id": None,
        "shopping_cart": [],
        "error_popup": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session_state()

session_id = st.session_state.session_id


# ============================================================
# Error handling
# ============================================================

def show_error_popup(message: str) -> None:
    """Store an error that can be displayed by the UI."""
    st.session_state.error_popup = {
        "visible": True,
        "message": message,
    }


def display_error_popup() -> None:
    """Display and clear the current error popup."""
    popup = st.session_state.get("error_popup")

    if popup and popup.get("visible"):
        st.error(popup.get("message", "An unexpected error occurred."))

        st.session_state.error_popup = None


# ============================================================
# Normal API call
# ============================================================

def api_call(
    method: str,
    url: str,
    **kwargs: Any,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Make a normal HTTP API request.

    Returns:
        (success, response_data)
    """

    kwargs.setdefault("timeout", REQUEST_TIMEOUT)

    try:
        response = requests.request(
            method=method,
            url=url,
            **kwargs,
        )

        try:
            response_data = response.json()
        except ValueError:
            response_data = {
                "message": response.text or "Invalid response format from server"
            }

        if response.ok:
            return True, response_data

        message = (
            response_data.get("message")
            if isinstance(response_data, dict)
            else None
        )

        show_error_popup(
            message
            or f"API request failed with HTTP {response.status_code}."
        )

        return False, (
            response_data
            if isinstance(response_data, dict)
            else {"message": str(response_data)}
        )

    except requests.exceptions.ConnectionError:
        message = "Connection error. Please check your network connection."
        show_error_popup(message)
        return False, {"message": message}

    except requests.exceptions.Timeout:
        message = "The request timed out. Please try again later."
        show_error_popup(message)
        return False, {"message": message}

    except requests.exceptions.RequestException as exc:
        message = f"Request failed: {exc}"
        show_error_popup(message)
        return False, {"message": message}

    except Exception as exc:
        message = f"An unexpected error occurred: {exc}"
        show_error_popup(message)
        return False, {"message": message}


# ============================================================
# Streaming API call
# ============================================================

def api_call_stream(
    method: str,
    url: str,
    **kwargs: Any,
) -> Iterator[str]:
    """
    Make a streaming HTTP request and yield decoded SSE lines.

    The caller receives strings rather than bytes.
    """

    kwargs.setdefault("timeout", STREAM_TIMEOUT)
    kwargs["stream"] = True

    response: Optional[requests.Response] = None

    try:
        response = requests.request(
            method=method,
            url=url,
            **kwargs,
        )

        if not response.ok:
            try:
                response_data = response.json()

                if isinstance(response_data, dict):
                    message = response_data.get(
                        "message",
                        f"Streaming request failed with HTTP {response.status_code}.",
                    )
                else:
                    message = str(response_data)

            except ValueError:
                message = (
                    response.text
                    or f"Streaming request failed with HTTP {response.status_code}."
                )

            show_error_popup(message)
            return

        for line in response.iter_lines(decode_unicode=True):
            if line is None:
                continue

            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="replace")

            yield line

    except requests.exceptions.ConnectionError:
        message = "Connection error. Please check your network connection."
        show_error_popup(message)

    except requests.exceptions.Timeout:
        message = "The streaming request timed out. Please try again later."
        show_error_popup(message)

    except requests.exceptions.RequestException as exc:
        message = f"Streaming request failed: {exc}"
        show_error_popup(message)

    except Exception as exc:
        message = f"An unexpected streaming error occurred: {exc}"
        show_error_popup(message)

    finally:
        if response is not None:
            response.close()


# ============================================================
# SSE helpers
# ============================================================

def parse_sse_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse one Server-Sent Events data line.

    Returns:
        Parsed JSON object or None.
    """

    if not line:
        return None

    line = line.strip()

    # Ignore SSE comments / keep-alive messages.
    if not line or line.startswith(":"):
        return None

    if not line.startswith("data:"):
        return None

    data = line[len("data:"):].strip()

    if not data:
        return None

    try:
        parsed = json.loads(data)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        # Some servers may send plain-text SSE data.
        return {
            "type": "text",
            "data": data,
        }

    return None


# ============================================================
# Response extraction
# ============================================================

def extract_final_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize the final-result API payload."""

    return {
        "answer": data.get(
            "answer",
            "The assistant did not return an answer.",
        ),
        "used_context": data.get(
            "used_context",
            [],
        ) or [],
        "trace_id": data.get(
            "trace_id",
        ),
        # Support both names used by the original code.
        "shopping_cart": data.get(
            "shopping_cart_items",
            data.get("shopping_cart", []),
        ) or [],
    }


# ============================================================
# Feedback
# ============================================================

def feedback_score(feedback_type: Optional[str]) -> Optional[int]:
    if feedback_type == "positive":
        return 1

    if feedback_type == "negative":
        return 0

    return None


def submit_feedback(
    feedback_type: Optional[str] = None,
    feedback_text: str = "",
) -> Tuple[bool, Dict[str, Any]]:
    """Submit feedback to the API."""

    trace_id = st.session_state.get("trace_id")

    if not trace_id:
        return False, {
            "message": "No trace ID is available for this response."
        }

    feedback_data = {
        "trace_id": trace_id,
        "thread_id": session_id,
        "feedback_score": feedback_score(feedback_type),
        "feedback_text": feedback_text,
        "feedback_score_type": "api",
    }

    return api_call(
        "post",
        f"{config.API_URL}/submit_feedback",
        json=feedback_data,
    )


# ============================================================
# Final result handling
# ============================================================

def store_final_result(data: Dict[str, Any]) -> str:
    """
    Store a final API result in session state.

    Returns:
        Assistant answer.
    """

    result = extract_final_result(data)

    answer = result["answer"]

    st.session_state.used_context = result["used_context"]
    st.session_state.trace_id = result["trace_id"]
    st.session_state.shopping_cart = result["shopping_cart"]

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    # Reset feedback state for the new assistant response.
    st.session_state.latest_feedback = None
    st.session_state.show_feedback_box = False
    st.session_state.feedback_submission_status = None

    return answer



# ============================================================
# Display sidebar
# ============================================================

def render_sidebar() -> None:
    with st.sidebar:
        suggestion_tab, shopping_cart_tab = st.tabs(
            ["Suggestions", "Shopping Cart"]
        )

        # ----------------------------------------------------
        # Suggestions
        # ----------------------------------------------------

        with suggestion_tab:
            used_context = st.session_state.get("used_context", [])

            if used_context:
                for item in used_context:
                    if not isinstance(item, dict):
                        continue

                    st.caption(
                        item.get(
                            "description",
                            "No description",
                        )
                    )

                    image_url = item.get("image_url")

                    if image_url:
                        st.image(
                            image_url,
                            width=250,
                        )

                    price = item.get("price")

                    if price is not None:
                        currency = item.get(
                            "currency",
                            "USD",
                        )

                        st.caption(
                            f"Price: {price} {currency}"
                        )

                    st.divider()

            else:
                st.info("No suggestions yet.")

        # ----------------------------------------------------
        # Shopping cart
        # ----------------------------------------------------

        with shopping_cart_tab:
            st.caption(session_id)
            shopping_cart = st.session_state.get(
                "shopping_cart",
                [],
            )

            if shopping_cart:
                for item in shopping_cart:
                    if not isinstance(item, dict):
                        continue

                    st.caption(
                        item.get(
                            "description",
                            "No description",
                        )
                    )

                    image_url = item.get(
                        "product_image_url"
                    )

                    if image_url:
                        st.image(
                            image_url,
                            width=250,
                        )

                    price = item.get("price")
                    currency = item.get(
                        "currency",
                        "USD",
                    )
                    quantity = item.get(
                        "quantity",
                        0,
                    )
                    total_price = item.get(
                        "total_price"
                    )

                    if price is not None:
                        st.caption(
                            f"Price: {price} {currency}"
                        )

                    st.caption(
                        f"Quantity: {quantity}"
                    )

                    if total_price is not None:
                        st.caption(
                            f"Total Price: "
                            f"{total_price} {currency}"
                        )

                    st.divider()

            else:
                st.info("Your cart is empty.")


# ============================================================
# Display messages
# ============================================================

def render_messages() -> None:
    messages = st.session_state.messages

    for idx, message in enumerate(messages):
        role = message.get("role", "assistant")
        content = message.get("content", "")

        with st.chat_message(role):
            st.markdown(content)

            is_latest_assistant = (
                role == "assistant"
                and idx == len(messages) - 1
                and idx > 0
            )

            if not is_latest_assistant:
                continue

            render_feedback(idx)


# ============================================================
# Feedback UI
# ============================================================

def render_feedback(message_idx: int) -> None:
    feedback_key = f"feedback_{message_idx}"

    feedback_result = st.feedback(
        "thumbs",
        key=feedback_key,
    )

    if feedback_result is not None:
        feedback_type = (
            "positive"
            if feedback_result == 1
            else "negative"
        )

        if st.session_state.latest_feedback != feedback_type:
            with st.spinner("Submitting feedback..."):
                status, response = submit_feedback(
                    feedback_type=feedback_type
                )

            if status:
                st.session_state.latest_feedback = feedback_type
                st.session_state.feedback_submission_status = "success"
                st.session_state.show_feedback_box = (
                    feedback_type == "negative"
                )

                st.rerun()

            else:
                st.session_state.feedback_submission_status = "error"
                st.error(
                    "Failed to submit feedback. Please try again."
                )

    # --------------------------------------------------------
    # Feedback status
    # --------------------------------------------------------

    if (
        st.session_state.latest_feedback
        and st.session_state.feedback_submission_status
        == "success"
    ):
        if st.session_state.latest_feedback == "positive":
            st.success(
                "✅ Thank you for your positive feedback!"
            )

        elif (
            st.session_state.latest_feedback == "negative"
            and not st.session_state.show_feedback_box
        ):
            st.success(
                "✅ Thank you for your feedback!"
            )

    elif (
        st.session_state.feedback_submission_status
        == "error"
    ):
        st.error(
            "❌ Failed to submit feedback. Please try again."
        )

    # --------------------------------------------------------
    # Negative feedback details
    # --------------------------------------------------------

    if st.session_state.show_feedback_box:
        st.markdown(
            "**Want to tell us more? (Optional)**"
        )

        st.caption(
            "Your negative feedback has already been recorded. "
            "You can optionally provide additional details below."
        )

        feedback_text = st.text_area(
            "Additional feedback (optional)",
            key=f"feedback_text_{message_idx}",
            placeholder=(
                "Please describe what was wrong with this response..."
            ),
            height=100,
        )

        col_send, col_spacer, col_close = st.columns(
            [3, 5, 2]
        )

        with col_send:
            if st.button(
                "Send Additional Details",
                key=f"send_additional_{message_idx}",
            ):
                if not feedback_text.strip():
                    st.warning(
                        "Please enter some feedback text before submitting."
                    )
                else:
                    with st.spinner(
                        "Submitting additional feedback..."
                    ):
                        status, response = submit_feedback(
                            feedback_text=feedback_text.strip()
                        )

                    if status:
                        st.session_state.show_feedback_box = False
                        st.session_state.feedback_submission_status = (
                            "success"
                        )

                        st.success(
                            "✅ Thank you! Your additional feedback "
                            "has been recorded."
                        )

                        st.rerun()

                    else:
                        st.error(
                            "❌ Failed to submit additional feedback. "
                            "Please try again."
                        )

        with col_close:
            if st.button(
                "Close",
                key=f"close_feedback_{message_idx}",
            ):
                st.session_state.show_feedback_box = False
                st.rerun()


# ============================================================
# Agent request
# ============================================================

def process_user_prompt(prompt: str) -> None:
    """Send a user message to the agent and process its SSE response."""

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        message_placeholder = st.empty()

        status_placeholder.info("Thinking...")

        got_final_result = False
        

        for line in api_call_stream(
            "post",
            f"{config.API_URL}/agent",
            json={
                "query": prompt,
                "thread_id": session_id,
            },
            headers={
                "Accept": "text/event-stream",
            },
        ):
            output = parse_sse_line(line)

            if output is None:
                continue

            output_type = output.get("type")

            # ------------------------------------------------
            # Final answer
            # ------------------------------------------------

            if output_type == "final_result":
                output_data = output.get("data", {})

                answer = store_final_result(output_data)

                status_placeholder.empty()
                message_placeholder.markdown(answer)

                got_final_result = True
                break

        
            # ------------------------------------------------
            # Server error
            # ------------------------------------------------

            elif output_type == "error":
                error_data = output.get("data", {})

                if isinstance(error_data, dict):
                    error_message = error_data.get(
                        "message",
                        "The server returned an error.",
                    )
                else:
                    error_message = str(error_data)

                status_placeholder.empty()
                message_placeholder.error(error_message)
                break

            # ------------------------------------------------
            # Generic text/status
            # ------------------------------------------------

            elif output_type == "text":
                status_placeholder.markdown(
                    str(output.get("data", ""))
                )



# ============================================================
# Main application
# ============================================================

display_error_popup()


# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------

render_sidebar()


# ------------------------------------------------------------
# Conversation
# ------------------------------------------------------------

render_messages()


# ------------------------------------------------------------
# Chat input
# ------------------------------------------------------------

prompt = st.chat_input(
    "Hello! How can I assist you today?"
)

if prompt:
    process_user_prompt(prompt)

    # One explicit rerun after processing the request.
    # There is NO unconditional rerun elsewhere.
    st.rerun()