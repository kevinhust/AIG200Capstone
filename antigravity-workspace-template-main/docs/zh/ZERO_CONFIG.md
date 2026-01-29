# ⚡ 零配置特性

## 🎯 零配置理念

**告别重复配置。** Antigravity 会自动发现工具与上下文，无需手动注册。

## 🛠️ 自动发现工具

把任意 Python 文件放进 `src/tools/`，Agent 会立刻识别其顶层函数——无需 import、无需登记。

### 工作方式
1) 🔍 扫描 `src/tools/` 下所有 `.py`  
2) 📋 索引顶层函数并读取 docstring  
3) ✅ 校验签名，注册为可调用工具  

### 示例
```python
# src/tools/sentiment_analyzer.py
def analyze_sentiment(text: str) -> dict:
    """情感分析：返回分数与标签。"""
    if len(text) > 10:
        return {"score": 0.8, "label": "positive"}
    return {"score": 0.3, "label": "neutral"}
```
重启一次 Agent 后即可在对话里直接使用 `analyze_sentiment()`。

### 编写建议
- 必写 docstring，说明参数/返回值/边界。  
- 使用类型注解，避免模糊参数。  
- 一个函数只做一件事，不要用 `*args/**kwargs` 随意接收。  

## 📚 自动注入上下文

把知识文件放到 `.context/` 会被自动拼接进系统提示，Agent 对话天然“带背景”。

### 工作方式
1) 扫描 `.context/`（支持 `.md/.txt/.json`）  
2) 读取内容进入记忆缓冲  
3) 在每次对话前注入系统提示前缀  
4) 重启 Agent 自动热加载新增文件  

### 组织建议
```
.context/
├── README.md                  # 索引
├── company_standards/         # 规范
│   ├── coding_standards.md
│   └── security_policies.md
├── project_info/              # 架构/数据库
└── api_docs/                  # API 文档
```
保持单文件 <100 行，命名自解释，旧内容及时归档。

## 🔗 工具 + 上下文 如何协同

**场景**：构建数据分析工具  
- 上下文：`.context/database_schema.md` 记录表结构  
- 工具：`src/tools/db_query.py` 提供查询函数  
- 对话：直接让 Agent“查找最近一月创建的用户”，它既“知道”结构，也“能”查询。

## 🎓 最佳实践
- 工具：写清 docstring 与类型；避免通配导入；函数单一职责。  
- 上下文：精简、分层、可维护；内容稳定的放上下文，动态操作放工具。  
- 性能：控制上下文总量（推荐 <50KB），定期清理旧文件。  

## 🐛 排查指引

**工具没加载？**
```bash
ls -la src/tools/
python -m py_compile src/tools/my_tool.py
python src/agent.py  # 重启
```

**上下文未注入？**
```bash
ls -la .context/
cat .context/your_file.md
du -sh .context/
python src/agent.py  # 重启
```

## 🚀 进阶

- 用 git 管理上下文版本  
- 按任务类型选择性注入上下文  
- 从 schema 动态生成工具  
- 组合工具完成更复杂的流程  

---

**下一步：** [开发路线图](ROADMAP.md) | [文档索引](README.md)
