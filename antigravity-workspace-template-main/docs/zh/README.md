# 📚 Antigravity 工作区文档（中文）

欢迎来到 **Antigravity Workspace Template** 的中文文档——一个在 Google Antigravity 上构建自主 AI 代理的生产级起步模板。

## 🎯 快速导航

### 入门
- **[快速开始](QUICK_START.md)** — 安装、本地开发、运行示例
- **[项目理念](PHILOSOPHY.md)** — 核心理念与 Artifact-First 协议

### 核心特性
- **[零配置特性](ZERO_CONFIG.md)** — 自动发现工具与上下文
- **[MCP 集成](MCP_INTEGRATION.md)** — 连接外部工具与数据源
- **[多 Agent Swarm](SWARM_PROTOCOL.md)** — Router-Worker 协作流程

### 规划与愿景
- **[开发路线图](ROADMAP.md)** — Phase 1-9 的进展与计划

## 🌟 亮点特性

### 🧠 无限记忆引擎
递归摘要自动压缩历史上下文，缓解上下文窗口限制。

### 🛠️ 通用工具协议
遵循通用 ReAct 模式；在 `src/tools/` 放入 Python 函数即被自动注册为工具。

### ⚡️ Gemini 原生
针对 Gemini 2.0 Flash 的速度与函数调用能力做了优化。

### 🔌 外部 LLM 支持
通过内置 `call_openai_chat` 工具可调用任意 OpenAI 兼容 API（OpenAI、Azure、Ollama 等）。

## 🚀 常见任务

| 目标 | 文档 |
|------|------|
| 体验与运行 | [快速开始](QUICK_START.md) |
| 编写自定义工具 | [零配置特性](ZERO_CONFIG.md) |
| 连接 MCP 服务器 | [MCP 集成](MCP_INTEGRATION.md) |
| 启用多 Agent | [多 Agent Swarm](SWARM_PROTOCOL.md) |
| 理解架构 | [项目理念](PHILOSOPHY.md) |
| 查看规划 | [开发路线图](ROADMAP.md) |

## 📊 项目结构

```
.
├── .antigravity/        # 🛸 Antigravity 配置/规则
├── .context/            # 📚 自动注入的知识库
├── artifacts/           # 📂 Agent 输出（计划、日志、证据）
├── src/                 # 🧠 Agent 源码
│   ├── agent.py         # 主循环
│   ├── memory.py        # JSON 记忆管理
│   ├── mcp_client.py    # MCP 集成
│   ├── swarm.py         # 多 Agent 编排
│   ├── agents/          # 专家型 Agent
│   └── tools/           # 工具实现
├── tests/               # ✅ 测试套件
├── scripts/             # 🧪 辅助脚本
├── docker-compose.yml   # 本地开发栈
├── README.md            # 项目主页
└── requirements.txt     # Python 依赖
```

## 🎓 按角色阅读

### 开发者
1) 先读 [快速开始](QUICK_START.md)  
2) 理解 [零配置特性](ZERO_CONFIG.md)  
3) 了解 [Swarm 协议](SWARM_PROTOCOL.md)

### DevOps/部署
1) 阅读 [快速开始](QUICK_START.md) 的 Docker 部分  
2) 查看 [开发路线图](ROADMAP.md) 的 Phase 9（Enterprise Core）  
3) 在 [MCP 集成](MCP_INTEGRATION.md) 配置外部服务器

### 架构师
1) 理解 [项目理念](PHILOSOPHY.md)  
2) 学习 [多 Agent Swarm](SWARM_PROTOCOL.md) 架构  
3) 复盘 [开发路线图](ROADMAP.md) 愿景

### 贡献者
1) 阅读 [项目理念](PHILOSOPHY.md)  
2) 查看 [开发路线图](ROADMAP.md) Phase 9 的开放议题  
3) 提交 Issue/PR 讨论想法或实现

## 🔗 外部资源

- 🌐 [Antigravity 官方文档](https://docs.antigravity.dev/)
- 📘 [MCP 协议规范](https://modelcontextprotocol.io/)
- 🐍 [Python 文档](https://docs.python.org/3/)
- 🐳 [Docker 文档](https://docs.docker.com/)
- 🧪 [Pytest 文档](https://docs.pytest.org/)

## ❓ 常见问题

**Q: 可以用 OpenAI 代替 Gemini 吗？**  
A: 可以，设置 `.env` 中的 `OPENAI_BASE_URL` 与 `OPENAI_API_KEY`，详见 [快速开始](QUICK_START.md)。

**Q: 如何添加自定义工具？**  
A: 将 Python 文件放进 `src/tools/`，无需额外注册，见 [零配置特性](ZERO_CONFIG.md)。

**Q: 如何部署到生产？**  
A: 使用 Docker，参考 [快速开始](QUICK_START.md) Docker 部分。

**Q: 是否支持多 Agent？**  
A: 支持，使用 Swarm 系统，见 [多 Agent Swarm](SWARM_PROTOCOL.md)。

**Q: 如何添加知识/上下文？**  
A: 在 `.context/` 创建文件会被自动加载，详见 [零配置特性](ZERO_CONFIG.md)。

## 🤝 贡献

- 报告问题或想法：[GitHub Issues](https://github.com/study8677/antigravity-workspace-template/issues)  
- 提交代码或改进文档：优先关注 [开发路线图](ROADMAP.md) Phase 9 的议题  
- 欢迎通过 PR 修复错别字、补充示例

## 📞 支持

- 📖 文档：当前页面或主仓库 `README.md`  
- 🐛 Bug：GitHub Issues  
- 💡 Feature：GitHub Discussions  
- 👥 社区：给仓库加星以获取更新

## 👥 贡献者

- [@devalexanderdaza](https://github.com/devalexanderdaza) — 初始贡献者，完成 demo 工具、Agent 功能增强、Agent OS 路线提出、MCP 集成。  
- [@Subham-KRLX](https://github.com/Subham-KRLX) — 增加动态工具/上下文加载（Fixes #4）与多 Agent 集群协议（Fixes #6）。

## 📄 许可证

MIT License，详见仓库根目录 `LICENSE`。

---

**最后更新：2025 年 12 月**  
**当前版本：Phase 8（MCP 集成）✅**

祝构建愉快！🚀
