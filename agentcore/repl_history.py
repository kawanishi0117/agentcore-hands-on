from strands import Agent
from strands.models import BedrockModel

SYSTEM = "あなたは親切な日本語アシスタントです。短く、実用的に答えてください。"

def build_agent():
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name="ap-northeast-1",
    )
    return Agent(model=model, system_prompt=SYSTEM)

def format_with_history(history, user_text):
    # history: list[tuple[str,str]] = [("user","..."), ("assistant","..."), ...]
    lines = [f"System: {SYSTEM}", ""]
    for role, msg in history[-20:]:
        if role == "user":
            lines.append(f"User: {msg}")
        else:
            lines.append(f"Assistant: {msg}")
    lines.append(f"User: {user_text}")
    lines.append("Assistant:")
    return "\n".join(lines)

def main():
    agent = build_agent()
    history = []
    print("REPL start (history): exit / quit で終了\n")

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
        if user.lower() == "/reset":
            history.clear()
            print("AI> 履歴をリセットしました。\n")
            continue

        prompt = format_with_history(history, user)

        try:
            ans = agent(prompt)
            print(f"AI> {ans}\n")
            history.append(("user", user))
            history.append(("assistant", str(ans)))
        except Exception as e:
            print(f"[ERROR] {e}\n")

if __name__ == "__main__":
    main()
