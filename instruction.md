写一个python脚本，做以下操作：

1.对/home/qianhai/parking_VLM/data中两个文件夹里的图片做整理，安装时间顺序排序，得到一个时间区间。用这个时间区间去parking_data.xls文件中找到对应的车辆信息。每辆车对应一张图片。如果对应不上的，输出对应图片的文件名，并存到一个txt里

2.
from openai import OpenAI
import os

client = OpenAI(
    # 如果没有配置环境变量，请用阿里云百炼API Key替换：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

messages = [{"role": "user", "content": "你是谁"}]
completion = client.chat.completions.create(
    model="qwen3.6-plus",  # 您可以按需更换为其它深度思考模型
    messages=messages,
    extra_body={"enable_thinking": True},
    stream=True
)
is_answering = False  # 是否进入回复阶段
print("\n" + "=" * 20 + "思考过程" + "=" * 20)
for chunk in completion:
    delta = chunk.choices[0].delta
    if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
        if not is_answering:
            print(delta.reasoning_content, end="", flush=True)
    if hasattr(delta, "content") and delta.content:
        if not is_answering:
            print("\n" + "=" * 20 + "完整回复" + "=" * 20)
            is_answering = True
        print(delta.content, end="", flush=True)
以上为VLM相关配置，APi_key我会自己填，我想要用VLM模型对unmatched_images.txt中对应的图片，来判断是什么情况导致对应不上。VLM的提示词暴露为一个yaml文件便于修改
