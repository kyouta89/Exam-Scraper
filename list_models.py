from google import genai
import os
from dotenv import load_dotenv # ★追加

# --- 設定 ---
load_dotenv() # .envファイルを読み込む
API_KEY = os.getenv("GEMINI_API_KEY") # 環境変数から取得
# ------------

def list_active_models():
    print("🚀 利用可能なモデル一覧を取得中...\n")

    if not API_KEY:
        print("❌ エラー: .envファイルが見つからないか、GEMINI_API_KEYが設定されていません。")
        return

    try:
        client = genai.Client(api_key=API_KEY)
        
        # モデル一覧を取得
        all_models = client.models.list()
        
        found_count = 0

        print(f"{'モデルID (これをコピペして使う)':<40} | {'説明 (Display Name)'}")
        print("-" * 85)

        for m in all_models:
            # 新しいライブラリではシンプルに名前で判定
            if "gemini" in m.name.lower():
                d_name = getattr(m, 'display_name', 'No description')
                print(f"{m.name:<40} | {d_name}")
                found_count += 1

        print("-" * 85)
        
        if found_count > 0:
            print(f"\n🎉 {found_count} 個のGeminiモデルが見つかりました。")
        else:
            print("⚠️ 'gemini' を含むモデルが見つかりませんでした。")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    list_active_models()