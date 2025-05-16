import requests
import json,uuid
import re
from datetime import datetime
from typing import Generator

class ZAIChatClient:
    def __init__(self, base_url="https://chat.z.ai"):
        self.base_url = base_url
        self.headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
            'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImQxNDQyZWU4LTBhMWItNDhhMi05NjU1LWYzMjkxMTdlZDRiMiJ9.G_c2_6hVJYycmqaJVk04ODKez1MjWcW-dqVYldjss-4',
            'content-type': 'application/json',
            'origin': 'https://chat.z.ai',
            'priority': 'u=1, i',
            'referer': 'https://chat.z.ai/',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
        }

    def stream_chat_completion(self, messages: list, model: str = "deep-research") -> Generator[str, None, None]:
        """
        Stream chat completion from ZAI API
        
        Args:
            messages: List of message dictionaries with role and content
            model: Model to use for completion
            
        Yields:
            Generator that yields chunks of the response
        """
        print("[DEBUG] stream_chat_completion called")
        json_data = {
            'stream': True,
            'model': model,
            'messages': messages,
            'params': {},
            'tool_servers': [],
            'features': {
                'image_generation': False,
                'code_interpreter': False,
                'web_search': False,
                'auto_web_search': False,
                'preview_mode': False,
            },
            'variables': {
                '{{USER_NAME}}': 'Guest',
                '{{USER_LOCATION}}': 'Unknown',
                '{{CURRENT_DATETIME}}': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '{{CURRENT_DATE}}': datetime.now().strftime('%Y-%m-%d'),
                '{{CURRENT_TIME}}': datetime.now().strftime('%H:%M:%S'),
                '{{CURRENT_WEEKDAY}}': datetime.now().strftime('%A'),
                '{{CURRENT_TIMEZONE}}': 'Asia/Shanghai',
                '{{USER_LANGUAGE}}': 'zh-CN',
            },
            'model_item': {
                'id': model,
                'name': 'Deep Research',
                'owned_by': 'openai',
                'urlIdx': 0
            },
            'chat_id': 'local',
            'id': str(uuid.uuid4())
        }

        print("[DEBUG] Sending POST request to:", f'{self.base_url}/api/chat/completions')
        with requests.post(
            f'{self.base_url}/api/chat/completions',
            headers=self.headers,
            json=json_data,
            stream=True
        ) as response:
            print("[DEBUG] Response status code:", response.status_code)
            response.raise_for_status()
            # Use a more sophisticated approach to track output
            last_output = ""
            output_buffer = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data = json.loads(decoded_line[6:])
                        try:
                            content = data['data']['data']['content']
                            # Remove <summary>...</summary> and their content
                            # Remove <summary>...</summary> and their content
                            content = re.sub(r'<summary.*?>.*?</summary>', '', content, flags=re.DOTALL)
                            # Remove any remaining HTML tags
                            text = re.sub(r'<[^>]+>', '', content)

                            # 完整的文本清理流程
                            # 1. 先处理所有大于号
                            text = re.sub(r'>\s*', '', text)  # 去除所有大于号及其后的空格

                            # 2. 处理换行和空格
                            text = re.sub(r'\s*\n\s*', ' ', text)  # 换行符替换为单个空格
                            text = re.sub(r'\s{2,}', ' ', text)  # 多个连续空格替换为单个空格

                            # 3. 处理中文标点符号
                            text = re.sub(r'([，。！？；：""''（）【】《》])[\s]+', r'\1', text)  # 中文标点后的空格去除

                            # 4. 处理英文标点符号
                            text = re.sub(r'([,.!?;:\"\'\\(\\)\\[\\]<>])[\s]+', r'\1 ', text)  # 英文标点后保留一个空格

                            # 5. 处理中文词语之间的空格 - 关键改进
                            text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', text)  # 移除中文字符之间的空格
                            # Handle cases where the model might restart or modify previous content
                            # Find the longest common prefix
                            i = 0
                            while i < min(len(last_output), len(text)) and last_output[i] == text[i]:
                                i += 1
                            
                            # If text is completely different or shorter than last_output
                            # (model might have restarted or modified content)
                            if i < len(last_output) * 0.8:  # Less than 80% match
                                # Consider it a restart
                                print("\n[DEBUG] Content restart detected")
                                new_text = text
                                output_buffer = ""
                            else:
                                # Normal incremental update
                                new_text = text[i:]
                            
                            last_output = text
                            
                            # Detect and handle duplicates in the stream
                            if new_text and not output_buffer.endswith(new_text):
                                output_buffer += new_text
                                yield new_text
                        except Exception as e:
                            print(f"[ERROR] Failed to extract content: {e}")

# Example usage:
if __name__ == "__main__":
    print("[DEBUG] Main started")
    client = ZAIChatClient()
    messages = [
        {
            'role': 'user',
            'content': '研究下A股近期寻龙思路和热门题材和标的'
        }
    ]
    
    # 用于保存完整响应的变量
    full_response = ""
    
    # 流式输出并收集完整响应
    for chunk in client.stream_chat_completion(messages):
        print(chunk, end='', flush=True)
        full_response += chunk
    
    print('\n\nChat completed.')
    
    # 将完整响应保存到 result.md 文件
    with open('result.md', 'w', encoding='utf-8') as f:
        f.write(full_response)
    
    print(f"\n响应已保存到 result.md 文件")