# 修复说明

本版本修复 3 个问题：

1. “生成风险识别报告”点击后无反馈：
   - 后端 `/api/analyze` 增加 `ok` 字段和错误返回；
   - 前端增加超时、错误提示和报告正文区域；
   - 按钮增加 `type="button"`，避免表单默认提交导致页面刷新。

2. “风险与证据链”滚动时固定在右上角：
   - 已将 `.result-panel` 从 `position: sticky` 改为 `position: static`。

3. “可视化病例对话”不回答：
   - 前端增加请求超时和错误提示；
   - 后端 OpenAI 调用设置 12 秒超时；
   - 如果没有 API Key 或 API 出错，会自动退回本地知识库兜底回答。

## 更新方法

最简单：把本压缩包解压到桌面，进入 `uscc_scc_flask_fixed` 文件夹，重新运行：

```powershell
cd ([Environment]::GetFolderPath("Desktop"))
cd .\uscc_scc_flask_fixed
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

如果已经创建过虚拟环境，也可以只替换这些文件：

- `app.py`
- `core/risk_engine.py`
- `core/llm_client.py`
- `templates/index.html`
- `static/js/app.js`
- `static/css/style.css`

然后在 PowerShell 停止旧服务：按 `Ctrl + C`，再执行：

```powershell
python app.py
```

浏览器打开：

```text
http://127.0.0.1:5000
```

如果页面还是旧样式，按 `Ctrl + F5` 强制刷新。
