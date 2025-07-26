#!/usr/bin/env python3
"""
运行语音增强工作流组件的测试
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """运行所有测试"""
    test_commands = [
        # 意图分析器测试
        ["python", "-m", "pytest", "tests/intent_processor/", "-v"],
        
        # 事件关联器测试
        ["python", "-m", "pytest", "tests/correlator/", "-v"],
        
        # 增强型工作流生成器测试
        ["python", "-m", "pytest", "tests/enhanced_generator/", "-v"],
    ]
    
    print("🧪 开始运行语音增强工作流组件测试...")
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n📋 运行测试 {i}/{len(test_commands)}: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
            
            if result.returncode == 0:
                print(f"✅ 测试 {i} 通过")
                print(result.stdout)
            else:
                print(f"❌ 测试 {i} 失败")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ 运行测试 {i} 时出错: {e}")
            return False
    
    print("\n🎉 所有测试通过！")
    return True


def run_single_test(test_path: str):
    """运行单个测试文件"""
    cmd = ["python", "-m", "pytest", test_path, "-v", "-s"]
    print(f"🧪 运行单个测试: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 运行指定的测试文件
        test_file = sys.argv[1]
        success = run_single_test(test_file)
    else:
        # 运行所有测试
        success = run_tests()
    
    sys.exit(0 if success else 1)
