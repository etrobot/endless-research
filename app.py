import requests
import json,uuid
import re,os,random
from datetime import datetime
from typing import Generator
from pyairtable import Table
import logging
import os, builtins

if not os.getenv('TESTING'):
    builtins.print = lambda *args, **kwargs: None
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
else:
    logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
AIRTABLE_KEY = os.environ.get('AIRTABLE_KEY') or 'YOUR_SECRET_API_TOKEN'
AIRTABLE_BASE_ID = 'applo1KcfFekTkIAU'
AIRTABLE_TABLE_NAME = 'ashare'

FINAL=''

def get_bearer_token_from_airtable_cookie():
    table = Table(AIRTABLE_KEY, AIRTABLE_BASE_ID, 'cookies')
    records = table.all(fields=["value"])
    if not records:
        raise Exception("No cookie records found in Airtable!")
    cookie_str = records[0]['fields']['value']
    logging.debug(f"[DEBUG] Airtable cookies string: {cookie_str[:80]}...")
    m = re.search(r'token=([^;]+)', cookie_str)
    if not m:
        raise Exception("token not found in cookie string!")
    bearer_token = m.group(1)
    logging.debug(f"[DEBUG] 提取到的bearer token: {bearer_token[:20]}...")
    return cookie_str,bearer_token

class ZAIChatClient:
    def __init__(self, base_url="https://chat.z.ai"):
        self.base_url = base_url
        cookie_str,bearer_token = get_bearer_token_from_airtable_cookie()
        self.headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'authorization': f'Bearer {bearer_token}',
            'content-type': 'application/json',
            'origin': 'https://chat.z.ai',
            'priority': 'u=1, i',
            'referer': 'https://chat.z.ai/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'cookies':cookie_str,
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
        # 创建一个集合来存储HTML标签
        html_tags = set()

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
                            # 收集HTML标签并移除它们
                            # 首先处理特殊的summary标签及其内容
                            summary_tag_patten = r'<summary.*?>.*?</summary>'
                            summary_tags = re.findall(summary_tag_patten, content, flags=re.DOTALL)
                            text = re.sub(summary_tag_patten, '', content, flags=re.DOTALL)

                            # 然后处理其他HTML标签
                            other_tags = re.findall(r'<[^>]+>', content)
                            for tag in other_tags:
                                html_tags.add(tag)
                            text = re.sub(r'<[^>]+>', '', content)
                            # 移除中文字符之间的空格
                            # text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', text)
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
                                if os.getenv('TESTING'):
                                    new_text = new_text.rstrip('\n')
                                output_buffer += new_text
                                for tag in summary_tags:
                                    if tag not in html_tags:
                                        html_tags.add(tag)
                                        new_text += tag
                                yield new_text
                        except Exception as e:
                            logging.error(f"Failed to extract content: {e}")
                    else:
                        print(decoded_line)
            # 在处理完所有响应后，打印收集到的HTML标签
            if html_tags:
                logging.info("\n[INFO] 收集到的HTML标签:")
                for tag in sorted(html_tags):
                    logging.info(f"  {tag}")

# Example usage:
def mission():
    refs = Table(AIRTABLE_KEY,AIRTABLE_BASE_ID, 'prompt').all(fields=["Name", "Notes"],formula=f"{{status}} = 'Done'")
    random_refs ='\n'.join(x['fields']['Name']+':'+x['fields']['Notes'] for x in random.sample(refs, 5))
    prompt = random_refs+'\n'+Table(AIRTABLE_KEY,AIRTABLE_BASE_ID, 'prompt').all(fields=["Name", "Notes"],formula=f"{{status}} = 'Todo'")[0]['fields']['Notes']

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
        if os.getenv('TESTING'):
            print(chunk, end='', flush=True)
        full_response += chunk

    logging.info('\n\nChat completed')
    # logging.debug(f'\n[DEBUG] 完整回复内容如下：\n{full_response}')

    # ======= 新增：抽取标题和正文 =======
    def extract_title_and_notes(text):
        title = text
        # 提取第一个 # 到换行符之间的内容作为标题
        title_match = re.search(r'# (.*?)(?:\n|$)', text)
        if title_match:
            title = title_match.group(1).strip()
        return title[:30]

    # 处理大模型输出，去除 finish 标记
    # 使用 <summary>Thought for xx seconds</summary> 标签后的内容作为回复的主要内容，其中秒数是不固定的
    # splits = re.split(r'<summary>Thought for \d+ seconds</summary>', full_response)
    # content = splits[-1].strip()
    try:
        content=full_response.split(' seconds</summary>\n# ')[1]
    except:
        content=full_response.split('\n# ')[1]
    logging.debug(f'\n[DEBUG] 抽取文章如下：\n{content}')

    # ======= 新增：去除末尾重复链接，只保留最后一个 =======
    # 匹配 http/https 链接和 markdown 链接
    link_pattern = r'(https?://[\w\-./?%&=:#@]+|\[[^\]]+\]\([^)]+\))'
    links = list(re.finditer(link_pattern, content))
    
    if links:
        # 用于存储处理后的内容
        content_new = ""
        # 用于记录已处理的链接
        processed_links = set()
        
        for i, link_match in enumerate(links):
            link = link_match.group(0)
            # 如果是markdown链接，提取URL部分
            if link.startswith('['):
                url = re.search(r'\((.*?)\)', link).group(1)
            else:
                url = link
                
            if url in processed_links:
                # 如果链接已存在，将当前链接转换为markdown格式
                content_new += f"[{url}]({url})"
            else:
                # 如果是新链接，保持原样
                content_new += link
                processed_links.add(url)
                
            # 添加链接之间的文本
            if i < len(links) - 1:
                next_start = links[i + 1].start()
                content_new += content[link_match.end():next_start]
            else:
                # 添加最后一个链接后的文本
                content_new += content[link_match.end():]
                
        logging.info(f"[INFO] 处理链接前: {content}")
        logging.info(f"[INFO] 处理链接后: {content_new}")
        content = content_new
    else:
        logging.info("[INFO] 未检测到链接，无需处理")

    name = extract_title_and_notes('# '+content)
    logging.debug(f"[DEBUG] 抽取标题: {name}")

    fields = {
        "Name": name,
        "Notes": content,
        "Status": "Done"
    }
    table =  Table(AIRTABLE_KEY,AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    table.create(fields)