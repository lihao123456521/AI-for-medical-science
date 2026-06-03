# ChatGPT 式前端 V4 更新

本版针对以下问题修改：

1. 左侧聊天记录增加删除按钮，只删除当前浏览器 localStorage 中的聊天，不影响病例知识库。
2. 知识库页和病例详情页增加删除病例按钮。删除后会写入 `data/deleted_cases.json`，即使重启服务也会从检索中隐藏该病例。
3. 去掉固定回复“已结合当前对话病例信息检索本地知识库。”，回答更接近医生问答。
4. 在相似病例基础上增加“治疗与转归对照”和“手术/用药讨论方向”。
5. 病例详情和知识库列表中补充显示手术治疗、其他治疗/用药、随访等字段。

运行方式不变：

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python app.py
```

浏览器打开：

```text
http://127.0.0.1:5000
```

如果页面仍是旧版，按 Ctrl + F5 强制刷新。
