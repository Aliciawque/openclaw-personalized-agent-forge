# OpenClaw Skills Bundle：个性化 Agent Forge 技能包

这是一个 3 合 1 的技能包，用于**快速创建个性化 OpenClaw Agent**，来源包括：

1. **公开创作者 / 数字 IP**
2. **真实职业岗位**
3. **虚构角色**

这个仓库适合希望把某种声音、角色、身份或人格，转化为可部署 OpenClaw Agent 配置包的用户。

---

## 包含的 Skills

### 1. `digital-ip-agent`
把公开创作者、博主、播客主、YouTuber、X/Twitter 账号人格化为可部署的 OpenClaw persona package。

**适用场景：**
- 博主 / KOL 数字分身
- 创作者风格克隆
- 公共人格提炼
- 创作者型 AI 助手构建

### 2. `professional-agent-forge`
为真实职业生成完整的 OpenClaw Agent 配置。

**适用场景：**
- 产品经理 Agent
- 工程师 Agent
- 律师 Agent
- 数据分析师 / 设计师 / 营销 Agent
- 专业岗位工作流助手

### 3. `fictional-companion-forge`
把虚构角色还原为具有真实感和角色一致性的 OpenClaw 陪伴型 Agent。

**适用场景：**
- 角色陪伴 Agent
- 游戏 / 电影 / 动漫 / 小说角色还原
- 沉浸式人格模拟
- 保留强烈原作语气和边界感

---

## 仓库结构

```text
openclaw-skills-bundle-md/
├── 01-digital-ip-agent/
│   ├── SKILL.md
│   └── references/
├── 02-professional-agent-forge/
│   ├── SKILL.md
│   └── references/
├── 03-fictional-companion-forge/
│   ├── SKILL.md
│   └── references/
├── README.md
└── README.zh-CN.md
```

---

## 快速示例

### `digital-ip-agent`
**示例提示词：**
> Turn this YouTube creator into an OpenClaw agent and generate the core persona files.

### `professional-agent-forge`
**示例提示词：**
> Create a product manager OpenClaw agent focused on B2B SaaS prioritization and stakeholder alignment.

### `fictional-companion-forge`
**示例提示词：**
> Turn Ghost from Call of Duty into a character-faithful OpenClaw companion agent.

---

## 设计理念

这个技能包的重点不是“套模板”，而是**构建高质量、可持续的人格与角色结构**。

这些 skills 主要围绕 OpenClaw 中最关键的 persona 文件来工作：

- `soul.md`
- `identity.md`
- `memory.md`
- `agents.md`
- `tools.md`（当职业和工具链很重要时）

目标不是生成一个“带人设开场白的普通聊天机器人”，而是生成一个具有以下特征的 Agent：

- 有可信的内在逻辑
- 有稳定的互动方式
- 有与角色/职业匹配的记忆和边界
- 有可以直接部署的核心配置文件

---

## 这个技能包的价值

### 1. File-first persona construction
优先沉淀为 durable files，而不是停留在模糊 prompt 层。

### 2. 按来源类型定制工作流
不同技能分别适配：
- 公开创作者内容
- 职业与岗位逻辑
- 虚构角色 canon 与角色一致性

### 3. 强反泛化倾向
这些 skill 的写法刻意避免 bland、空泛、模板味太重的输出。

### 4. 可加载 reference material
每个 skill 都附带了参考文件，在需要更高细节时可以加载使用。

---

## 建议的公开定位

如果你要把这个仓库发布到 **GitHub** 和 **ClawHub**，推荐定位为：

> 一个用于从创作者、职业、虚构角色快速构建个性化 OpenClaw Agent 的紧凑技能包。

推荐关键词：
- openclaw
- agent persona
- digital twin
- creator clone
- profession agent
- fictional companion
- soul identity memory agent

---

## 发布前建议

在正式发布前，你可以进一步考虑：
- 在 GitHub 根目录补充 demo 输出示例，增强可发现性
- 如果 ClawHub 更适合逐个 skill 发布，可以把 3 个 skill 分开打包上传
- 保持根目录 README 面向人类读者，而 skill 内部继续面向 agent 使用

---

## License

发布前请补一个许可证。

如果想最大化传播，MIT 最简单；如果你更希望文档类内容保留署名和演化约束，可以考虑 CC BY-SA。
