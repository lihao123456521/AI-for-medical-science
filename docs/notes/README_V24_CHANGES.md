# v24 更新说明

## 1. 病例标签可编辑

- 病例知识库卡片新增“编辑标签”按钮。
- 病例详情页也可编辑标签。
- 标签保存到用户持久化目录：`~/.uscc_scc_flask_data/case_tags.json`。
- 更新前端版本时，只要不删除 `~/.uscc_scc_flask_data`，自定义标签不会丢失。

## 2. 支持其他公司的 API

API Key 配置弹窗新增：

- API 供应商选择；
- Base URL；
- 模型选择；
- 自定义模型名称。

目前预设：

- OpenAI；
- DeepSeek；
- 阿里云百炼 / 通义千问 DashScope；
- 智谱 GLM；
- SiliconFlow；
- Moonshot / Kimi；
- 自定义 OpenAI-compatible 接口。

OpenAI 使用 Responses API；其他 OpenAI-compatible 平台默认使用 Chat Completions 接口，以提高兼容性。
