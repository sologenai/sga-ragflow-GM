#!/usr/bin/env python3
"""
修改RAGFlow内部的实体类型为中文
注意：这需要重启Docker容器才能生效
"""

import subprocess
import time

def backup_files():
    """备份原始文件"""
    print("📋 备份原始文件...")
    
    files_to_backup = [
        "/ragflow/graphrag/light/graph_prompt.py",
        "/ragflow/graphrag/general/extractor.py"
    ]
    
    for file_path in files_to_backup:
        backup_path = file_path + ".backup"
        cmd = f"docker exec ragflow-server cp {file_path} {backup_path}"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 已备份: {file_path}")
        else:
            print(f"❌ 备份失败: {file_path} - {result.stderr}")
            return False
    
    return True

def modify_light_prompt():
    """修改light方法的提示词文件"""
    print("\n🔧 修改 light/graph_prompt.py...")

    # 使用sed命令直接替换
    old_pattern = 'PROMPTS\["DEFAULT_ENTITY_TYPES"\] = \["organization", "person", "geo", "event", "category"\]'
    new_pattern = 'PROMPTS["DEFAULT_ENTITY_TYPES"] = ["组织", "人员", "地理位置", "事件", "类别"]'

    cmd = f"""docker exec ragflow-server sed -i 's/{old_pattern}/{new_pattern}/g' /ragflow/graphrag/light/graph_prompt.py"""

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ light/graph_prompt.py 修改成功")
        return True
    else:
        print(f"❌ 修改失败: {result.stderr}")
        return False

def modify_general_extractor():
    """修改general方法的提取器文件"""
    print("\n🔧 修改 general/extractor.py...")

    # 使用sed命令直接替换
    old_pattern = 'DEFAULT_ENTITY_TYPES = \["organization", "person", "geo", "event", "category"\]'
    new_pattern = 'DEFAULT_ENTITY_TYPES = ["组织", "人员", "地理位置", "事件", "类别"]'

    cmd = f"""docker exec ragflow-server sed -i 's/{old_pattern}/{new_pattern}/g' /ragflow/graphrag/general/extractor.py"""

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ general/extractor.py 修改成功")
        return True
    else:
        print(f"❌ 修改失败: {result.stderr}")
        return False

def restart_ragflow():
    """重启RAGFlow服务"""
    print("\n🔄 重启RAGFlow服务...")
    
    # 重启容器
    cmd = "docker-compose restart ragflow"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="E:/sga-rag/docker")
    
    if result.returncode == 0:
        print("✅ RAGFlow服务重启成功")
        
        # 等待服务启动
        print("⏳ 等待服务启动...")
        time.sleep(30)
        
        # 检查服务状态
        check_cmd = "docker-compose ps ragflow"
        check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, cwd="E:/sga-rag/docker")
        
        if "Up" in check_result.stdout:
            print("✅ 服务启动成功")
            return True
        else:
            print("⚠️ 服务可能还在启动中")
            return True
    else:
        print(f"❌ 重启失败: {result.stderr}")
        return False

def verify_changes():
    """验证修改是否生效"""
    print("\n🔍 验证修改结果...")
    
    # 检查修改后的文件
    files_to_check = [
        "/ragflow/graphrag/light/graph_prompt.py",
        "/ragflow/graphrag/general/extractor.py"
    ]
    
    for file_path in files_to_check:
        cmd = f"docker exec ragflow-server grep -n '组织.*人员.*地理位置.*事件.*类别' {file_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {file_path} 已包含中文实体类型")
        else:
            print(f"⚠️ {file_path} 可能未正确修改")

def restore_backup():
    """恢复备份文件"""
    print("\n🔄 恢复备份文件...")
    
    files_to_restore = [
        "/ragflow/graphrag/light/graph_prompt.py",
        "/ragflow/graphrag/general/extractor.py"
    ]
    
    for file_path in files_to_restore:
        backup_path = file_path + ".backup"
        cmd = f"docker exec ragflow-server cp {backup_path} {file_path}"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 已恢复: {file_path}")
        else:
            print(f"❌ 恢复失败: {file_path}")

def main():
    """主函数"""
    print("🚀 RAGFlow 实体类型中文化修改工具")
    print("=" * 50)
    print("⚠️  注意：此操作需要重启Docker容器")
    print("⚠️  建议在非生产环境中测试")
    print("=" * 50)
    
    # 询问用户确认
    choice = input("\n❓ 是否继续修改实体类型为中文？(y/N): ").lower().strip()
    
    if choice != 'y':
        print("❌ 操作已取消")
        return
    
    try:
        # 1. 备份文件
        if not backup_files():
            print("❌ 备份失败，操作终止")
            return
        
        # 2. 修改文件
        success1 = modify_light_prompt()
        success2 = modify_general_extractor()
        
        if not (success1 and success2):
            print("❌ 文件修改失败，正在恢复备份...")
            restore_backup()
            return
        
        # 3. 重启服务
        if not restart_ragflow():
            print("❌ 服务重启失败，正在恢复备份...")
            restore_backup()
            restart_ragflow()
            return
        
        # 4. 验证修改
        verify_changes()
        
        print("\n🎉 实体类型中文化修改完成！")
        print("\n📝 后续步骤:")
        print("  1. 等待服务完全启动 (约2-3分钟)")
        print("  2. 重新解析文档以应用新的实体类型")
        print("  3. 运行 python chinese_graph_api.py 检查结果")
        print("  4. 新提取的实体类型应该是中文的")
        
        print("\n💡 如果出现问题，可以运行以下命令恢复:")
        print("  python update_entity_types.py --restore")
        
    except Exception as e:
        print(f"\n❌ 运行出错: {str(e)}")
        print("🔄 正在恢复备份...")
        restore_backup()
        restart_ragflow()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--restore":
        print("🔄 恢复备份文件...")
        restore_backup()
        restart_ragflow()
        print("✅ 备份已恢复")
    else:
        main()
