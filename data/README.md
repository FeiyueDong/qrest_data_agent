# data/ — qREST 示例数据

- metadata.json：qREST_DATA 元数据格式的**注释版模板**。其中的 // 注释不是
  JSON 语法，仅用于说明字段重要性（必须 / 重要 / 不重要），机器校验请使用
  schema/metadata.schema.json。
- kunming/：昆明工程示例
  - metadata.json —— 完整机器 JSON（18 通道），同时是 Validator 固定合法样例
  - data.txt —— 30000 行、每行 18 个加速度值（文本形态）
  - kunming.qrest —— 对应 .qrest 二进制记录
- wuhan/：武汉工程示例
  - metadata.json —— 完整机器 JSON（27 通道，Elevation 63 个）
  - data.txt / wuhan.qrest —— 对应波形记录

V0.1 处理边界：Agent 负责整理 metadata.json；波形文件（.qrest / data.txt）
由 qREST 数据层使用，V0.1 不解析波形内容。
