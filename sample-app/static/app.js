// HTMLのidと対応させる。フレームワークは使わない。
const form = document.getElementById('question-form');
const button = document.getElementById('send-button');
const statusText = document.getElementById('status');

function renderSources(sources) {
  const list = document.getElementById('sources');
  list.replaceChildren();
  for (const source of sources) {
    const item = document.createElement('li');
    const title = document.createElement('strong');
    title.textContent = '[資料' + source.id + '] ' + source.title + ' / ' + source.heading;
    const body = document.createElement('p');
    body.textContent = source.body;
    const filename = document.createElement('small');
    filename.textContent = '原本: data/' + source.source;
    if (source.score !== undefined) filename.textContent += ' / 検索スコア: ' + source.score;
    item.appendChild(title);
    item.appendChild(body);
    item.appendChild(filename);
    list.appendChild(item);
  }
}

async function askQuestion(event) {
  event.preventDefault();
  const question = document.getElementById('question').value.trim();
  if (!question) {
    statusText.textContent = '質問を入力してください。';
    return;
  }
  button.disabled = true;
  statusText.textContent = '調べています…';
  document.getElementById('answer').textContent = '';
  renderSources([]);
  document.getElementById('debug').textContent = '';
  try {
    // BEGIN EXERCISE fetch
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        question: question,
        use_keyword: document.getElementById('use-keyword').checked,
        use_tools: document.getElementById('use-tools').checked,
        top_k: Number(document.getElementById('top-k').value)
      })
    });
    // END EXERCISE fetch
    const data = await response.json();
    if (!response.ok) {
      let message = '入力内容を確認してください。';
      if (typeof data.detail === 'string') message = data.detail;
      throw new Error(message);
    }
    // LLMの出力も信頼せず、HTMLとして実行しない。
    document.getElementById('answer').textContent = data.answer;
    renderSources(data.sources);
    document.getElementById('debug').textContent = JSON.stringify({
      keywords: data.keywords,
      context: data.context,
      tool_results: data.tool_results,
      input_tokens: data.input_tokens,
      output_tokens: data.output_tokens
    }, null, 2);
    statusText.textContent = '完了 / ' + data.seconds + '秒';
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

form.addEventListener('submit', askQuestion);
