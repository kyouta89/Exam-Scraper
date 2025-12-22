from google import genai
import time
import os
from dotenv import load_dotenv # ★追加

# --- 設定 ---
load_dotenv() # .envファイルを読み込む
API_KEY = os.getenv("GEMINI_API_KEY") # 環境変数から取得
# ------------

def check_available_models():
    print("🚀 モデルの稼働状況をテスト中...\n")
    
    if not API_KEY:
        print("❌ エラー: .envファイルが見つからないか、GEMINI_API_KEYが設定されていません。")
        return

    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"初期化エラー: {e}")
        return

    # テストしたい候補
    candidates = [
        "models/gemini-2.5-pro",
        "models/gemini-3-pro-preview",
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash-exp",
        "models/gemini-2.0-flash",
        "models/gemini-flash-latest",
    ]

    working_model = None

    for model_name in candidates:
        print(f"👉 テスト中: {model_name:<30} ... ", end="")
        
        try:
            # 実際に通信してみる
            response = client.models.generate_content(
                model=model_name,
                contents="Hello"
            )
            print("✅ 成功！")
            working_model = model_name
            break 
            
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                print("❌ 見つかりません (404)")
            elif "429" in error_msg:
                print("⚠️ 容量オーバー (429)")
            else:
                print(f"❌ エラー: {error_msg}")
        
        time.sleep(1)

    print("\n------------------------------------------------")
    if working_model:
        print(f"🎉 決定！ このモデルIDが使えます:")
        print(f"\nMODEL_ID = '{working_model}'\n")
    else:
        print("😢 有効なモデルが見つかりませんでした。")

if __name__ == "__main__":
    check_available_models()