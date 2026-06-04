# 部署到 Render：公开网址版本

目标：让别人只打开一个网址即可访问，不需要安装 Python 或配置环境。

## 1. 上传到 GitHub

1. 登录 GitHub，新建一个仓库，例如 `uscc-scc-flask`。
2. 把本项目文件夹里的所有文件上传到仓库。
3. 不要上传 `.env` 文件。API Key 只在 Render 后台配置。
4. 本部署版已把 Excel 改名为 `data/knowledge_base.xlsx`，避免中文文件名在云端部署时出现路径编码问题。

## 2. 在 Render 创建 Web Service

1. 打开 Render，选择 New -> Web Service。
2. 连接你的 GitHub 仓库。
3. 主要配置：
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`

## 3. 配置环境变量

在 Render 的 Environment 页面添加：

```text
FLASK_DEBUG=0
DATA_PATH=data/knowledge_base.xlsx
OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=你的 OpenAI API Key（可选）
FLASK_SECRET_KEY=任意一串长随机字符
```

没有 `OPENAI_API_KEY` 时，系统仍可运行，但病例对话会使用本地兜底解释。

## 4. 部署并访问

点击 Deploy。部署成功后，Render 会给你一个类似：

```text
https://uscc-scc-flask.onrender.com
```

的公开网址。把这个网址发给同学或老师即可。

## 5. 常见问题

- 打不开：看 Render Logs，检查是否依赖安装失败。
- 数据读不到：确认 `data/knowledge_base.xlsx` 已上传到 GitHub。
- 对话不回答：确认是否配置 `OPENAI_API_KEY`；没配置时会显示本地兜底回答。
- 首次打开较慢：免费实例可能会休眠，首次访问需要等待一段时间。
