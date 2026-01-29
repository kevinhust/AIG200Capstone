# 🔥 多 Agent Swarm 协议

## 🪐 架构：Router-Worker 模式

Swarm 把复杂任务拆分给专家 Agent 协同完成：Router 分析并分发任务，Coder/Reviewer/Researcher 执行并回传，Router 汇总结果。

## 🧠 专家角色

- 🧭 **Router**：任务分析、拆解、分配、结果合成。  
- 💻 **Coder**：实现与测试，遵循干净代码与文档规范。  
- 🔍 **Reviewer**：正确性/安全/性能审查与改进建议。  
- 📚 **Researcher**：调研信息、补充上下文与洞察。  

## 🚀 如何使用

### 交互式演示
```bash
python -m src.swarm_demo
```
输入任务即可观察协作过程。

### 代码调用
```python
from src.swarm import SwarmOrchestrator

swarm = SwarmOrchestrator()
result = swarm.execute("构建带错误处理的文件压缩工具")
print(result)
```

## 🔧 配置

- `.antigravity/swarm_config.json` 可设置模型、温度、最大迭代、各 Agent 是否启用/超时、是否并行等。  
- 自定义 Agent：继承 `BaseAgent`（参考 `src/agents`），在 `swarm.py` 注册即可。  

## 📊 日志与产物

- 日志：`artifacts/logs/`（可用 `tail -f`、`grep` 查看）。  
- 产物：`artifacts/` 下保存计划、实现、测试、评审报告等。  

## ⚡ 性能提示

- 任务描述要清晰；独立子任务可开启并行；预加载上下文；为长任务设定合理超时。  
- 禁用不需要的 Agent，定期清理旧 artifacts，必要时做结果缓存。  

## 🐛 故障排查

- Agent 未初始化：在 Python 中实例化 `SwarmOrchestrator` 看日志。  
- 执行卡住：查看 `artifacts/logs/swarm.log` 错误，适当提高超时或简化任务。  
- 结果质量低：提供更多上下文，描述更具体，确保 Reviewer 启用。  

## 📚 示例

```python
# 示例：Web 爬虫
swarm.execute("""
构建新闻爬虫：
1) 抓取文章
2) 提取标题/作者/日期
3) 保存 JSON
4) 有错误处理
""")
```

```python
# 示例：Flask API + 测试 + 安全评审
swarm.execute("""
创建 REST API：
- GET/POST /users
- 请求校验
- 单元测试齐全
- 做安全检查
""")
```

---

**下一步：** [零配置特性](ZERO_CONFIG.md) | [文档索引](README.md)
