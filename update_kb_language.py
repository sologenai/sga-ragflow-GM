#!/usr/bin/env python3
"""
修改知识库语言配置，让RAGFlow内部提取中文实体
"""

import requests
import json

# 配置信息
BASE_URL = "http://localhost:9380"
API_KEY = "ragflow-BlMGQyNzM0OTBhNzExZjA4MzU4ZGU3NW"
KB_ID = "dc949110906a11f08b78aa7cd3e67281"

def update_kb_language():
    """修改知识库语言为中文"""
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 1. 获取当前知识库配置
    print("📋 获取当前知识库配置...")
    response = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ 获取知识库失败: {response.text}")
        return False
    
    datasets = response.json()
    kb_data = None
    
    for dataset in datasets.get('data', []):
        if dataset['id'] == KB_ID:
            kb_data = dataset
            break
    
    if not kb_data:
        print(f"❌ 未找到知识库: {KB_ID}")
        return False
    
    print(f"✅ 当前知识库语言: {kb_data['language']}")
    print(f"✅ 知识库名称: {kb_data['name']}")
    
    # 2. 修改语言配置
    if kb_data['language'] == 'Chinese':
        print("✅ 知识库语言已经是中文，无需修改")
        return True
    
    print("\n🔧 修改知识库语言为中文...")
    
    # 准备更新数据
    update_data = {
        "name": kb_data['name'],
        "description": kb_data.get('description', ''),
        "language": "Chinese",  # 修改为中文
        "permission": kb_data.get('permission', 'me'),
        "chunk_method": kb_data.get('chunk_method', 'naive'),
        "parser_config": kb_data.get('parser_config', {})
    }
    
    # 发送更新请求
    response = requests.put(
        f"{BASE_URL}/api/v1/datasets/{KB_ID}",
        headers=headers,
        json=update_data
    )
    
    if response.status_code == 200:
        print("✅ 知识库语言已修改为中文")
        return True
    else:
        print(f"❌ 修改失败: {response.text}")
        return False

def rebuild_knowledge_graph():
    """重新构建知识图谱以应用中文配置"""
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("\n🔄 重新构建知识图谱...")
    
    # 获取知识库中的文档
    response = requests.get(f"{BASE_URL}/api/v1/datasets/{KB_ID}/documents", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ 获取文档列表失败: {response.text}")
        return False
    
    documents = response.json()
    doc_list = documents.get('data', [])
    
    print(f"📄 找到 {len(doc_list)} 个文档")
    
    # 重新解析文档以触发知识图谱重建
    success_count = 0
    test_count = min(3, len(doc_list))  # 先处理前3个文档测试
    for i, doc in enumerate(doc_list[:test_count]):
        doc_id = doc['id']
        doc_name = doc['name']
        
        print(f"🔄 重新解析文档 {i+1}/{test_count}: {doc_name}")
        
        # 触发文档重新解析
        parse_data = {
            "document_ids": [doc_id],
            "run": "1"  # 开始解析
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/datasets/{KB_ID}/documents/run",
            headers=headers,
            json=parse_data
        )
        
        if response.status_code == 200:
            print(f"  ✅ {doc_name} 重新解析已启动")
            success_count += 1
        else:
            print(f"  ❌ {doc_name} 重新解析失败: {response.text}")
    
    print(f"\n📊 重新解析结果: {success_count}/{test_count} 个文档成功启动")
    
    if success_count > 0:
        print("\n⏳ 知识图谱重建已启动，请等待几分钟后检查结果")
        print("💡 可以通过以下命令检查进度:")
        print("   docker logs ragflow-server --tail 20")
        return True
    else:
        return False

def check_graph_language():
    """检查知识图谱是否已经使用中文"""
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("\n🔍 检查当前知识图谱语言...")
    
    response = requests.get(f"{BASE_URL}/api/v1/datasets/{KB_ID}/knowledge_graph", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ 获取知识图谱失败: {response.text}")
        return
    
    graph_data = response.json()
    
    if 'data' not in graph_data or 'graph' not in graph_data['data']:
        print("❌ 知识图谱数据格式错误")
        return
    
    nodes = graph_data['data']['graph']['nodes']
    
    if not nodes:
        print("⚠️ 知识图谱为空，可能正在重建中")
        return
    
    # 检查前几个节点的描述语言
    print("📊 当前知识图谱节点示例:")
    
    chinese_count = 0
    english_count = 0
    
    for i, node in enumerate(nodes[:5]):
        description = node.get('description', '')
        entity_name = node.get('entity_name', '')
        entity_type = node.get('entity_type', '')
        
        print(f"  {i+1}. {entity_name} ({entity_type})")
        
        # 简单判断描述语言
        if description:
            # 检查是否包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in description)
            if has_chinese:
                chinese_count += 1
                print(f"     描述: {description[:50]}... (中文)")
            else:
                english_count += 1
                print(f"     描述: {description[:50]}... (英文)")
        else:
            print(f"     描述: 无")
    
    print(f"\n📈 语言统计 (前5个节点):")
    print(f"  中文描述: {chinese_count} 个")
    print(f"  英文描述: {english_count} 个")
    
    if chinese_count > english_count:
        print("✅ 知识图谱主要使用中文描述")
    elif english_count > chinese_count:
        print("⚠️ 知识图谱主要使用英文描述，建议重新构建")
    else:
        print("🔄 知识图谱语言混合，可能正在重建中")

def main():
    """主函数"""
    print("🚀 RAGFlow 知识库语言配置修改工具")
    print("=" * 50)
    
    try:
        # 1. 检查当前状态
        check_graph_language()
        
        # 2. 修改知识库语言
        if update_kb_language():
            print("\n✅ 知识库语言配置已更新")
            
            # 3. 询问是否重建知识图谱
            print("\n❓ 是否重新构建知识图谱以应用中文配置？")
            print("   注意：这将重新解析所有文档，可能需要较长时间")
            
            choice = input("   输入 'y' 继续，其他键跳过: ").lower().strip()
            
            if choice == 'y':
                if rebuild_knowledge_graph():
                    print("\n🎉 知识图谱重建已启动！")
                    print("\n📝 后续步骤:")
                    print("  1. 等待5-10分钟让重建完成")
                    print("  2. 运行 python chinese_graph_api.py 检查结果")
                    print("  3. 新的实体描述应该是中文的")
                else:
                    print("\n❌ 知识图谱重建启动失败")
            else:
                print("\n⏭️ 跳过知识图谱重建")
                print("💡 您可以稍后手动重新解析文档来应用中文配置")
        else:
            print("\n❌ 知识库语言配置修改失败")
            
    except Exception as e:
        print(f"\n❌ 运行出错: {str(e)}")
        print("\n🔧 请检查:")
        print("  1. RAGFlow 服务是否正常运行")
        print("  2. API 密钥是否正确")
        print("  3. 网络连接是否正常")

if __name__ == "__main__":
    main()
