# v28 更新说明

1. API 配置新增“保存并测试 / 仅测试连接”，保存后会由 Flask 后端真实请求对应供应商接口，避免只保存在浏览器但后台未连通。
2. 多供应商调用逻辑调整：OpenAI 走 Responses API；DeepSeek、通义千问、智谱、SiliconFlow、Kimi、OpenRouter、火山等走 OpenAI-compatible Chat Completions；Anthropic / Claude Code 走 Claude Messages API。
3. 吉祥物图片改为可上传。上传后的图片保存到持久数据目录，更新前端版本时不会丢失。
4. 对话气泡去除用户头像、“医生”标题、AI 头像和“系统”标题。
5. 文章上传增强：DOCX/PDF 中的图片会被提取保存；如已配置可用多模态 API，会把图片一起传给模型分析，并把中文图片分析写入文章内容。
6. 新增 `/api/llm/test`、`/api/settings/mascot` 接口。
