# qREST Metadata Agent (V0.21)

你的任务：把 source/ 中的工程资料（以及用户在 PROJECT.md 中给出的说明）忠实整理为
Extraction State（working/facts.json + working/issues.json），由程序判断
Readiness 并严格导出 output/metadata.json。

你不要手工编辑 output/metadata.json；它只由

    qrest-agent export

在状态 READY 时生成。

## Sources

原始工程资料位于 source/；解析结果位于 parsed/。先运行：

    qrest-agent parse

并优先阅读 parsed/PROJECT_INDEX.md，再按需读取 document.md / workbook.md / CSV。

## Working Principle

- 你的首要任务是忠实记录工程资料中的信息。
- 所有可靠信息写入 working/facts.json。
- 缺失、部分、冲突、不确定的信息写入 working/issues.json。
- 不得为了满足最终 qREST_DATA Schema：
  1. 删除已经知道的信息；
  2. 将已知数值改成 0 / UNKNOWN / 空；
  3. 编造缺失字段；
  4. 任意解决冲突。
- 未知 != 0：Extraction State 中不存在的 Fact 就是未知，不要用 0 表示未知。

完成事实整理后运行：

    qrest-agent status

只有 Status = READY 时才能运行：

    qrest-agent export

导出后的 output/metadata.json 会自动经过严格 Validator。

## facts.json 结构

    {
      "version": 1,
      "facts": [
        {
          "key": "building.height",
          "value": 47.4,
          "unit": "m",
          "provenance": "document",
          "source": {"file": "report.pdf", "location": {"page": 1}}
        }
      ]
    }

Fact 字段：key（点分语义键）、value（任意 JSON）、unit（可选）、
provenance（user/document/derived/default）、source（可选）、
derived_from（可选）、note（可选）。

常用 key（值必须是忠实原值，不能为 Schema 改写）：

    building.project_name         字符串
    building.geo_location         {Longitude, Latitude, NorthAngle}
    building.geo.longitude/latitude/north_angle  数值（或整体 geo_location）
    building.structural_type      字符串，如 SteelFrame
    building.footprint.shape      Rectangular | Polygon | Circular
    building.footprint.length     m
    building.footprint.width      m
    building.footprint.corners    [[x, y], ...]
    building.footprint.radius     m
    building.bounding_box         {MaxX, MinX, MaxY, MinY}
    building.elevations           [z0, z1, ...]（m）
    monitoring.provider           字符串
    monitoring.channel_count      整数（知道 18 就写 18，即使没有明细）
    monitoring.channels           [通道对象...]
    data.event_name               字符串
    data.start_time               时间字符串
    data.npts                     整数
    data.dt                       秒
    data.corrected                如 "NULL"

monitoring.channels 每个对象至少包含（缺少哪个就在 issues.json 中记 partial）：

    ChannelNo, Measurand, Scale, Azimuth, LocationXYZ

可选的通道字段：ChannelID、DeviceType（资料没有可以不写）。

## issues.json 结构

    {
      "version": 1,
      "issues": [
        {
          "type": "missing",
          "key": "monitoring.channels",
          "severity": "blocking",
          "message": "Channel count is 18 but channel definitions are unavailable."
        }
      ]
    }

type：missing / partial / conflict / uncertain（整体 INVALID 状态由程序在 State 结构/映射错误时产生，Agent 不写 invalid issue）
severity：blocking / warning / info

- 知道 channel_count=18 但没有任何通道明细 → missing blocking
- 知道 18 但只有 12 个明细 → partial blocking（同时 facts 中保留 18 与 12 个定义）
- 两个来源数值不同 → conflict blocking，candidates 里保留全部候选，
  不要任选其一
- 证据不足 → uncertain warning
- 资料冲突/缺失无法解决时，status 不会是 READY，禁止为导出编造数值。

## Defaults（由程序负责，不是 Agent）

Exporter 可以根据 qREST_DATA Contract 生成协议默认值（例如 "UNKNOWN" /
"NULL" / 0）；这些值仅存在于最终 Metadata 中，不会被写回 Extraction State，
也不代表提取到的事实。Agent 不得把这些默认值当作事实写进 facts.json。

## Units（单位原则）

- 保留资料中的原始数值和单位（value + unit）。
- 不要为了最终 qREST_DATA 自行换算单位。
- 单位换算由 qrest-agent export 的确定性逻辑负责。
- 例如资料写 20 ms：应写 value=20、unit="ms"，不要自己改成 0.02 s。
- 支持单位：长度 m/cm/mm；时间 s/ms/us；角度 deg/degree/degrees/°。
- monitoring.channels[].LocationXYZ 在 Extraction State 中默认使用米。

## Workflow

1. 阅读 PROJECT.md 与 AGENTS.md；
2. 查看 source/，运行 qrest-agent parse；
3. 阅读 parsed/PROJECT_INDEX.md 并搜索资料；
4. 将可靠信息写入 working/facts.json（保留所有已知信息与来源）；
5. 将缺失/部分/冲突/不确定写入 working/issues.json；
6. 运行 qrest-agent status；
7. Status = NEEDS_INPUT / CONFLICT 时：继续补充或明确汇报，不得 export；
8. Status = READY 时运行 qrest-agent export；
9. 对 output/metadata.json 运行 qrest-agent validate（应 0 ERROR）。

不要为了遵循固定流程执行无意义步骤；事实忠实、状态明确、导出严格。
