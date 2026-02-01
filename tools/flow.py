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
            current_branch = os.popen("git branch --show-current").read().strip()
            try:
                # 既存PRがあるかチェック（あればURLが出る）
                run(["gh", "pr", "view", "--web"])
                print("\n既存PRを開きました（内容更新済みならそのPRをレビューしてください）")
            except subprocess.CalledProcessError:
                # 無ければ作成
                run([
                    "gh", "pr", "create",
                    "--base", "master",
                    "--head", current_branch,
                    "--title", "AI flow: update IaC",
                    "--body", "Generated from design.json via Gemini dialog. Please review."
                ])
                print("\n新規PRを作成しました。")

            print("\nGO完了: PRレビュー → マージでAWSへ反映（既存のGO②フロー）")
            continue

        print("unknown command. use: chat / preview / go / exit")

if __name__ == "__main__":
    raise SystemExit(main())
