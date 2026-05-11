import os
import base64
import yaml
from openai import OpenAI


DATA_DIR = "/home/qianhai/parking_VLM/data"
IMAGE_DIR = os.path.join(DATA_DIR, "anomaly_images_cropped")
PROMPT_YAML = "/home/qianhai/parking_VLM/vlm_prompt.yaml"
RESULT_TXT = os.path.join(DATA_DIR, "vlm_analysis_result.txt")


def load_prompt_config(yaml_path):
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def encode_image_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(client, config, image_path, filename):
    img_b64 = encode_image_base64(image_path)
    user_prompt = config["user_prompt"].format(filename=filename)

    messages = []
    if config.get("system_prompt"):
        messages.append({"role": "system", "content": config["system_prompt"]})

    messages.append({
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
            {"type": "text", "text": user_prompt},
        ],
    })

    extra_body = {}
    if config.get("enable_thinking"):
        extra_body["enable_thinking"] = True

    is_answering = False
    full_reply = ""

    completion = client.chat.completions.create(
        model=config["model"],
        messages=messages,
        extra_body=extra_body if extra_body else None,
        stream=True,
    )

    for chunk in completion:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
        if hasattr(delta, "content") and delta.content:
            if not is_answering:
                print(f"\n{'=' * 20} 完整回复 {'=' * 20}")
                is_answering = True
            print(delta.content, end="", flush=True)
            full_reply += delta.content

    print()
    return full_reply


def main():
    if not os.path.isdir(IMAGE_DIR):
        print(f"图片目录不存在: {IMAGE_DIR}")
        return

    image_files = sorted(f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(".jpg"))
    if not image_files:
        print(f"目录中没有 jpg 图片: {IMAGE_DIR}")
        return

    config = load_prompt_config(PROMPT_YAML)

    client = OpenAI(
        api_key=config.get("api_key") or os.getenv("DASHSCOPE_API_KEY"),
        base_url=config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )

    total = len(image_files)
    success_count = 0
    fail_count = 0

    with open(RESULT_TXT, "w", encoding="utf-8") as out_f:
        out_f.write("VLM 图片分析报告\n")
        out_f.write(f"图片目录: {IMAGE_DIR}\n")
        out_f.write(f"共需分析 {total} 张图片\n")
        out_f.write(f"使用模型: {config.get('model')}\n")
        out_f.write("=" * 50 + "\n\n")
        out_f.flush()

        for i, filename in enumerate(image_files, 1):
            image_path = os.path.join(IMAGE_DIR, filename)

            print(f"\n{'#' * 50}")
            print(f"[{i}/{total}] 分析: {filename}")
            print(f"{'#' * 50}")

            out_f.write(f"[{i}/{total}] {filename}\n")

            try:
                reply = analyze_image(client, config, image_path, filename)
                out_f.write("状态: 成功\n")
                out_f.write("分析结论:\n")
                out_f.write(reply + "\n")
                success_count += 1
            except Exception as e:
                msg = f"分析失败: {e}"
                print(msg)
                out_f.write(f"状态: 失败\n结论: {msg}\n")
                fail_count += 1

            out_f.write("-" * 50 + "\n\n")
            out_f.flush()

        out_f.write("\n" + "=" * 50 + "\n")
        out_f.write(f"分析完成: 成功 {success_count} 张, 失败 {fail_count} 张\n")

    print(f"\n\n分析报告已保存到: {RESULT_TXT}")
    print(f"成功: {success_count}, 失败: {fail_count}")


if __name__ == "__main__":
    main()
