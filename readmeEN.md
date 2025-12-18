# WebAItoAPI

[中文说明 (Chinese)](./README.md)

> ⚠️ **Important**: Please carefully read and understand the following Disclaimer and License terms before using this project.

<details>
<summary><strong>⚠️ Click to expand Disclaimer - Strict Non-Commercial Use. Using this project implies acceptance of these terms.</strong></summary>

### ⚖️ Disclaimer

1. **Academic Research Only**: This project is intended solely for personal learning, academic research, and technical exchange.
2. **Strictly Non-Commercial**: No individual or organization is permitted to use this project for any commercial purposes.
3. **Use at Your Own Risk**:
    * This project involves simulating browser operations, which may trigger the anti-bot mechanisms of the target platform.
    * **Users are solely responsible for any consequences resulting from the use of this project (including but not limited to account bans).**
4. **No Warranty**: This project is provided "as is" without warranty of any kind, express or implied.

---

### 📄 License

This project is licensed under the **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en)** license.

**In summary, you are free to:**
* ✅ **Share** — Copy and redistribute the material in any medium or format.
* ✅ **Adapt** — Remix, transform, and build upon the material.

**Under the following terms:**
* 🛑 **NonCommercial** — You may not use the material for commercial purposes.
* 🗣️ **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
* 🔄 **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.
</details>

---

## 🇺🇸 English Version

### Project Introduction
**WebAItoAPI** is a lightweight Python middleware that utilizes **DrissionPage** automation technology to encapsulate the web version of AI (currently supporting Google Gemini) into a standard API interface, serving it via **FastAPI**.

Designed specifically for **personal users** and **academic research**, this project aims to solve the issues of expensive official APIs or overly strict rate limits on free versions, significantly lowering the barrier for individuals to build AI Agents.

**Key Highlights:**
* **Cost Reduction**: Directly leverages the conversational capabilities of the web interface without purchasing expensive API quotas.
* **Browser-Use Optimization**: Originally built to support the [browser-use](https://github.com/browser-use/browser-use) library, it features built-in targeted JSON cleaning and repair functions, significantly improving the stability of Agent execution.
* **Flexible & Lightweight**: Suitable for personal experimental scenarios that do not require high concurrency.
* **Standardized API**: Provides an OpenAI-like interface format, making it easy to integrate into existing workflows.

### ⚙️ Configuration
This project manages configuration via `config.json`. Upon the first run, the system will automatically generate a default `config.json` file in the root directory. You can modify the following fields as needed:

```json
{
    "user_data_path": "C:\\path\\to\\ChromeBotData",  // Path to store browser user data (Cookies, login sessions, etc.)
    "target_url": "[https://gemini.google.com/app](https://gemini.google.com/app)",    // Target AI service URL
    "port": 9333,                                     // Browser debugging port
    "use_temporary_chat": true                        // Chat mode toggle
}
```
### Field Details:
- user_data_path: The folder path where Chrome user data is stored. Keeping this folder preserves your login state, avoiding the need to scan a QR code or log in every time you restart.
- port: The local port number used by DrissionPage to control the browser. Default is 9333.
- use_temporary_chat:
 - true (Default): Temporary Chat Mode. Refreshes the page and starts a new conversation for every request. No history is saved on the web side. Ideal for API usage.
 - false: Standard Chat Mode. Retains history on the web interface and only refreshes when an error occurs.

Browser-Use Configuration Guide:
- Example:
  ```python
  llm = ChatOpenAI(
  model="gemini-3.0-pro",
  base_url="http://localhost:8000/v1/",
  api_key="",  # Leave empty if not required by the middleware
  timeout=200
  )
  
  agent = Agent(
    task='Find out what is the top search on Baidu', # Be as specific as possible, see Browser-Use docs
    browser=browser,
    llm=llm,
    tools=tools,
    step_timeout=250,
    llm_timeout=200 # This configuration is crucial; otherwise, timeouts occur frequently
  )
  ```
### Request Example
```python
payload = {
    "messages": [
        {"role": "user", "content": "Please output a JSON object containing 'status' and 'code'"}
    ],
    "stream": False,      # Whether to enable streaming output
    "clean_json": True    # Whether to enable the cleaning function (Enabled by default)
}

response = requests.post(url, json=payload, headers=headers)
print(response.json()["choices"][0]["message"]["content"])
```
