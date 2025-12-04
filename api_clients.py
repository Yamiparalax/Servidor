import requests
from datetime import datetime

class WeatherClient:
    @staticmethod
    def get_weather_sp():
        """
        Busca clima de São Paulo via Open-Meteo API (Free).
        """
        try:
            # Lat/Lon de SP
            url = "https://api.open-meteo.com/v1/forecast?latitude=-23.5475&longitude=-46.6361&current_weather=true&timezone=America%2FSao_Paulo"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                curr = data.get("current_weather", {})
                return {
                    "temp": curr.get("temperature"),
                    "wind": curr.get("windspeed"),
                    "code": curr.get("weathercode"), # WMO code
                    "time": datetime.now().strftime("%H:%M")
                }
        except Exception:
            pass
        return None

    @staticmethod
    def get_wmo_description(code):
        # Simplificado
        if code is None: return "Desconhecido"
        if code == 0: return "Céu Limpo"
        if code in [1, 2, 3]: return "Parcialmente Nublado"
        if code in [45, 48]: return "Nevoeiro"
        if code in [51, 53, 55]: return "Garoa"
        if code in [61, 63, 65]: return "Chuva"
        if code in [71, 73, 75]: return "Neve"
        if code in [80, 81, 82]: return "Chuva Forte"
        if code in [95, 96, 99]: return "Tempestade"
        return "Nublado"

class FinanceClient:
    @staticmethod
    def get_top_crypto(limit=100):
        """
        Busca top criptos via CoinGecko (Free).
        """
        try:
            url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                res = []
                for item in data:
                    res.append({
                        "rank": item.get("market_cap_rank"),
                        "name": item.get("name"),
                        "symbol": str(item.get("symbol")).upper(),
                        "price_usd": item.get("current_price"),
                        "change_24h": item.get("price_change_percentage_24h"),
                        "last_updated": item.get("last_updated")
                    })
                return res
        except Exception:
            pass
        return []

    @staticmethod
    def get_top_fiat():
        """
        Busca taxas de cambio via AwesomeAPI (BRL base).
        Retorna todas as moedas disponíveis (all).
        """
        try:
            url = "https://economia.awesomeapi.com.br/json/all"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                res = []
                # AwesomeAPI retorna dict com chaves tipo 'USDBRL'
                for k, v in data.items():
                    # Filtra apenas pares com BRL para simplificar ou mostra tudo?
                    # O usuário pediu "100 moedas reais", vamos mostrar tudo que vier.
                    res.append({
                        "name": v.get("name"),
                        "code": v.get("code"),
                        "codein": v.get("codein"),
                        "bid": float(v.get("bid") or 0),
                        "pct_change": float(v.get("pctChange") or 0),
                        "last_updated": v.get("create_date")
                    })
                # Ordenar por nome para facilitar
                res.sort(key=lambda x: x["name"])
                return res[:50] # Limit to 50 as requested
        except Exception:
            pass
        return []
