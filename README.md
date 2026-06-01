# AI for Medical Science

这是一个用于医学科研与教学展示的 Flask 原型：围绕尿道鳞状细胞癌（SCC）、硬化性苔藓（LS）和尿道狭窄等因素，演示规则评分、相似病例检索、病例文件解析、图片附件上传和可选 AI 对话。

## 公开版本说明

本仓库仅包含**完全合成的演示病例**，不包含真实患者姓名、住院日期、病历或受保护健康信息。默认知识库位于 `data/knowledge_base.xlsx`，其中每条记录均标记为 `DEMO-*`。

该项目只适合教学、科研讨论和软件原型展示，不构成诊断、分期或治疗建议。

## 本地运行

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

打开：

```text
http://127.0.0.1:5000
```

健康检查：

```text
http://127.0.0.1:5000/healthz
```

macOS 或 Linux 可使用：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## 可选 AI 接入

复制 `.env.example` 为 `.env` 后再填写本地配置。不要把 `.env` 或 API Key 提交到 GitHub。

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
FLASK_SECRET_KEY=change-this-in-production
```

不配置 API Key 时，应用仍可使用本地规则和演示病例运行。

## 主要功能

- 结构化病例录入与文件解析
- 规则化风险特征提取与可追溯评分
- 相似病例检索
- 图片和文档附件上传
- 可选 OpenAI、Anthropic 或 OpenAI-compatible 模型调用
- Render 部署配置

## 编辑项目

常用修改位置：

- 页面布局：`templates/`
- 样式：`static/css/style.css`
- 前端交互：`static/js/`
- Flask 接口：`app.py`
- 风险规则：`core/risk_engine.py`
- 模型调用：`core/llm_client.py`
- 合成演示知识库：`data/knowledge_base.xlsx`

每次公开提交前，请确认没有加入真实病例、上传文件、`.env` 或 API Key。详细要求见 [SECURITY_AND_DATA_POLICY.md](SECURITY_AND_DATA_POLICY.md)。

## 部署

仓库已包含 `render.yaml` 和 `Procfile`。在 Render 中创建 Blueprint 并连接本仓库，首次部署时填写 `FLASK_SECRET_KEY`。公网演示应只使用合成数据；如需在线模型，再在托管平台后台单独配置 API Key。

## 后续路线

1. 增加登录和角色权限。
2. 将真实研究数据保存在受控环境，而不是公开仓库。
3. 为规则评分增加验证集、敏感度、特异度、AUC 和错误案例分析。
4. 建立合规的数据字典、版本说明和研究协议。
5. 录制简短演示视频，并在项目首页加入截图和使用场景。
