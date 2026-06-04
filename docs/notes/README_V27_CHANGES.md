# v27 更新说明

## 1. 保存机制修复

v27 将 `C:\\Users\\你的用户名\\.uscc_scc_flask_data` 作为唯一持久化数据目录。项目包内的 `data/*.json` 只作为首次初始化时的空模板，不会在每次启动时反复覆盖或重新导入。

这解决两个问题：

- 删除全部文章后，重启不应恢复旧文章；
- 新增病例保存后，重启不应变成 0 个用户病例。

关键文件：

- `user_cases.json`：用户新增病例；
- `articles.json`：投喂文章；
- `deleted_cases.json`：删除病例记录；
- `storage_manifest.json`：保存状态和读回校验；
- `migration_state.json`：迁移状态。

如需完全重置用户投喂数据，请手动删除 `.uscc_scc_flask_data` 目录；普通升级前端时不要删除该目录。

## 2. 用户病例标签机制

用户新增病例只保留一个可编辑分组标签。未填写时自动设为：

```text
用户新增
```

原始 Excel 数据库病例仍保留原工作表分组，不建议编辑。

## 3. Claude / Claude Code API 选项

API 配置新增：

```text
Anthropic / Claude Code
```

预设模型包括：

- `claude-opus-4-7`
- `claude-sonnet-4-6`
- `claude-haiku-4-5-20251001`
- `claude-opus-4-6`
- `claude-sonnet-4-5`
- 自定义模型

Anthropic 使用原生 Messages API，不走 OpenAI-compatible 接口。
