import os
import shutil


DATA_DIR = "/home/qianhai/parking_VLM/data"
UNMATCHED_TXT = os.path.join(DATA_DIR, "unmatched_images.txt")
ANOMALY_DIR = os.path.join(DATA_DIR, "anomaly_images")


def main():
    if not os.path.exists(UNMATCHED_TXT):
        print(f"未找到文件: {UNMATCHED_TXT}")
        print("请先运行 match_parking.py 生成未匹配图片列表")
        return

    with open(UNMATCHED_TXT, "r", encoding="utf-8") as f:
        unmatched_files = [line.strip() for line in f if line.strip()]

    if not unmatched_files:
        print("未匹配图片列表为空，无需提取。")
        return

    os.makedirs(ANOMALY_DIR, exist_ok=True)

    copied = 0
    missing = 0
    for rel_path in unmatched_files:
        src = os.path.join(DATA_DIR, rel_path)
        if not os.path.exists(src):
            print(f"[警告] 源文件不存在: {src}")
            missing += 1
            continue

        folder_name = os.path.dirname(rel_path).replace("/", "_")
        base_name = os.path.basename(rel_path)
        dst_name = f"{folder_name}_{base_name}" if folder_name else base_name
        dst = os.path.join(ANOMALY_DIR, dst_name)

        shutil.copy2(src, dst)
        copied += 1
        print(f"已复制: {rel_path} -> {dst_name}")

    print()
    print(f"完成: 复制 {copied} 张异常图片到 {ANOMALY_DIR}")
    if missing:
        print(f"缺失文件: {missing} 张")


if __name__ == "__main__":
    main()
