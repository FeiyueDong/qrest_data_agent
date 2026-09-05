# Project

Name: Case 05 - Conflicting / Missing Information（Kunming_SSJY）

## User Description

source/report.pdf 与 source/note.txt 对同一建筑的部分参数描述冲突
（见 expected/REPORT.md）。不要擅自选值：冲突字段保留基准数据
（data/kunming/metadata.json），并在汇报中向用户说明。

## Goal

output/metadata.json 通过 qrest-agent validate（无 ERROR）。
