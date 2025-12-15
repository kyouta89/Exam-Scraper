import pandas as pd
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import re
import os
import time

# --- 設定 ---
INPUT_FILE = 'CIS-CSM_Complete_Questions.html'  # ステップ2で取った生データ
OUTPUT_HTML = 'CIS-CSM_Master_Textbook.html'    # 成果物1: 日英HTML
OUTPUT_EXCEL = 'CIS-CSM_My_Notebook.xlsx'       # 成果物2: 管理Excel
# ------------

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ エラー: {INPUT_FILE} が見つかりません。先にステップ2を実行してください。")
        return

    print("🚀 最終処理を開始します...")
    print("   1. HTML解析\n   2. 自動翻訳 (Google翻訳)\n   3. 教材(HTML/Excel)の同時生成")
    print("   ※ 翻訳APIを使用するため、時間がかかります (目安: 1問あたり2秒)")

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    cards = soup.find_all('div', class_='question-card')
    questions_data = []
    translator = GoogleTranslator(source='auto', target='ja')

    total = len(cards)
    
    for i, card in enumerate(cards):
        # 進捗表示
        print(f"   [{i+1}/{total}] Processing...", end="\r")

        # --- データ抽出 ---
        # 問題番号
        q_num = 9999
        header = card.find('div', class_='q-header')
        if header:
            m = re.search(r'Question\s+(\d+)', header.get_text())
            if m: q_num = int(m.group(1))

        # 解答情報
        full_text = card.get_text(" ", strip=True)
        suggested_match = re.search(r'Suggested Answer:\s*([A-Za-z]+)', full_text)
        suggested_ans = suggested_match.group(1) if suggested_match else "-"

        vote_bar = card.find('div', class_='vote-bar')
        vote_detail = vote_bar.get_text(strip=True) if vote_bar else "投票なし"
        vote_match = re.match(r'([A-Za-z]+)', vote_detail)
        vote_ans = vote_match.group(1) if vote_match else "-"

        # URL
        link_tag = card.find('a', class_='source-link')
        url = link_tag['href'] if link_tag else "#"

        # --- 翻訳 & HTML整形 ---
        q_body_div = card.find('div', class_='question-body') or card.find('div', class_='q-text')
        
        en_html = ""
        jp_html_parts = []
        excel_text_preview = ""

        if q_body_div:
            # Excel用プレビュー
            excel_text_preview = q_body_div.get_text(" ", strip=True)[:50] + "..."

            # 不要要素削除
            for trash in q_body_div.find_all('div', class_=['question-answer', 'voting-summary', 'voted-answers-tally']):
                trash.decompose()
            for trash in q_body_div.find_all(['script', 'style', 'button']):
                trash.decompose()
            
            en_html = str(q_body_div)

            # 翻訳処理
            try:
                # 本文
                p_text = q_body_div.find('p', class_='card-text')
                if p_text:
                    txt = p_text.get_text(strip=True)
                    if txt:
                        trans = translator.translate(txt)
                        jp_html_parts.append(f"<p class='jp-text'>{trans}</p>")
                        time.sleep(0.5)

                # 選択肢
                choices = q_body_div.find_all('li', class_='multi-choice-item')
                if choices:
                    jp_html_parts.append("<ul class='jp-choices'>")
                    for choice in choices:
                        letter_span = choice.find('span', class_='multi-choice-letter')
                        letter = letter_span.get_text(strip=True) if letter_span else "●"
                        choice_body = choice.get_text(" ", strip=True).replace(letter, "", 1).strip()
                        
                        trans_choice = translator.translate(choice_body)
                        # クラスを引き継ぐ（正解の色付けなどがあれば）
                        css = " ".join(choice.get('class', []))
                        jp_html_parts.append(f"<li class='{css}'><span class='jp-letter'>{letter}</span> {trans_choice}</li>")
                        time.sleep(0.2)
                    jp_html_parts.append("</ul>")

            except Exception as e:
                jp_html_parts.append(f"<p style='color:red'>翻訳エラー: {e}</p>")

        jp_html = "".join(jp_html_parts) if jp_html_parts else "<p>翻訳データなし</p>"

        # --- 意見割れ判定 ---
        status_alert = ""
        excel_status = "OK"
        if vote_ans != "-" and suggested_ans != vote_ans:
            status_alert = "<span class='warning'>⚠️ 意見割れ</span>"
            excel_status = "⚠️ CHECK"
        elif vote_ans == "-":
            excel_status = "-"

        # --- HTML用カード作成 ---
        html_card = f"""
        <div class="question-card" id="q{q_num}">
            <div class="q-header">
                <div class="q-title-group">
                    <span class="q-title">Question {q_num}</span>
                    {status_alert}
                </div>
                <button class="toggle-btn" onclick="toggleLang({q_num})">🇯🇵 / 🇺🇸 切替</button>
            </div>
            
            <div id="jp-area-{q_num}" class="q-content jp-area">{jp_html}</div>
            <div id="en-area-{q_num}" class="q-content en-area" style="display:none;">{en_html}</div>

            <div class="answer-section">
                <div class="ans-box">
                    <span class="ans-label">サイト解答</span>
                    <span class="ans-value">{suggested_ans}</span>
                </div>
                <div class="ans-box community-box">
                    <span class="ans-label">みんなの解答</span>
                    <span class="ans-value">{vote_detail}</span>
                </div>
                <a href="{url}" target="_blank" class="ref-link">Webで議論を見る ↗</a>
            </div>
        </div>
        """

        # リストに追加
        questions_data.append({
            'num': q_num,
            'html': html_card,
            'excel_row': {
                'No.': q_num,
                '自分の結論': '',
                'メモ': '',
                '判定': excel_status,
                'サイト解答': suggested_ans,
                'みんなの解答': vote_ans,
                '投票率': vote_detail,
                '問題文(冒頭)': excel_text_preview,
                'HTMLリンク': f'=HYPERLINK("{OUTPUT_HTML}#q{q_num}", "問題へ")',
                'Webリンク': f'=HYPERLINK("{url}", "Web")'
            }
        })

    # --- ソート ---
    questions_data.sort(key=lambda x: x['num'])

    # --- 1. HTML書き出し ---
    print("\n📘 HTMLファイルを生成中...")
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><title>CIS-CSM Master Textbook</title><style>
        body{font-family:"Segoe UI",sans-serif;background:#f0f2f5;color:#333;padding:20px} .question-card{background:#fff;max-width:850px;margin:0 auto 30px;padding:25px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.1)}
        .q-header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #eee;padding-bottom:15px;margin-bottom:15px}
        .q-title{font-weight:700;font-size:1.2em;color:#0056b3} .warning{color:#d9534f;font-weight:700;margin-left:10px;background:#fce8e6;padding:2px 8px;border-radius:4px;font-size:.9em}
        .toggle-btn{background:#fff;border:1px solid #ccc;padding:5px 15px;border-radius:20px;cursor:pointer;transition:.2s} .toggle-btn:hover{background:#e9ecef}
        .q-content{font-size:1.1em;line-height:1.6;min-height:100px} .jp-text{font-weight:500} .jp-choices{list-style:none;padding-left:10px}
        .jp-choices li{padding:8px;margin-bottom:5px;background:#f8f9fa;border-radius:6px} .jp-letter{font-weight:700;color:#0056b3;margin-right:10px}
        .answer-section{margin-top:20px;padding-top:15px;border-top:1px solid #eee;display:flex;gap:15px;align-items:center;flex-wrap:wrap}
        .ans-box{background:#f8f9fa;padding:5px 15px;border-radius:5px;border:1px solid #ddd;text-align:center;display:flex;flex-direction:column;min-width:80px}
        .community-box{border-left:4px solid #28a745;background:#e6f9ed;border-color:#c3e6cb} .ans-label{font-size:.75em;color:#666} .ans-value{font-weight:700;font-size:1.1em}
        .ref-link{margin-left:auto;color:#007bff;text-decoration:none;font-size:.9em}
        </style><script>function toggleLang(id){var j=document.getElementById('jp-area-'+id),e=document.getElementById('en-area-'+id);if(j.style.display==='none'){j.style.display='block';e.style.display='none'}else{j.style.display='none';e.style.display='block'}}</script></head><body><h1 style="text-align:center">CIS-CSM 完全攻略問題集</h1>""")
        for q in questions_data:
            f.write(q['html'])
        f.write("</body></html>")

    # --- 2. Excel書き出し ---
    print("📓 Excelファイルを生成中...")
    df = pd.DataFrame([q['excel_row'] for q in questions_data])
    # 列順序整理
    cols = ['No.', '自分の結論', 'メモ', '判定', 'サイト解答', 'みんなの解答', '投票率', 'HTMLリンク']
    df = df[cols]
    
    with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Study Log')
        ws = writer.sheets['Study Log']
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 40
        ws.column_dimensions['H'].width = 12

    print(f"\n🎉 全ての処理が完了しました！")
    print(f"1. 閲覧用: {OUTPUT_HTML}")
    print(f"2. 記録用: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()