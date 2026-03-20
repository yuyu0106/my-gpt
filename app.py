import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# 1. 讀取 .env 檔案
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. 網頁基本設定
st.set_page_config(page_title="Minimal AI Assistant", layout="centered")

# 3. 固定式極簡 CSS (側邊欄淺灰 + 主畫面純白)
st.markdown("""
    <style>
    /* 全域背景：純白 */
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    
    /* 側邊欄：淺灰色 */
    [data-testid="stSidebar"] {
        background-color: #EEEEEE !important;
    }
    
    /* 確保側邊欄內的文字與標籤為黑色 */
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] .stHeader {
        color: #000000 !important;
    }

    /* 修正：讓側邊欄收合按鈕 (Header) 保持可見，但不影響美觀 */
    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.5); /* 半透明白 */
        color: #000000;
    }

    /* 聊天對話框樣式：扁平化線條分隔 */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        border-bottom: 1px solid #F0F0F0;
        border-radius: 0px;
    }

    /* 輸入框樣式 */
    .stTextInput input, .stTextArea textarea {
        background-color: #FFFFFF !important;
        border: 1px solid #DDDDDD !important;
        color: #000000 !important;
    }

    /* 隱藏 Streamlit 多餘元件 (保留 Header 確保按鈕可用) */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 側邊欄介面 ---
with st.sidebar:
    st.title("Settings")
    
    # 功能 1：挑選模型
    model_choice = st.selectbox(
        "Model",
        ["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"]
    )
    
    # 功能 2：自訂 System Prompt
    system_input = st.text_area(
        "System Prompt",
        value="你是一個簡潔的助手，用繁體中文回答問題。",
        height=120
    )
    
    # 功能 3：自訂 API 參數
    with st.expander("Advanced Parameters"):
        temp = st.slider("Temperature", 0.0, 2.0, 1.0, 0.1)
        top_p = st.slider("Top P", 0.0, 1.0, 1.0, 0.05)
    
    st.divider()
    # 清除歷史紀錄按鈕
    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- 主畫面顯示 ---
st.title("AI Assistant")
st.caption(f"Status: Ready | Model: {model_choice}")

# 功能 5：交談短期記憶初始化
if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示歷史訊息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 對話邏輯 ---
if prompt := st.chat_input("Ask me anything..."):
    
    # 紀錄使用者輸入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 組合訊息列表 (System + History)
    full_messages = [{"role": "system", "content": system_input}] + st.session_state.messages

    # 功能 4：Streaming 串流輸出
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        stream = client.chat.completions.create(
            model=model_choice,
            messages=full_messages,
            temperature=temp,
            top_p=top_p,
            stream=True,
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                full_response += content
                message_placeholder.markdown(full_response + "▊")
        
        message_placeholder.markdown(full_response)

    # 將回覆存入記憶
    st.session_state.messages.append({"role": "assistant", "content": full_response})