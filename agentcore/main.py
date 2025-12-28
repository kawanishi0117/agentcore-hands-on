# main.py
from strands import Agent
from strands.models import BedrockModel


def build_agent():
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name="ap-northeast-1",
    )
    return Agent(model=model, system_prompt="あなたは親切な日本語アシスタントです。")

def main():
    agent = build_agent()
    print("REPL開始。終了は Ctrl+C か 'exit' / 'quit'。\n")

    while True:
        user = input("you> ").strip()
        if not user:
            continue
        if user.lower() in ("exit", "quit"):
            print("bye!")
            break

        # ここがポイント：毎ターン agent(...) を呼ぶだけで REPL になる
        assistant = agent(user)
        print(f"bot> {assistant}\n")

if __name__ == "__main__":
    main()
