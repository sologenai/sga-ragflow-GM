#!/usr/bin/env python3
"""
RAGFlow 知识图谱 API 快速调用示例
最简单的使用方法演示
"""

from chinese_graph_api import ChineseGraphRAGAPI
import json

def quick_demo():
    """快速演示：5分钟上手知识图谱API"""
    
    print("🚀 RAGFlow 知识图谱 API 快速演示")
    print("=" * 50)
    
    # 1. 创建API实例
    api = ChineseGraphRAGAPI(
        base_url="http://localhost:9380",
        api_key="ragflow-BlMGQyNzM4OTBhNzExZjA4MzU4ZGU3NW"  # 您的API密钥
    )
    
    kb_id = "dc949110906a11f08b78aa7cd3e67281"  # 您的知识库ID
    
    # 2. 获取中文化知识图谱
    print("\n📊 获取知识图谱...")
    graph = api.get_chinese_knowledge_graph(kb_id)
    
    if 'error' in graph:
        print(f"❌ 错误: {graph['error']}")
        return
    
    nodes = graph['data']['graph']['nodes']
    edges = graph['data']['graph']['edges']
    
    print(f"✅ 成功！图谱包含 {len(nodes)} 个实体，{len(edges)} 个关系")
    
    # 3. 显示实体类型分布
    print("\n📈 实体类型分布:")
    stats = api.get_entity_statistics(kb_id)
    for entity_type, count in stats['entity_type_distribution'].items():
        print(f"  {entity_type}: {count} 个")
    
    # 4. 显示重要实体
    print("\n⭐ 最重要的5个实体:")
    top_nodes = sorted(nodes, key=lambda x: x.get('pagerank', 0), reverse=True)[:5]
    for i, node in enumerate(top_nodes):
        print(f"  {i+1}. {node['entity_name']} ({node['entity_type']}) - 重要性: {node.get('pagerank', 0):.3f}")
    
    # 5. 查看具体实体详情
    print(f"\n🔍 查看实体详情: {top_nodes[0]['entity_name']}")
    node_info = api.get_node_source_info(kb_id, top_nodes[0]['id'])
    
    if 'error' not in node_info:
        print(f"  类型: {node_info['node_type']}")
        print(f"  来源文件: {node_info['source_files_count']} 个")
        print(f"  描述: {node_info['description'][:100]}...")
    
    # 6. 搜索特定类型的实体
    print(f"\n🏢 组织类实体 (前5个):")
    org_nodes = [n for n in nodes if n['entity_type'] == '组织'][:5]
    for i, node in enumerate(org_nodes):
        print(f"  {i+1}. {node['entity_name']} (文件数: {node['source_files_count']})")
    
    print(f"\n👥 人员类实体 (前5个):")
    person_nodes = [n for n in nodes if n['entity_type'] == '人员'][:5]
    for i, node in enumerate(person_nodes):
        print(f"  {i+1}. {node['entity_name']} (重要性: {node.get('pagerank', 0):.3f})")
    
    print("\n🎉 演示完成！")

def simple_search_demo():
    """简单搜索演示"""
    print("\n" + "=" * 50)
    print("🔍 简单搜索演示")
    print("=" * 50)
    
    api = ChineseGraphRAGAPI(
        base_url="http://localhost:9380",
        api_key="ragflow-BlMGQyNzM4OTBhNzExZjA4MzU4ZGU3NW"
    )
    
    kb_id = "dc949110906a11f08b78aa7cd3e67281"
    
    # 获取图谱数据
    graph = api.get_chinese_knowledge_graph(kb_id)
    if 'error' in graph:
        print(f"❌ 错误: {graph['error']}")
        return
    
    nodes = graph['data']['graph']['nodes']
    
    # 搜索关键词
    keywords = ["财务", "安全", "审批", "管理"]
    
    for keyword in keywords:
        print(f"\n🔍 搜索关键词: '{keyword}'")
        
        # 在实体名称中搜索
        matching_nodes = [
            node for node in nodes 
            if keyword in node.get('entity_name', '')
        ]
        
        if matching_nodes:
            print(f"  找到 {len(matching_nodes)} 个相关实体:")
            for i, node in enumerate(matching_nodes[:3]):  # 只显示前3个
                print(f"    {i+1}. {node['entity_name']} ({node['entity_type']})")
        else:
            print(f"  未找到包含'{keyword}'的实体")

def relationship_demo():
    """关系分析演示"""
    print("\n" + "=" * 50)
    print("🔗 关系分析演示")
    print("=" * 50)
    
    api = ChineseGraphRAGAPI(
        base_url="http://localhost:9380",
        api_key="ragflow-BlMGQyNzM4OTBhNzExZjA4MzU4ZGU3NW"
    )
    
    kb_id = "dc949110906a11f08b78aa7cd3e67281"
    
    graph = api.get_chinese_knowledge_graph(kb_id)
    if 'error' in graph:
        print(f"❌ 错误: {graph['error']}")
        return
    
    nodes = graph['data']['graph']['nodes']
    edges = graph['data']['graph']['edges']
    
    # 分析核心实体的关系网络
    core_entity = "厦门国贸股份有限公司"
    
    print(f"🏢 分析 '{core_entity}' 的关系网络:")
    
    # 找到相关的边
    related_edges = [
        edge for edge in edges 
        if edge['source'] == core_entity or edge['target'] == core_entity
    ]
    
    print(f"  直接关系数: {len(related_edges)}")
    
    # 统计关联的实体类型
    connected_entities = set()
    for edge in related_edges:
        if edge['source'] == core_entity:
            connected_entities.add(edge['target'])
        else:
            connected_entities.add(edge['source'])
    
    # 按类型分组
    entity_types = {}
    for entity_id in connected_entities:
        entity_info = next((n for n in nodes if n['id'] == entity_id), None)
        if entity_info:
            entity_type = entity_info['entity_type']
            if entity_type not in entity_types:
                entity_types[entity_type] = []
            entity_types[entity_type].append(entity_info['entity_name'])
    
    print(f"  关联实体类型分布:")
    for entity_type, entities in entity_types.items():
        print(f"    {entity_type}: {len(entities)} 个")
        for entity in entities[:3]:  # 只显示前3个
            print(f"      - {entity}")
        if len(entities) > 3:
            print(f"      - ... 还有 {len(entities) - 3} 个")

def export_demo():
    """数据导出演示"""
    print("\n" + "=" * 50)
    print("💾 数据导出演示")
    print("=" * 50)
    
    api = ChineseGraphRAGAPI(
        base_url="http://localhost:9380",
        api_key="ragflow-BlMGQyNzM4OTBhNzExZjA4MzU4ZGU3NW"
    )
    
    kb_id = "dc949110906a11f08b78aa7cd3e67281"
    
    # 获取数据
    graph = api.get_chinese_knowledge_graph(kb_id)
    if 'error' in graph:
        print(f"❌ 错误: {graph['error']}")
        return
    
    # 导出为JSON文件
    output_file = "knowledge_graph_chinese.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 图谱数据已导出到: {output_file}")
    
    # 导出实体列表为CSV格式的文本
    nodes = graph['data']['graph']['nodes']
    csv_file = "entities_list.csv"
    
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("实体名称,实体类型,重要性,来源文件数\n")
        for node in nodes:
            f.write(f"{node['entity_name']},{node['entity_type']},{node.get('pagerank', 0):.3f},{node['source_files_count']}\n")
    
    print(f"✅ 实体列表已导出到: {csv_file}")
    
    # 统计信息
    stats = api.get_entity_statistics(kb_id)
    stats_file = "graph_statistics.txt"
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("知识图谱统计信息\n")
        f.write("=" * 30 + "\n")
        f.write(f"总节点数: {stats['total_nodes']}\n")
        f.write(f"总边数: {stats['total_edges']}\n")
        f.write(f"文件覆盖率: {stats['coverage_rate']}\n")
        f.write("\n实体类型分布:\n")
        for entity_type, count in stats['entity_type_distribution'].items():
            f.write(f"  {entity_type}: {count} 个\n")
    
    print(f"✅ 统计信息已导出到: {stats_file}")

def main():
    """运行所有演示"""
    try:
        quick_demo()
        simple_search_demo()
        relationship_demo()
        export_demo()
        
        print("\n" + "=" * 50)
        print("🎉 所有演示完成！")
        print("=" * 50)
        print("\n📝 生成的文件:")
        print("  - knowledge_graph_chinese.json (完整图谱数据)")
        print("  - entities_list.csv (实体列表)")
        print("  - graph_statistics.txt (统计信息)")
        
    except Exception as e:
        print(f"\n❌ 运行出错: {str(e)}")
        print("\n🔧 请检查:")
        print("  1. RAGFlow 服务是否运行")
        print("  2. API 密钥是否正确")
        print("  3. chinese_graph_api.py 文件是否存在")

if __name__ == "__main__":
    main()
