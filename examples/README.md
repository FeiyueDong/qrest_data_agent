# examples

## demo_project

固定演示工程：Kunming_SSJY（真实输入文档）

- source/report.pdf、source/design.docx：Kunming_building_metadata_test_case
  （实际工程说明，PDF/DOCX 内容一致）
- expected/metadata.json：data/kunming/metadata.json 参考答案
- output/metadata.json：完整的 qREST_DATA 元数据（18 通道）

运行：

    qrest-agent parse
    qrest-agent validate

## benchmark_cases

五个固定 Agent Benchmark 案例（case01 … case05）。每个案例都是独立 qREST
工程，包含 expected/metadata.json 参考答案与 CHECKLIST.md。

## input_doc

Agent 测试用的真实工程文档原件（PDF + DOCX），demo 与 case03/case04/case05
均从该目录复制 source。
