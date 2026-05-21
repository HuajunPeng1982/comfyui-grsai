import json
import time
import base64
import io
import numpy as np
from PIL import Image
import requests
import torch

# Use a session that ignores system proxy settings
_http = requests.Session()
_http.trust_env = False

# Aspect ratio -> image size mapping per model
VIP_SIZES = {
    "1:1": ["1024x1024", "2048x2048", "2880x2880"],
    "16:9": ["1280x720", "2048x1152", "3840x2160"],
    "9:16": ["720x1280", "1152x2048", "2160x3840"],
    "4:3": ["1152x864", "2304x1728", "3264x2448"],
    "3:4": ["864x1152", "1728x2304", "2448x3264"],
    "3:2": ["1536x1024", "2048x1360", "3504x2336"],
    "2:3": ["1024x1536", "1360x2048", "2336x3504"],
    "5:4": ["1120x896", "2240x1792", "3200x2560"],
    "4:5": ["896x1120", "1792x2240", "2560x3200"],
    "21:9": ["1456x624", "2912x1248", "3840x1648"],
    "9:21": ["624x1456", "1248x2912", "1648x3840"],
    "1:3": ["688x2048", "1280x3840"],
    "3:1": ["2048x688", "3840x1280"],
    "2:1": ["1536x768", "3072x1536", "3840x1920"],
    "1:2": ["768x1536", "1536x3072", "1920x3840"],
}

STANDARD_SIZES = {
    "1:1": ["1024x1024"],
    "16:9": ["1672x941"],
    "9:16": ["941x1672"],
    "4:3": ["1443x1090"],
    "3:4": ["1090x1443"],
    "3:2": ["1536x1024"],
    "2:3": ["1024x1536"],
    "5:4": ["1408x1120"],
    "4:5": ["1120x1408"],
    "21:9": ["1920x832"],
    "9:21": ["832x1920"],
    "1:2": ["896x1792"],
    "2:1": ["1792x896"],
}

# gpt-image-2 has no 1:3 or 3:1
STANDARD_RATIOS = [k for k in STANDARD_SIZES.keys()]
VIP_RATIOS = [k for k in VIP_SIZES.keys()]

ALL_SIZES = sorted(set(
    size for sizes in {**VIP_SIZES, **STANDARD_SIZES}.values() for size in sizes
))


def tensor_to_base64(img_tensor):
    """Convert a single ComfyUI image tensor [H, W, C] float32(0-1) to base64 PNG string."""
    img_np = (img_tensor.cpu().numpy() * 255).astype(np.uint8)
    pil_img = Image.fromarray(img_np, mode="RGB")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def url_to_tensor(url, timeout=60):
    """Download an image from URL and convert to ComfyUI tensor [1, H, W, C] float32."""
    last_error = None
    for i in range(3):
        try:
            resp = _http.get(url, timeout=timeout)
            resp.raise_for_status()
            pil_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img_np = np.array(pil_img).astype(np.float32) / 255.0
            return torch.from_numpy(img_np).unsqueeze(0)
        except Exception as e:
            last_error = e
            if i < 2:
                time.sleep(2 * (i + 1))
    raise RuntimeError(f"Failed to download image after 3 attempts") from last_error


class GrsaiImageGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "forceInput": True,
                }),
                "model": (["gpt-image-2", "gpt-image-2-vip"], {
                    "default": "gpt-image-2",
                }),
                "api_key": ("STRING", {
                    "multiline": False,
                    "default": "sk-3e09bb0bd5d541b2b6e9e683d08e74fd",
                }),
                "base_url": ("STRING", {
                    "multiline": False,
                    "default": "https://grsai.dakka.com.cn",
                }),
                "aspect_ratio": (VIP_RATIOS, {
                    "default": "1:1",
                }),
                "image_size": (ALL_SIZES, {
                    "default": "1024x1024",
                }),
                "reply_type": (["json", "async"], {
                    "default": "json",
                }),
                "timeout": ("INT", {
                    "default": 300,
                    "min": 30,
                    "max": 3600,
                    "display": "number",
                }),
                "retry_count": ("INT", {
                    "default": 1,
                    "min": 0,
                    "max": 10,
                    "display": "number",
                }),
            },
            "optional": {
                f"image_{i}": ("IMAGE",) for i in range(1, 17)
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "image_url", "response")
    FUNCTION = "generate"
    CATEGORY = "Grsai"

    def _collect_images(self, kwargs):
        """Collect connected image inputs (up to 16), convert each to base64."""
        images = []
        for i in range(1, 17):
            key = f"image_{i}"
            val = kwargs.get(key)
            if val is None:
                continue
            # val could be a batch tensor [B, H, W, C]
            # Take the first image from each connected input
            if isinstance(val, torch.Tensor):
                if val.ndim == 3:
                    images.append(tensor_to_base64(val))
                elif val.ndim == 4:
                    for j in range(val.shape[0]):
                        images.append(tensor_to_base64(val[j]))
            if len(images) >= 16:
                break
        return images

    def _request_with_retry(self, url, headers, body, retry_count):
        last_error = None
        for attempt in range(retry_count + 1):
            try:
                resp = _http.post(url, headers=headers, json=body, timeout=300)
                if resp.status_code == 400:
                    err_detail = resp.text
                    raise RuntimeError(f"API 400 error: {err_detail}")
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "")
                if status == "violation":
                    raise RuntimeError("Content violation")
                if status == "failed":
                    err = data.get("error", "Unknown error")
                    raise RuntimeError(f"Generation failed: {err}")
                return data
            except RuntimeError:
                raise
            except Exception as e:
                last_error = e
                if attempt < retry_count:
                    time.sleep(2 * (attempt + 1))
        raise RuntimeError(
            f"Request failed after {retry_count + 1} attempts"
        ) from last_error

    def _poll_async(self, base_url, headers, task_id, timeout):
        query_url = f"{base_url.rstrip('/')}/v1/api/result?id={task_id}"
        deadline = time.time() + timeout
        interval = 2
        consecutive_errors = 0
        while time.time() < deadline:
            time.sleep(min(interval, deadline - time.time()))
            if time.time() >= deadline:
                break
            try:
                resp = _http.get(query_url, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "")
                if status == "succeeded":
                    return data
                if status == "violation":
                    raise RuntimeError("Content violation")
                if status == "failed":
                    err = data.get("error", "Unknown error")
                    raise RuntimeError(f"Generation failed: {err}")
                consecutive_errors = 0
                interval = min(interval + 1, 10)
            except RuntimeError:
                raise
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    raise RuntimeError(
                        f"Polling failed after {consecutive_errors} consecutive errors"
                    ) from e
                interval = min(interval + 2, 15)
        raise TimeoutError(
            f"Async generation timed out after {timeout}s. task_id={task_id}"
        )

    def generate(self, prompt, model, api_key, base_url, aspect_ratio, image_size,
                 reply_type, timeout, retry_count, **kwargs):
        images = self._collect_images(kwargs)

        body = {
            "model": model,
            "prompt": prompt,
            "images": images,
            "aspectRatio": image_size,
            "replyType": reply_type,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        api_url = f"{base_url.rstrip('/')}/v1/api/generate"

        # Step 1: call generation API (with retry)
        resp_data = self._request_with_retry(api_url, headers, body, retry_count)

        # Step 2: async polling if needed
        if reply_type == "async":
            task_id = resp_data.get("id", "")
            if not task_id:
                raise RuntimeError("Async response missing task id")
            resp_data = self._poll_async(base_url, headers, task_id, timeout)

        # Step 3: download result image
        results = resp_data.get("results", [])
        image_url = results[0].get("url", "") if results else ""
        img_tensor = None
        if image_url:
            try:
                img_tensor = url_to_tensor(image_url)
            except Exception as e:
                raise RuntimeError(f"Failed to download result image: {e}")

        if img_tensor is None:
            img_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32, device="cpu")

        response_json = json.dumps(resp_data, ensure_ascii=False)

        return (img_tensor, image_url, response_json)


NODE_CLASS_MAPPINGS = {
    "GrsaiImageGenerate": GrsaiImageGenerate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GrsaiImageGenerate": "Grsai Image Generate",
}
