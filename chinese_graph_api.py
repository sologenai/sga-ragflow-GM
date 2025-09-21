#!/usr/bin/env python3
"""
RAGFlow 知识图谱中文化处理脚本
立即可用，无需修改RAGFlow源码
"""

import requests
import json
from typing import Dict, List, Any, Optional
import time

class ChineseGraphRAGAPI:
    """中文化的知识图谱API包装器"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 实体类型中英文映射
        self.entity_type_mapping = {
            "ORGANIZATION": "组织",
            "PERSON": "人员",
            "GEO": "地理位置",
            "LOCATION": "地理位置", 
            "EVENT": "事件",
            "CATEGORY": "类别",
            "CONCEPT": "概念",
            "PRODUCT": "产品",
            "TECHNOLOGY": "技术",
            "OTHER": "其他"
        }
        
        # 反向映射
        self.entity_type_reverse_mapping = {v: k for k, v in self.entity_type_mapping.items()}
    
    def translate_entity_type(self, entity_type: str, to_chinese: bool = True) -> str:
        """翻译实体类型"""
        if to_chinese:
            return self.entity_type_mapping.get(entity_type.upper(), entity_type)
        else:
            return self.entity_type_reverse_mapping.get(entity_type, entity_type)
    
    def get_datasets(self) -> Dict[str, Any]:
        """获取数据集列表"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/datasets", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_chinese_knowledge_graph(self, kb_id: str) -> Dict[str, Any]:
        """获取中文化的知识图谱"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/datasets/{kb_id}/knowledge_graph",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            # 中文化处理
            if 'data' in data and 'graph' in data['data']:
                self._process_nodes_chinese(data['data']['graph'].get('nodes', []))
                self._process_edges_chinese(data['data']['graph'].get('edges', []))
            
            return data
            
        except Exception as e:
            return {"error": str(e)}
    
    def _process_nodes_chinese(self, nodes: List[Dict[str, Any]]) -> None:
        """处理节点的中文化"""
        for node in nodes:
            # 翻译实体类型
            if 'entity_type' in node:
                original_type = node['entity_type']
                node['entity_type_en'] = original_type  # 保留英文
                node['entity_type'] = self.translate_entity_type(original_type)
            
            # 添加文件统计信息
            source_ids = node.get('source_id', [])
            node['source_files_count'] = len(source_ids)
            node['has_source_files'] = len(source_ids) > 0
            
            # 添加中文标签
            node['display_type'] = node.get('entity_type', '未知类型')
    
    def _process_edges_chinese(self, edges: List[Dict[str, Any]]) -> None:
        """处理边的中文化"""
        for edge in edges:
            # 可以在这里添加关系类型的中文化
            if 'relation' in edge:
                edge['relation_zh'] = edge['relation']  # 暂时保持原样
    
    def get_node_source_info(self, kb_id: str, node_id: str) -> Dict[str, Any]:
        """获取节点的源文件信息"""
        try:
            # 先获取完整图谱找到节点
            graph_data = self.get_chinese_knowledge_graph(kb_id)
            
            if 'error' in graph_data:
                return graph_data
            
            # 查找目标节点
            target_node = None
            for node in graph_data['data']['graph']['nodes']:
                if node['id'] == node_id:
                    target_node = node
                    break
            
            if not target_node:
                return {"error": "节点未找到"}
            
            source_ids = target_node.get('source_id', [])
            
            return {
                "node_id": node_id,
                "node_name": target_node.get('entity_name', ''),
                "node_type": target_node.get('entity_type', ''),
                "node_type_en": target_node.get('entity_type_en', ''),
                "description": target_node.get('description', ''),
                "source_ids": source_ids,
                "source_files_count": len(source_ids),
                "pagerank": target_node.get('pagerank', 0),
                "message": "源文件ID列表，需要额外API获取文件详情"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_entity_statistics(self, kb_id: str) -> Dict[str, Any]:
        """获取实体统计信息"""
        try:
            graph_data = self.get_chinese_knowledge_graph(kb_id)
            
            if 'error' in graph_data:
                return graph_data
            
            nodes = graph_data['data']['graph']['nodes']
            edges = graph_data['data']['graph']['edges']
            
            # 统计实体类型分布
            type_distribution = {}
            for node in nodes:
                entity_type = node.get('entity_type', '未知')
                type_distribution[entity_type] = type_distribution.get(entity_type, 0) + 1
            
            # 统计文件关联
            total_source_files = sum(node.get('source_files_count', 0) for node in nodes)
            nodes_with_files = sum(1 for node in nodes if node.get('has_source_files', False))
            
            return {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "entity_type_distribution": type_distribution,
                "total_source_files": total_source_files,
                "nodes_with_source_files": nodes_with_files,
                "coverage_rate": f"{(nodes_with_files/len(nodes)*100):.1f}%" if nodes else "0%"
            }
            
        except Exception as e:
            return {"error": str(e)}

# 使用示例和测试代码
def main():
    """主函数 - 演示用法"""
    
    # 配置信息
    BASE_URL = "http://localhost:9380"
    API_KEY = "ragflow-BlMGQyNzM0OTBhNzExZjA4MzU4ZGU3NW"
    KB_ID = "dc949110906a11f08b78aa7cd3e67281"
    
    # 创建API实例
    api = ChineseGraphRAGAPI(BASE_URL, API_KEY)
    
    print("🚀 RAGFlow 知识图谱中文化测试")
    print("=" * 50)
    
    # 1. 获取数据集
    print("\n📋 1. 获取数据集列表...")
    datasets = api.get_datasets()
    if 'error' not in datasets:
        print(f"✅ 找到 {len(datasets.get('data', []))} 个数据集")
    else:
        print(f"❌ 错误: {datasets['error']}")
        return
    
    # 2. 获取中文化知识图谱
    print(f"\n🕸️ 2. 获取知识图谱 (KB: {KB_ID})...")
    graph_data = api.get_chinese_knowledge_graph(KB_ID)
    
    if 'error' not in graph_data:
        nodes = graph_data['data']['graph']['nodes']
        edges = graph_data['data']['graph']['edges']
        print(f"✅ 成功获取图谱: {len(nodes)} 个节点, {len(edges)} 条边")
        
        # 显示前3个节点的中文化信息
        print("\n📊 节点中文化示例:")
        for i, node in enumerate(nodes[:3]):
            print(f"  {i+1}. 实体: {node['entity_name']}")
            print(f"     类型: {node['entity_type']} (英文: {node.get('entity_type_en', 'N/A')})")
            print(f"     来源文件: {node['source_files_count']} 个")
            print(f"     重要性: {node.get('pagerank', 0):.3f}")
            print()
    else:
        print(f"❌ 错误: {graph_data['error']}")
        return
    
    # 3. 获取统计信息
    print("\n📈 3. 实体统计信息...")
    stats = api.get_entity_statistics(KB_ID)
    if 'error' not in stats:
        print(f"✅ 总节点数: {stats['total_nodes']}")
        print(f"✅ 总边数: {stats['total_edges']}")
        print(f"✅ 文件覆盖率: {stats['coverage_rate']}")
        print("✅ 实体类型分布:")
        for entity_type, count in stats['entity_type_distribution'].items():
            print(f"   - {entity_type}: {count} 个")
    
    # 4. 获取节点详情
    if nodes:
        test_node_id = nodes[0]['id']
        print(f"\n📄 4. 获取节点详情 (节点: {test_node_id})...")
        node_info = api.get_node_source_info(KB_ID, test_node_id)
        if 'error' not in node_info:
            print(f"✅ 节点名称: {node_info['node_name']}")
            print(f"✅ 节点类型: {node_info['node_type']}")
            print(f"✅ 源文件数量: {node_info['source_files_count']}")
            print(f"✅ 源文件ID: {node_info['source_ids'][:2]}...")  # 只显示前2个
    
    print("\n🎉 测试完成！")

if __name__ == "__main__":
    main()
