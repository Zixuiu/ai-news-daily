import os
import time
import requests

API_KEY = '1d720464b9794a16a4ceb7a7aafe6752.G64vf7F7gOEwx2QM'
API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'

def test_speed():
    print("=" * 50)
    print("🤖 智谱 GLM-4-Flash 响应速度测试")
    print("=" * 50)
    
    test_messages = [
        "你好",
        "解释一下什么是人工智能",
        "写一首关于春天的诗",
        "帮我总结一下AI的发展历程"
    ]
    
    for msg in test_messages:
        print(f"\n📝 问题: {msg}")
        print("AI: ", end="", flush=True)
        
        start_time = time.time()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }
        
        payload = {
            'model': 'glm-4-flash',
            'messages': [
                {'role': 'user', 'content': msg}
            ],
            'temperature': 0.7,
            'stream': False
        }
        
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            response = data['choices'][0]['message']['content']
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            print(response[:50] + "..." if len(response) > 50 else response)
            print(f"\n⏱️ 响应时间: {elapsed:.2f}秒")
            
        except Exception as e:
            print(f"\n❌ 出错: {e}")
    
    print("\n" + "=" * 50)

if __name__ == '__main__':
    test_speed()