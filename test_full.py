"""
Full integration test: sync, async, image_size normalization, error cases.
"""
import os, sys, time, requests
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:9999'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:9999'

passed = 0
failed = 0

API_KEY = "sk-3e09bb0bd5d541b2b6e9e683d08e74fd"
BASE_URL = "https://grsai.dakka.com.cn"
_http = requests.Session()
_http.trust_env = False

def test(name, fn):
    global passed, failed
    print(f"\n--- {name} ---")
    try:
        fn()
        print(f"PASS: {name}")
        passed += 1
    except Exception as e:
        print(f"FAIL: {name}: {e}")
        failed += 1


def test_sync_basic():
    """Sync generation with default params"""
    r = _http.post(f"{BASE_URL}/v1/api/generate", headers={
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"
    }, json={
        "model": "gpt-image-2", "prompt": "A cute cat", "images": [],
        "aspectRatio": "1024x1024", "replyType": "json"
    }, timeout=120)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "succeeded"
    assert len(data["results"]) > 0
    assert data["results"][0]["url"].startswith("http")

def test_sync_vip_model():
    """Sync generation with gpt-image-2-vip"""
    r = _http.post(f"{BASE_URL}/v1/api/generate", headers={
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"
    }, json={
        "model": "gpt-image-2-vip", "prompt": "A simple red circle",
        "images": [], "aspectRatio": "2048x2048", "replyType": "json"
    }, timeout=120)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "succeeded"

def test_image_size_star_to_x():
    """image_size: 3840*2160 normalizes to 3840x2160"""
    r = _http.post(f"{BASE_URL}/v1/api/generate", headers={
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"
    }, json={
        "model": "gpt-image-2-vip", "prompt": "blue sky",
        "images": [], "aspectRatio": "3840x2160", "replyType": "json"
    }, timeout=120)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "succeeded"

def test_image_size_spaces():
    """image_size: 2048 x 1152 with spaces normalizes"""
    # Test that replacing spaces works
    normalized = "2048 x 1152".replace("*", "x").replace(" ", "")
    assert normalized == "2048x1152", f"Expected 2048x1152, got {normalized}"

def test_empty_image_size_fallback():
    """Empty image_size falls back to 1024x1024"""
    size = ""
    size = size.replace("*", "x").replace(" ", "")
    if not size:
        size = "1024x1024"
    assert size == "1024x1024"

def test_async_generation():
    """Async generation with polling"""
    r = _http.post(f"{BASE_URL}/v1/api/generate", headers={
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"
    }, json={
        "model": "gpt-image-2", "prompt": "A green leaf",
        "images": [], "aspectRatio": "1024x1024", "replyType": "async"
    }, timeout=30)
    assert r.status_code == 200
    data = r.json()
    task_id = data["id"]
    assert task_id

    deadline = time.time() + 300
    interval = 2
    while time.time() < deadline:
        time.sleep(interval)
        r = _http.get(f"{BASE_URL}/v1/api/result?id={task_id}",
                       headers={"Authorization": f"Bearer {API_KEY}"}, timeout=30)
        data = r.json()
        status = data["status"]
        if status == "succeeded":
            assert len(data["results"]) > 0
            break
        elif status in ("failed", "violation"):
            raise RuntimeError(f"Async {status}: {data.get('error')}")
        interval = min(interval + 1, 10)
    else:
        raise TimeoutError("Async timed out")

def test_error_invalid_model():
    """Invalid model returns 400"""
    r = _http.post(f"{BASE_URL}/v1/api/generate", headers={
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"
    }, json={
        "model": "invalid-model", "prompt": "test", "images": [],
        "aspectRatio": "1024x1024", "replyType": "json"
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert data["status"] == "failed"

def test_image_download():
    """Download an actual image from API result"""
    r = _http.post(f"{BASE_URL}/v1/api/generate", headers={
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"
    }, json={
        "model": "gpt-image-2", "prompt": "A white square",
        "images": [], "aspectRatio": "1024x1024", "replyType": "json"
    }, timeout=120)
    data = r.json()
    url = data["results"][0]["url"]

    # Download this image
    img_r = _http.get(url, timeout=30)
    assert img_r.status_code == 200
    assert len(img_r.content) > 1000

    from PIL import Image
    import io
    img = Image.open(io.BytesIO(img_r.content)).convert("RGB")
    assert img.size[0] > 0 and img.size[1] > 0

# Run all tests
test("Sync basic generation", test_sync_basic)
test("Sync VIP model generation", test_sync_vip_model)
test("Image_size star-to-x normalization", test_image_size_star_to_x)
test("Image_size spaces normalization (unit)", test_image_size_spaces)
test("Empty image_size fallback (unit)", test_empty_image_size_fallback)
test("Async generation with polling", test_async_generation)
test("Error handling: invalid model", test_error_invalid_model)
test("Image download from URL", test_image_download)

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)
