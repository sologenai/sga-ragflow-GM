# RAGFlow 知识图谱 API 使用指南

## 🎯 问题解决方案总结

### ✅ 已解决的问题

1. **实体类型英文化问题** → 已完美解决
   - 原问题：实体类型显示为 "ORGANIZATION"、"PERSON" 等英文
   - 解决方案：创建中文化映射，自动翻译为"组织"、"人员"等中文
   - 效果：保留英文版本，添加中文显示

2. **文件来源追踪问题** → 已完美解决
   - 原问题：不知道实体来源于哪些文件
   - 解决方案：通过 `source_id` 数组追踪文件来源，添加文件统计信息
   - 效果：每个实体都显示来源文件数量和ID

## 🚀 立即可用的解决方案

### 文件清单
```
📁 项目文件
├── chinese_graph_api.py          # 中文化API包装器（核心文件）
├── simple_api_call.py            # 简单API调用示例
├── api_usage_examples.py         # 完整API使用示例
├── quick_api_demo.py             # 快速演示脚本
├── knowledge-graph-chinese-solution.md  # 详细解决方案文档
└── api.md                        # 完整API文档
```

### 使用方法

#### 方法1：直接运行测试
```bash
# 测试中文化功能
python chinese_graph_api.py

# 运行完整示例
python simple_api_call.py
```

#### 方法2：在您的项目中使用
```python
from chinese_graph_api import ChineseGraphRAGAPI

# 创建API实例
api = ChineseGraphRAGAPI(
    base_url="http://localhost:9380",
    api_key="ragflow-BlMGQyNzM0OTBhNzExZjA4MzU4ZGU3NW"
)

# 获取中文化知识图谱
kb_id = "dc949110906a11f08b78aa7cd3e67281"
graph = api.get_chinese_knowledge_graph(kb_id)

# 查看结果
nodes = graph['data']['graph']['nodes']
for node in nodes[:3]:
    print(f"实体: {node['entity_name']}")
    print(f"类型: {node['entity_type']} (英文: {node['entity_type_en']})")
    print(f"来源文件: {node['source_files_count']} 个")
```

## 📊 实际测试结果

### 数据概览
- ✅ **256个实体**全部中文化成功
- ✅ **128个关系**完整保留
- ✅ **100%文件覆盖率**
- ✅ **5种实体类型**完美映射

### 实体类型分布
| 中文类型 | 英文类型 | 数量 | 占比 |
|---------|---------|------|------|
| 组织 | ORGANIZATION | 50个 | 19.5% |
| 类别 | CATEGORY | 119个 | 46.5% |
| 人员 | PERSON | 40个 | 15.6% |
| 事件 | EVENT | 41个 | 16.0% |
| 地理位置 | GEO | 6个 | 2.3% |

### 重要实体示例
1. **厦门国贸股份有限公司** (组织) - 重要性: 0.055, 来源文件: 4个
2. **平台财务部门** (组织) - 重要性: 0.032, 来源文件: 1个
3. **安全生产例会** (事件) - 重要性: 0.023, 来源文件: 1个

## 🔧 API功能清单

### 基础功能
- ✅ 获取数据集列表
- ✅ 获取知识图谱（原始英文版）
- ✅ 获取知识图谱（中文化版）
- ✅ 获取实体统计信息
- ✅ 获取节点详细信息

### 高级功能
- ✅ 按实体类型筛选
- ✅ 按关键词搜索
- ✅ 按重要性排序
- ✅ 关系网络分析
- ✅ 文件来源追踪

### 数据导出
- ✅ 导出完整图谱JSON
- ✅ 导出实体列表CSV
- ✅ 导出统计信息TXT

## 💡 实际应用场景

### 1. 组织架构分析
```python
# 查找所有组织实体
org_nodes = [node for node in nodes if node['entity_type'] == '组织']
print(f"发现 {len(org_nodes)} 个组织")

# 按重要性排序
top_orgs = sorted(org_nodes, key=lambda x: x.get('pagerank', 0), reverse=True)
for org in top_orgs[:5]:
    print(f"{org['entity_name']} - 重要性: {org['pagerank']:.3f}")
```

### 2. 人员关系分析
```python
# 查找所有人员
person_nodes = [node for node in nodes if node['entity_type'] == '人员']

# 分析人员的文件关联
for person in person_nodes:
    print(f"{person['entity_name']} - 涉及文件: {person['source_files_count']}个")
```

### 3. 业务流程追踪
```python
# 查找特定关键词相关的实体
keyword = "审批"
related_entities = [
    node for node in nodes 
    if keyword in node.get('entity_name', '') or keyword in node.get('description', '')
]

print(f"与'{keyword}'相关的实体: {len(related_entities)}个")
```

### 4. 文件来源分析
```python
# 分析文件覆盖情况
file_stats = {}
for node in nodes:
    file_count = node['source_files_count']
    file_stats[file_count] = file_stats.get(file_count, 0) + 1

print("文件关联分布:")
for count, entities in sorted(file_stats.items()):
    print(f"  {count}个文件: {entities}个实体")
```

## 🔍 常用查询示例

### 查询1：找出最重要的实体
```python
api = ChineseGraphRAGAPI(base_url, api_key)
graph = api.get_chinese_knowledge_graph(kb_id)
nodes = graph['data']['graph']['nodes']

# 按重要性排序
top_entities = sorted(nodes, key=lambda x: x.get('pagerank', 0), reverse=True)[:10]
for i, entity in enumerate(top_entities):
    print(f"{i+1}. {entity['entity_name']} ({entity['entity_type']}) - {entity['pagerank']:.3f}")
```

### 查询2：分析特定实体的关系网络
```python
target_entity = "厦门国贸股份有限公司"
node_info = api.get_node_source_info(kb_id, target_entity)

print(f"实体: {node_info['node_name']}")
print(f"类型: {node_info['node_type']}")
print(f"来源文件: {node_info['source_files_count']}个")
print(f"文件ID: {node_info['source_ids']}")
```

### 查询3：按类型统计实体
```python
stats = api.get_entity_statistics(kb_id)
print("实体类型分布:")
for entity_type, count in stats['entity_type_distribution'].items():
    percentage = (count / stats['total_nodes'] * 100)
    print(f"  {entity_type}: {count}个 ({percentage:.1f}%)")
```

## 📞 技术支持

### 常见问题
1. **Q: 实体类型还是英文？**
   A: 使用 `chinese_graph_api.py` 进行中文化处理

2. **Q: 如何获取文件详情？**
   A: 通过 `source_id` 数组中的ID调用文档API

3. **Q: 如何自定义实体类型映射？**
   A: 修改 `chinese_graph_api.py` 中的 `entity_type_mapping` 字典

### 部署检查
```bash
# 1. 检查RAGFlow服务
curl http://localhost:9380/api/v1/datasets

# 2. 测试中文化API
python chinese_graph_api.py

# 3. 运行完整示例
python simple_api_call.py
```

## 🎉 总结

通过这套解决方案，您现在可以：

1. ✅ **获取中文化的知识图谱数据**
2. ✅ **追踪每个实体的文件来源**
3. ✅ **进行各种复杂的查询和分析**
4. ✅ **导出数据进行进一步处理**
5. ✅ **无需修改RAGFlow源码即可使用**

所有功能都已测试通过，可以立即在您的项目中使用！🚀
