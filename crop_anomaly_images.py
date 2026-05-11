import os
from PIL import Image
import numpy as np


DATA_DIR = "/home/qianhai/parking_VLM/data"
SRC_DIR = os.path.join(DATA_DIR, "anomaly_images")
DST_DIR = os.path.join(DATA_DIR, "anomaly_images_cropped")

DARK_PIXEL_THRESHOLD = 30
DARK_RATIO_THRESHOLD = 0.5
CONFIRM_WINDOW = 20
CONFIRM_RATIO = 0.7


def detect_crop_y(img):
    arr = np.array(img.convert("RGB"))
    H = arr.shape[0]

    is_dark = arr.max(axis=2) < DARK_PIXEL_THRESHOLD
    dark_ratio = is_dark.mean(axis=1)

    for y in range(H - 1, -1, -1):
        if dark_ratio[y] < DARK_RATIO_THRESHOLD:
            window = dark_ratio[max(0, y - CONFIRM_WINDOW):y]
            if len(window) > 0 and (window < DARK_RATIO_THRESHOLD).mean() > CONFIRM_RATIO:
                return y + 1
    return H


def main():
    if not os.path.isdir(SRC_DIR):
        print(f"源目录不存在: {SRC_DIR}")
        return

    os.makedirs(DST_DIR, exist_ok=True)

    files = [f for f in sorted(os.listdir(SRC_DIR)) if f.lower().endswith(".jpg")]
    if not files:
        print(f"源目录中没有 jpg 图片: {SRC_DIR}")
        return

    for fname in files:
        src = os.path.join(SRC_DIR, fname)
        dst = os.path.join(DST_DIR, fname)

        img = Image.open(src)
        W, H = img.size
        cut_y = detect_crop_y(img)
        cropped = img.crop((0, 0, W, cut_y))
        cropped.save(dst, quality=95)

        print(f"{fname}: {W}x{H} -> {W}x{cut_y} (裁掉底部 {H - cut_y} 像素)")

    print(f"\n完成: 共裁剪 {len(files)} 张图片，保存到 {DST_DIR}")


if __name__ == "__main__":
    main()
