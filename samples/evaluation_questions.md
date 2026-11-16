# 可复现评估问题

这是一组带人工期望的验收题，不是准确率性能评测。D2 执行 E1 与 E5；D5 对 E1/E2/E3/E4/E7 完成关闭/开启补检的真实成对观察，并复核 E5 基础空检索。E6 没有执行，不能记作通过。

| 编号 | 问题与语料范围 | 人工期望 | D2 观察 |
| --- | --- | --- | --- |
| E1 | 仅 KG²RAG：Which benchmark dataset and its variants were used to evaluate KG2RAG? Answer only from the paper and give source quotes. | 从实际片段回答 HotpotQA；每条引用能在原页面中找到。未检索到的变体不能凭模型记忆补写。 | 已实测。回答 HotpotQA 与 Shuffle-HotpotQA，附实际 PDF 第 2、7 页引用，并说明变体清单证据不完整。 |
| E2 | 仅 KG²RAG：What is the difference between the distractor setting and the fullwiki setting in this paper? | 只使用片段明确描述的设置区别；片段不足时指出缺失，不从外部知识补全。 | 待执行，不能记作通过。 |
| E3 | 仅 LightRAG：LightRAG 的 dual-level retrieval 中，两个层级分别检索什么？ | 引用方法正文解释两个层级；若关键词未召回所需方法段，应报告不足。 | 待执行，不能记作通过。 |
| E4 | 全部三篇：是否能仅根据当前论文断言 LightRAG 在所有检索任务上都优于 KG2RAG？ | 不能将不同论文的实验直接排名。若没有共同实验条件证据，应保留“无法确定”，不可编造比较数值。 | 待执行，不能记作通过。 |
| E5 | 全部语料：zzzxquantumunfindable | 用于检测完全无词面匹配的空检索；引用为空、LLM 调用数为 0，明确报告不足。不是完整的语义无答案评测。 | 已实测。insufficient，0 片段、0 引用、0 模型请求。 |
| E6 | 仅 PaperQA2：What limitations or error sources does this paper explicitly report? | 必须引用限制或误差讨论，不能根据标题推断能力；来源不足时说明不足。 | 待执行，不能记作通过。 |

E1 真实结果见 `artifacts/d2/live-check.json`。E1 的引用文字核对仅证明来源位置存在，不等于科学结论正确。D2 没有 Requirement 或一次补检机制，不报告补检覆盖率。

## D3 缺口与补检案例

- 范围：仅官方 KG²RAG，`mode="audited"`，允许一次补检与术语共现扩展。
- 问题：Which evaluation dataset does KG2RAG use, and what measured energy consumption in joules per query does the paper report? Cite evidence for each; if a measurement is not supported by the excerpts, say it is unknown.
- 期望：数据集能定位来源；缺少每查询能耗时不能用时延数据冒充能耗；补检最多一次，之后保留缺口并停止。
- 最终实测：拆出 2 项需求，1 项有引用支持，能耗需求在一轮补检后仍不足；4 次模型请求（含格式重试）。25 节点 / 47 边的出处、引句与页码、计数和 trace 引用通过脚本核对。报告 `artifacts/d3/live-check.json`；初次存在未被引用片段支持的变体名，已记录并修正保护逻辑，不将初次观察当作验收通过。
- 此案例不代表其他问题已完成评估，也不证明模型支持判断始终正确。

## D5 最终观察

E7 即上面的“数据集 + 焦耳能耗”问题。五个成对输入及人工期望保存在 `samples/d5_questions.json`，完整结果与限制见 [D5 验收记录](../docs/D5_VERIFICATION.md)，原始记录为 `artifacts/d5/`。

| 编号 | D5 关闭补检 | D5 允许一次补检 | 内容核对 |
| --- | --- | --- | --- |
| E1 | 2/2 支持，3 引用，2 请求，3593ms | 2/2 支持，3 引用，2 请求，2922ms；无需补检 | HotpotQA 与 Shuffle-HotpotQA 可定位第 2/5/7 页；构建方式引句有截词，细节需查 PDF |
| E2 | 3/3 支持，3 引用，2 请求，3406ms | 3/3 支持，3 引用，2 请求，3391ms；无需补检 | 第 5 页十篇材料与 66,581 篇候选范围，第 7 页规模差异讨论 |
| E3 | 2/2 支持，2 引用，2 请求，1953ms | 2/2 支持，2 引用，2 请求，2156ms；无需补检 | 第 2 页具体实体/关系与更广主题两级 |
| E4 | 0/3 支持，0 引用，2 请求，4281ms | 1/3 支持，1 引用，3 请求，6437ms；补检一次后停 | 只接受 MuSiQue Table 7 局部比较；所有任务的普遍排名仍不足 |
| E5 | 基础模式 0 片段、0 引用、0 模型请求 | 不作审计模式成对题 | 只检查完全无词面匹配，不冒充语义无答案评测 |
| E6 | 未执行 | 未执行 | 不计入本次五题对比 |
| E7 | 1/2 支持，1 引用，2 请求，2219ms | 1/2 支持，2 引用，3 请求，4422ms；补检一次后停 | 数据集有来源，焦耳能耗不足，不拿毫秒时延替代 |

支持数是模型判断结合引用保护后的系统状态，不是事实正确率。两次独立规划需求，措辞与分解可能不同；E1–E3 使用回答保护相同、解释检查更严格的中间修复版记录并经最终校验复核，E4/E7 为解释上下文修正后重新执行。不是固定规划的因果消融，不能将 +1 支持需求或不同耗时解释为已证明的普遍提升。修复前和过度收紧时的记录均保留，不挑选后隐藏失败；详见 D5 记录。
