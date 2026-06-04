# ChatGPT UI v5 更新说明

本版本修复知识库页的病例卡片渲染与分组筛选，并新增左上角 API Key 配置入口。

## 主要更新

1. 知识库页恢复可视化病例卡片，病例卡片和“查看详情”均可跳转病例详情页。
2. 分组筛选改为从 `/api/summary` 读取完整工作表分组，不再只显示“全部分组”。
3. 首页左上角新增“API Key 配置”，Key 仅保存在当前浏览器 localStorage，不写入项目文件。
4. 顶部标题改为更简洁的“病例问答”，并加入轻量吉祥物，不占用主体对话区域。
5. 保留默认三组相似病例、删除聊天记录、删除病例、添加病例和图片上传能力。

## 使用

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python app.py
```

浏览器打开：

```text
http://127.0.0.1:5000
```

如果看到旧页面，请按 Ctrl + F5 强制刷新。
