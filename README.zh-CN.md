# OpenClaw Skills Bundle：个性化 Agent Forge 技能包

**Language / 语言：** [English](./README.md) | [简体中文](./README.zh-CN.md)


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

## 项目定位

**OpenClaw Personalized Agent Forge** 是一个紧凑的技能包，用于从三类来源快速构建可部署的个性化 Agent：

- 公开创作者与数字 IP
- 真实职业岗位
- 虚构角色

它适合那些希望获得**比单条 prompt 更稳定、更耐用的人格构建能力**的用户。重点不是一次性角色扮演，而是生成可持续复用的 OpenClaw 核心文件。

**推荐关键词：**
- openclaw
- ai agents
- agent skills
- persona
- digital twin
- creator clone
- profession agent
- fictional companion

---

## 公开发布说明

这个仓库适合采用双层发布方式：

- **GitHub**：作为完整仓库、文档首页和版本历史的公开主页
- **ClawHub**：把每个 skill 分别作为独立可安装条目发布

推荐流程：
1. 先公开 GitHub 仓库
2. 再把 3 个 skill 分别发布到 ClawHub
3. 仓库根目录 README 面向人类读者，`SKILL.md` 继续面向 agent 使用

---

## License

**推荐许可证：MIT。**

如果目标是低门槛传播、方便复用、便于社区采用，MIT 是这套仓库最合适的默认选择。
