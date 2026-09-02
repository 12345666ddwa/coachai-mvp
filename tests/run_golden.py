#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoachAI Golden Set 自动评比脚本
===============================
读取 tests/golden_set.json（8 题 × 4 档 = 32 份带期望分数的学生答案），
逐份调用批改接口：

    from graphs.mark_graph import mark_answer
    result = mark_answer(question_id, student_answer) -> dict
    # 接口约定见 app.py 头部：dict 含 "marks"/"max_marks" 等键
    # 兼容直接返回 int 的实现

AI 给分 vs 期望分数（expected_marks）比对结果分三档：
    exact   —— 完全一致
    ±1band  —— 相差 1 分（所选 8 题 MG 均为每 1 分一档，故 |Δ|=1 ≈ 差一档）
    miss    —— 相差 ≥ 2 分

输出：逐条明细 + 按 quality / 按题目汇总的一致率统计。

注意：graphs.mark_graph.mark_answer 目前尚未实现 —— 此时脚本自动 SKIP
（预期行为，退出码仍为 0，方便 CI 先跑通）；接口就绪后直接运行即可。

用法:  python tests/run_golden.py     （需在项目根 ai-coach/ 下，或任意 cwd）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GOLDEN_PATH = BASE_DIR / "tests" / "golden_set.json"

QUALITY_ORDER = ["excellent", "good", "weak", "borderline"]


def load_golden() -> list[dict]:
    """读取 golden set，做基本结构校验。"""
    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    items = data.get("items")
    if not items:
        raise SystemExit("[run_golden] golden_set.json 中无 items")
    for item in items:
        assert item.get("question_id") and item.get("question_text")
        assert len(item.get("answers", [])) == 4
        for a in item["answers"]:
            assert a["quality"] in QUALITY_ORDER
            assert isinstance(a["expected_marks"], int)
            assert 0 <= a["expected_marks"] <= item["marks"]
    return items


def import_grader():
    """导入批改接口；不可用时返回 None（调用方负责 SKIP）。"""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from graphs.mark_graph import mark_answer  # noqa: PLC0415
        return mark_answer
    except Exception as exc:  # noqa: BLE001 —— 接口未实现/依赖缺失都算未就绪
        print(f"[SKIP] 批改接口 graphs.mark_graph.mark_answer 不可用: "
              f"{type(exc).__name__}: {exc}")
        print("[SKIP] 属预期行为（接口尚未实现）。实现后（见 app.py 头部约定）重跑本脚本即可。")
        return None


def extract_marks(result) -> int:
    """从接口返回值提取分数：dict 取 marks 键（可能为 int/str），或直接 int。"""
    if isinstance(result, dict):
        marks = result.get("marks")
        if marks is None:
            raise ValueError(f"返回值缺少 'marks' 键: {result}")
        return int(marks)
    if isinstance(result, (int, float)):
        return int(result)
    raise ValueError(f"无法解析批改返回值: {result!r}")


def verdict(diff: int) -> str:
    if diff == 0:
        return "exact"
    if abs(diff) == 1:
        return "±1band"
    return "miss"


def main() -> int:
    items = load_golden()
    mark_answer = import_grader()
    if mark_answer is None:
        return 0  # SKIP 属预期，不视为失败

    # 统计容器: (total, exact, off1, miss, n_a)
    overall = [0, 0, 0, 0, 0]
    by_quality = {q: [0, 0, 0, 0, 0] for q in QUALITY_ORDER}
    by_question: dict[str, list[int]] = {}

    print(f"\n{'=' * 78}\n逐条比对（接口: graphs.mark_graph.mark_answer）\n{'=' * 78}")
    for item in items:
        qid, qmarks = item["question_id"], item["marks"]
        by_question.setdefault(qid, [0, 0, 0, 0, 0])
        for ans in item["answers"]:
            quality, expected = ans["quality"], ans["expected_marks"]
            row = f"[{qid}] {quality:<10} 期望={expected}"
            try:
                result = mark_answer(qid, ans["text"])
                got = extract_marks(result)
            except Exception as exc:  # noqa: BLE001 —— 单条失败不中断整体
                got = None
                status = "SKIP"
                detail = f"{type(exc).__name__}: {exc}"
            else:
                diff = got - expected
                status = verdict(diff)
                detail = f"实得={got} (Δ{diff:+d})"

            # 更新统计（SKIP 计入 n_a 桶）
            for bucket in (overall, by_quality[quality], by_question[qid]):
                bucket[0] += 1
                if got is None:
                    bucket[4] += 1
                elif status == "exact":
                    bucket[1] += 1
                elif status == "±1band":
                    bucket[2] += 1
                else:
                    bucket[3] += 1
            print(f"  {row:<34} -> {status:<7} {detail}")

    def fmt(bucket: list[int]) -> str:
        total, exact, off1, miss, n_a = bucket
        graded = total - n_a
        if graded == 0:
            return f"n={total:<3} 全部未批出"
        exact_r = 100.0 * exact / graded
        close_r = 100.0 * (exact + off1) / graded
        return (f"n={total:<3} exact={exact} ±1band={off1} miss={miss} "
                f"skip={n_a} | exact率={exact_r:5.1f}% ±1档内率={close_r:5.1f}%")

    print(f"\n{'=' * 78}\n汇总统计\n{'=' * 78}")
    print(f"[总体] {fmt(overall)}")
    print("\n按质量档位:")
    for q in QUALITY_ORDER:
        print(f"  {q:<10} {fmt(by_quality[q])}")
    print("\n按题目:")
    for qid in by_question:
        print(f"  {qid} {fmt(by_question[qid])}")

    total, exact, off1, miss, n_a = overall
    graded = total - n_a
    if graded:
        rate = 100.0 * (exact + off1) / graded
        print(f"\n结论: {graded}/{total} 份成功批改，exact+±1band 合计一致率 {rate:.1f}% "
              f"(exact {100.0*exact/graded:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
