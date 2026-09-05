# examples

## demo_project

固定演示工程：Kunming Building。

source/ 包含 PDF、DOCX、XLSX、TXT、JSON 五类资料；parsed/ 已生成；
output/metadata.json 为 Schema-valid 的完整结果。运行：

    qrest-agent validate

## benchmark_cases

五个固定 Agent Benchmark 案例（case01 … case05）。每个案例都是独立
qREST 工程，包含 expected/ 参考答案与 CHECKLIST.md。

运行方式示例（case04）：

    cd benchmark_cases/case04_pdf_xlsx
    qrest-agent parse
    qrest-agent validate
