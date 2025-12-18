# WebAItoAPI
[Read this in English](./readmeEN.md)

> ⚠️ **重要提示**：在使用本项目之前，请务必仔细阅读并理解以下免责声明和许可条款。

<details>
<summary><strong>⚠️ 展开查看免责声明 (Disclaimer) - 严禁商用, 使用本项目默认同意本协议 </strong></summary>

### ⚖️ 免责声明 (Disclaimer)

1. **仅供学术研究**：本项目仅供个人学习、学术研究和技术交流使用。
2. **严禁商业用途**：任何个人或组织**不得**将本项目用于任何商业目的。
3. **后果自负**：
    * 本项目涉及到模拟浏览器操作，可能会触发目标平台的反爬虫机制。
    * **因使用本项目导致的任何后果（包括账号被封禁），由使用者自行承担。**
4. **无担保**：本项目按“原样”提供，不提供任何形式的担保。
---
### 📄 许可协议 (License)

本项目采用 **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)** 许可协议。

**简而言之，您可以：**
* ✅ **共享** — 在任何媒介以任何形式复制、发行本作品。
* ✅ **演绎** — 修改、转换或以本作品为基础进行创作。

**只要你遵守以下条款：**
* 🛑 **非商业性使用** — 您不得将本作品用于商业目的。
* 🗣️ **署名** — 您必须给出适当的署名，提供指向本许可协议的链接，同时标明是否（对原始作品）作了修改。
* 🔄 **相同方式共享** — 如果您再混合、转换或者基于本作品进行创作，您必须基于与原先许可协议相同的许可协议分发您贡献的作品。
</details>  

---  
## 🇨🇳 中文版 (Chinese)

### 项目简介
**WebAItoAPI** 是一个基于 Python 的轻量级中间件，利用 **DrissionPage** 自动化技术将网页版 AI（目前仅支持 Google Gemini）封装为标准的 API 接口，并通过 **FastAPI** 对外提供服务。

本项目专为**个人用户**和**学术研究**设计，旨在解决官方 API 价格昂贵或免费版速率限制（Rate Limit）过严的问题，极大降低了个人搭建 AI Agent 的门槛。

**核心亮点：**
* **降低成本**：直接利用网页版对话能力，无需购买昂贵的 API 额度。
* **Browser-Use 优化**：项目最初为配合 [browser-use](https://github.com/browser-use/browser-use) 库搭建，内置针对性的 JSON 清洗与修复功能，显著提升 Agent 执行稳定性。
* **灵活轻量**：适合无需高并发的个人实验场景。
* **API 标准化**：提供类 OpenAI 的接口格式，易于集成到现有工作流中。

### ⚙️ 配置说明
本项目采用 `config.json` 进行配置管理。首次运行程序时，系统会自动在根目录下生成默认的 `config.json` 文件。您可以根据需求修改以下字段：

```json
{
    "user_data_path": "C:\\path\\to\\ChromeBotData",  // 浏览器用户数据存储路径 (Cookies, 登录状态等)
    "target_url": "[https://gemini.google.com/app](https://gemini.google.com/app)",    // 目标 AI 服务地址
    "port": 9333,                                     // 浏览器调试端口
    "use_temporary_chat": true                        // 聊天模式开关
}
```
字段详解：
- user_data_path: 存放 Chrome 用户数据的文件夹路径。保留此文件夹可以保持您的登录状态，避免每次重启都需要重新扫码登录。
- port: DrissionPage 控制浏览器使用的本地端口号，默认 9333。
- use_temporary_chat:
  - true (默认): 临时对话模式。每次请求都会刷新页面并开启新对话，不保留历史记录，适合 API 调用。
  - false: 标准对话模式。保留网页侧的历史记录，仅在页面出错时刷新。

**Browser-Use**配置说明:
- 示例：
  ```python
  llm = ChatOpenAI(
    model="gemini-3.0-pro",
    base_url="http://localhost:8000/v1/",
    api_key="",
    timeout=200
  )

  agent = Agent(
    task='帮我找一下百度热搜第一是什么', #描述尽量详细，详见Browser-Use文档
    browser=browser,
    llm=llm,
    tools=tools,
    step_timeout=250,
    llm_timeout=200 #该配置项一定要配置，否则极易超时
  )
  ```


### 请求示例：
```python
payload = {
    "messages": [
        {"role": "user", "content": "请输出一个包含 'status' 和 'code' 的 JSON 格式数据"}
    ],
    "stream": False,      # 是否开启流式模式输出
    "clean_json": True    # 是否开启清洗功能（默认开启）
}

response = requests.post(url, json=payload, headers=headers)
print(response.json()["choices"][0]["message"]["content"])
```

