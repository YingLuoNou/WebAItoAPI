import time
import json
import os
import requests
import base64
import ast
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from DrissionPage import ChromiumPage, ChromiumOptions
from threading import Lock
from json_repair import repair_json

# --- Configuration Section / 配置区域 ---

CONFIG_FILE = "config.json"

# Default configuration settings
# 默认配置设置
DEFAULT_CONFIG = {
    # Path to store Chrome user data (cookies, sessions, etc.)
    # Chrome 用户数据存储路径 (Cookies, 会话等)
    "user_data_path": os.path.join(os.getcwd(), "ChromeBotData"),
    
    # Target URL for the chatbot
    # 目标聊天机器人的 URL
    "target_url": "https://gemini.google.com/app",
    
    # Port to run the Chromium browser debugger
    # 运行 Chromium 浏览器调试器的端口
    "port": 9333,
    
    # Chat Mode Configuration:
    # True: Force Temporary Chat (temp-chat-on) + Refresh before every chat
    # False: Standard Chat (History saved) + Refresh only on error
    # 聊天模式配置：
    # True: 强制进入临时对话模式 (temp-chat-on) + 每次对话前强制刷新页面
    # False: 强制进入标准对话模式 (保留历史) + 仅在页面错误时刷新
    "use_temporary_chat": True
}

def load_or_create_config():
    """
    Load configuration from file or create a default one if it doesn't exist.
    从文件加载配置，如果不存在则创建默认配置。
    """
    if not os.path.exists(CONFIG_FILE):
        print(f">>> Configuration file not found. Creating default {CONFIG_FILE}...")
        print(f">>> 配置文件未找到。正在创建默认 {CONFIG_FILE}...")
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            return DEFAULT_CONFIG
        except Exception as e:
            print(f"!!! Failed to create config file: {e}. Using defaults.")
            print(f"!!! 创建配置文件失败: {e}。使用默认值。")
            return DEFAULT_CONFIG
    else:
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Update with any missing default keys
                # 使用缺失的默认键更新配置
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"!!! Failed to load config file: {e}. Using defaults.")
            print(f"!!! 加载配置文件失败: {e}。使用默认值。")
            return DEFAULT_CONFIG

# Load configuration
# 加载配置
current_config = load_or_create_config()

USER_DATA_PATH = current_config["user_data_path"]
TARGET_URL = current_config["target_url"]
PORT = current_config["port"]
USE_TEMPORARY_CHAT = current_config["use_temporary_chat"]

browser_lock = Lock()
page = None

# --- Helper Functions / 辅助函数 ---

def js_paste_image(base64_str, mime_type):
    """
    Inject JS to simulate image pasting (automatically generates random filename).
    注入 JS 模拟粘贴图片 (自动随机文件名)。
    """
    base64_clean = base64_str.replace('\n', '').replace('\r', '')
    js_code = f"""
    async function doPaste() {{
        try {{
            function b64toBlob(b64Data, contentType='', sliceSize=512) {{
                const byteCharacters = atob(b64Data);
                const byteArrays = [];
                for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {{
                    const slice = byteCharacters.slice(offset, offset + sliceSize);
                    const byteNumbers = new Array(slice.length);
                    for (let i = 0; i < slice.length; i++) {{
                        byteNumbers[i] = slice.charCodeAt(i);
                    }}
                    byteArrays.push(new Uint8Array(byteNumbers));
                }}
                return new Blob(byteArrays, {{type: contentType}});
            }}
            const blob = b64toBlob('{base64_clean}', '{mime_type}');
            const ext = '{mime_type}'.split('/')[1] || 'png';
            const timestamp = new Date().getTime(); 
            const randomId = Math.floor(Math.random() * 10000);
            const filename = "img_" + timestamp + "_" + randomId + "." + ext;
            const file = new File([blob], filename, {{ type: '{mime_type}' }});
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            const target = document.querySelector('div[contenteditable="true"]');
            if (!target) return "not_found";
            target.focus();
            const inputEvent = new ClipboardEvent('paste', {{
                bubbles: true,
                cancelable: true,
                clipboardData: dataTransfer
            }});
            target.dispatchEvent(inputEvent);
            return "success";
        }} catch (e) {{
            return "error: " + e.message;
        }}
    }}
    return doPaste();
    """
    return js_code

def init_browser():
    """
    Initialize the Chromium browser with the specified configuration.
    使用指定配置初始化 Chromium 浏览器。
    """
    global page
    if not os.path.exists(USER_DATA_PATH):
        os.makedirs(USER_DATA_PATH)
    co = ChromiumOptions()
    co.set_user_data_path(path=USER_DATA_PATH)
    co.set_local_port(PORT) 
    try:
        page = ChromiumPage(co)
        page.get(TARGET_URL)
        mode_str = 'Temp Chat / 临时对话' if USE_TEMPORARY_CHAT else 'Standard Chat / 标准对话'
        print(f">>> Browser launched (Port {PORT}) | Mode: {mode_str}")
    except Exception as e:
        print(f"!!! Browser launch failed / 浏览器启动失败: {e}")
        raise e

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_browser()
    yield

app = FastAPI(lifespan=lifespan)

def download_image_to_base64(url_or_base64):
    """
    Convert image URL or Data URI to Base64 string.
    将图片 URL 或 Data URI 转换为 Base64 字符串。
    """
    try:
        if url_or_base64.startswith("data:image"):
            header, encoded = url_or_base64.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
            return encoded, mime_type
        elif url_or_base64.startswith("http"):
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url_or_base64, headers=headers, timeout=15)
            if resp.status_code == 200:
                encoded = base64.b64encode(resp.content).decode('utf-8')
                mime_type = "image/jpeg" 
                if url_or_base64.endswith(".png"): mime_type = "image/png"
                return encoded, mime_type
            else:
                return None, None
        else:
            return None, None
    except Exception as e:
        print(f"!!! Image to Base64 failed / 图片转Base64失败: {e}")
        return None, None

def process_full_conversation(messages):
    """
    [Mode A: Full Context] Concatenate full history.
    【模式A：全量】拼接完整历史。
    """
    full_text = ""
    all_images = []
    
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        text_part = ""
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    text_part += item.get("text", "")
        elif isinstance(content, str):
            text_part = content

        if role == "system":
            full_text += f"【System Instruction】:\n{text_part}\n\n"
        elif role == "user":
            full_text += f"【User Input】:\n{text_part}\n\n"
        elif role == "assistant":
            full_text += f"【Model Output History】:\n{text_part}\n\n"

    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "image_url":
                    url = item.get("image_url", {}).get("url", "")
                    if url:
                        b64, mime = download_image_to_base64(url)
                        if b64: all_images.append((b64, mime))
    return full_text.strip(), all_images

def process_last_message_only(messages):
    """
    [Mode B: Incremental] Only extract the last message.
    【模式B：增量】只提取最后一条。
    """
    if not messages: return "", []
    last_msg = messages[-1]
    content = last_msg.get("content", "")
    text_part = ""
    current_images = []
    
    if isinstance(content, list):
        for item in content:
            if item.get("type") == "text":
                text_part += item.get("text", "")
    elif isinstance(content, str):
        text_part = content
        
    if isinstance(content, list):
        for item in content:
            if item.get("type") == "image_url":
                url = item.get("image_url", {}).get("url", "")
                if url:
                    b64, mime = download_image_to_base64(url)
                    if b64: current_images.append((b64, mime))
    return text_part.strip(), current_images

# --- Key Modification: collect_stream_content receives clean_json parameter ---
# --- 关键修改：collect_stream_content 接收 clean_json 参数 ---
async def collect_stream_content(generator, clean_json=True):
    """
    Consume the generator.
    clean_json=True: Repair JSON using json_repair, force unpack list (Browser-Use mode)
    clean_json=False: Return Gemini's response as is (Chat mode)
    
    消费生成器。
    clean_json=True: 使用 json_repair 修复，强制解包列表 (Browser-Use 模式)
    clean_json=False: 原样返回 Gemini 的回复 (Chat 模式)
    """
    full_content = ""
    last_id = f"chatcmpl-{int(time.time())}"
    
    for line in generator:
        if not line.startswith("data: "): continue
        json_str = line.replace("data: ", "").strip()
        if json_str == "[DONE]": break
        try:
            chunk = json.loads(json_str)
            if not last_id and chunk.get("id"): last_id = chunk.get("id")
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                full_content += delta.get("content", "")
        except: pass

    print(f">>> [Non-Stream] Raw Text Length / 原始文本长度: {len(full_content)}")

    def ultra_robust_repair(text):
        """
        Deep cleaning and repair.
        深度清洗与修复。
        """
        text = text.strip()
        # Remove Markdown / 去除 Markdown
        if "```" in text:
            import re
            pattern = r"```(?:json)?(.*?)```"
            match = re.search(pattern, text, re.DOTALL)
            if match: text = match.group(1).strip()
        
        # Find JSON boundaries / 寻找 JSON 边界
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx == -1: 
            start_idx = text.find("[")
            end_idx = text.rfind("]")

        if start_idx != -1 and end_idx != -1:
            text = text[start_idx : end_idx + 1]

        # Repair and Unpack / 修复与解包
        try:
            repaired_obj = repair_json(text, return_objects=True)
            if isinstance(repaired_obj, list):
                print(">>> [Warning] List detected, automatically extracting first item... / [警告] 检测到返回的是列表，自动提取第一项...")
                repaired_obj = repaired_obj[0] if len(repaired_obj) > 0 else {}
            return json.dumps(repaired_obj, ensure_ascii=False)
        except Exception as e:
            print(f">>> [json_repair Failed / 失败] {e}")
            return text

    # --- Logic Branch / 逻辑分支 ---
    if clean_json:
        # Perform cleaning and repair (Needed for Browser-use)
        # 执行清洗和修复 (Browser-use 需要)
        final_content = ultra_robust_repair(full_content)
    else:
        # Return as is (Needed for normal chat)
        # 原样返回 (普通对话需要)
        print(">>> [Mode] Raw Return / 原样返回 (Raw Mode)")
        final_content = full_content
    # ----------------

    return {
        "id": last_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "gemini-web-agent",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": final_content}, "finish_reason": "stop"}]
    }

# --- Core Interaction Logic / 核心交互逻辑 ---

def ensure_chat_mode():
    """
    Accurately switch chat modes based on configuration.
    根据配置，精准切换对话模式。
    """
    try:
        temp_btn = page.ele('css:button[data-test-id="temp-chat-button"]', timeout=0.5)

        if not temp_btn:
            menu_btn = page.ele('css:button[data-test-id="side-nav-menu-button"]', timeout=2)
            if menu_btn:
                menu_btn.click()
                temp_btn = page.ele('css:button[data-test-id="temp-chat-button"]', timeout=2)
        
        if not temp_btn:
            print("!!! Critical: Cannot locate Temporary Chat button / 严重：无法定位临时对话按钮")
            return

        class_str = temp_btn.attr('class') or ""
        is_temp_on = "temp-chat-on" in class_str
        
        if USE_TEMPORARY_CHAT and not is_temp_on:
            print(">>> [Action] Enabling Temporary Chat / 开启临时对话")
            temp_btn.click()
            time.sleep(0.5) 
        elif not USE_TEMPORARY_CHAT and is_temp_on:
            print(">>> [Action] Disabling Temporary Chat / 关闭临时对话")
            temp_btn.click()
            time.sleep(0.5)
        temp_btn = page.ele('css:button[data-test-id="temp-chat-button"]', timeout=0.3)
        # Close menu / 关闭菜单
        if  temp_btn:
            menu_btn = page.ele('css:button[data-test-id="side-nav-menu-button"]', timeout=2)
            menu_btn.click()
            time.sleep(0.2)
            
    except Exception as e:
        print(f"!!! Mode switch detection error / 模式切换检测出错: {e}")

def gemini_stream_generator(text_message: str, images: list):
    check_login()
    
    # 1. Refresh/Navigate / 刷新/跳转页面
    if USE_TEMPORARY_CHAT:
        page.get(TARGET_URL)
    elif "gemini.google.com" not in page.url:
        page.get(TARGET_URL)

    try:
        # 2. Wait for UI readiness / 等待 UI 就绪
        input_box = page.ele('css:div[contenteditable="true"][role="textbox"]', timeout=10)
        
        if not input_box:
            page.refresh()
            input_box = page.ele('css:div[contenteditable="true"][role="textbox"]', timeout=10)
            if not input_box:
                yield f"data: {json.dumps({'error': 'Input box not found'})}\n\n"
                return

        # 3. Confirm Mode / 确认模式
        ensure_chat_mode()

        # 4. Get input box again / 再次获取输入框
        input_box = page.ele('css:div[contenteditable="true"][role="textbox"]', timeout=2)
        if not input_box: 
             input_box = page.ele('css:div[contenteditable="true"][role="textbox"]', timeout=5)
        
        # Optimization: Fast detection of history messages / 优化：快速检测历史消息
        prev_chunks = page.eles('css:.model-response-text', timeout=0.5)
        if not prev_chunks:
            prev_chunks = page.eles('css:[data-message-id]', timeout=0.5)
        prev_count = len(prev_chunks)

        # 5. Upload Images / 上传图片
        if images:
            print(f">>> Preparing to inject {len(images)} images... / 准备注入 {len(images)} 张图片...")
            for b64, mime in images:
                script = js_paste_image(b64, mime)
                result = page.run_js(script)
                if result == "success":
                    print(">>> JS Paste Success / JS 粘贴成功")
                    time.sleep(2.5) 
                else:
                    yield f"data: {json.dumps({'error': f'Image upload failed: {result}'})}\n\n"
                    return

        # 6. Input Text / 输入文本
        if text_message:
            input_box.input(text_message)
        time.sleep(0.1)

        send_btn = page.ele('css:button[aria-label*="Send"]', timeout=2)
        if send_btn:
            send_btn.click()
        else:
            input_box.input('\n')

        # 7. Wait for Response / 等待响应
        last_response_ele = None
        wait_start = time.time()
        
        while True:
            if time.time() - wait_start > 120:
                yield f"data: {json.dumps({'error': 'Timeout'})}\n\n"
                return

            if int(time.time() * 10) % 5 == 0:
                error_toast = page.ele('text:出现了点问题', timeout=0.01) or page.ele('css:.error-message', timeout=0.01)
                if error_toast:
                    yield f"data: {json.dumps({'error': f'Gemini Error: {error_toast.text}'})}\n\n"
                    return

            current_chunks = page.eles('css:.model-response-text') or page.eles('css:[data-message-id]')
            
            if current_chunks and len(current_chunks) > prev_count:
                last_response_ele = current_chunks[-1]
                if last_response_ele: break
            
            if prev_count == 0 and current_chunks:
                last_response_ele = current_chunks[-1]
                break
            time.sleep(0.1)

        # 8. Robust Stream Transmission / 稳健流式传输
        last_text = ""
        start_time = time.time()
        resp_id = f"chatcmpl-{int(time.time())}"
        stable_count = 0 
        REQUIRED_STABLE_COUNT = 15
        
        while True:
            if time.time() - start_time > 130: break
            try:
                current_text = last_response_ele.text 
            except:
                chunks = page.eles('css:.model-response-text') or page.eles('css:[data-message-id]')
                if chunks: last_response_ele = chunks[-1]
                current_text = last_text

            if len(current_text) > len(last_text):
                stable_count = 0
                delta = current_text[len(last_text):]
                last_text = current_text
                chunk_data = {
                    "id": resp_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gemini-web-vision",
                    "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            else:
                stop_btn = page.ele('css:button[aria-label="Stop responding"]', timeout=0.01)
                if stop_btn: stable_count = 0
                else: stable_count += 1
            
            if len(current_text) > 0 and stable_count > REQUIRED_STABLE_COUNT:
                break
            time.sleep(0.1) 

        yield f"data: {json.dumps({'choices': [{'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

def check_login():
    if "accounts.google.com" in page.url: pass

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try: data = await request.json()
    except: return {"error": "Invalid JSON body"}
        
    messages = data.get("messages", [])
    is_stream = data.get("stream", False)
    # Get clean_json param, default is True (Compatible with Browser-use)
    # 获取 clean_json 参数，默认为 True (保持 Browser-use 兼容)
    clean_json = data.get("clean_json", True)

    if not messages: return {"error": "No messages"}
    
    print(f">>> Request Received | Stream: {is_stream} | Clean JSON: {clean_json} | Temp Chat: {USE_TEMPORARY_CHAT}")
    print(f">>> 收到请求 | 流式: {is_stream} | 清洗JSON: {clean_json} | 临时会话: {USE_TEMPORARY_CHAT}")
    
    if USE_TEMPORARY_CHAT:
        full_prompt, images = process_full_conversation(messages)
    else:
        full_prompt, images = process_last_message_only(messages)

    if full_prompt.strip() == "/reset":
         try:
            ensure_chat_mode()
            if not is_stream:
                return {"id": "reset", "choices": [{"index": 0, "message": {"role": "assistant", "content": "对话已重置 / Chat Reset"}, "finish_reason": "stop"}]}
            else:
                 return StreamingResponse(iter([f"data: {json.dumps({'choices': [{'delta': {'content': '对话已重置 / Chat Reset'}}]})}\n\n", "data: [DONE]\n\n"]), media_type="text/event-stream")
         except: pass

    if browser_lock.acquire(timeout=300):
        try:
            generator = gemini_stream_generator(full_prompt, images)
            if is_stream:
                # Stream mode usually returns raw data directly
                # 流式模式通常直接返回原始数据
                return StreamingResponse(generator, media_type="text/event-stream")
            else:
                print(">>> Buffering full response in background... / 正在后台缓冲完整响应...")
                # Pass clean_json parameter
                # 传入 clean_json 参数
                response_json = await collect_stream_content(generator, clean_json=clean_json)
                print(f">>> Sending response to Client (Length: {len(response_json['choices'][0]['message']['content'])})")
                return response_json
        except Exception as e:
            print(f"!!! Error processing request / 处理请求出错: {e}")
            return {"error": str(e)}
        finally:
            browser_lock.release()
    else:
        return {"error": "Browser Busy"}
    
if __name__ == "__main__":
    import uvicorn
    # Start the server with the configured port
    # 使用配置的端口启动服务器
    uvicorn.run(app, host="0.0.0.0", port=PORT)