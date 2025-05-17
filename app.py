import requests
import json,uuid
import re,os
from datetime import datetime
from typing import Generator


example=''
if os.path.exists("result.md"):
    with open("result.md", "r", encoding="utf-8") as f:
        example = f.read()
    print("[DEBUG] 成功读取 result.md 作为 example")

prompt='''
A股对不同类型龙头股有细分化的“龙系”术语体系，以下是基于市场规律和搜索结果整理的完整分类：

一、按周期属性划分

1. 穿越龙
需跨越至少两个情绪周期（如高潮→冰点→新周期），具有抗跌性和市场地位重塑能力。例如断板后仍逆势连板。

2. 补涨龙
总龙头断板后出现的梯队接力股，通常具有位差优势但缺乏独立性。

3. 活口龙
旧周期退潮中未完全陨落的过渡性标的，常以N型反包形态出现。

二、按市场地位划分

4. 总龙头
阶段性绝对核心，具备板块带动效应。

5. 卡位龙
在旧龙头分歧时迅速接力的新标的，常见于题材切换期

6. 日内龙
单日领涨的先锋股，多为资金情绪试探选择

三、按驱动因素划分

7. 行业龙
行业绝对领导者

8. 概念龙
题材炒作核心

9. 趋势龙
依托基本面长周期走强

四、技术形态划分

10. 换手龙
通过充分换手走强

11. 一字龙
连续一字涨停的通道党标的

五、特殊阶段产物

12. 反核龙
地天板逆转情绪的标的

13. 破局龙
打破市场高度压制的品种

{example}

根据以上分类，搜索近一两周内的A股热点新闻，找出符合定义的标的并分析
'''.format(example)



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
                            # 移除HTML标签
                            content = re.sub(r'<summary.*?>.*?</summary>', '', content, flags=re.DOTALL)
                            text = re.sub(r'<[^>]+>', '', content)
                            
                            # 文本清理流程
                            # 1. 处理换行
                            text = re.sub(r'\s*\n\s*', '\n', text)
                            
                            # 2. 移除中文字符之间的空格
                            text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', text)
                            
                            # 3. 处理标点符号
                            text = re.sub(r'\s*([，。！？；：""''（）【】《》])\s*', r'\1', text)  # 中文标点
                            text = re.sub(r'\s*([,.!?;:"\'\\(\\)\\[\\]<>])\s*', r'\1 ', text)  # 英文标点
                            
                            # 4. 最后处理多余空格
                            text = re.sub(r'\s{2,}', ' ', text)
                            text = text.strip()

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
            'content': prompt
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
        f.write(full_response.split('{"name":"finish","arguments": {}}')[-1])
    
    print(f"\n响应已保存到 result.md 文件")