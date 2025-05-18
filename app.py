import requests
import json,uuid
import re,os,random
from datetime import datetime
from typing import Generator
from pyairtable import Table
import logging
import os, builtins

if os.environ.get("ENV") == "prod":
    builtins.print = lambda *args, **kwargs: None

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
AIRTABLE_KEY = os.environ.get('AIRTABLE_KEY') or 'YOUR_SECRET_API_TOKEN'
AIRTABLE_BASE_ID = 'applo1KcfFekTkIAU'
AIRTABLE_TABLE_NAME = 'ashare'


class ZAIChatClient:
    def __init__(self, base_url="https://chat.z.ai"):
        self.base_url = base_url
        self.headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImFhZGIyMmE0LWY5MWQtNDQ3My05MDc1LTU4NGIxZGM4NzZjMSJ9.xv3LC8T2ISFAvlbnUVvQPmbstorjNlN_Bto7mRL_Xns',
            'content-type': 'application/json',
            'origin': 'https://chat.z.ai',
            'priority': 'u=1, i',
            'referer': 'https://chat.z.ai/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
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
        logging.info("[DEBUG] stream_chat_completion called")
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

        logging.debug(f"[DEBUG] Sending POST request to: {self.base_url}/api/chat/completions")
        with requests.post(
            f'{self.base_url}/api/chat/completions',
            headers=self.headers,
            json=json_data,
            stream=True
        ) as response:
            logging.debug(f"Response status code: {response.status_code}")
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
                            if isinstance(content, dict):
                                content = json.dumps(content, ensure_ascii=False)
                            # 移除HTML标签
                            text = re.sub(r'<summary.*?>.*?</summary>', '', content, flags=re.DOTALL)
                            text = re.sub(r'<[^>]+>', '', content)
                            # 移除中文字符之间的空格
                            text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', text)
                            # 处理标点符号
                            text = re.sub(r'\s*([，。！？；："“''（）【】《》])\s*', r'\1', text)  # 中文标点
                            text = re.sub(r'\s*([,.!?;:"\'\\(\\)\\[\\]<>])\s*', r'\1 ', text)  # 英文标点
                            # 最后处理多余空格
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
                                logging.debug("\n[DEBUG] Content restart detected")
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
                            logging.error(f"Failed to extract content: {e}")

# Example usage:
def mission():
    refs = Table(AIRTABLE_KEY,AIRTABLE_BASE_ID, 'prompt').all(fields=["Name", "Notes"])
    random_refs ='\n'.join(x['fields']['Name']+':'+x['fields']['Notes'] for x in random.sample(refs, 5))

    prompt = random_refs+'''
搜索近一两周内的A股新闻，尽量找出符合定义的标的并分析入选原因及可能存在的风险，如果搜索的资讯如果是宏观没有具体个股的跳过
切忌一个标的反复讲解！！
最后输出标的报告（重点是个股，不需要重复解释龙的概念和寻龙理念，不需要标出引用，但个股要加粗！）
报告要有一个新闻感的标题，比如“\n# 有妖气！打破七板压制！警惕极端走势！\n”或者“\n# 炸板回封！超预期暗藏分歧信号！\n”或者“\n# 破局！这一板块或将成为新主线？\n”等，突出内容中精彩的部份
'''

    logging.debug(f"[DEBUG]\n {prompt} \n Main started")
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
    
    logging.info('\n\nChat completed.')
    logging.debug('\n[DEBUG] 完整回复内容如下：\n', full_response)

    # ======= 新增：抽取标题和正文 =======
    def extract_title_and_notes(text):
        lines = text.strip().split('\n')
        # 优先找以#、##、###、标题:开头的行
        for line in lines:
            l = line.strip()
            if l.startswith('#'):
                return l.lstrip('#').strip(), text
            if l.startswith('标题：') or l.startswith('标题:'):
                return l.split('：',1)[-1].strip(), text
        # 否则用前30字
        return text.strip()[:30], text

    # 处理大模型输出，去除 finish 标记
    if '\n> > # ' in full_response:
        content = full_response.split('\n> > # ')[-1]
    elif '"name":"finish"'  in full_response:
        # 用正则查找所有 {"name":"finish" ... }} 作为分隔符
        splits = re.split(r'\{"name":"finish".*?\}\}', full_response)
        content = splits[-1].strip() if splits else ""
        if not isinstance(content, str):
            content = str(content)
    else:
        raise('分割失败')
    name, notes = extract_title_and_notes(content)
    logging.debug(f"[DEBUG] 抽取标题: {name}")

    fields = {
        "Name": name,
        "Notes": notes,
        "Status": "Done"
    }
    table =  Table(AIRTABLE_KEY,AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    table.create(fields)

if __name__ == "__main__":
    mission()