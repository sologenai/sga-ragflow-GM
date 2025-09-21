#!/usr/bin/env python3
"""
简单的实体类型中文化修改工具
"""

import subprocess
import os
import time

def copy_files_from_docker():
    """从Docker容器复制文件到本地"""
    print("📋 从Docker容器复制文件到本地...")
    
    files_to_copy = [
        ("/ragflow/graphrag/light/graph_prompt.py", "graph_prompt_light.py"),
        ("/ragflow/graphrag/general/extractor.py", "extractor_general.py")
    ]
    
    for docker_path, local_path in files_to_copy:
        cmd = f"docker cp ragflow-server:{docker_path} {local_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 已复制: {docker_path} -> {local_path}")
        else:
            print(f"❌ 复制失败: {docker_path} - {result.stderr}")
            return False
    
    return True

def modify_local_files():
    """修改本地文件"""
    print("\n🔧 修改本地文件...")
    
    # 修改 graph_prompt_light.py
    try:
        with open("graph_prompt_light.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        old_line = 'PROMPTS["DEFAULT_ENTITY_TYPES"] = ["organization", "person", "geo", "event", "category"]'
        new_line = 'PROMPTS["DEFAULT_ENTITY_TYPES"] = ["组织", "人员", "地理位置", "事件", "类别"]'
        
        if old_line in content:
            content = content.replace(old_line, new_line)
            
            with open("graph_prompt_light.py", "w", encoding="utf-8") as f:
                f.write(content)
            
            print("✅ graph_prompt_light.py 修改成功")
        else:
            print("⚠️ graph_prompt_light.py 未找到要替换的行")
    
    except Exception as e:
        print(f"❌ 修改 graph_prompt_light.py 失败: {e}")
        return False
    
    # 修改 extractor_general.py
    try:
        with open("extractor_general.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        old_line = 'DEFAULT_ENTITY_TYPES = ["organization", "person", "geo", "event", "category"]'
        new_line = 'DEFAULT_ENTITY_TYPES = ["组织", "人员", "地理位置", "事件", "类别"]'
        
        if old_line in content:
            content = content.replace(old_line, new_line)
            
            with open("extractor_general.py", "w", encoding="utf-8") as f:
                f.write(content)
            
            print("✅ extractor_general.py 修改成功")
        else:
            print("⚠️ extractor_general.py 未找到要替换的行")
    
    except Exception as e:
        print(f"❌ 修改 extractor_general.py 失败: {e}")
        return False
    
    return True

def copy_files_to_docker():
    """将修改后的文件复制回Docker容器"""
    print("\n📤 将修改后的文件复制回Docker容器...")
    
    files_to_copy = [
        ("graph_prompt_light.py", "/ragflow/graphrag/light/graph_prompt.py"),
        ("extractor_general.py", "/ragflow/graphrag/general/extractor.py")
    ]
    
    for local_path, docker_path in files_to_copy:
        cmd = f"docker cp {local_path} ragflow-server:{docker_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 已复制: {local_path} -> {docker_path}")
        else:
            print(f"❌ 复制失败: {local_path} - {result.stderr}")
            return False
    
    return True

def restart_ragflow():
    """重启RAGFlow服务"""
    print("\n🔄 重启RAGFlow服务...")
    
    # 切换到docker目录
    os.chdir("E:/sga-rag/docker")
    
    # 重启容器
    cmd = "docker-compose restart ragflow"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ RAGFlow服务重启命令已执行")
        
        # 等待服务启动
        print("⏳ 等待服务启动...")
        for i in range(6):  # 等待60秒
            time.sleep(10)
            print(f"   等待中... {(i+1)*10}秒")
        
        # 检查服务状态
        check_cmd = "docker-compose ps ragflow"
        check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        
        if "Up" in check_result.stdout:
            print("✅ 服务启动成功")
            return True
        else:
            print("⚠️ 服务可能还在启动中，请稍后检查")
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
            print(f"   {result.stdout.strip()}")
        else:
            print(f"⚠️ {file_path} 可能未正确修改")

def cleanup_local_files():
    """清理本地临时文件"""
    print("\n🧹 清理本地临时文件...")
    
    files_to_remove = [
        "graph_prompt_light.py",
        "extractor_general.py"
    ]
    
    for file_path in files_to_remove:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ 已删除: {file_path}")
        except Exception as e:
            print(f"⚠️ 删除失败: {file_path} - {e}")

def main():
    """主函数"""
    print("🚀 RAGFlow 实体类型中文化修改工具 (简化版)")
    print("=" * 60)
    print("⚠️  注意：此操作需要重启Docker容器")
    print("⚠️  建议在非生产环境中测试")
    print("=" * 60)
    
    # 询问用户确认
    choice = input("\n❓ 是否继续修改实体类型为中文？(y/N): ").lower().strip()
    
    if choice != 'y':
        print("❌ 操作已取消")
        return
    
    try:
        # 1. 复制文件到本地
        if not copy_files_from_docker():
            print("❌ 复制文件失败，操作终止")
            return
        
        # 2. 修改本地文件
        if not modify_local_files():
            print("❌ 修改文件失败，操作终止")
            cleanup_local_files()
            return
        
        # 3. 复制文件回Docker
        if not copy_files_to_docker():
            print("❌ 复制文件回Docker失败，操作终止")
            cleanup_local_files()
            return
        
        # 4. 重启服务
        if not restart_ragflow():
            print("❌ 服务重启失败")
            cleanup_local_files()
            return
        
        # 5. 验证修改
        verify_changes()
        
        # 6. 清理临时文件
        cleanup_local_files()
        
        print("\n🎉 实体类型中文化修改完成！")
        print("\n📝 后续步骤:")
        print("  1. 等待服务完全启动 (约2-3分钟)")
        print("  2. 重新解析文档以应用新的实体类型:")
        print("     python update_kb_language.py")
        print("  3. 运行 python chinese_graph_api.py 检查结果")
        print("  4. 新提取的实体类型应该是中文的")
        
    except Exception as e:
        print(f"\n❌ 运行出错: {str(e)}")
        cleanup_local_files()

if __name__ == "__main__":
    main()
