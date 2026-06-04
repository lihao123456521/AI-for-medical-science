# v26 更新说明

1. 新增病例的“标签/分组”改为单一可自定义标签；未填写时默认保存为“用户新增”。
2. 取消前端多关键词标签入口，避免与病例分组标签混淆。
3. API 配置增加更多可选供应商与模型：DeepSeek 增加 deepseek-v3 / deepseek-v3.1 / deepseek-v4 选项，同时增加 OpenRouter、火山引擎/豆包等 OpenAI-compatible 接口。
4. 完善病例保存机制：用户新增病例保存到系统用户目录 `.uscc_scc_flask_data/user_cases.json`，写入时生成 `.bak` 备份，并维护 `storage_manifest.json` 状态文件；旧版默认标签会自动迁移为“用户新增”。

长期保留数据时，不要删除：

```text
C:\Users\你的用户名\.uscc_scc_flask_data
```
