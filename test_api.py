import requests
import json

def test_fiat():
    url = "https://economia.awesomeapi.com.br/json/all" # Trying json/all instead of last/all which might be better
    print(f"Testing URL: {url}")
    try:
        resp = requests.get(url, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Keys found: {len(data)}")
            print("First item:", list(data.values())[0])
        else:
            print("Error response:", resp.text)
    except Exception as e:
        print(f"Exception: {e}")

    url2 = "https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL,BTC-BRL"
    print(f"\nTesting URL 2: {url2}")
    try:
        resp = requests.get(url2, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
             print("Success URL 2")
    except Exception as e:
        print(f"Exception 2: {e}")

if __name__ == "__main__":
    test_fiat()
