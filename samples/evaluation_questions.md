# 可复现评估问题

这是一组带人工期望的验收题，不是已完成的性能评测。D2 只执行 E1 与 E5；D5 再记录同组问题在开启/关闭补检时的差异。

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
