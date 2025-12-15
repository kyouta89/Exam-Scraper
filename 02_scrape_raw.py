import time
import random
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- 設定 ---
INPUT_FILE = 'ServiceNow_CIS-CSM_links.txt'
OUTPUT_FILE = 'CIS-CSM_Complete_Questions.html' # 完成版のファイル名
# ------------

def init_driver():
    options = webdriver.ChromeOptions()
    # MacのChromeの場所
    options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    # 成功したステルス設定（ロボット検知回避）
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    
    # WebDriverであることを隠すJavascript
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def create_html_header():
    return """
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f0f2f5; color: #333; }
            h1 { text-align: center; color: #2c3e50; margin-bottom: 30px; }
            .question-card { background: white; padding: 25px; margin-bottom: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .q-header { font-weight: bold; font-size: 1.2em; color: #34495e; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; }
            .card-text { font-size: 1.1em; line-height: 1.6; margin-bottom: 20px; }
            
            /* 選択肢のリストを見やすく */
            ul { list-style-type: none; padding: 0; }
            li.multi-choice-item { background: #f8f9fa; margin: 8px 0; padding: 12px 15px; border: 1px solid #e9ecef; border-radius: 6px; transition: background 0.2s; }
            li.multi-choice-item:hover { background: #e2e6ea; }
            .multi-choice-letter { font-weight: bold; color: #007bff; margin-right: 10px; }
            
            /* 正解エリアのデザイン */
            .correct-answer-box { display: block; margin-top: 20px; padding: 15px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 6px; color: #155724; }
            .vote-distribution-bar { height: 25px; margin-top: 10px; background-color: #e9ecef; border-radius: 5px; overflow: hidden; }
            
            .source-link { font-size: 0.8em; color: #6c757d; text-decoration: none; display: block; margin-top: 15px; text-align: right; }
            .source-link:hover { color: #007bff; }
            .error { color: #dc3545; font-weight: bold; }
        </style>
    </head>
    <body>
    <h1>ServiceNow CIS-CSM Exam Questions (Full)</h1>
    """

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"エラー: {INPUT_FILE} が見つかりません。")
        return

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if "http" in line]
    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")
        return

    print(f"全 {len(urls)} 件の処理を開始します。これには時間がかかります...")
    print("Chromeが起動したら、基本的には放置でOKです。")
    print("（もし万が一『人間ですか？』が出たらクリックしてください）")
    
    driver = init_driver()
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        out.write(create_html_header())
        
        for index, url in enumerate(urls):
            print(f"[{index + 1}/{len(urls)}] 取得中... {url}")
            
            try:
                driver.get(url)
                
                # サーバー負荷とブロック回避のため、少し長めにランダム待機
                time.sleep(random.uniform(5, 8))
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # コンテンツの抽出
                question_body = soup.find('div', class_='discussion-header-container')
                
                if not question_body:
                    # サブプラン：クラス名が違う場合
                    bodies = soup.find_all('div', class_='card-body')
                    for b in bodies:
                        if len(b.text) > 50:
                            question_body = b
                            break
                
                q_html = ""
                if question_body:
                    # 不要な要素（ボタン、スクリプト、スタイル、投票エリアなど）を削除
                    for unwanted in question_body.find_all(['script', 'style', 'button', 'form']):
                        unwanted.decompose()
                    
                    # 特定のクラスを持つ不要要素を削除（Show Answerボタンなど）
                    for hidden in question_body.find_all(class_=['btn', 'reveal-solution', 'hide-solution', 'voted-answers-tally']):
                        hidden.decompose()

                    q_html = str(question_body)
                else:
                    q_html = f"<p class='error'>問題文を取得できませんでした (Link: {url})</p>"

                out.write(f"""
                <div class="question-card">
                    <div class="q-header">
                        <span>Question {index + 1}</span>
                    </div>
                    <div class="q-text">{q_html}</div>
                    <a href="{url}" class="source-link" target="_blank">Open Original Page</a>
                </div>
                """)
                out.flush() 

            except Exception as e:
                print(f"  >> エラー: {e}")
                # エラーが起きてもHTMLレイアウトが崩れないように空のカードを入れる
                out.write(f"<div class='question-card'><p class='error'>Error processing: {url}</p></div>")
            
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as out:
        out.write("</body></html>")

    driver.quit()
    print(f"\n完了しました！ '{OUTPUT_FILE}' を確認してください。")

if __name__ == "__main__":
    main()