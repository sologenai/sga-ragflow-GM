#!/usr/bin/env python3
"""
最简单的 RAGFlow 知识图谱 API 调用示例
"""

import requests
import json
from chinese_graph_api import ChineseGraphRAGAPI

# 配置信息
BASE_URL = "http://localhost:9380"
API_KEY = "ragflow-BlMGQyNzM0OTBhNzExZjA4MzU4ZGU3NW"  # 正确的API密钥
KB_ID = "dc949110906a11f08b78aa7cd3e67281"

def method_1_direct_api():
    """方法1：直接调用原生API"""
    print("🔥 方法1：直接调用原生API")
    print("-" * 40)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 1. 获取数据集列表
    print("1️⃣ 获取数据集列表")
    response = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"数据集数量: {len(data.get('data', []))}")
        if data.get('data'):
            dataset = data['data'][0]
            print(f"数据集名称: {dataset['name']}")
    
    # 2. 获取知识图谱
    print("\n2️⃣ 获取知识图谱")
    response = requests.get(f"{BASE_URL}/api/v1/datasets/{KB_ID}/knowledge_graph", headers=headers)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        graph_data = response.json()
        if 'data' in graph_data and 'graph' in graph_data['data']:
            nodes = graph_data['data']['graph']['nodes']
            edges = graph_data['data']['graph']['edges']
            print(f"节点数: {len(nodes)}")
            print(f"边数: {len(edges)}")
            
            # 显示前2个节点
            print("\n📊 前2个节点（原始英文）:")
            for i, node in enumerate(nodes[:2]):
                print(f"  {i+1}. {node['entity_name']} ({node['entity_type']})")
                print(f"     来源文件: {len(node.get('source_id', []))} 个")
    else:
        print(f"错误: {response.text}")

def method_2_chinese_api():
    """方法2：使用中文化API"""
    print("\n🇨🇳 方法2：使用中文化API")
    print("-" * 40)
    
    # 创建中文化API实例
    api = ChineseGraphRAGAPI(BASE_URL, API_KEY)
    
    # 1. 获取中文化知识图谱
    print("1️⃣ 获取中文化知识图谱")
    graph = api.get_chinese_knowledge_graph(KB_ID)
    
    if 'error' not in graph:
        nodes = graph['data']['graph']['nodes']
        edges = graph['data']['graph']['edges']
        print(f"✅ 成功获取图谱")
        print(f"节点数: {len(nodes)}")
        print(f"边数: {len(edges)}")
        
        # 显示前3个节点（中文化）
        print("\n📊 前3个节点（中文化）:")
        for i, node in enumerate(nodes[:3]):
            print(f"  {i+1}. {node['entity_name']}")
            print(f"     类型: {node['entity_type']} (英文: {node.get('entity_type_en', 'N/A')})")
            print(f"     来源文件: {node['source_files_count']} 个")
            print(f"     重要性: {node.get('pagerank', 0):.3f}")
            print()
    else:
        print(f"❌ 错误: {graph['error']}")
    
    # 2. 获取统计信息
    print("2️⃣ 获取统计信息")
    stats = api.get_entity_statistics(KB_ID)
    
    if 'error' not in stats:
        print(f"✅ 统计信息:")
        print(f"  总节点: {stats['total_nodes']}")
        print(f"  总边: {stats['total_edges']}")
        print(f"  文件覆盖率: {stats['coverage_rate']}")
        
        print("\n📈 实体类型分布:")
        for entity_type, count in stats['entity_type_distribution'].items():
            print(f"  {entity_type}: {count} 个")

def method_3_specific_queries():
    """方法3：特定查询示例"""
    print("\n🔍 方法3：特定查询示例")
    print("-" * 40)
    
    api = ChineseGraphRAGAPI(BASE_URL, API_KEY)
    
    # 获取图谱数据
    graph = api.get_chinese_knowledge_graph(KB_ID)
    if 'error' in graph:
        print(f"❌ 错误: {graph['error']}")
        return
    
    nodes = graph['data']['graph']['nodes']
    
    # 1. 查找所有组织
    print("1️⃣ 查找所有组织实体")
    org_nodes = [node for node in nodes if node.get('entity_type') == '组织']
    print(f"找到 {len(org_nodes)} 个组织")
    
    # 按重要性排序，显示前5个
    top_orgs = sorted(org_nodes, key=lambda x: x.get('pagerank', 0), reverse=True)[:5]
    for i, node in enumerate(top_orgs):
        print(f"  {i+1}. {node['entity_name']} (重要性: {node.get('pagerank', 0):.3f})")
    
    # 2. 查找所有人员
    print(f"\n2️⃣ 查找所有人员实体")
    person_nodes = [node for node in nodes if node.get('entity_type') == '人员']
    print(f"找到 {len(person_nodes)} 个人员")
    
    # 显示前5个
    for i, node in enumerate(person_nodes[:5]):
        print(f"  {i+1}. {node['entity_name']}")
    
    # 3. 查找包含特定关键词的实体
    print(f"\n3️⃣ 查找包含'财务'的实体")
    finance_nodes = [
        node for node in nodes 
        if '财务' in node.get('entity_name', '') or '财务' in node.get('description', '')
    ]
    print(f"找到 {len(finance_nodes)} 个相关实体")
    
    for i, node in enumerate(finance_nodes[:3]):
        print(f"  {i+1}. {node['entity_name']} ({node['entity_type']})")
    
    # 4. 查看特定实体的详细信息
    if org_nodes:
        target_entity = org_nodes[0]['entity_name']
        print(f"\n4️⃣ 查看实体详情: {target_entity}")
        
        node_info = api.get_node_source_info(KB_ID, target_entity)
        if 'error' not in node_info:
            print(f"  类型: {node_info['node_type']}")
            print(f"  重要性: {node_info['pagerank']:.3f}")
            print(f"  来源文件数: {node_info['source_files_count']}")
            print(f"  源文件ID: {node_info['source_ids'][:2]}...")
        else:
            print(f"  错误: {node_info['error']}")

def method_4_export_data():
    """方法4：导出数据示例"""
    print("\n💾 方法4：导出数据示例")
    print("-" * 40)
    
    api = ChineseGraphRAGAPI(BASE_URL, API_KEY)
    
    # 获取数据
    graph = api.get_chinese_knowledge_graph(KB_ID)
    if 'error' in graph:
        print(f"❌ 错误: {graph['error']}")
        return
    
    # 1. 导出完整图谱为JSON
    with open('graph_chinese.json', 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print("✅ 完整图谱已导出到: graph_chinese.json")
    
    # 2. 导出实体列表
    nodes = graph['data']['graph']['nodes']
    with open('entities.txt', 'w', encoding='utf-8') as f:
        f.write("实体名称\t类型\t重要性\t文件数\n")
        for node in nodes:
            f.write(f"{node['entity_name']}\t{node['entity_type']}\t{node.get('pagerank', 0):.3f}\t{node['source_files_count']}\n")
    print("✅ 实体列表已导出到: entities.txt")
    
    # 3. 导出统计信息
    stats = api.get_entity_statistics(KB_ID)
    with open('statistics.txt', 'w', encoding='utf-8') as f:
        f.write("知识图谱统计信息\n")
        f.write("=" * 20 + "\n")
        f.write(f"总节点数: {stats['total_nodes']}\n")
        f.write(f"总边数: {stats['total_edges']}\n")
        f.write(f"文件覆盖率: {stats['coverage_rate']}\n")
        f.write("\n实体类型分布:\n")
        for entity_type, count in stats['entity_type_distribution'].items():
            f.write(f"{entity_type}: {count} 个\n")
    print("✅ 统计信息已导出到: statistics.txt")

def main():
    """主函数：演示所有调用方法"""
    print("🚀 RAGFlow 知识图谱 API 调用示例")
    print("=" * 50)
    
    try:
        # 运行所有示例
        method_1_direct_api()
        method_2_chinese_api()
        method_3_specific_queries()
        method_4_export_data()
        
        print("\n" + "=" * 50)
        print("🎉 所有示例运行完成！")
        print("=" * 50)
        print("\n📁 生成的文件:")
        print("  - graph_chinese.json (完整图谱数据)")
        print("  - entities.txt (实体列表)")
        print("  - statistics.txt (统计信息)")
        
        print("\n💡 使用提示:")
        print("  1. 直接调用原生API获取英文数据")
        print("  2. 使用中文化API获取中文数据")
        print("  3. 进行特定查询和筛选")
        print("  4. 导出数据进行进一步分析")
        
    except Exception as e:
        print(f"\n❌ 运行出错: {str(e)}")
        print("\n🔧 请检查:")
        print("  1. RAGFlow 服务是否运行在 http://localhost:9380")
        print("  2. API 密钥是否正确")
        print("  3. 知识库ID是否存在")
        print("  4. chinese_graph_api.py 文件是否在同一目录")

if __name__ == "__main__":
    main()
