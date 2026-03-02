import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = 'ep_live_9ab68f299a3d2f71234269e2b309b4a891328444441e7a508489e1fa62cc6c72'
BASE_URL = "http://localhost:8002/api/v1"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def send_event(event_num):
    event = {
        "event_name": random.choice(["page_view", "click", "purchase", "error"]),
        "user_id": f"user_{random.randint(1, 100)}",
        "properties": {
            "test": True,
            "event_num": event_num,
            "timestamp": time.time()
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/ingest/events",
            json=event,
            headers=headers,
            timeout=5
        )
        return response.status_code == 202
    except Exception:
        return False

def stress_test(num_events=100, num_workers=10):
    print(f"🚀 Stress Test: {num_events} events, {num_workers} workers\\n")
    
    start_time = time.time()
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(send_event, i) for i in range(num_events)]
        
        for i, future in enumerate(as_completed(futures)):
            if future.result():
                success_count += 1
            
            if (i + 1) % 20 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"   Progress: {i+1}/{num_events} - Rate: {rate:.1f} events/sec")
    
    elapsed_time = time.time() - start_time
    print(f"\\n📊 RESULTS:")
    print(f"   Success: {success_count}/{num_events}")
    print(f"   Rate: {success_count/elapsed_time:.1f} events/sec")

if __name__ == "__main__":
    stress_test(num_events=100, num_workers=10)
