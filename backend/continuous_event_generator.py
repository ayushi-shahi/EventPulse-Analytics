# continuous_event_generator.py
import requests
import time
import random
from datetime import datetime

API_KEY = "ep_live_7526cc263f58ec8856cc9762f1f098ac5adcba8f78fbb140b56fed2d6984d65c"
BASE_URL = "http://127.0.0.1:8000/api/v1"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

event_types = [
    "page_view", "button_click", "form_submit", 
    "api_call", "purchase", "error", "login", "logout"
]

pages = ["/home", "/dashboard", "/profile", "/settings", "/checkout"]

def send_random_event():
    """Generate and send a random event"""
    event = {
        "event_name": random.choice(event_types),
        "user_id": f"user_{random.randint(1, 50)}",
        "properties": {
            "page": random.choice(pages),
            "timestamp": datetime.utcnow().isoformat(),
            "value": round(random.uniform(1, 100), 2)
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/ingest/events",
        json=event,
        headers=headers
    )
    
    if response.status_code == 202:
        print(f"✅ {datetime.now().strftime('%H:%M:%S')} - Sent: {event['event_name']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        return False

if __name__ == "__main__":
    if API_KEY == "YOUR_API_KEY_HERE":
        print("❌ Please set your API_KEY!")
        exit(1)
    
    print("🚀 Starting continuous event generator...")
    print("Sending 1 event every 2 seconds. Press Ctrl+C to stop.\n")
    
    event_count = 0
    
    try:
        while True:
            if send_random_event():
                event_count += 1
                
                # Every 10 events, show summary
                if event_count % 10 == 0:
                    print(f"\n📊 Sent {event_count} events so far\n")
            
            time.sleep(2)  # 2 seconds between events
    
    except KeyboardInterrupt:
        print(f"\n\n👋 Stopped. Total events sent: {event_count}")