import os
import re
import json
import base64
import yaml
import pandas as pd
from datetime import datetime
from openai import OpenAI


DATA_DIR = "/home/qianhai/parking_VLM/data"
IMAGE_DIR = os.path.join(DATA_DIR, "anomaly_images_cropped")
EXCEL1_PATH = os.path.join(DATA_DIR, "parking_data_1.xls")   # 出入完整记录，用于无牌车时间匹配
EXCEL2_PATH = os.path.join(DATA_DIR, "parking_data_2.xls")   # 未驶出记录，用于疑似逃费核查
PROMPT_YAML = "/home/qianhai/parking_VLM/vlm_prompt.yaml"
RESULT_TXT = os.path.join(DATA_DIR, "vlm_analysis_result.txt")

TIME_TOLERANCE_SECONDS = 60


def load_prompt_config(yaml_path):
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def encode_image_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def parse_exit_time(filename):
    m = re.match(r"pic\d+_\d+_(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})", filename)
    if not m:
        return None
    return datetime(
        int(m.group(1)), int(m.group(2)), int(m.group(3)),
        int(m.group(4)), int(m.group(5)), int(m.group(6)),
    )


def lookup_unlicensed(df1, exit_time):
    """无牌车：返回驶出时间 >= 图片时间的第一条记录的车牌号码"""
    if exit_time is None:
        return None
    after = df1[df1["驶出时间"] >= exit_time].sort_values("驶出时间")
    if not after.empty:
        return after.iloc[0]["车牌号码"]
    return None


def lookup_escape(df2, plate):
    """疑似逃费：在 parking_data_2 中查车牌，返回匹配信息"""
    if not plate:
        return None
    matched = df2[df2["车牌号码"].str.strip() == plate.strip()]
    if not matched.empty:
        row = matched.iloc[0]
        entry_time = pd.to_datetime(row.get("驶入时间"), errors="coerce")
        exit_time = pd.to_datetime(row.get("预出场时间"), errors="coerce")
        duration = None
        if pd.notna(entry_time) and pd.notna(exit_time):
            duration = exit_time - entry_time
        return {
            "status": "confirmed",
            "驶入时间": entry_time if pd.notna(entry_time) else None,
            "预出场时间": exit_time if pd.notna(exit_time) else None,
            "停车时长": duration,
        }
    return {"status": "manual"}


def analyze_image(client, config, image_path, filename):
    img_b64 = encode_image_base64(image_path)
    user_prompt = config["user_prompt"].replace("{filename}", filename)

    messages = []
    if config.get("system_prompt", "").strip():
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
                is_answering = True
            print(delta.content, end="", flush=True)
            full_reply += delta.content

    print()
    return full_reply


def extract_json(text):
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


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

    df1 = pd.read_excel(EXCEL1_PATH)
    df1["驶出时间"] = pd.to_datetime(df1["驶出时间"])

    df2 = pd.read_excel(EXCEL2_PATH)

    total = len(image_files)
    success_count = 0
    fail_count = 0

    with open(RESULT_TXT, "w", encoding="utf-8") as out_f:
        out_f.write("VLM 图片分析报告\n")
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
                vlm_json = extract_json(reply)

                if vlm_json:
                    out_f.write("VLM分析:\n")
                    out_f.write(json.dumps(vlm_json, ensure_ascii=False, indent=2) + "\n")

                    situation = vlm_json.get("车牌情况", "")
                    plate = vlm_json.get("车牌号码", "")

                    if situation == "无牌":
                        # 无牌车：按出场时间查 parking_data_1
                        exit_time = parse_exit_time(filename)
                        record = lookup_unlicensed(df1, exit_time)
                        if record:
                            time_str = exit_time.strftime("%Y-%m-%d %H:%M:%S")
                            out_f.write(f"XLS查询(人工登记): 驶出时间 {time_str} → 登记号码: {record}（人工登记）\n")
                            print(f"  XLS查询: {time_str} → {record}（人工登记）")
                        else:
                            out_f.write("XLS查询: 未找到对应记录\n")
                            print("  XLS查询: 未找到对应记录")

                    elif situation == "车牌完整" and plate:
                        # 疑似逃费：在 parking_data_2 中查车牌
                        result = lookup_escape(df2, plate)
                        if result["status"] == "confirmed":
                            entry = result["驶入时间"]
                            exit_ = result["预出场时间"]
                            dur = result["停车时长"]
                            entry_str = entry.strftime("%Y-%m-%d %H:%M:%S") if entry else "空"
                            exit_str = exit_.strftime("%Y-%m-%d %H:%M:%S") if exit_ else "空"
                            dur_str = str(dur) if dur else "无法计算"
                            out_f.write(f"逃费核查: 车牌 {plate} → 确认逃费\n")
                            out_f.write(f"  驶入时间: {entry_str}\n")
                            out_f.write(f"  预出场时间: {exit_str}\n")
                            out_f.write(f"  停车时长: {dur_str}\n")
                            print(f"  逃费核查: {plate} → 确认逃费 | 驶入: {entry_str} | 预出场: {exit_str} | 时长: {dur_str}")
                        else:
                            out_f.write(f"逃费核查: 车牌 {plate} 未在未驶出记录中找到 → 人工登记\n")
                            print(f"  逃费核查: {plate} → 人工登记")

                else:
                    out_f.write("VLM分析（原始输出，JSON解析失败）:\n")
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
