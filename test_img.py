import random, urllib.parse
prompt = "modern entrance with yellow tactile paving and stainless steel handrails, architectural photography"
seed = random.randint(1, 10**9)
url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1280&height=720&nologo=true&seed={seed}"
print(f"Скопируй эту ссылку в браузер:\n{url}")
