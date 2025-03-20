#!/usr/bin/env python3
"""
API密钥测试和修复工具
"""
import os
import sys
from dotenv import load_dotenv, find_dotenv, set_key

def main():
    """检测和修复API密钥问题"""
    print("API密钥测试和修复工具")
    print("-" * 40)
    
    # 查找并加载.env文件
    dotenv_path = find_dotenv(usecwd=True)
    
    if not dotenv_path:
        print("未找到.env文件，将在当前目录创建一个")
        dotenv_path = os.path.join(os.getcwd(), ".env")
        with open(dotenv_path, "w", encoding="utf-8") as f:
            f.write("# OpenAI API配置\n")
            f.write("OPENAI_API_KEY=\n")
            f.write("OPENAI_MODEL=gpt-3.5-turbo\n\n")
            f.write("# MQTT配置\n")
            f.write("MQTT_HOST=localhost\n")
            f.write("MQTT_PORT=1883\n\n")
            f.write("# 设备配置\n")
            f.write("DEVICE_ID=rpi_001\n")
    
    print(f"使用.env文件: {dotenv_path}")
    load_dotenv(dotenv_path)
    
    # 获取当前API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # 掩码显示密钥
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
        print(f"当前API密钥: {masked_key}")
    else:
        print("当前未设置API密钥")
    
    # 询问是否需要设置新的API密钥
    new_key = input("请输入新的API密钥 (留空保持不变): ").strip()
    
    if new_key:
        # 更新.env文件中的API密钥
        set_key(dotenv_path, "OPENAI_API_KEY", new_key)
        print("API密钥已更新")
        
        # 同时更新环境变量，确保当前进程立即生效
        os.environ["OPENAI_API_KEY"] = new_key
    
    # 选择模型
    print("\n可用模型:")
    models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    for i, model in enumerate(models, 1):
        print(f"{i}. {model}")
    
    current_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    print(f"当前模型: {current_model}")
    
    model_choice = input("请选择模型编号 (留空保持不变): ").strip()
    if model_choice and model_choice.isdigit() and 1 <= int(model_choice) <= len(models):
        selected_model = models[int(model_choice) - 1]
        set_key(dotenv_path, "OPENAI_MODEL", selected_model)
        print(f"模型已更新为: {selected_model}")
        
        # 同时更新环境变量
        os.environ["OPENAI_MODEL"] = selected_model
    
    # 测试API连接
    print("\n测试API连接...")
    try:
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": "你是一个帮助用户的助手。"},
                {"role": "user", "content": "请回复'API连接测试成功'"}
            ]
        )
        print(f"API测试结果: {response.choices[0].message.content}")
        print("✓ API连接测试成功")
    except Exception as e:
        print(f"API连接测试失败: {e}")
        print("请检查API密钥和网络连接")
    
    print("\n使用以下命令启动Web服务器:")
    print("python start_web.py --debug")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
    finally:
        input("\n按Enter键退出...") 