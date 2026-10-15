// 1つの会話で質問できる回数の上限。main.py の MAX_TURNS と同じ値にする。
const MAX_TURNS = 10;

// 会話の履歴。質問と回答を、この順番でためていく。
// 例: [{role: 'user', content: '私の名前は佐藤です。'}, {role: 'assistant', content: 'こんにちは。'}]
let history = [];

// 画面の部品を、HTMLのidで取り出しておく。
const form = document.getElementById('chat-form');
const questionInput = document.getElementById('question');
const sendButton = document.getElementById('send-button');
const resetButton = document.getElementById('reset-button');
const statusText = document.getElementById('status');
const messagesList = document.getElementById('messages');

// 履歴を、会話の一覧として表示し直す。
function showMessages() {
  messagesList.replaceChildren(); // 前の表示を消す
  for (const message of history) {
    const item = document.createElement('li');
    if (message.role === 'user') {
      item.className = 'user';
      item.textContent = 'あなた: ' + message.content;
    } else {
      item.className = 'assistant';
      item.textContent = 'LLM: ' + message.content;
    }
    messagesList.appendChild(item);
  }
}

// 「送信」ボタンを押したときの処理。
async function sendQuestion(event) {
  event.preventDefault(); // フォーム送信でページが再読み込みされるのを止める

  const question = questionInput.value.trim();
  if (question === '') {
    statusText.textContent = '質問を入力してください。';
    return;
  }
  // 質問の回数は、履歴の中の質問（user）の数。
  if (history.length / 2 >= MAX_TURNS) {
    statusText.textContent = '質問は' + MAX_TURNS + '回までです。会話をリセットしてください。';
    return;
  }

  // 1. 今回の質問を履歴に追加して表示する。
  history.push({role: 'user', content: question});
  showMessages();
  questionInput.value = '';
  // 回答を待つ間は、送信もリセットもできないようにする。
  sendButton.disabled = true;
  resetButton.disabled = true;
  statusText.textContent = '回答を待っています…';

  try {
    // 2. 履歴をまとめてサーバーに送る。
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({history: history})
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

    // 3. LLMの回答も履歴に追加する。次の質問のときに一緒に送られる。
    history.push({role: 'assistant', content: data.answer});
    showMessages();
    statusText.textContent = '送った履歴 ' + (history.length - 1) + ' 件 / 入力 '
      + data.input_tokens + ' トークン / 出力 ' + data.output_tokens + ' トークン';
  } catch (error) {
    // 送れなかった質問は履歴から外し、入力欄に戻す。
    history.pop();
    showMessages();
    questionInput.value = question;
    statusText.textContent = error.message;
  } finally {
    sendButton.disabled = false;
    resetButton.disabled = false;
  }
}

// 「会話をリセット」ボタンを押したときの処理。履歴を空にする。
function resetChat() {
  history = [];
  showMessages();
  statusText.textContent = '会話をリセットしました。LLMは前の会話を知らない状態に戻ります。';
}

form.addEventListener('submit', sendQuestion);
resetButton.addEventListener('click', resetChat);
