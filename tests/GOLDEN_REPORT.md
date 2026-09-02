# CoachAI Golden Set 回归报告

- 日期: 2026-09-02
- 数据集: tests/golden_set.json (8 题 x 4 质量档 = 32 份模拟学生答案)
- 题目来源: 2025 HSC Enterprise Computing 真题 (首届 HSC 考试)
- 期望分数: 依据 NESA 官方 Marking Guidelines 人工标定 (q24 weak 经复核修正为 band 2)
- 引擎: LangGraph Workflow 1 (Marker + Verifier + RAG + 置信度混合)
- 模型: DeepSeek deepseek-v4-flash
- 运行: python3 tests/run_golden.py (exit_code=0, 32/32 成功, skip=0)

## 汇总统计

| 指标 | 结果 |
|---|---|
| 完全一致率 (exact) | 25/32 = 78.1% |
| ±1 档内一致率 | 32/32 = 100.0% |
| 离谱评分 (miss, >=2 档) | 0 |
| 失败/跳过 | 0 (verifier max_tokens 截断 bug 已修复) |

## 按质量档位

| 档位 | exact | ±1band | miss | exact率 | ±1档内率 |
|---|---|---|---|---|---|
| excellent (优) | 8 | 0 | 0 | 100.0% | 100.0% |
| good (好) | 7 | 1 | 0 | 87.5% | 100.0% |
| weak (差) | 6 | 2 | 0 | 75.0% | 100.0% |
| borderline (边界) | 4 | 4 | 0 | 50.0% | 100.0% |

## 按题目

| 题目 | exact | ±1band | miss | skip |
|---|---|---|---|---|
| ec2025-q14 | 3 | 1 | 0 | 0 |
| ec2025-q16a | 3 | 1 | 0 | 0 |
| ec2025-q16b | 4 | 0 | 0 | 0 |
| ec2025-q17a | 3 | 1 | 0 | 0 |
| ec2025-q20 | 3 | 1 | 0 | 0 |
| ec2025-q22a | 2 | 2 | 0 | 0 |
| ec2025-q22b | 4 | 0 | 0 | 0 |
| ec2025-q24 | 3 | 1 | 0 | 0 |

## 解读

- 优/好档答案 100%/87.5% 完全一致 —— 系统对高质量答案的认可非常可靠
- 边界答案 100% 落在 ±1 档内 —— 这正是产品设计的用武之地: AI 拿不准时由 Verifier 标记、老师复核
- 零离谱评分 —— 没有出现"给差答案高分"或"给优答案低分"的严重错误
- 单人验证 (人工标定) 本身也存在主观性; 真实考试场景中两位老师独立评分也有 ±1 档分歧
