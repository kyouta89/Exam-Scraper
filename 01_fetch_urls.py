import time
import random
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- 設定（ここを変更してください） ---
TARGET_EXAM = "cis-csm"       # 検索したい試験名（リンク文字に含まれるもの）
CATEGORY_NAME = "servicenow"  # URLの一部 (discussions/servicenow/)
MAX_PAGE = 150                 # https://www.examtopics.com/discussions/servicenow/ の最大ページ数
OUTPUT_FILENAME = f'ServiceNow_{TARGET_EXAM}_links.txt'
# ----------------------------------

def init_driver():
    options = webdriver.ChromeOptions()
    # MacのChromeの場所
    options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    # ステルス設定（Cloudflare回避）
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def main():
    base_url = f'https://www.examtopics.com/discussions/{CATEGORY_NAME}/'
    all_links = []

    print(f"試験「{TARGET_EXAM}」のURL収集を開始します（全{MAX_PAGE}ページ）...")
    
    driver = init_driver()

    try:
        # ページを1から順に巡回
        for page in range(1, MAX_PAGE + 1):
            target_url = f"{base_url}{page}/"
            print(f"[{page}/{MAX_PAGE}] アクセス中: {target_url}")
            
            try:
                driver.get(target_url)
                
                # ページ読み込み＆ブロック回避のための待機
                time.sleep(random.uniform(5, 8))
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # リンクを取得 (class="discussion-link" を探す)
                elements = soup.find_all('a', class_='discussion-link')
                
                count_in_page = 0
                for element in elements:
                    link_text = element.get_text().strip()
                    link_href = element.get('href')
                    
                    # 試験名が含まれているかチェック
                    if TARGET_EXAM.lower() in link_text.lower() and link_href:
                        # 相対パスなら絶対パスに変換
                        if not link_href.startswith('http'):
                            link_href = "https://www.examtopics.com" + link_href
                        
                        all_links.append(link_href)
                        count_in_page += 1
                
                print(f"  -> {count_in_page} 件のリンクを発見")

            except Exception as e:
                print(f"  -> エラー: {e}")

    finally:
        driver.quit()

    # 重複を除去して保存
    unique_links = sorted(list(set(all_links)))
    
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        for link in unique_links:
            f.write(link + '\n')

    print(f"\n🎉 完了しました！")
    print(f"合計 {len(unique_links)} 件のURLを '{OUTPUT_FILENAME}' に保存しました。")

if __name__ == "__main__":
    main()