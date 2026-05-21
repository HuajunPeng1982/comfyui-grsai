# ComfyUI Grsai Node

Generate images via Grsai API (gpt-image-2 / gpt-image-2-vip) directly in ComfyUI.

## Installation

Copy the `comfyui-grsai` folder into ComfyUI's `custom_nodes` directory:

```
ComfyUI/custom_nodes/comfyui-grsai/
├── __init__.py
├── js/
│   └── grsai_dynamic.js
└── README.md
```

No additional dependencies required. Uses only libraries already available in ComfyUI's Python environment.

## Node: Grsai Image Generate

### Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| prompt | STRING | - | Text prompt or JSON string. Can be wired or typed. |
| model | dropdown | gpt-image-2 | gpt-image-2 or gpt-image-2-vip |
| api_key | STRING | (built-in) | Grsai API key (without "Bearer" prefix) |
| base_url | STRING | https://grsai.dakka.com.cn | API base URL |
| aspect_ratio | dropdown | 1:1 | Image aspect ratio (options depend on model) |
| image_size | dropdown | 1024x1024 | Output resolution (options depend on model and ratio) |
| reply_type | dropdown | json | json (sync) or async (polling) |
| timeout | INT | 300 | Overall timeout in seconds (async mode) |
| retry_count | INT | 1 | Retry attempts on failure |
| image_1 ~ image_16 | IMAGE | - | Optional reference images (wire input) |

### Outputs

| Name | Type | Description |
|------|------|-------------|
| image | IMAGE | Generated image |
| image_url | STRING | Direct image URL |
| response | STRING | Full API response JSON |
