# Parking VLM - 停车场车牌异常分析工具

基于 VLM（视觉语言模型）的停车场车牌异常检测与分析工具。将停车场摄像头图片与出入记录进行匹配，对无法匹配的异常车辆图片调用 VLM 进行智能分析，判断车牌不匹配的原因。

## 项目流程

```
图片整理 & 匹配 → 提取异常图片 → 裁剪黑色文字区域 → VLM 智能分析 → 输出报告
```

## 模块说明

| 脚本 | 功能 |
|------|------|
| `match_parking.py` | 解析 `data/pic1`、`data/pic2` 中的图片文件名，按时间排序得到时间区间，与 `parking_data.xls` 中的车辆记录按车牌号匹配。未匹配的图片输出到 `data/unmatched_images.txt` |
| `extract_anomaly_images.py` | 读取 `unmatched_images.txt`，将未匹配的异常图片复制到 `data/anomaly_images/` 目录，文件名加上来源文件夹前缀避免重名 |
| `crop_anomaly_images.py` | 自动检测异常图片底部的黑色背景文字区域并裁剪掉，输出到 `data/anomaly_images_cropped/` 目录。使用像素亮度分析自动确定裁剪位置 |
| `analyze_unmatched.py` | 读取裁剪后的图片，逐张调用 VLM API 进行车牌识别与异常分析，结果实时写入 `data/vlm_analysis_result.txt` |
| `vlm_prompt.yaml` | VLM 配置文件，包含 API 地址、模型名称、提示词等参数，修改提示词无需改代码 |

## 数据结构

```
data/
├── pic1/                        # 摄像头1 原始图片
├── pic2/                        # 摄像头2 原始图片
├── parking_data.xls             # 停车场出入记录
├── unmatched_images.txt         # 未匹配图片列表（自动生成）
├── anomaly_images/              # 提取出的异常图片（自动生成）
├── anomaly_images_cropped/      # 裁剪后的异常图片（自动生成）
└── vlm_analysis_result.txt      # VLM 分析报告（自动生成）
```

## 使用方法

### 1. 安装依赖

```bash
pip install pandas openpyxl xlrd pillow numpy pyyaml openai
```

### 2. 配置 API Key

编辑 `vlm_prompt.yaml`，填入阿里云百炼 API Key：

```yaml
api_key: "sk-your-api-key-here"
```

或通过环境变量设置：

```bash
export DASHSCOPE_API_KEY="sk-your-api-key-here"
```

### 3. 按顺序运行

```bash
# Step 1: 匹配图片与停车记录
python3 match_parking.py

# Step 2: 提取异常图片
python3 extract_anomaly_images.py

# Step 3: 裁剪图片底部文字区域
python3 crop_anomaly_images.py

# Step 4: VLM 分析
python3 analyze_unmatched.py
```

### 4. 查看结果

分析报告保存在 `data/vlm_analysis_result.txt`。

## 配置说明

`vlm_prompt.yaml` 支持以下配置项：

| 字段 | 说明 |
|------|------|
| `api_key` | 阿里云百炼 API Key |
| `base_url` | API 地址 |
| `model` | 模型名称（如 `qwen-vl-plus`） |
| `enable_thinking` | 是否开启思考过程输出 |
| `system_prompt` | 系统提示词 |
| `user_prompt` | 用户提示词，支持 `{filename}` 占位符 |
