import json, os

os.makedirs("diagram", exist_ok=True)

with open("design/design.json", encoding="utf-8") as f:
    d = json.load(f)

region = d.get("region", "ap-northeast-1")
vpc_cidr = d.get("network", {}).get("vpcCidr", "10.0.0.0/16")
subs = d.get("network", {}).get("publicSubnets", [
    {"az": f"{region}a", "cidr": "10.0.1.0/24"},
    {"az": f"{region}c", "cidr": "10.0.2.0/24"},
])

instances = int(d.get("web", {}).get("instances", 1))
server = d.get("web", {}).get("server", "nginx")

# 安全のため 1〜2 台に制限（今はデモ用）
instances = max(1, min(instances, 2))

def q(s: str) -> str:
    # Mermaidラベルは必ずダブルクォートで囲う（日本語や記号で壊れにくい）
    return f'"{s}"'

lines = []
lines.append("flowchart TB")
lines.append(f'  User[{q("👤 作業者/利用者")}] --> ALB[{q("⚖️ ALB（後で追加）")}]\n')

lines.append(f'  IGW[{q("🌐 Internet Gateway")}] --- VPC\n')

lines.append(f'  subgraph VPC[{q(f"VPC {vpc_cidr}")}]')
lines.append("    direction TB")

# Subnet 1
az1 = subs[0].get("az", f"{region}a")
cidr1 = subs[0].get("cidr", "10.0.1.0/24")
lines.append(f'    subgraph Pub1[{q(f"Public Subnet ({az1}) {cidr1}")}]')
lines.append("      direction TB")
lines.append(f'      EC2A[{q(f"🖥️ EC2 ({server}) #1")}]')
lines.append("    end\n")

# Subnet 2 + EC2 #2（instances>=2のとき）
az2 = subs[1].get("az", f"{region}c")
cidr2 = subs[1].get("cidr", "10.0.2.0/24")
lines.append(f'    subgraph Pub2[{q(f"Public Subnet ({az2}) {cidr2}")}]')
lines.append("      direction TB")
if instances >= 2:
    lines.append(f'      EC2B[{q(f"🖥️ EC2 ({server}) #2")}]')
else:
    lines.append(f'      Note2[{q("（予備）")}]\n')
lines.append("    end")
lines.append("  end\n")

# 矢印
lines.append("  ALB --> EC2A")
if instances >= 2:
    lines.append("  ALB --> EC2B")

text = "\n".join(lines) + "\n"

with open("diagram/architecture.mmd", "w", encoding="utf-8") as f:
    f.write(text)

print("generated: diagram/architecture.mmd")
