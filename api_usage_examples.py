#!/usr/bin/env python3
"""
RAGFlow 知识图谱 API 调用实例
包含原生API和中文化API的完整使用示例
"""

import requests
import json
from chinese_graph_api import ChineseGraphRAGAPI
from typing import Dict, List, Any

# 配置信息
BASE_URL = "http://localhost:9380"
API_KEY = "ragflow-BlMGQyNzM0OTBhNzExZjA4MzU4ZGU3NW"
KB_ID = "dc949110906a11f08b78aa7cd3e67281"

def example_1_basic_api_calls():
    """示例1：基础API调用"""
    print("=" * 60)
    print("📋 示例1：基础API调用")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 1. 获取数据集列表
    print("\n1️⃣ 获取数据集列表")
    response = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
    datasets = response.json()
    
    print(f"状态码: {response.status_code}")
    print(f"数据集数量: {len(datasets.get('data', []))}")
    
    if datasets.get('data'):
        dataset = datasets['data'][0]
        print(f"数据集名称: {dataset['name']}")
        print(f"数据集ID: {dataset['id']}")
        print(f"文档数量: {dataset['document_count']}")
        print(f"分块数量: {dataset['chunk_count']}")
    
    # 2. 获取知识图谱（原始英文版本）
    print("\n2️⃣ 获取知识图谱（原始版本）")
    response = requests.get(f"{BASE_URL}/api/v1/datasets/{KB_ID}/knowledge_graph", headers=headers)
    graph_data = response.json()
    
    if graph_data.get('data'):
        nodes = graph_data['data']['graph']['nodes']
        edges = graph_data['data']['graph']['edges']
        
        print(f"节点数量: {len(nodes)}")
        print(f"边数量: {len(edges)}")
        
        # 显示前2个节点（英文版本）
        print("\n📊 原始节点示例（英文）:")
        for i, node in enumerate(nodes[:2]):
            print(f"  节点{i+1}:")
            print(f"    名称: {node['entity_name']}")
            print(f"    类型: {node['entity_type']} (英文)")
            print(f"    重要性: {node.get('pagerank', 0):.3f}")
            print(f"    来源文件数: {len(node.get('source_id', []))}")

def example_2_chinese_api():
    """示例2：中文化API调用"""
    print("\n" + "=" * 60)
    print("🇨🇳 示例2：中文化API调用")
    print("=" * 60)
    
    # 创建中文化API实例
    chinese_api = ChineseGraphRAGAPI(BASE_URL, API_KEY)
    
    # 1. 获取中文化知识图谱
    print("\n1️⃣ 获取中文化知识图谱")
    chinese_graph = chinese_api.get_chinese_knowledge_graph(KB_ID)
    
    if 'error' not in chinese_graph:
        nodes = chinese_graph['data']['graph']['nodes']
        edges = chinese_graph['data']['graph']['edges']
        
        print(f"✅ 成功获取中文化图谱")
        print(f"节点数量: {len(nodes)}")
        print(f"边数量: {len(edges)}")
        
        # 显示前3个节点（中文版本）
        print("\n📊 中文化节点示例:")
        for i, node in enumerate(nodes[:3]):
            print(f"  节点{i+1}:")
            print(f"    名称: {node['entity_name']}")
            print(f"    类型: {node['entity_type']} (中文)")
            print(f"    英文类型: {node.get('entity_type_en', 'N/A')}")
            print(f"    重要性: {node.get('pagerank', 0):.3f}")
            print(f"    来源文件数: {node['source_files_count']}")
            print(f"    有源文件: {'是' if node['has_source_files'] else '否'}")
            print()
    
    # 2. 获取实体统计
    print("2️⃣ 获取实体统计信息")
    stats = chinese_api.get_entity_statistics(KB_ID)
    
    if 'error' not in stats:
        print(f"✅ 统计信息:")
        print(f"  总节点数: {stats['total_nodes']}")
        print(f"  总边数: {stats['total_edges']}")
        print(f"  文件覆盖率: {stats['coverage_rate']}")
        print(f"  有源文件的节点: {stats['nodes_with_source_files']}")
        
        print("\n📈 实体类型分布:")
        for entity_type, count in stats['entity_type_distribution'].items():
            percentage = (count / stats['total_nodes'] * 100) if stats['total_nodes'] > 0 else 0
            print(f"    {entity_type}: {count} 个 ({percentage:.1f}%)")

def example_3_node_details():
    """示例3：获取节点详细信息"""
    print("\n" + "=" * 60)
    print("🔍 示例3：获取节点详细信息")
    print("=" * 60)
    
    chinese_api = ChineseGraphRAGAPI(BASE_URL, API_KEY)
    
    # 先获取一些节点
    graph_data = chinese_api.get_chinese_knowledge_graph(KB_ID)
    if 'error' in graph_data:
        print(f"❌ 错误: {graph_data['error']}")
        return
    
    nodes = graph_data['data']['graph']['nodes']
    
    # 选择几个有代表性的节点
    test_nodes = [
        "厦门国贸股份有限公司",
        "财务部", 
        "黄向华"
    ]
    
    for node_name in test_nodes:
        print(f"\n🔍 查询节点: {node_name}")
        node_info = chinese_api.get_node_source_info(KB_ID, node_name)
        
        if 'error' not in node_info:
            print(f"✅ 节点详情:")
            print(f"  名称: {node_info['node_name']}")
            print(f"  类型: {node_info['node_type']}")
            print(f"  英文类型: {node_info['node_type_en']}")
            print(f"  重要性评分: {node_info['pagerank']:.3f}")
            print(f"  源文件数量: {node_info['source_files_count']}")
            print(f"  源文件ID: {node_info['source_ids'][:2]}..." if len(node_info['source_ids']) > 2 else f"  源文件ID: {node_info['source_ids']}")
            
            # 显示描述的前100个字符
            description = node_info.get('description', '')
            if description:
                print(f"  描述: {description[:100]}...")
        else:
            print(f"❌ 未找到节点: {node_info['error']}")

def example_4_search_and_filter():
    """示例4：搜索和筛选实体"""
    print("\n" + "=" * 60)
    print("🔎 示例4：搜索和筛选实体")
    print("=" * 60)
    
    chinese_api = ChineseGraphRAGAPI(BASE_URL, API_KEY)
    
    # 获取完整图谱用于筛选
    graph_data = chinese_api.get_chinese_knowledge_graph(KB_ID)
    if 'error' in graph_data:
        print(f"❌ 错误: {graph_data['error']}")
        return
    
    nodes = graph_data['data']['graph']['nodes']
    
    # 1. 按实体类型筛选
    print("\n1️⃣ 按实体类型筛选")
    entity_types = ["组织", "人员", "事件"]
    
    for entity_type in entity_types:
        filtered_nodes = [node for node in nodes if node.get('entity_type') == entity_type]
        print(f"\n📋 {entity_type}类实体 (共{len(filtered_nodes)}个):")
        
        # 按重要性排序，显示前5个
        top_nodes = sorted(filtered_nodes, key=lambda x: x.get('pagerank', 0), reverse=True)[:5]
        for i, node in enumerate(top_nodes):
            print(f"  {i+1}. {node['entity_name']} (重要性: {node.get('pagerank', 0):.3f})")
    
    # 2. 按关键词搜索
    print("\n2️⃣ 按关键词搜索")
    keywords = ["财务", "安全", "审批"]
    
    for keyword in keywords:
        matching_nodes = [
            node for node in nodes 
            if keyword in node.get('entity_name', '') or keyword in node.get('description', '')
        ]
        
        print(f"\n🔍 包含'{keyword}'的实体 (共{len(matching_nodes)}个):")
        for i, node in enumerate(matching_nodes[:3]):  # 只显示前3个
            print(f"  {i+1}. {node['entity_name']} ({node['entity_type']})")
    
    # 3. 按文件来源筛选
    print("\n3️⃣ 按文件来源筛选")
    
    # 找出来源文件最多的实体
    nodes_with_files = [node for node in nodes if node.get('source_files_count', 0) > 0]
    top_file_nodes = sorted(nodes_with_files, key=lambda x: x.get('source_files_count', 0), reverse=True)[:5]
    
    print(f"\n📁 来源文件最多的实体:")
    for i, node in enumerate(top_file_nodes):
        print(f"  {i+1}. {node['entity_name']} - {node['source_files_count']} 个文件 ({node['entity_type']})")

def example_5_relationship_analysis():
    """示例5：关系分析"""
    print("\n" + "=" * 60)
    print("🔗 示例5：关系分析")
    print("=" * 60)
    
    chinese_api = ChineseGraphRAGAPI(BASE_URL, API_KEY)
    
    graph_data = chinese_api.get_chinese_knowledge_graph(KB_ID)
    if 'error' in graph_data:
        print(f"❌ 错误: {graph_data['error']}")
        return
    
    nodes = graph_data['data']['graph']['nodes']
    edges = graph_data['data']['graph']['edges']
    
    # 1. 关系类型统计
    print("\n1️⃣ 关系类型统计")
    relation_stats = {}
    for edge in edges:
        relation = edge.get('description', '未知关系')[:20]  # 取前20个字符
        relation_stats[relation] = relation_stats.get(relation, 0) + 1
    
    # 显示最常见的关系类型
    top_relations = sorted(relation_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    print("📊 最常见的关系类型:")
    for relation, count in top_relations:
        print(f"  {relation}: {count} 次")
    
    # 2. 节点连接度分析
    print("\n2️⃣ 节点连接度分析")
    node_connections = {}
    
    for edge in edges:
        source = edge['source']
        target = edge['target']
        
        node_connections[source] = node_connections.get(source, 0) + 1
        node_connections[target] = node_connections.get(target, 0) + 1
    
    # 找出连接度最高的节点
    top_connected = sorted(node_connections.items(), key=lambda x: x[1], reverse=True)[:5]
    print("🌟 连接度最高的节点:")
    for node_id, connections in top_connected:
        # 找到对应的节点信息
        node_info = next((n for n in nodes if n['id'] == node_id), None)
        if node_info:
            print(f"  {node_info['entity_name']} ({node_info['entity_type']}): {connections} 个连接")
    
    # 3. 特定节点的关系网络
    print("\n3️⃣ 特定节点的关系网络")
    target_node = "厦门国贸股份有限公司"
    
    related_edges = [edge for edge in edges if edge['source'] == target_node or edge['target'] == target_node]
    
    print(f"🏢 '{target_node}' 的关系网络:")
    print(f"  直接关系数: {len(related_edges)}")
    
    # 显示前5个关系
    for i, edge in enumerate(related_edges[:5]):
        if edge['source'] == target_node:
            other_node = edge['target']
            direction = "→"
        else:
            other_node = edge['source']
            direction = "←"
        
        # 找到对方节点的类型
        other_node_info = next((n for n in nodes if n['id'] == other_node), None)
        other_type = other_node_info['entity_type'] if other_node_info else '未知'
        
        print(f"  {i+1}. {direction} {other_node} ({other_type})")

def main():
    """主函数：运行所有示例"""
    print("🚀 RAGFlow 知识图谱 API 调用实例")
    print("包含原生API和中文化API的完整使用示例")
    
    try:
        # 运行所有示例
        example_1_basic_api_calls()
        example_2_chinese_api()
        example_3_node_details()
        example_4_search_and_filter()
        example_5_relationship_analysis()
        
        print("\n" + "=" * 60)
        print("🎉 所有示例运行完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 运行出错: {str(e)}")
        print("请检查：")
        print("1. RAGFlow 服务是否正常运行")
        print("2. API 密钥是否正确")
        print("3. 网络连接是否正常")
        print("4. chinese_graph_api.py 文件是否存在")

if __name__ == "__main__":
    main()
