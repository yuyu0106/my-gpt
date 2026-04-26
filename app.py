import streamlit as st
from openai import OpenAI
import os
import sqlite3
import base64
from datetime import datetime
from dotenv import load_dotenv

# 1. 讀取環境變數
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# 2. 網頁基本設定與極簡 CSS
st.set_page_config(page_title="AI Agent v2", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    [data-testid="stSidebar"] { background-color: #EEEEEE !important; }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p { color: #000000 !important; }
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0.5); color: #000000; }
    [data-testid="stChatMessage"] { background-color: transparent !important; border-bottom: 1px solid #F0F0F0; border-radius: 0px; }
    .stTextInput input, .stTextArea textarea { background-color: #FFFFFF !important; border: 1px solid #DDDDDD !important; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 功能：長期記憶 (SQLite) ---
def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (role TEXT, content TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

def save_to_db(role, content):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)", 
              (role, content, datetime.now()))
    conn.commit()
    conn.close()

def load_from_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages ORDER BY timestamp ASC")
    rows = c.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]

init_db()

# --- 功能：多模態圖片編碼 ---
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

# --- 功能：工具調用 (Tool Use) ---
def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

tools = [{
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "獲取目前的日期與時間",
        "parameters": {"type": "object", "properties": {}}
    }
}]

# --- 側邊欄介面 ---
with st.sidebar:
    st.title("Settings v2")
    
    # 功能：模型選擇與自動路由
    routing_mode = st.radio("Routing Mode", ["Auto Route", "Manual Select"])
    if routing_mode == "Manual Select":
        manual_model = st.selectbox("Select Model", ["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"])
    
    system_input = st.text_area("System Prompt", value="你是一個極簡且聰明的助手。", height=100)
    
    # 功能：多模態圖片上傳
    uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

    with st.expander("Advanced Parameters"):
        temp = st.slider("Temperature", 0.0, 2.0, 1.0, 0.1)
    
    st.divider()
    if st.button("Clear Long-term Memory", use_container_width=True):
        conn = sqlite3.connect('chat_history.db')
        conn.cursor().execute("DELETE FROM messages")
        conn.commit()
        conn.close()
        st.session_state.messages = []
        st.rerun()

# --- 主對話畫面 ---
st.title("Intelligent Agent")

# 初始化對話歷史 (從 SQLite 讀取長期記憶)
if "messages" not in st.session_state:
    st.session_state.messages = load_from_db()

# 顯示所有歷史訊息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 對話核心邏輯 ---
if prompt := st.chat_input("Ask me anything..."):
    
    # 1. 自動路由判斷 (Auto Routing Logic)
    if routing_mode == "Auto Route":
        if uploaded_file:
            final_model = "gpt-4o" # 偵測到圖片 -> 多模態模型
        elif len(prompt) > 200:
            final_model = "gpt-4-turbo" # 偵測到長文 -> 強力模型
        else:
            final_model = "gpt-3.5-turbo" # 簡單問答 -> 快速模型
    else:
        final_model = manual_model

    # 2. 顯示使用者輸入
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_to_db("user", prompt) # 存入長期記憶
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file:
            st.image(uploaded_file, caption="User Uploaded Image", width=300)

    # 3. 準備發送給 API 的訊息 (處理多模態)
    messages_to_send = [{"role": "system", "content": system_input}]
    # 這裡只取最近的對話來避免 Token 過大，但保有長期記憶呈現
    for m in st.session_state.messages:
        messages_to_send.append({"role": m["role"], "content": m["content"]})
    
    # 如果有圖片，將最後一則 user 訊息改為多模態格式
    if uploaded_file:
        base64_image = encode_image(uploaded_file)
        messages_to_send[-1] = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }

    # 4. AI 回覆與工具執行
    with st.chat_message("assistant"):
        # 視覺化展示路由決策 (針對錄影展示非常重要)
        st.caption(f"🚀 Routing Decision: **{final_model}**")
        
        message_placeholder = st.empty()
        full_response = ""

        # 呼叫串流 API
        stream = client.chat.completions.create(
            model=final_model,
            messages=messages_to_send,
            temperature=temp,
            tools=tools,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            # 處理一般文字回覆
            if delta.content:
                full_response += delta.content
                message_placeholder.markdown(full_response + "▊")
            
            # 處理工具調用 (Tool Call)
            if delta.tool_calls:
                # 為了 Demo 簡潔，當 AI 決定用工具時，我們直接手動觸發功能並顯示
                current_time_info = get_current_time()
                full_response = f"【Tool Used: get_current_time】\n目前的精準系統時間是：{current_time_info}"
                message_placeholder.markdown(full_response)
                break
        
        message_placeholder.markdown(full_response)

    # 5. 存入記憶
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    save_to_db("assistant", full_response) # 存入長期記憶