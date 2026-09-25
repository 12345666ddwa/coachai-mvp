# CoachAI 项目工作总纲 v1.0
**Master Work Plan — for Xing (Happy) + Hermes execution**
最后更新：2026-09-16 | 依据：方向确认文档（Scope C 已确认）+ Alfos 9/16 两次补充 + Kla 意见 + 电话会议三点 + 设计 Avoid 清单

---

## 〇、一句话总览

**目标**：把 CoachAI 从"已建成的批改 MVP"升级为覆盖 **老师端 + 学生端 + 教研端** 的完整产品演示（Scope C + Alfos 增补功能分层落地）。
**工作方式**：先设计后代码、先确认后开工、多 Agent 并行开发、总管（Hermes 主代理）只做计划-审核-验收-汇报。

---

## 一、现状盘点（起点资产，全部已验证）

| 资产 | 状态 | 证据 |
|---|---|---|
| 批改引擎（Marker + Verifier 双 Agent） | ✅ 运行中 | 18 道 2025 HSC 真题、置信度、教师复核标记 |
| Golden Set 验证 | ✅ | 32 份：78.1% 完全一致、100% ±1 档内、0 离谱 |
| 题库（HSC 真题 + 官方评分标准） | ✅ | data/questions.json，18 题总分 65 |
| RAG 知识库 | ✅ | 4 份 NESA TSR，1046 块 |
| 模型抽象层 | ✅ | agents/models.py，换模型一行配置 |
| Gradio UI | ✅ | 已去 emoji、方正化、题目完整显示 |
| 概念站 + 报告 + 部署 | ✅ | GitHub Pages + Cloudflare Tunnel |
| 转录管线 | ✅ | faster-whisper 已实测（34 分钟会议转写完成） |

---

## 二、需求总清单（全部来源汇总，每条含验收标准）

### A 表：已确认范围（Scope C）
| # | 需求 | 来源 | 优先级 | 验收标准 |
|---|---|---|---|---|
| A1 | UI 重设计（anti-AI-coded） | 方向文档 + avoid 清单 | P0 | 逐项通过 avoid 检查表；撑满宽度无死空间；去 emoji |
| A2 | 隐私匿名化层 | 团队要求（proprietary data） | P0 | 姓名→占位符→批改→还原；可演示左右对比 |
| A3 | 教案生成（勾选+导入） | 电话会议 #2 | P0 | 勾选 syllabus dot points → 导入文本 → 生成结构化教案 |
| A4 | 批改升级（suggested mark + rubric 引用） | 团队任务清单 | P0 | 输出措辞为建议性；每条判断引用评分标准行 |
| A5 | 自建题目功能 | Alfos 9/16 #3 | P0 | 老师录入题目/分值/评分标准/参考答案 → 入库 → 可批改 |
| A6 | 报告生成 | Scope C 3.5 | P1 | 成绩表+老师自定义评语+性别 → NESA 风格个性化评语 |
| A7 | 网页撑满宽度 | Alfos 9/16 | P0 | 宽度利用充分，无两侧死空间 |

### B 表：Alfos 增补功能（分层落地）
| # | 需求 | 分层 | 验收标准 |
|---|---|---|---|
| B1 | 学生追踪（进度+教师建议） | L2 | 每个学生：当前水平/趋势/薄弱点 + 建议 |
| B2 | 学生端（出题+答疑+思维导图） | L3（出题+答疑先做） | 针对性出题；对话答疑；思维导图（后置） |
| B3 | 课堂录音分析（转录→教研反馈） | L3 | 转录+对照 syllabus dot points 检查覆盖/遗漏/亮点 |

### C 表：事务性任务
| # | 任务 | 负责人 |
|---|---|---|
| C1 | 项目改名（候选名列表） | Hermes 草稿 → Xing 定稿 → 团队选 |
| C2 | GitHub 加队友 admin/editor 权限 | Xing（需用户名） |
| C3 | iLearn 比赛页面研究 | Xing + Hermes（CDP 抓取） |
| C4 | 查收 Alfos 的 marking criteria 邮件（Outlook） | Xing |
| C5 | 教案主题清单（syllabus dot points/outcomes 提取） | Hermes（研究+提取）→ 团队审 |
| C6 | 回复 Alfos 的建议征集（报告生成专业建议） | Hermes 草稿 → Xing 发 |

---

## 三、架构总蓝图

```
              【一个引擎 · 一个知识库】
   ┌─────────────────────────────────────┐
   │  批改引擎 + TSR RAG + 题库 + 模型抽象层   │
   └─────────────────────────────────────┘
        │        │        │        │        │        │
      批改     教案     报告     追踪    学生端   听课分析
    (现成)   (新建)   (新建)   (新建)   (新建)   (新建)
        └────── 共享：SQLite 数据层 + 统一 UI 体系 ──────┘
```

**新增模块（对应文件）**：
- `store/` — SQLite 数据层（批改记录 / 学生 / 成绩 / 自定义评语）
- `privacy/anonymizer.py` — 匿名化管道
- `agents/lesson_planner.py` — 教案生成
- `agents/report_writer.py` — 报告评语生成
- `agents/tracker.py` — 学生追踪分析
- `agents/student_coach.py` — 学生端（出题/答疑）
- `tools/transcript_analyzer.py` — 课堂录音分析
- `data/syllabus.json` — Enterprise Computing 大纲 dot points/outcomes（教案清单数据源）

---

## 四、Phase 执行路线图（7 个阶段）

### Phase 0：准备 ✅ 已完成（9/25）
- [x] C1 项目改名：草拟 8-10 个候选名（英文为主，教育/批改/教练语义，避开 AI 味套路）
- [x] C5 syllabus 提取：NSW Enterprise Computing 大纲 dot points + outcomes → 教案勾选清单初稿
- [ ] C3 iLearn 页面抓取（需 Xing 配合登录）
- [ ] C4 邮件查收提醒
- **验收**：候选名列表 + syllabus 清单 + iLearn 关键信息（比赛时间/评审要求）

### Phase 1：数据层 ✅ 已完成（9/25，commit 5193bde）
- [x] SQLite schema：students / submissions / marks / report_comments / custom_notes
- [x] 存储 API + 现有批改流程接入（每次批改自动落库）
- [x] 迁移脚本（Golden Set 数据可作为演示种子）
- **验收**：批改一次 → 数据库可见完整记录；重跑历史可查

### Phase 2：UI 重设计 + 隐私层 🟡 大部分完成（9/25）
> ✅ 设计稿 v2（docs/design/，双语+真切换）｜✅ 隐私层（privacy/，21 测试 + E2E 验证）｜⏳ UI 落地待设计定稿
- [x] 设计稿：批改页 + 教案页（HTML mockup，先给 Xing/团队过目）
- [x] 视觉落地：批改红纸感设计系统（纸 #FAFAF7 / 墨 / 批改红强调 / 撑满宽度）
- [x] avoid 清单逐项检查（表格形式留档）
- [x] 匿名化管道：姓名/学校 → 占位符 → 还原；UI 对比演示
- **验收**：设计稿确认版 + 新 UI 可交互 + 脱敏演示跑通

### Phase 3：批改升级 + 自建题目 ✅ 已完成（9/25，commits e1e110a/49c16b7）
> ✅ 隐私接入 app 管道｜✅ suggested mark 语气（marker/verifier prompt）｜✅ rubric 引用 + 防瞎编核查｜✅ 自建题目（表单+questions_io+引擎集成，E2E 4/4 分验证）
- [x] 输出语气改造（suggested mark / draft evaluation）
- [x] rubric 逐条引用（结果卡展示"依据：评分标准第 X 行"）
- [x] 自建题目界面（录入表单 → questions.json → 立即可批改）
- **验收**：新题录入 → 批改 → rubric 引用展示全链路

### Phase 4：教案生成（3-4 天）
- [ ] 勾选界面（syllabus dot points 清单）
- [ ] 文档导入（粘贴文本 / 文件上传）
- [ ] 生成引擎（LLM + TSR RAG）→ 结构化教案（目标/活动/评估/时长）
- **依赖**：Alfos 的参考文档（邮件）；未到则用 NESA TSR 材料先建
- **验收**：完整流程演示 + 输出质量样例

### Phase 5：报告生成 + 学生追踪（4-5 天）
- [ ] 报告生成：成绩表输入 + 老师自定义评语 + 性别代词 → NESA 风格评语
- [ ] 学生追踪：进度画像（水平/趋势/薄弱点）+ 教师建议
- **依赖**：Alfos 真实成绩样本；marking criteria 邮件
- **验收**：真实数据跑通 + 与 nswschoolreports 指南原则对照

### Phase 6：学生端 + 课堂录音（L3 最小惊艳版，3-4 天）
- [ ] 学生端：针对性出题 + 对话答疑（复用引擎）
- [ ] 课堂录音分析：转录（faster-whisper 现成）→ syllabus 覆盖检查 → 教研反馈
- [ ] （后置）思维导图渲染
- **验收**：两个可演示原型（各 1 个完整案例）

### Phase 7：整合 QA + 演示彩排（2-3 天）
- [ ] 全功能联调 + 回归测试（Golden Set 不降准）
- [ ] 团队试用轮 + 反馈修复
- [ ] 演示脚本设计（评委动线：批改→追问→教案→报告→追踪→听课）
- [ ] 部署更新 + 报告文档更新
- **验收**：完整演示彩排通过 + 部署在线

---

## 五、职能划分（铁律）

| 角色 | 职责 | 禁止 |
|---|---|---|
| **Hermes 主管道**（主代理） | 计划制定、方案设计、子 Agent 委派、审核验收、向 Xing 汇报、用户沟通稿起草 | ❌ 不亲自写大模块代码（>50 行交给子 Agent） |
| **子 Agent**（delegate_task） | 模块开发（每批 ≤3 并发）、测试、修复 | ❌ 不碰未分配模块；输出必须落文件 |
| **Xing（用户）** | 需求确认、团队沟通（发消息/文档）、收集数据（邮件/样本）、验收演示 | ❌ 不做技术决策盲区（一切经 Hermes 分析） |
| **队友（Alfos/Kla 等）** | 提供样本数据、确认反馈、iLearn 信息、优先级排序 | — |

---

## 六、多 Agent 协作方案

### 6.1 委派原则（硬性）
1. **大项目必用子 Agent 并行**，总管只做计划-审核-验收-汇报
2. 多 Agent 执行方案**先呈 Xing 确认**再动工
3. 子代理超时/报错**先查现场**（文件 mtime + live transcript）再判断，禁自行猜测
4. 需修复时**派专职修复代理**（带崩溃现场），总管不亲自改代码
5. 子 Agent 输出**存文件供审阅**，每 Phase 汇报

### 6.2 Agent 批次设计

| 批次 | Agents（≤3 并发） | 依赖 |
|---|---|---|
| Batch 1 | Agent-Data（SQLite 层）+ Agent-Design（UI mockup 2 页）+ Agent-Research（syllabus 提取）| Phase 0/1 并行 |
| Batch 2 | Agent-Privacy（匿名化）+ Agent-Marking（批改升级+自建题目）| 依赖 Batch 1 设计稿 |
| Batch 3 | Agent-Lesson（教案生成）+ Agent-Report（报告生成）| 依赖数据层 |
| Batch 4 | Agent-Tracker（学生追踪）+ Agent-Student（学生端）| 依赖数据层 + 报告架构 |
| Batch 5 | Agent-Transcript（录音分析）+ Agent-QA（全量回归验证）| 依赖转录管线 |

### 6.3 每批次交付规范
- 交付物：**代码文件 + 测试脚本 + 运行证据（真实输出）**
- 目录规范：模块自含（代码/测试/样例数据）
- 验收：主管道独立复跑验证，**不信任自报**

---

## 七、质量与验证纪律

1. **数据铁律**：所有数字必须真实运行产出，禁编造（违反=返工）
2. **Ground Truth 验证**：每个功能验收时独立复算（如报告：成绩表→评语→核对数据点）
3. **设计验收**：avoid 清单逐项打勾（17 条）
4. **回归底线**：Golden Set 32 份不得降准（78.1%/100% 为底线）
5. **演示数据脱敏**：展示用数据全部过匿名化管道
6. **commit 纪律**：每 Phase 完成 push 一次，含中文说明

---

## 八、沟通与交付节奏

| 对象 | 频率 | 形式 |
|---|---|---|
| Xing | 每 Phase 完成 + 关键决策点 | 中文汇报 + 截图/文件 |
| 团队（Alfos 等） | 里程碑（每 1-2 Phase） | 英文文档/群消息 + 演示链接 |
| 共享文档 | 关键更新时 | 追加式修改（原文保留） |

---

## 九、风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 比赛时间压缩 | 功能做不完 | 分层 L1→L2→L3；每层有可演示版本 |
| 样本数据未到（成绩/评分标准） | 报告/追踪功能悬空 | 先用 Golden Set 种子数据；双轨准备 |
| 参考文档未到（教案） | 教案功能演示缺真实素材 | 用 NESA TSR 先建；文档到了即替换 |
| 录音分析演示数据难准备 | L3 功能演示不实 | 用现有会议转录做首次演示；找课堂录音样本 |
| 团队意见变化 | 返工 | 一切变更走文档确认流程 |
| 名字/IP 问题 | 改名连锁（文档/仓库/演示） | 改名列表 → 团队定；定后统一替换 |

---

## 十、待确认清单（阻塞项）

| # | 事项 | 等待谁 | 状态 |
|---|---|---|---|
| 1 | 队友 GitHub 用户名（开权限用） | Alfos | ⏳ |
| 2 | 功能优先级排序（L1/L2/L3 确认） | Alfos | ⏳ |
| 3 | 真实成绩样本 | Alfos | ⏳ |
| 4 | marking criteria 邮件 | Alfos（今日） | ⏳ |
| 5 | iLearn 页面关键信息（比赛时间线） | Xing + Hermes | ⏳ |
| 6 | 参考文档（教案用） | Alfos | ⏳ |
| 7 | 改名列表确认 | 团队 | ⏳ |

---

## 附：设计 Avoid 清单（验收用，17 条）
purple-blue gradient / gradient hero text / emoji in headings / Inter everywhere / colored border cards / glassmorphism / low-contrast dark mode / 3 icon boxes in a row / badge above headline / lucide icons everywhere / untouched shadcn / fade-in-scroll + cursor beam / hover fade buttons / inconsistent spacing / em dashes / buzzword copy / serif italic accents / Space Grotesk+Instrument Serif / grain over gradient

**我们的替代**：实体色（纸/墨/批改红）、系统字体栈、无图标、考试纸布局、状态型动效、具体语言、零 em dash。
