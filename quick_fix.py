import os
import re
from bs4 import BeautifulSoup

# --- 設定 ---
# 修正したいファイル名（生成済みのファイルを指定してください）
INPUT_FILE = 'CIS-CSM_Master_Textbook_AI_SplitOnly.html'
# 修正後のファイル名
OUTPUT_FILE = 'CIS-CSM_Master_Textbook_Fixed.html'

# 削除したい文言のリスト
REMOVE_TARGETS = [
    "最も投票された",
    "Most Voted",
    "voted answers",
    "投票された回答"
]
# ------------

def clean_html_text():
    if not os.path.exists(INPUT_FILE):
        print(f"エラー: {INPUT_FILE} が見つかりません。")
        return

    print(f"📂 {INPUT_FILE} を読み込み中...")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    count = 0
    
    # HTML内のすべてのテキストノードを走査
    # find_all(text=True) は非推奨になりつつあるので string=True を使用
    for element in soup.find_all(string=True):
        if element.parent.name in ['script', 'style']:
            continue
            
        original_text = element.string
        if not original_text:
            continue

        new_text = original_text
        modified = False

        for target in REMOVE_TARGETS:
            if target in new_text:
                # 大文字小文字を区別せず削除したい場合は re.sub を使うことも可能ですが
                # ここではシンプルに replace で削除します
                new_text = new_text.replace(target, "")
                modified = True

        if modified:
            # 置き換え実行（stripで余計な空白も削除）
            element.replace_with(new_text.strip())
            count += 1

    print(f"✨ 修正完了: 合計 {count} 箇所の不要テキストを削除しました。")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    
    print(f"💾 {OUTPUT_FILE} に保存しました。")

if __name__ == "__main__":
    clean_html_text()