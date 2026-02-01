import os, json, re
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("APIキー未設定: PowerShellで $env:GEMINI_API_KEY=... を設定してください")
    raise SystemExit(1)

client = genai.Client(api_key=API_KEY)

DESIGN_PATH = "design/design.json"
os.makedirs("design", exist_ok=True)

if not os.path.exists(DESIGN_PATH):
    with open(DESIGN_PATH, "w", encoding="utf-8") as f:
        json.dump({"web": {"instances": 1}}, f, ensure_ascii=False, indent=2)

with open(DESIGN_PATH, encoding="utf-8") as f:
    design = json.load(f)

req = input("要望を入力: ").strip()

prompt = f"""
あなたはAWS構成の design.json を更新するアシスタントです。
出力は **必ず JSONのみ**。説明文や ``` は禁止。

次のスキーマを必ず守ってください（キー名を変えない / キーを消さない）：
{{
  "project": "ai-iac-demo",
  "region": "ap-northeast-1",
  "network": {{
    "vpcCidr": "10.0.0.0/16",
    "publicSubnets": [
      {{"az":"ap-northeast-1a","cidr":"10.0.1.0/24"}},
      {{"az":"ap-northeast-1c","cidr":"10.0.2.0/24"}}
    ]
  }},
  "web": {{
    "instanceType": "t3.micro",
    "instances": 1,
    "server": "nginx"
  }}
}}

現在のJSON（これをベースに更新）：
{json.dumps(design, ensure_ascii=False)}

要望：
{req}

ルール：
- 変更が必要な部分だけ値を更新し、それ以外は維持する
- EC2の台数は必ず web.instances（整数）で表現する（例: 2）
- EC2 など別キー（"EC2"）は作らない
"""

resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

text = (resp.text or "").strip()

# もし ```json ... ``` で返ってきたら中身だけ抜き出す
m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
if m:
    text = m.group(1).strip()

try:
    new_design = json.loads(text)
except Exception:
    print("\nERROR: Geminiの返答がJSONとして読めませんでした。返答全文↓\n")
    print(text)
    raise

with open(DESIGN_PATH, "w", encoding="utf-8") as f:
    json.dump(new_design, f, ensure_ascii=False, indent=2)

print("更新完了: design/design.json を更新しました")
