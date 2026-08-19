import streamlit as st
import requests
from core.config import config
API_URL= config.API_URL

st.set_page_config(
    page_icon="Enterprise Agent Platform Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

def api_call(method, url, **kwargs):

    def _show_error_popup(message):
        """Show error message as a popup in the top-right corner."""
        st.session_state["error_popup"] = {
            "visible": True,
            "message": message,
        }

    try:
        response = getattr(requests, method)(url, **kwargs)

        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            response_data = {"message": "Invalid response format from server"}

        if response.ok:
            return True, response_data

        return False, response_data

    except requests.exceptions.ConnectionError:
        _show_error_popup("Connection error. Please check your network connection.")
        return False, {"message": "Connection error"}
    except requests.exceptions.Timeout:
        _show_error_popup("The request timed out. Please try again later.")
        return False, {"message": "Request timeout"}
    except Exception as e:
        _show_error_popup(f"An unexpected error occurred: {str(e)}")
        return False, {"message": str(e)}


if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I assist you today?"}]


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if "used_context" not in  st.session_state:
    st.session_state.used_context=[]

with st.sidebar:
    suggestion_tab,= st.tabs(["Suggestions"])

    with suggestion_tab:
        if st.session_state.used_context:
            for idx, item in enumerate(st.session_state.used_context):
                st.caption(item.get("description", "no description"))
                if "image_url" in item:
                    st.image(item["image_url"],width=250)
                st.caption(f"Prices: {item['price']} UDS")
                st.divider()
        else:
            st.info("No suggestion yet")


if prompt := st.chat_input("Hello! How can I assist you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status,output = api_call("post", f"{API_URL}/agent", json={"query":prompt})
        answer= output["answer"]
        used_context=output["references"]

        st.session_state.used_context= used_context
        st.write(answer)




    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()