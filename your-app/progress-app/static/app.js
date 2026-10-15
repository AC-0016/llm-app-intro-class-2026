// 画面の部品を、HTMLのidで取り出しておく。
const form = document.getElementById('question-form');
const questionInput = document.getElementById('question');
const button = document.getElementById('send-button');
const statusText = document.getElementById('status');
const answerArea = document.getElementById('answer');
const toolResultsArea = document.getElementById('tool-results');

// LLMが呼んだ関数と、DBから読んだ進捗を表で表示する。
function showToolResults(toolResults) {
  toolResultsArea.replaceChildren(); // 前回の表示を消す
  if (toolResults.length === 0) {
    toolResultsArea.textContent = '関数は呼ばれませんでした。';
    return;
  }
  for (const toolResult of toolResults) {
    const call = document.createElement('p');
    const code = document.createElement('code');
    code.textContent = toolResult.name + '(' + toolResult.arguments + ')';
    call.appendChild(code);
    toolResultsArea.appendChild(call);

    const table = document.createElement('table');
    const header = document.createElement('tr');
    for (const text of ['id', 'やること', '完了']) {
      const th = document.createElement('th');
      th.textContent = text;
      header.appendChild(th);
    }
    table.appendChild(header);

    for (const row of toolResult.rows) {
      const tr = document.createElement('tr');
      const id = document.createElement('td');
      id.textContent = row.id;
      const task = document.createElement('td');
      task.textContent = row.task;
      const done = document.createElement('td');
      done.textContent = row.done ? '完了' : '未完了';
      tr.appendChild(id);
      tr.appendChild(task);
      tr.appendChild(done);
      table.appendChild(tr);
    }
    toolResultsArea.appendChild(table);
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
  toolResultsArea.textContent = '-';

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
    showToolResults(data.tool_results);
    statusText.textContent = '完了（入力' + data.input_tokens + 'トークン・出力' + data.output_tokens + 'トークン）';
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

form.addEventListener('submit', askQuestion);
