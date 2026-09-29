import httpx
import sys
import json

url = "http://localhost:8000/api/v1/chat/stream"
payload = {
    "question": "በቅጽ 15፣ መዝገብ ቁጥር 80343 በውሳኔው ውስጥ የተገለጸ ዋና የሕግ መርህ ምን ነበር?",
    "case_number": "80343",
    "top_k": 5
}

print("Connecting to stream...\n")

with httpx.Client(timeout=None) as client:
    with client.stream("POST", url, json=payload) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                try:
                    # Strip "data: " and parse the JSON
                    data = json.loads(line[6:])
                    
                    if data["type"] == "info":
                        print(f"[Conversation ID]: {data['conversation_id']}\n")
                    
                    elif data["type"] == "sources":
                        print(f"[Retrieved {len(data['content'])} sources]\n")
                        print("AI Answer: ", end="")
                        sys.stdout.flush()
                        
                    elif data["type"] == "text":
                        # Print the text chunk exactly as it arrives without a newline
                        sys.stdout.write(data["content"])
                        sys.stdout.flush()
                        
                except json.JSONDecodeError:
                    pass

print("\n\n[Stream Finished]")