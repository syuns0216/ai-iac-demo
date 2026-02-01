import os
import subprocess
import sys
import re

def run(cmd):
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, shell=False)

def main():
    print("AI-IaC Flow")
    print("commands: chat / preview / go / exit")

    while True:
        cmd = input("\nflow> ").strip().lower()

        if cmd in ("exit", "quit"):
            return 0

        if cmd == "chat":
            run([sys.executable, "tools/ai_chat.py"])
            continue

        if cmd == "preview":
            run([sys.executable, "tools/render_mermaid.py"])
            run([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                r"C:\Users\puzzl\AppData\Roaming\npm\mmdc.ps1",
                "-i", "diagram/architecture.mmd",
                "-o", "diagram/architecture.png"
            ])
            run(["powershell", "-NoProfile", "-Command", "start diagram\\architecture.png"])
            continue

        if cmd == "go":
            # 現在のブランチ確認
            current_branch = os.popen("git branch --show-current").read().strip()
            if current_branch in ("master", "main", ""):
                print(f"ERROR: 現在のブランチが '{current_branch}' です。featureブランチで実行してください。")
                print("例: git checkout -b feature/ai-dialog")
                continue

            # YAML生成
            run([sys.executable, "tools/render_cfn.py"])

            # Mermaid/PNG生成
            run([sys.executable, "tools/render_mermaid.py"])
            run([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                r"C:\Users\puzzl\AppData\Roaming\npm\mmdc.ps1",
                "-i", "diagram/architecture.mmd",
                "-o", "diagram/architecture.png"
            ])

            # git commit & push
            run(["git", "add", "design", "diagram", "cfn", "tools"])
            try:
                run(["git", "commit", "-m", "AI flow: update design and generate artifacts"])
            except subprocess.CalledProcessError:
                print("No changes to commit. continue...")

            try:
                run(["git", "push"])
            except subprocess.CalledProcessError:
                run(["git", "push", "-u", "origin", "HEAD"])

            # PR処理（jq使わずURL取得）
            pr_json = os.popen(f"gh pr list --head {current_branch} --json url").read().strip()
            m = re.search(r'"url"\s*:\s*"([^"]+)"', pr_json)
            pr_url = m.group(1) if m else ""

            if pr_url:
                print(f"\n既存PR: {pr_url}")
                run(["gh", "pr", "view", pr_url, "--web"])
            else:
                run([
                    "gh", "pr", "create",
                    "--base", "master",
                    "--head", current_branch,
                    "--title", "AI flow: update IaC",
                    "--body", "Generated from design.json via Gemini dialog. Please review."
                ])
                pr_json = os.popen(f"gh pr list --head {current_branch} --json url").read().strip()
                m = re.search(r'"url"\s*:\s*"([^"]+)"', pr_json)
                pr_url = m.group(1) if m else ""
                print(f"\n新規PR: {pr_url}")
                if pr_url:
                    run(["gh", "pr", "view", pr_url, "--web"])

            print("\nGO完了")
            continue

        print("unknown command. use: chat / preview / go / exit")


if __name__ == "__main__":
    raise SystemExit(main())
