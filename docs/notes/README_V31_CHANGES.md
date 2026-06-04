# v31 修改说明

1. 相似度显示改为百分比。
2. 后端增加 HTML 响应检测：如果 API 平台返回网页 HTML（例如平台首页/控制台页面），前端不再原样显示代码，而是提示 Base URL 填错。
3. API 配置中增加“4Router / 自定义聚合平台”选项；需要填写该平台文档中的 OpenAI-compatible API Base URL，而不是网页首页。
4. 前端增加 HTML 响应兜底转换，避免对话框里出现大段 `<!doctype html>`。

注意：如果使用 4Router、OpenRouter 或其他中转平台，Base URL 必须是 API 接口地址，通常类似 `/v1`、`/api/v1`，不能填写平台网页地址。
