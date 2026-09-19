import requests
import os
import time

# ====================== 配置区 ======================
WEATHER_KEY = os.getenv("WEATHER_KEY")
CITY_ID = "101280102"       # 番禺
BARK_KEY = os.getenv("BARK_KEY")
BARK_EXTRA = "?sound=alert"

MAX_RETRY = 2
RETRY_DELAY = 3
# ====================================================

API_HOST = "mc76xbbbde.re.qweatherapi.com"

def request_with_retry(url, timeout=12):
    for attempt in range(MAX_RETRY + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt < MAX_RETRY:
                print(f"请求失败，{RETRY_DELAY}秒后重试 ({attempt+1}/{MAX_RETRY})：{e}")
                time.sleep(RETRY_DELAY)
            else:
                raise e

def get_location_info():
    url = f"https://{API_HOST}/geo/v2/city/lookup?location={CITY_ID}&key={WEATHER_KEY}"
    resp_raw = request_with_retry(url)
    resp = resp_raw.json()
    loc = resp["location"][0]
    return {
        "province": loc["adm1"],
        "city": loc["adm2"],
        "district": loc["name"]
    }

def get_weather():
    url_now = f"https://{API_HOST}/v7/weather/now?location={CITY_ID}&key={WEATHER_KEY}"
    res_now = request_with_retry(url_now).json()
    now = res_now["now"]

    url_day = f"https://{API_HOST}/v7/weather/3d?location={CITY_ID}&key={WEATHER_KEY}"
    res_day = request_with_retry(url_day).json()
    today = res_day["daily"][0]
    return now, today

def get_dress(temp):
    t = int(temp)
    if t < 10:
        return "🧥厚外套+毛衣，注意防寒保暖"
    elif t < 20:
        return "🧥薄外套/风衣，早晚温差大"
    elif t < 28:
        return "👕短袖薄长袖均可，薄长裤"
    else:
        return "☀️短袖短裤，做好防晒防暑"

def send_bark(title, body):
    url = f"https://api.day.app/{BARK_KEY}/{title}/{body}{BARK_EXTRA}"
    r = request_with_retry(url)
    print("Bark返回：", r.json())

def main():
    try:
        print("====获取番禺天气====")
        loc = get_location_info()
        now, today = get_weather()

        temp = now["temp"]
        feels = now["feelsLike"]
        weather_text = now["text"]
        wind = f'{now["windDir"]}{now["windScale"]}级'
        humidity = now["humidity"]
        dress = get_dress(temp)

        t_max = today["tempMax"]
        t_min = today["tempMin"]
        precip = float(today["precip"])

        rain_tip = "\n☔⚠️今日有雨，出门记得带伞" if precip > 0 else ""

        title = "🌤番禺每日天气提醒"
        content = f"""📍{loc['province']}{loc['city']}{loc['district']}
🌤天气：{weather_text}
🌡当前{temp}℃｜体感{feels}℃
📅今日 {t_min}~{t_max}℃
💧湿度：{humidity}%｜降水：{precip}mm
💨风力：{wind}

👔穿搭建议：{dress}{rain_tip}"""
        print(content)
        send_bark(title, content)
        print("✅推送完成")
    except Exception as e:
        print(f"❌执行异常：{e}")

if __name__ == "__main__":
    main()
