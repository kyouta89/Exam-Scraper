from google import genai
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import re
import os
import time
from dotenv import load_dotenv

# --- 設定エリア ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

INPUT_FILE = 'CIS-CSM_Complete_Questions.html'
OUTPUT_HTML = 'CIS-CSM_Master_Textbook_AI_SplitOnly.html' 
MODEL_ID = 'models/gemini-2.5-pro' 

# 'ALL':全問, 'SPLIT_ONLY':意見割れのみ, 'NONE':翻訳のみ
AI_TARGET_MODE = 'SPLIT_ONLY' 

TEST_LIMIT = 1000
# ------------------

def init_client():
    if not API_KEY:
        print("⚠️ エラー: .envファイルまたはAPIキーが見つかりません。")
        return None
    return genai.Client(api_key=API_KEY)

def get_ai_answer(client, question_text):
    if not client: return "API未設定"
    
    prompt = f"""
    あなたはServiceNowのエキスパート(CIS-CSM認定資格保持者)です。
    以下の「英語の試験問題」について、サイトの正解とコミュニティの投票が割れています。
    どちらが正しいか、あるいは問題自体が古いのか、論理的に正解を導き出し解説してください。

    【重要】
    1. 出力は「日本語」で行ってください。
    2. なぜその選択肢が正解なのか、ServiceNowの仕組みに基づいて解説してください。

    出力フォーマット:
    正解: [あなたの考える正解]
    解説: [理由と分析]

    --- Question ---
    {question_text}
    """
    
    max_retries = 3
    base_wait = 20
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=MODEL_ID, contents=prompt)
            return response.text.strip()
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = base_wait * (attempt + 1)
                print(f"   ⏳ 制限待機中... ({wait}秒)")
                time.sleep(wait)
            else:
                return f"エラー: {e}"
    return "生成失敗"

def main():
    if not os.path.exists(INPUT_FILE):
        print("❌ ファイルが見つかりません")
        return

    client = init_client()
    print(f"🚀 処理開始 | モード: {AI_TARGET_MODE} | モデル: {MODEL_ID}")

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    cards = soup.find_all('div', class_='question-card')
    questions_data = []
    translator = GoogleTranslator(source='auto', target='ja')
    
    process_count = 0

    for i, card in enumerate(cards):
        if process_count >= TEST_LIMIT:
            print(f"\n🛑 制限 ({TEST_LIMIT}問) に達しました。")
            break

        full_text = card.get_text(" ", strip=True)
        suggested_match = re.search(r'Suggested Answer:\s*([A-Za-z]+)', full_text)
        suggested_ans = suggested_match.group(1) if suggested_match else "-"
        
        vote_bar = card.find('div', class_='vote-bar')
        vote_detail = vote_bar.get_text(strip=True) if vote_bar else "投票なし"
        vote_match = re.match(r'([A-Za-z]+)', vote_detail)
        vote_ans = vote_match.group(1) if vote_match else "-"
        
        is_split = (vote_ans != "-" and suggested_ans != vote_ans)
        
        should_run_ai = False
        if AI_TARGET_MODE == 'ALL': should_run_ai = True
        elif AI_TARGET_MODE == 'SPLIT_ONLY':
            if is_split: should_run_ai = True
        
        status_icon = "⚠️" if is_split else "✅"
        print(f"   [{i+1}] {status_icon} Ans:{suggested_ans} / Vote:{vote_ans} -> AI生成: {'ON' if should_run_ai else 'OFF'} ...", end="\r")
        process_count += 1

        q_num = 9999
        header = card.find('div', class_='q-header')
        if header:
            m = re.search(r'Question\s+(\d+)', header.get_text())
            if m: q_num = int(m.group(1))
        
        link_tag = card.find('a', class_='source-link')
        url = link_tag['href'] if link_tag else "#"

        q_body_div = card.find('div', class_='question-body') or card.find('div', class_='q-text')
        jp_html_parts = []
        en_html = ""
        clean_text_for_ai = ""

        if q_body_div:
            # ① 先にゴミを削除する
            for trash in q_body_div.find_all(['script', 'style', 'button', 'div']):
                # クラス判定を少し緩くしてヒットしやすくする（in判定に変更）
                trash_classes = trash.get('class', [])
                if any(c in ['question-answer', 'voting-summary', 'vote-bar'] for c in trash_classes):
                    trash.decompose()
            
            # ② きれいになった状態でテキストを取得する
            clean_text_for_ai = q_body_div.get_text("\n", strip=True)
            en_html = str(q_body_div)

            try:
                p_text = q_body_div.find('p', class_='card-text')
                if p_text:

                    # --- 【追加】翻訳前に不要なバッジやスパンを削除する ---
                    # 投票バッジや不要な補足テキストが含まれるクラスを指定して削除
                    # サイトの仕様変更に対応できるよう、汎用的な span もチェック対象にするか検討が必要ですが
                    # まずは 'vote-distribution-bar', 'badge' などを狙い撃ちします
                    for badge in p_text.find_all(['span', 'div'], class_=['vote-distribution-bar', 'badge', 'voted-answers-tally']):
                        badge.decompose()
                    
                    # 念のため、"Most Voted" というテキストを持つ要素を強力に削除
                    for element in p_text.find_all(string=lambda text: text and "Most Voted" in text):
                        element.parent.decompose() # そのテキストを含む親タグごと削除
                    # ----------------------------------------------------

                    txt = p_text.get_text(strip=True)
                    if txt:
                        trans = translator.translate(txt)
                        jp_html_parts.append(f"<p class='jp-text'>{trans}</p>")
                        time.sleep(0.3)

                choices = q_body_div.find_all('li', class_='multi-choice-item')
                if choices:
                    jp_html_parts.append("<ul class='jp-choices'>")
                    for choice in choices:
                        letter_span = choice.find('span', class_='multi-choice-letter')
                        letter = letter_span.get_text(strip=True) if letter_span else "●"
                        body = choice.get_text(" ", strip=True).replace(letter, "", 1).strip()
                        t_body = translator.translate(body) if body else ""
                        css = " ".join(choice.get('class', []))
                        jp_html_parts.append(f"<li class='{css}'><span class='jp-letter'>{letter}</span> {t_body}</li>")
                        time.sleep(0.2)
                    jp_html_parts.append("</ul>")
            except:
                jp_html_parts.append("<p>翻訳失敗</p>")

        jp_html = "".join(jp_html_parts) if jp_html_parts else "<p>データなし</p>"

        ai_html = "<span style='color:#999; font-size:0.9em;'>(条件外のためAI解説なし)</span>"
        if should_run_ai and client and clean_text_for_ai:
            ai_text = get_ai_answer(client, clean_text_for_ai)
            ai_html = ai_text.replace("\n", "<br>")
            time.sleep(5)

        warning_tag = "<span class='warning'>⚠️ 意見割れ</span>" if is_split else ""
        card_html = f"""
        <div class="question-card" id="q{q_num}">
            <div class="q-header">
                <div class="q-title-group"><span class="q-title">Question {q_num}</span> {warning_tag}</div>
                <div class="btn-group">
                    <button class="toggle-btn answer-btn" onclick="toggleAns({q_num}, this)">🫣 正解を表示</button>
                    <button class="toggle-btn" onclick="toggleLang({q_num})">🇯🇵 / 🇺🇸</button>
                </div>
            </div>
            <div id="jp-area-{q_num}" class="q-content jp-area">{jp_html}</div>
            <div id="en-area-{q_num}" class="q-content en-area" style="display:none;">{en_html}</div>
            <div id="ans-area-{q_num}" class="answer-section" style="display:none;">
                <div class="ans-box"><span class="ans-label">サイト解答</span><span class="ans-value">{suggested_ans}</span></div>
                <div class="ans-box community-box"><span class="ans-label">投票</span><span class="ans-value">{vote_ans}</span></div>
                <div class="ans-box ai-box"><span class="ans-label">🤖 AI解説</span><span class="ans-value-sm">{ai_html}</span></div>
                <a href="{url}" target="_blank" class="ref-link">Discussion ↗</a>
            </div>
        </div>
        """
        questions_data.append({'num': q_num, 'html': card_html})

    questions_data.sort(key=lambda x: x['num'])
    print(f"\n📘 ファイル保存中: {OUTPUT_HTML}")
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><title>CIS-CSM Master</title><style>
        body{font-family:"Segoe UI",sans-serif;background:#f0f2f5;padding:20px;color:#333} .question-card{background:#fff;max-width:850px;margin:0 auto 30px;padding:25px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.1)}
        .q-header{display:flex;justify-content:space-between;border-bottom:2px solid #eee;padding-bottom:15px;margin-bottom:15px} .q-title{font-weight:bold;color:#0056b3}
        .warning{color:#d9534f;background:#fce8e6;padding:2px 8px;border-radius:4px;font-size:0.9em;margin-left:10px;font-weight:bold}
        .btn-group{display:flex;gap:10px} .toggle-btn{border:1px solid #ccc;background:#fff;padding:5px 15px;border-radius:20px;cursor:pointer} .answer-btn{background:#e3f2fd;color:#1565c0;font-weight:bold}
        .jp-choices li{padding:8px;margin-bottom:5px;background:#f8f9fa;border-radius:5px} .jp-letter{font-weight:bold;color:#0056b3;margin-right:10px}
        .answer-section{margin-top:20px;padding-top:15px;border-top:1px solid #eee;display:flex;gap:15px;flex-wrap:wrap}
        .ans-box{background:#f8f9fa;padding:10px;border:1px solid #ddd;border-radius:5px;text-align:center;min-width:80px}
        .community-box{background:#e6f9ed;border-color:#c3e6cb;border-left:4px solid #28a745}
        .ai-box{background:#f3e5f5;border-color:#e1bee7;border-left:4px solid #8e44ad;text-align:left;flex:1;min-width:250px}
        .ans-value{font-weight:bold;font-size:1.2em} .ans-value-sm{font-size:0.95em;line-height:1.4}
        .ref-link{margin-left:auto;align-self:center;text-decoration:none;color:#007bff}
        </style><script>
        function toggleLang(id){var j=document.getElementById('jp-area-'+id),e=document.getElementById('en-area-'+id);if(j.style.display==='none'){j.style.display='block';e.style.display='none'}else{j.style.display='none';e.style.display='block'}}
        function toggleAns(id,b){var a=document.getElementById('ans-area-'+id);if(a.style.display==='none'){a.style.display='flex';b.innerText='🙈 隠す'}else{a.style.display='none';b.innerText='🫣 正解を表示'}}
        </script></head><body><h1 style="text-align:center">CIS-CSM 問題集 (AI Split Only)</h1>""")
        for q in questions_data: f.write(q['html'])
        f.write("</body></html>")

    print("🎉 完了しました！")

if __name__ == "__main__":
    main()