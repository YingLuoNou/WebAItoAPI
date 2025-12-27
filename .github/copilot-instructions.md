# Copilot 使用说明（供 AI 代码助手）

此仓库 `WebAItoAPI` 将网页端的 Gemini（Google）封装为本地 API，主要由浏览器自动化（DrissionPage）与 `FastAPI` 组成。下面的说明帮助 AI 代码助手快速上手并安全修改代码。

- **项目入口**：[main.py](main.py) — 核心实现，包含浏览器初始化、SSE 流式产出、和 `/v1/chat/completions` 的 FastAPI 路由。
- **配置文件**：[config.json](config.json) — 包含 `user_data_path`、`port`、`api_port`、`use_temporary_chat` 等关键配置。首次运行会自动生成默认值。
- **依赖与 Python 版本**：参见 [pyproject.toml](pyproject.toml)（要求 Python >=3.12，依赖 `drissionpage`、`fastapi`、`uvicorn`、`json-repair`、`requests`）。
- **持久化浏览器数据**：`ChromeBotData/` 目录保存 Chrome 用户数据，保留以维持登录状态。

关键约定与易错点
- 模式切换：`use_temporary_chat` 决定两种工作流——临时对话（每次刷新、适合 API）或标准对话（保留历史）；见 [main.py](main.py#L1-L120) 中的 `DEFAULT_CONFIG` 与 `ensure_chat_mode()`。
- 流/非流：API 支持 `stream` 参数（SSE 输出）与 `clean_json` 参数（默认 True）。`collect_stream_content(..., clean_json=True)` 会使用 `json_repair` 修复并尝试从返回文本抽取 JSON；修改相关逻辑要保留向后兼容性（Browser-Use 场景）。
- 图片支持：项目通过 `js_paste_image()` 把 Base64 注入网页（见 `download_image_to_base64` 与 `js_paste_image`），任何对图片上传流程的改动须兼顾 data URI 和远程 URL 两种输入格式。
- 并发/互斥：使用全局 `browser_lock`（threading.Lock）序列化对浏览器的访问，改动时要保持相同的锁语义以避免并发破坏页面状态。
- 全局状态：`page` 是全局对象，由 `init_browser()` 设置，生命周期由 FastAPI 的 `lifespan` 管理。不要随意用多个浏览器实例，除非同时调整生命周期逻辑。

典型开发/运行命令
- 快速启动（已在 README 中）：
```
.venv/Scripts/activate
python main.py
```
- 也可直接用 uvicorn：
```
uvicorn main:app --host 0.0.0.0 --port 8000
```
- 依赖安装：`pyproject.toml` 中声明，推荐使用 `uv sync`（项目 README 提到），或使用 pip 在虚拟环境中安装依赖。

调试提示（来自代码可观测行为）
- 若浏览器启动失败：检查 `user_data_path`（[config.json](config.json)）与本地 Chrome 是否安装，确认 `port`（默认 9333）未被占用。
- 若返回不是合法 JSON：优先检查 `clean_json` 的使用场景，`collect_stream_content` 会尝试去除 Markdown 包裹和修复 JSON；不要删除此修复流程，除非确保替代方案更稳健。
- 若发生超时或页面找不到输入框：`gemini_stream_generator` 包含多处 DOM 查询（例如 `div[contenteditable="true"]`、`.model-response-text` 等），修改时要按原有选择器的容错策略（短超时 + 重试 + refresh）保持一致。

修改守则（编辑建议）
- 保持现有 API 兼容性：对 `/v1/chat/completions` 路由的输入/输出格式修改需明确说明并同时支持旧参数（`stream`, `clean_json`）。
- 小步提交并说明：浏览器相关改动可能在不同机器/Chrome 版本上表现不同，提交 PR 时在描述中列出测试的 Chrome 版本与本地 `config.json` 关键字段。
- 日志与错误消息：项目大量使用 print 输出用于调试（中/英双语）。新增日志应保留可读性并考虑中文输出对排查问题有帮助。

示例请求（来源：README）：
```python
payload = {
  "messages": [{"role": "user", "content": "请输出一个包含 'status' 和 'code' 的 JSON 格式数据"}],
  "stream": False,
  "clean_json": True
}
```

如果有遗漏或想补充的项目特有规则（例如 CI、代码风格、测试用例位置），请指出，我会把它们合并进本文件。 

— 自动生成（更新） by AI 助手
