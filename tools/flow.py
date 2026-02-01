import os
import subprocess
import sys

def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, shell=False)

def main() -> int:
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
            # PNG生成
            run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
		r"C:\Users\puzzl\AppData\Roaming\npm\mmdc.ps1",
		"-i", "diagram/architecture.mmd", "-o", "diagram/architecture.png"])

            # 画像を開く（Windows）
            run(["powershell", "-NoProfile", "-Command", "start diagram\\architecture.png"])
            continue

        if cmd == "go":
            # YAML生成
            run([sys.executable, "tools/render_cfn.py"])

            # Mermaid/PNGも最新化（GO時点で成果物を揃える）
            run([sys.executable, "tools/render_mermaid.py"])
            run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                 r"C:\Users\puzzl\AppData\Roaming\npm\mmdc.ps1",
                 "-i", "diagram/architecture.mmd", "-o", "diagram/architecture.png"])

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

            # PR: 既存があればURLを表示、なければ作成
                        # PR: ブランチを指定して「そのPR」を確実に取得する
            current_branch = os.popen("git branch --show-current").read().strip()

            # まず「このブランチのPRがあるか」検索してURLを取る
            pr_url = ""
            try:
                # --head でブランチ指定して1件取る（なければ空）
                pr_url = os.popen(f"gh pr list --head {current_branch} --json url --jq '.[0].url'").read().strip()
            except Exception:
                pr_url = ""

            if pr_url:
                print(f"\n既存PR: {pr_url}")
                run(["gh", "pr", "view", pr_url, "--web"])
            else:
                # 無ければ作成してURLを取る
                run([
                    "gh", "pr", "create",
                    "--base", "master",
                    "--head", current_branch,
                    "--title", "AI flow: update IaC",
                    "--body", "Generated from design.json via Gemini dialog. Please review."
                ])
                pr_url = os.popen(f"gh pr list --head {current_branch} --json url --jq '.[0].url'").read().strip()
                print(f"\n新規PR: {pr_url}")
                if pr_url:
                    run(["gh", "pr", "view", pr_url, "--web"])


            print("\nGO完了: PRレビュー → マージでAWSへ反映（既存のGO②フロー）")
            continue

        print("unknown command. use: chat / preview / go / exit")

if __name__ == "__main__":
    raise SystemExit(main())
