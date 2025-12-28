# repl_plus.py
from strands import Agent
from strands.models import BedrockModel


def build_agent():
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name="ap-northeast-1",
    )
    return Agent(model=model, system_prompt="あなたは親切な日本語アシスタントです。")


HELP = """\
Commands:
  /help      このヘルプ
  /history   直近の会話ログを表示（ローカルで保持してるだけ）
  exit|quit  終了
"""


def main():
    agent = build_agent()
    history: list[tuple[str, str]] = []

    print("REPL開始。/help でコマンド。\n")

    while True:
        try:
            user = input("you> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nbye!")
            break

        if not user:
            continue

        if user.lower() in ("exit", "quit"):
            print("bye!")
            break

        if user == "/help":
            print(HELP)
            continue

        if user == "/history":
            if not history:
                print("(no history)\n")
            else:
                for i, (u, b) in enumerate(history[-10:], start=1):
                    print(f"[{i}] you> {u}")
                    print(f"    bot> {b}\n")
            continue

        try:
            assistant = agent(user)
        except Exception as e:
            print(f"bot> (error) {e}\n")
            continue

        print(f"bot> {assistant}\n")
        history.append((user, str(assistant)))


if __name__ == "__main__":
    main()
