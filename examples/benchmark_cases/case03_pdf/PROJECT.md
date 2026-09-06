# Project

Name: Case 03 - PDF Source（Kunming_SSJY）

## User Description

工程资料为 source/report.pdf（Kunming_building_metadata_test_case）。
请从 PDF 中识别楼层、结构、测点布置与事件采样参数并生成 qREST_DATA 元数据。
PDF 未给出精确坐标/通道明细时，不得编造 LocationXYZ 或 Channels，请在汇报中列出缺失。

## Goal

建立符合 qREST_DATA 格式的 output/metadata.json 并运行 qrest-agent validate。
