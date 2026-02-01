import json, os

os.makedirs("diagram", exist_ok=True)

with open("design/design.json", encoding="utf-8") as f:
    d = json.load(f)

instances = d.get("web", {}).get("instances", 1)

lines = []
lines.append("flowchart TB")
lines.append('  User[作業者/利用者] --> ALB[ALB(後で追加)]')
lines.append(f'  ALB --> Web[Webサーバ x{instances}]')
lines.append("  Web --> VPC[VPC]")
lines.append("  VPC --> Sub1[Public Subnet 1]")
lines.append("  VPC --> Sub2[Public Subnet 2]")
lines.append("  IGW[Internet Gateway] --> VPC")
text = "\n".join(lines) + "\n"

with open("diagram/architecture.mmd", "w", encoding="utf-8") as f:
    f.write(text)

print("generated: diagram/architecture.mmd")
