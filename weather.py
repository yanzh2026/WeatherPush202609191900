import requests
import os
import time

# ====================== 配置区 ======================
WEATHER_KEY = os.getenv("WEATHER_KEY")
# 用户列表：一行一条，格式 BarkKey|CityId，多行
RAW_USERS = os.getenv("BARK_USERS", "")
BARK_EXTRA = "?sound=alert"

MAX_RETRY = 2
RETRY_DELAY = 3
# ====================================================

API_HOST = "https://mc76xbbbde.re.qweatherapi.com"

def request_with_retry(url, timeout=25):
    for attempt in range(MAX_RETRY):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"请求失败，{RETRY_DELAY}秒后重试 ({attempt+1}/{MAX_RETRY})：{e}")
            time.sleep(RETRY_DELAY)
    raise Exception("多次请求全部失败")

def get_location_info(city_id):
    url = f"{API_HOST}/geo/v2/city/lookup?location={city_id}&key={WEATHER_KEY}"
    resp = request_with_retry(url)
    data = resp.json()
    loc = data["location"][0]
    return {
        "province": loc["adm1"],
        "city": loc["adm2"],
        "district": loc["name"]
    }

def get_weather(city_id):
    # 实时天气
    url_now = f"{API_HOST}/v7/weather/now?location={city_id}&key={WEATHER_KEY}"
    resp_now = request_with_retry(url_now)
    res_now = resp_now.json()
    now = res_now["now"]

    # 3天预报
    url_3d = f"{API_HOST}/v7/weather/3d?location={city_id}&key={WEATHER_KEY}"
    resp_3d = request_with_retry(url_3d)
    res_3d = resp_3d.json()
    today = res_3d["daily"][0]
    return now, today

def get_clothing_advice(feels_temp, wind_scale, humidity, uv_index):
    """综合体感、风力、湿度、紫外线生成穿搭建议"""
    t = int(feels_temp)
    wind = int(wind_scale)
    hum = int(humidity)
    uv = int(uv_index)

    base_tip = ""

    # 基础温度档位
    if t >= 30:
        base_tip = "☀️炎热，短袖短裤为主"
    elif t >= 24:
        base_tip = "🌞偏热，短袖T恤，薄长裤或短裤均可"
    elif t >= 18:
        base_tip = "😌温度舒适，短袖或薄长袖，随身备一件薄外套"
    elif t >= 12:
        base_tip = "🍂微凉，长袖上衣，建议薄外套/风衣"
    elif t >= 5:
        base_tip = "🧥偏冷，厚长袖加外套，注意保暖"
    else:
        base_tip = "❄️严寒，厚棉衣/羽绒服，做好防寒"

    extra = []
    # 风力补充
    if wind >= 4:
        extra.append("风力偏大，注意防风")
    # 湿度：闷热潮湿 / 干燥
    if hum >=75 and t >=22:
        extra.append("湿度高，体感闷热")
    elif hum <=30:
        extra.append("空气干燥，注意补水保湿")
    # 紫外线
    if uv >=5:
        extra.append("紫外线较强，外出做好防晒")

    if extra:
        base_tip += "；" + "，".join(extra)
    return base_tip

def send_bark(title, body, bark_key):
    url = f"https://api.day.app/{bark_key}/{title}/{body}{BARK_EXTRA}"
    r = request_with_retry(url)
    print(f"设备[{bark_key[:8]}...] 返回：{r.json()}")

def process_one_user(bark_key, city_id):
    print(f"\n--- 开始处理设备 {bark_key[:8]}，城市ID:{city_id} ---")
    loc = get_location_info(city_id)
    now, today = get_weather(city_id)

    temp = now["temp"]
    feels = now["feelsLike"]
    weather_text = now["text"]
    wind_dir = now["windDir"]
    wind_scale = now["windScale"]
    humidity = now["humidity"]
    # ✅安全读取uvIndex，不存在就默认0，解决KeyError
    uv_index = now.get("uvIndex", 0)

    dress_advice = get_clothing_advice(feels, wind_scale, humidity, uv_index)

    t_max = today["tempMax"]
    t_min = today["tempMin"]
    precip = float(today["precip"])

    rain_tip = "\n☔⚠️今日有雨，出门记得带伞" if precip > 0 else ""

    city_name = loc["district"]
    title = f"🌤{city_name}每日天气提醒"
    content = f"""📍{loc['province']}{loc['city']}{loc['district']}
🌤天气：{weather_text}
🌡气温{temp}℃｜体感{feels}℃
📅今日 {t_min}~{t_max}℃
💧湿度：{humidity}%
💨风力：{wind_dir}{wind_scale}级
☀️紫外线等级：{uv_index}

👔穿搭建议：{dress_advice}{rain_tip}"""
    print(content)
    send_bark(title, content, bark_key)

def main():
    lines = RAW_USERS.splitlines()
    for line in lines:
        line = line.strip()
        if not line or "|" not in line:
            continue
        bark_key, city_id = line.split("|")
        bark_key = bark_key.strip()
        city_id = city_id.strip()
        try:
            process_one_user(bark_key, city_id)
        except Exception as e:
            print(f"❌设备{bark_key[:8]}处理失败：{e}")

if __name__ == "__main__":
    main()
