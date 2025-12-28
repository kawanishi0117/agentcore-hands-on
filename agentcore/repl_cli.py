# repl_cli.py
import json
from datetime import datetime
from strands import Agent
from strands.models import BedrockModel

SYSTEM = "あなたは親切な日本語アシスタントです。結論→理由→手順の順で短く答えてください。"

def build_agent():
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name="ap-northeast-1",
    )
    return Agent(model=model, system_prompt=SYSTEM)

def format_prompt(history, user_text):
    lines = [f"System: {SYSTEM}", ""]
    for m in history[-30:]:
        lines.append(f"{m['role'].capitalize()}: {m['content']}")
    lines.append(f"User: {user_text}")
    lines.append("Assistant:")
    return "\n".join(lines)

def save_history(history, path="chat_log.jsonl"):
    with open(path, "a", encoding="utf-8") as f:
        for m in history:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

def main():
    agent = build_agent()
    history = []
    print(
        "REPL start\n"
        "Commands:\n"
        "  /reset   履歴リセット\n"
        "  /save    ログ保存（jsonl）\n"
        "  /history 履歴を表示（直近）\n"
        "  exit     終了\n"
    )

    while True:
        try:
            user = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user:
            continue
        if user.lower() in ("exit", "quit"):
            print("Bye!")
            break

        if user == "/reset":
            history.clear()
            print("AI> 履歴をリセットしました。\n")
            continue

        if user == "/history":
            for m in history[-10:]:
                print(f"{m['role']}> {m['content']}")
            print()
            continue

        if user == "/save":
            # 保存用にタイムスタンプ付けて書き出す
            stamped = []
            now = datetime.now().isoformat()
            for m in history:
                stamped.append({**m, "ts": now})
            save_history(stamped)
            print("AI> 保存しました: chat_log.jsonl\n")
            continue

        # 通常会話
        history.append({"role": "user", "content": user})
        prompt = format_prompt(history, user)

        try:
            ans = agent(prompt)
            ans_text = str(ans)
            history.append({"role": "assistant", "content": ans_text})
            print(f"AI> {ans_text}\n")
        except Exception as e:
            print(f"[ERROR] {e}\n")

if __name__ == "__main__":
    main()
