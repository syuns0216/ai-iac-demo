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
あなたはJSONだけを返すアシスタントです。説明文は禁止。
次のdesign.jsonを、要望に合わせて更新してください。

【現在のdesign.json】
{json.dumps(design, ensure_ascii=False)}

【要望】
{req}

【出力ルール】
- 出力は必ずJSONのみ
- 先頭や末尾に説明文や```は付けない
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
