// 画面の部品を、HTMLのidで取り出しておく。
const form = document.getElementById('question-form');
const questionInput = document.getElementById('question');
const button = document.getElementById('send-button');
const statusText = document.getElementById('status');
const answerArea = document.getElementById('answer');
const keywordsArea = document.getElementById('keywords');
const sourcesList = document.getElementById('sources');

// LLMに渡した資料を一覧で表示する。
function showSources(sources) {
  sourcesList.replaceChildren(); // 前回の表示を消す
  for (const source of sources) {
    const item = document.createElement('li');

    const title = document.createElement('strong');
    title.textContent = '[資料' + source.id + '] ' + source.title + ' / ' + source.heading;

    const body = document.createElement('p');
    body.textContent = source.body;

    const note = document.createElement('small');
    note.textContent = '原本: data/' + source.source + ' / 一致した検索語の数: ' + source.score;

    item.appendChild(title);
    item.appendChild(body);
    item.appendChild(note);
    sourcesList.appendChild(item);
  }
}

// 「質問する」ボタンを押したときの処理。
async function askQuestion(event) {
  event.preventDefault(); // フォーム送信でページが再読み込みされるのを止める

  const question = questionInput.value.trim();
  if (question === '') {
    statusText.textContent = '質問を入力してください。';
    return;
  }

  // 前回の結果を消し、ボタンを押せないようにする。
  button.disabled = true;
  statusText.textContent = '調べています…';
  answerArea.textContent = '';
  keywordsArea.textContent = '-';
  showSources([]);

  try {
    // サーバーに質問を送る。
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question: question})
    });
    const data = await response.json();

    if (!response.ok) {
      // サーバーが返したエラーの説明を表示する。
      let message = '入力内容を確認してください。';
      if (typeof data.detail === 'string') {
        message = data.detail;
      }
      throw new Error(message);
    }

    // textContentを使い、LLMの出力をHTMLとして実行しない。
    answerArea.textContent = data.answer;
    keywordsArea.textContent = data.keywords.join('、');
    showSources(data.sources);
    statusText.textContent = '完了（入力' + data.input_tokens + 'トークン・出力' + data.output_tokens + 'トークン）';
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

form.addEventListener('submit', askQuestion);
