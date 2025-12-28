import sys
from strands import Agent
from strands.models import BedrockModel

EXIT_WORDS = {"exit", "quit", ":q", "bye"}
RESET_WORDS = {"/reset", "/new"}

def build_agent():
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name="ap-northeast-1",
    )

    # ストリーミングイベントをここで受ける
    def callback_handler(**kwargs):
        # LLMが出してくるテキストの断片
        if "data" in kwargs:
            print(kwargs["data"], end="", flush=True)

        # ツール利用があれば通知（今はツール無しでもOK）
        if "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
            tool_name = kwargs["current_tool_use"]["name"]
            print(f"\n[tool] {tool_name}\n", end="", flush=True)

        # 1リクエスト完了
        if kwargs.get("complete", False):
            print("\n", flush=True)

    return Agent(
        model=model,
        system_prompt="あなたは親切な日本語アシスタントです。",
        callback_handler=callback_handler,
    )

def main():
    agent = build_agent()

    print("Strands REPL（callback streaming）")
    print("  - 終了: exit / quit / :q")
    print("  - 会話リセット: /reset")
    print("")

    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return

        if not user:
            continue

        if user in EXIT_WORDS:
            print("bye")
            return

        if user in RESET_WORDS:
            # Strandsは「完全リセット」は基本 “Agent作り直し” が確実
            agent = build_agent()
            print("(reset done)\n")
            continue

        # ここでストリーミングされて表示される（callback_handlerがprintする）
        _ = agent(user)

if __name__ == "__main__":
    main()
