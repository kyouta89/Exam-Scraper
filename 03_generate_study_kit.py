from google import genai
from google.genai import types
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import re
import os
import time
from dotenv import load_dotenv

# --- 設定エリア ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

INPUT_FILE = 'CSA_Complete_Questions.html'
OUTPUT_HTML = 'CSA_Master_Textbook_Hybrid.html'
TEST_LIMIT = None  # None = 全問, 数値(例:10) = テスト用に最初のN問

# ★ 生成モード設定
# 'ALL'       : 全問解説 (難問はPro、通常はFlashで使い分け)
# 'SPLIT_ONLY': 意見割れのみ解説 (通常問は生成しない)
# 'NONE'      : AI解説なし (翻訳のみ)
AI_TARGET_MODE = 'ALL'

# ★ モデル設定
MODEL_HIGH_IQ = 'models/gemini-2.0-pro-exp-02-05'  # 意見割れ用：賢い
MODEL_FAST    = 'models/gemini-2.0-flash'          # 通常用：速い
# ------------------

def init_client():
    if not API_KEY:
        print("⚠️ エラー: .envファイルまたはAPIキーが見つかりません。")
        return None
    return genai.Client(api_key=API_KEY)

def get_ai_answer(client, question_text, mode='FAST'):
    """AIに解説を生成させる"""
    if not client: return "API未設定"
    
    # プロンプトの使い分け
    if mode == 'HIGH_IQ':
        model_id = MODEL_HIGH_IQ
        prompt = f"""
        あなたはServiceNowの最高権威(CIS-CSM/CSA認定)です。
        以下の「英語の試験問題」について、サイトの正解とコミュニティの投票が割れており、難問です。
        ServiceNowの仕様やドキュメントに基づき、論理的に「真の正解」を導き出してください。

        【要件】
        1. 出力は「日本語」です。
        2. なぜ意見が割れているのかの背景も含めて分析してください。
        3. 最終的な正解を断定してください。

        出力フォーマット:
        【正解】: [正解の選択肢]
        【詳細解説】: [論理的な分析と理由]
        
        --- Question ---
        {question_text}
        """
    else:
        # FASTモード
        model_id = MODEL_FAST
        prompt = f"""
        あなたはServiceNowの認定講師です。
        以下の試験問題の「正解」と「簡潔な解説」を日本語で出力してください。
        
        【要件】
        1. 解説は3行以内で端的にまとめてください。
        2. 初学者にもわかりやすい言葉を使ってください。

        出力フォーマット:
        【正解】: [選択肢]
        【ポイント】: [短い解説]

        --- Question ---
        {question_text}
        """
    
    max_retries = 3
    base_wait = 20 if mode == 'HIGH_IQ' else 2
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_id, 
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3)
            )
            return response.text.strip()
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                wait = base_wait * (attempt + 1)
                print(f"   ⏳ ({mode}) 制限待機中... {wait}秒")
                time.sleep(wait)
            else:
                return f"エラー: {e}"
    return "生成失敗"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ ファイルが見つかりません: {INPUT_FILE}")
        return

    client = init_client()
    print(f"🚀 処理開始 | モード: {AI_TARGET_MODE}")
    print(f"   - 難問(Pro): {MODEL_HIGH_IQ}")
    print(f"   - 通常(Flash): {MODEL_FAST}")

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    cards = soup.find_all('div', class_='question-card')
    questions_data = []
    translator = GoogleTranslator(source='auto', target='ja')
    
    process_count = 0
    total_cards = len(cards)
    
    for i, card in enumerate(cards):
        if TEST_LIMIT is not None and process_count >= TEST_LIMIT:
            print(f"\n🛑 制限 ({TEST_LIMIT}問) に達しました。")
            break

        # --- 1. データ抽出 ---
        full_text = card.get_text(" ", strip=True)
        suggested_match = re.search(r'Suggested Answer:\s*([A-Za-z]+)', full_text)
        suggested_ans = suggested_match.group(1) if suggested_match else "-"
        
        # 投票情報の詳細
        vote_bars = card.find_all('div', class_='vote-bar')
        vote_distribution = []
        vote_ans = "-"
        
        for bar in vote_bars:
            style_attr = bar.get('style', '')
            if 'display: none' in style_attr.lower(): continue
                
            vote_text = bar.get_text(strip=True)
            if vote_text and '(' in vote_text:
                match = re.match(r'([A-Z]+)\s*\((\d+)%\)', vote_text)
                if match:
                    choice = match.group(1)
                    vote_distribution.append(f"{choice}: {match.group(2)}%")
                    if vote_ans == "-": vote_ans = choice
        
        vote_detail_html = "<br>".join(vote_distribution) if vote_distribution else "投票なし"
        
        # 難易度判定
        is_community_split = len(vote_distribution) > 1
        is_site_community_split = (vote_ans != "-" and suggested_ans != vote_ans)
        is_difficult = is_site_community_split or is_community_split

        # ★ 実行判定ロジック
        should_run_ai = False
        ai_execution_mode = 'FAST' # デフォルト

        if AI_TARGET_MODE == 'ALL':
            should_run_ai = True
            ai_execution_mode = 'HIGH_IQ' if is_difficult else 'FAST'
        
        elif AI_TARGET_MODE == 'SPLIT_ONLY':
            if is_difficult:
                should_run_ai = True
                ai_execution_mode = 'HIGH_IQ'
            else:
                should_run_ai = False # 通常問題はスキップ
        
        elif AI_TARGET_MODE == 'NONE':
            should_run_ai = False

        # --- ログ表示 ---
        if is_difficult:
            status_icon = "⚠️ 難"
        else:
            status_icon = "✅ 普"
        
        ai_status_msg = f"AI:{ai_execution_mode}" if should_run_ai else "AI:OFF"
        print(f"   [{i+1}/{total_cards}] {status_icon} -> {ai_status_msg} ...", end="\r")
        process_count += 1

        # --- 2. HTML整形・翻訳 ---
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
            # ゴミ掃除
            for trash in q_body_div.find_all(['script', 'style', 'button']): trash.decompose()
            for trash in q_body_div.find_all('div'):
                if not trash.attrs: continue
                trash_classes = trash.get('class', [])
                if any(c in ['question-answer', 'voting-summary', 'vote-bar'] for c in trash_classes):
                    trash.decompose()
            for badge in q_body_div.find_all(['span', 'div'], class_=['badge', 'most-voted-answer-badge']):
                badge.decompose()
            for element in q_body_div.find_all(string=lambda text: text and "Most Voted" in text):
                element.replace_with("")
            
            clean_text_for_ai = q_body_div.get_text("\n", strip=True)
            en_html = str(q_body_div)

            # 翻訳処理
            try:
                p_text = q_body_div.find('p', class_='card-text')
                if p_text:
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

        # --- 3. AI解説実行 ---
        ai_html = "<span style='color:#999; font-size:0.9em'>(AI解説なし)</span>"
        ai_badge = "🤖 AI"
        ai_box_class = "ai-box-none"

        if should_run_ai and client and clean_text_for_ai:
            ai_text = get_ai_answer(client, clean_text_for_ai, mode=ai_execution_mode)
            ai_html = ai_text.replace("\n", "<br>")
            
            # 実行モードに応じたスタイル設定
            if ai_execution_mode == 'HIGH_IQ':
                ai_box_class = "ai-box-pro"
                ai_badge = "🤖 Pro解説 (詳細)"
                wait_time = 4 # 賢いモデルは少し休ませる
            else:
                ai_box_class = "ai-box-fast"
                ai_badge = "⚡ Flash解説 (要点)"
                wait_time = 1

            time.sleep(wait_time)

        # --- 4. HTML組み立て ---
        warning_tag = ""
        if is_difficult:
            warning_tag = "<span class='warning'>⚠️ 意見割れ</span>"

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
                <div class="ans-box community-box"><span class="ans-label">コミュニティ投票</span><span class="ans-value-sm">{vote_detail_html}</span></div>
                <div class="ans-box {ai_box_class}"><span class="ans-label">{ai_badge}</span><span class="ans-value-sm">{ai_html}</span></div>
                <a href="{url}" target="_blank" class="ref-link">Discussion ↗</a>
            </div>
        </div>
        """
        questions_data.append({'num': q_num, 'html': card_html})

    # --- 5. 保存 ---
    questions_data.sort(key=lambda x: x['num'])
    print(f"\n📘 ファイル保存中: {OUTPUT_HTML}")
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><title>CSA Master Hybrid</title><style>
        body{font-family:"Segoe UI",sans-serif;background:#f0f2f5;padding:20px;color:#333} .question-card{background:#fff;max-width:850px;margin:0 auto 30px;padding:25px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.1)}
        .q-header{display:flex;justify-content:space-between;border-bottom:2px solid #eee;padding-bottom:15px;margin-bottom:15px} .q-title{font-weight:bold;color:#0056b3}
        .warning{color:#d9534f;background:#fce8e6;padding:2px 8px;border-radius:4px;font-size:0.9em;margin-left:10px;font-weight:bold}
        .btn-group{display:flex;gap:10px} .toggle-btn{border:1px solid #ccc;background:#fff;padding:5px 15px;border-radius:20px;cursor:pointer} .answer-btn{background:#e3f2fd;color:#1565c0;font-weight:bold}
        .jp-choices li{padding:8px;margin-bottom:5px;background:#f8f9fa;border-radius:5px} .jp-letter{font-weight:bold;color:#0056b3;margin-right:10px}
        .answer-section{margin-top:20px;padding-top:15px;border-top:1px solid #eee;display:flex;gap:15px;flex-wrap:wrap}
        .ans-box{background:#f8f9fa;padding:10px;border:1px solid #ddd;border-radius:5px;text-align:center;min-width:80px}
        .community-box{background:#e6f9ed;border-color:#c3e6cb;border-left:4px solid #28a745;min-width:200px}
        /* スタイル定義 */
        .ai-box-pro{background:#f3e5f5;border-color:#e1bee7;border-left:4px solid #8e44ad;text-align:left;flex:1;min-width:250px}
        .ai-box-fast{background:#e3f2fd;border-color:#bbdefb;border-left:4px solid #2196f3;text-align:left;flex:1;min-width:250px}
        .ai-box-none{background:#f5f5f5;border-color:#ddd;text-align:left;flex:1;min-width:250px;color:#999}
        .ans-value{font-weight:bold;font-size:1.2em} .ans-value-sm{font-size:0.95em;line-height:1.4}
        .ans-label{display:block;font-weight:bold;margin-bottom:5px;color:#666}
        .ref-link{margin-left:auto;align-self:center;text-decoration:none;color:#007bff}
        </style><script>
        function toggleLang(id){var j=document.getElementById('jp-area-'+id),e=document.getElementById('en-area-'+id);if(j.style.display==='none'){j.style.display='block';e.style.display='none'}else{j.style.display='none';e.style.display='block'}}
        function toggleAns(id,b){var a=document.getElementById('ans-area-'+id);if(a.style.display==='none'){a.style.display='flex';b.innerText='🙈 隠す'}else{a.style.display='none';b.innerText='🫣 正解を表示'}}
        </script></head><body><h1 style="text-align:center">CSA 完全攻略問題集 (AI Hybrid版)</h1>""")
        for q in questions_data: f.write(q['html'])
        f.write("</body></html>")

    print("\n🎉 完了しました！")

if __name__ == "__main__":
    main()