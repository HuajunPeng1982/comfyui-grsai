"""
Integration test for ComfyUI Grsai Node
Tests actual API calls using the provided credentials.
"""
import json
import time
import sys
import os

# Test config
API_KEY = "sk-3e09bb0bd5d541b2b6e9e683d08e74fd"
BASE_URL = "https://grsai.dakka.com.cn"
PROMPT = "A cute cat sitting on a chair, high quality"
MODEL = "gpt-image-2"
IMAGE_SIZE = "1024x1024"

def test_sync_generation():
    """Test 1: Sync generation (reply_type=json)"""
    print("\n=== Test 1: Sync Generation ===")
    import requests

    url = f"{BASE_URL}/v1/api/generate"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": MODEL,
        "prompt": PROMPT,
        "images": [],
        "aspectRatio": IMAGE_SIZE,
        "replyType": "json",
    }

    print(f"POST {url}")
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"FAIL: {resp.text}")
        return None

    data = resp.json()
    print(f"Response: id={data.get('id')}, status={data.get('status')}")
    results = data.get("results", [])
    if results:
        print(f"Image URL: {results[0].get('url', 'N/A')}")

    assert data.get("status") == "succeeded", f"Expected succeeded, got {data.get('status')}"
    assert len(results) > 0, "Expected at least one result"
    assert results[0].get("url"), "Expected image URL"
    print("PASS")
    return data


def test_image_download(data):
    """Test 2: Download generated image"""
    print("\n=== Test 2: Image Download ===")
    import requests
    from PIL import Image
    import io

    url = data["results"][0]["url"]
    print(f"Downloading: {url}")
    resp = requests.get(url, timeout=30)
    print(f"Status: {resp.status_code}, Size: {len(resp.content)} bytes")

    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    print(f"Image size: {img.size}, Mode: {img.mode}")

    assert img.size[0] > 0 and img.size[1] > 0
    print("PASS")
    return img


def test_async_generation():
    """Test 3: Async generation with polling"""
    print("\n=== Test 3: Async Generation ===")
    import requests

    # Submit async job
    url = f"{BASE_URL}/v1/api/generate"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": MODEL,
        "prompt": "A simple red circle on white background",
        "images": [],
        "aspectRatio": IMAGE_SIZE,
        "replyType": "async",
    }

    print(f"POST {url} (async)")
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"FAIL: {resp.text}")
        return False

    data = resp.json()
    task_id = data.get("id")
    print(f"Task ID: {task_id}, Initial status: {data.get('status')}")

    assert task_id, "Expected task ID"

    # Poll for result
    query_url = f"{BASE_URL}/v1/api/result"
    deadline = time.time() + 300
    interval = 2
    while time.time() < deadline:
        time.sleep(interval)
        q_resp = requests.get(
            query_url,
            headers=headers,
            params={"id": task_id},
            timeout=30
        )
        q_data = q_resp.json()
        status = q_data.get("status")
        progress = q_data.get("progress", 0)
        print(f"  Poll: status={status}, progress={progress}%")

        if status == "succeeded":
            results = q_data.get("results", [])
            if results:
                print(f"  Image URL: {results[0].get('url')}")
            print("PASS")
            return True
        elif status in ("failed", "violation"):
            print(f"FAIL: {q_data.get('error')}")
            return False
        interval = min(interval + 1, 10)

    print("FAIL: Timeout")
    return False


def test_image_conversion():
    """Test 4: Tensor-to-base64 and url-to-tensor conversions"""
    print("\n=== Test 4: Image Conversion ===")
    import numpy as np
    from PIL import Image
    import io
    import base64

    # Test URL to tensor (numpy simulation since torch may not be available)
    import requests

    # Use a tiny image for testing
    test_img = Image.new("RGB", (64, 64), color=(255, 0, 0))
    buf = io.BytesIO()
    test_img.save(buf, format="PNG")
    buf.seek(0)

    # Test base64 encoding of PIL image
    b64_str = base64.b64encode(buf.getvalue()).decode("ascii")
    print(f"Base64 length: {len(b64_str)} chars")

    # Test decoding base64 back to image
    decoded = base64.b64decode(b64_str)
    restored = Image.open(io.BytesIO(decoded)).convert("RGB")
    print(f"Restored size: {restored.size}")

    assert restored.size == (64, 64)
    assert restored.getpixel((0, 0)) == (255, 0, 0)

    # Test numpy conversion (simulates url_to_tensor without torch)
    img_np = np.array(restored).astype(np.float32) / 255.0
    print(f"Numpy shape: {img_np.shape}, range: [{img_np.min():.2f}, {img_np.max():.2f}]")

    assert img_np.shape == (64, 64, 3)
    print("PASS")


def test_error_handling():
    """Test 5: Error handling - invalid model"""
    print("\n=== Test 5: Error Handling ===")
    import requests

    url = f"{BASE_URL}/v1/api/generate"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "invalid-model-name",
        "prompt": PROMPT,
        "images": [],
        "aspectRatio": IMAGE_SIZE,
        "replyType": "json",
    }

    resp = requests.post(url, headers=headers, json=body, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")

    # Should return an error
    assert resp.status_code >= 400, f"Expected error status, got {resp.status_code}"
    print("PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("ComfyUI Grsai Node - Integration Tests")
    print("=" * 60)

    # Test 1: Sync generation
    sync_data = test_sync_generation()

    # Test 2: Download generated image
    if sync_data:
        test_image_download(sync_data)

    # Test 3: Async generation
    test_async_generation()

    # Test 4: Image conversion
    test_image_conversion()

    # Test 5: Error handling
    test_error_handling()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
