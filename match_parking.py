import os
import re
import pandas as pd
from datetime import datetime


DATA_DIR = "/home/qianhai/parking_VLM/data"
PIC_DIRS = [os.path.join(DATA_DIR, "pic1"), os.path.join(DATA_DIR, "pic2")]
EXCEL_PATH = os.path.join(DATA_DIR, "parking_data.xls")
OUTPUT_TXT = os.path.join(DATA_DIR, "unmatched_images.txt")

FILENAME_PATTERN = re.compile(
    r"^(\d+)_(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(.+)\.jpg$"
)


def parse_image_filename(filename):
    m = FILENAME_PATTERN.match(filename)
    if not m:
        return None
    index = int(m.group(1))
    dt = datetime(
        int(m.group(2)), int(m.group(3)), int(m.group(4)),
        int(m.group(5)), int(m.group(6)), int(m.group(7)),
    )
    plate = m.group(8)
    return {"index": index, "datetime": dt, "plate": plate, "filename": filename}


def main():
    all_images = []
    for pic_dir in PIC_DIRS:
        folder_name = os.path.basename(pic_dir)
        for f in os.listdir(pic_dir):
            if not f.lower().endswith(".jpg"):
                continue
            parsed = parse_image_filename(f)
            if parsed:
                parsed["folder"] = folder_name
                all_images.append(parsed)
            else:
                print(f"[警告] 无法解析文件名: {f}")

    all_images.sort(key=lambda x: x["datetime"])
    time_min = all_images[0]["datetime"]
    time_max = all_images[-1]["datetime"]
    print(f"图片总数: {len(all_images)}")
    print(f"时间区间: {time_min} ~ {time_max}")
    print()

    df = pd.read_excel(EXCEL_PATH)
    df["驶入时间"] = pd.to_datetime(df["驶入时间"])
    df["驶出时间"] = pd.to_datetime(df["驶出时间"])

    mask = (
        ((df["驶入时间"] >= time_min) & (df["驶入时间"] <= time_max))
        | ((df["驶出时间"] >= time_min) & (df["驶出时间"] <= time_max))
    )
    df_filtered = df[mask].copy()
    print(f"Excel总记录数: {len(df)}")
    print(f"时间区间内的记录数: {len(df_filtered)}")
    print()

    excel_plates = set(df_filtered["车牌号码"].str.strip().tolist())

    matched = []
    unmatched = []
    for img in all_images:
        plate = img["plate"].strip()
        if plate in excel_plates:
            matched.append(img)
        else:
            unmatched.append(img)

    print(f"匹配成功: {len(matched)} 张")
    print(f"匹配失败: {len(unmatched)} 张")
    print()

    if unmatched:
        print("未匹配的图片:")
        with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
            for img in unmatched:
                line = f"{img['folder']}/{img['filename']}"
                print(f"  {line}")
                f.write(line + "\n")
        print(f"\n未匹配图片列表已保存到: {OUTPUT_TXT}")
    else:
        print("所有图片均匹配成功！")


if __name__ == "__main__":
    main()
