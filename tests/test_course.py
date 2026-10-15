"""外部APIを呼ばずに、コピーの起動・境界・通信形式を検証する。"""
import importlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI
import httpx

ROOT = Path(__file__).resolve().parents[1]
MODULES = ['settings', 'main', 'llm', 'knowledge', 'embeddings', 'assignment_tools',
           'documents', 'search', 'progress_db']


@pytest.fixture
def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv('DEMO_MODE', 'true')
    def load(relative):
        for name in MODULES:
            sys.modules.pop(name, None)
        destination = tmp_path / relative.replace('/', '-')
        shutil.copytree(ROOT / relative, destination,
                        ignore=shutil.ignore_patterns('*.db', '*.db-*', '__pycache__', '.env'))
        monkeypatch.syspath_prepend(str(destination))
        main = importlib.import_module('main' if (destination / 'main.py').exists() else 'llm')
        if relative != 'your-app':
            monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
            def handle(request):
                body = json.loads(request.content)
                if request.url.path.endswith('/embeddings'):
                    return httpx.Response(200, json={
                        'object': 'list', 'model': body['model'],
                        'data': [{'object': 'embedding', 'index': 0, 'embedding': [1.0, 0.0]}],
                        'usage': {'prompt_tokens': 1, 'total_tokens': 1}})
                if 'tools' in body:
                    output = [tool_call(body)]
                else:
                    output = [message('テスト用のAPI回答')]
                return httpx.Response(200, json=response_json(output))
            sdk = OpenAI(api_key='test-only', http_client=httpx.Client(
                transport=httpx.MockTransport(handle)))
            monkeypatch.setattr(importlib.import_module('llm'), 'OpenAI', lambda **kwargs: sdk)
        return main, destination
    yield load
    for name in MODULES:
        sys.modules.pop(name, None)


@pytest.mark.parametrize('relative,stage', [('your-app',8)] +
                         [(f'session{i:02}/solution',i) for i in [1,3,4,5,6,7,8]])
def test_each_complete_app(load_app, relative, stage):
    main, directory = load_app(relative)
    if stage == 1: stage = 8
    client = TestClient(main.app)
    assert client.get('/').status_code == 200
    if relative != 'your-app':
        assert client.get('/api/config').status_code == 404
    else:
        assert client.get('/api/config').json() == {'demo_mode': True}
    assert client.get('/.env').status_code == 404
    assert client.get('/classroom.db').status_code == 404
    modes = ['plain']
    if stage >= 4: modes.append('context')
    if stage >= 5: modes.append('keyword')
    if stage >= 6 and (directory / 'embeddings.py').exists():
        embeddings = importlib.import_module('embeddings')
        assert embeddings.build_embeddings() == 10
        modes.append('vector')
    if stage >= 7: modes.append('tools')
    for mode in modes:
        response = client.post('/api/ask', json={
            'question':'SQLiteに保存するには？', 'mode':mode, 'search_text':'SQLite 保存'})
        assert response.status_code == 200, response.text
        assert response.json()['answer']
    for question in ['', '   ', 'x'*501]:
        assert client.post('/api/ask',json={'question':question,'mode':'plain'}).status_code == 422
    assert client.post('/api/ask',json={'question':'a','mode':'unknown'}).status_code == 422
    assert client.post('/api/ask',json={'question':'a','top_k':100}).status_code == 422


def test_keyword_app(load_app):
    main, directory = load_app('sample-app/keyword-app')
    documents = importlib.import_module('documents')
    search = importlib.import_module('search')
    client = TestClient(main.app)
    assert client.get('/').status_code == 200
    assert client.get('/.env').status_code == 404
    assert len(main.documents) == 10
    assert main.documents[0]['id'] == 1
    # Janomeで検索語を取り出す。
    assert search.extract_words('SQLiteに保存するには？') == ['sqlite', '保存']
    assert search.extract_words('ページを閉じてもデータが残るのはなぜ？') == ['ページ', '閉じる', 'データ', '残る']
    assert search.extract_words('は？') == []
    found = search.search_documents(['sqlite', '保存'], main.documents, 3)
    headings = []
    for document in found:
        headings.append(document['heading'])
    assert 'SQLiteと永続化' in headings
    assert found[0]['score'] == 2
    assert 'score' not in main.documents[0]
    assert search.search_documents(['zzzz'], main.documents, 3) == []
    # APIの入口。
    response = client.post('/api/ask', json={'question': 'SQLiteに保存するには？'})
    assert response.status_code == 200, response.text
    assert response.json()['answer'] == 'テスト用のAPI回答'
    assert response.json()['keywords'] == ['sqlite', '保存']
    assert len(response.json()['sources']) == 3
    response = client.post('/api/ask', json={'question': 'zzzzについて'})
    assert response.json()['sources'] == []
    assert response.json()['input_tokens'] == 0
    assert client.post('/api/ask', json={'question': 'は？'}).status_code == 400
    for question in ['', '   ', 'x'*501]:
        assert client.post('/api/ask', json={'question': question}).status_code == 422
    # 資料を削除して読み直すと、その資料が消える。
    (directory/'data/03-api.md').unlink()
    assert len(documents.load_documents()) == 7
    (directory/'data/04-long.md').write_text('# 長い資料\n## 長い見出し\n' + 'あ'*1001)
    with pytest.raises(ValueError, match='長すぎます'):
        documents.load_documents()


def test_progress_app(load_app):
    main, directory = load_app('sample-app/progress-app')
    db = importlib.import_module('progress_db')
    llm = importlib.import_module('llm')
    client = TestClient(main.app)
    assert client.get('/').status_code == 200
    assert client.get('/progress.db').status_code == 404
    todo = db.get_tasks('todo')
    assert len(todo) == 3
    assert todo[0] == {'id': 4, 'task': 'Janomeでキーワード検索を作る', 'done': False}
    assert db.get_tasks('done')[0]['done'] is True
    assert len(db.get_tasks('done')) == 3
    assert len(db.get_tasks('all')) == 6
    # 再起動しても変更済みの進捗を上書きしない。
    import sqlite3
    conn = sqlite3.connect(directory / 'progress.db')
    conn.execute('UPDATE tasks SET done = 1 WHERE id = 4')
    conn.commit()
    conn.close()
    db.init_db()
    assert len(db.get_tasks('todo')) == 2
    for name,args in [('delete_all','{}'), ('get_assignments','{"status":"pending"}'),
                      ('get_tasks','{"status":"bad"}'),
                      ('get_tasks','{"status":"all","sql":"DROP TABLE"}'),
                      ('get_tasks','[]'), ('get_tasks','not json')]:
        with pytest.raises(ValueError): llm.run_tool(name,args)
    response = client.post('/api/ask', json={'question': 'まだの作業は？'})
    assert response.status_code == 200, response.text
    assert response.json()['answer'] == 'テスト用のAPI回答'
    assert response.json()['tool_results'][0]['name'] == 'get_tasks'
    assert len(response.json()['tool_results'][0]['rows']) == 2
    for question in ['', '   ', 'x'*501]:
        assert client.post('/api/ask', json={'question': question}).status_code == 422


@pytest.mark.parametrize('stage,mode',[(5,'keyword'),(6,'vector'),(7,'tools'),(8,'plain')])
def test_exercises_fail_explicitly_until_completed(load_app, stage, mode):
    main, _ = load_app(f'session{stage:02}/exercise')
    if stage == 6:
        importlib.import_module('embeddings').build_embeddings()
    response = TestClient(main.app).post('/api/ask',json={
        'question':'SQLite 保存','mode':mode,'search_text':'SQLite 保存'})
    assert response.status_code == 501
    assert 'TODO' in response.json()['detail']


def tool_call(body):
    # アプリが渡した関数で呼び出す。sample-appは進捗DB、各回のコピーは課題DB。
    name = body['tools'][0]['name']
    arguments = '{"status":"todo"}' if name == 'get_tasks' else '{"status":"pending"}'
    return {'type': 'function_call', 'id': 'fc_test', 'call_id': 'call_test',
            'name': name, 'arguments': arguments}


def response_json(output, response_id='resp_test'):
    return {'id':response_id,'object':'response','created_at':0,'model':'gpt-6-luna',
            'status':'completed','output':output,
            'usage':{'input_tokens':12,'output_tokens':6,'total_tokens':18},
            'parallel_tool_calls':False,'tool_choice':'auto','tools':[]}


def message(text):
    return {'type':'message','id':'msg_test','role':'assistant','status':'completed',
            'content':[{'type':'output_text','text':text,'annotations':[]}]}


def test_real_sdk_request_and_function_roundtrip(load_app, monkeypatch):
    main, _ = load_app('sample-app/progress-app')
    llm = importlib.import_module('llm')
    requests = []
    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        assert body['model'] == 'gpt-6-luna'
        assert body['reasoning'] == {'effort':'none'}
        assert body['store'] is False
        if 'tools' in body:
            output = [tool_call(body)]
        else:
            output = [message('確認した回答')]
        return httpx.Response(200,json=response_json(output))
    sdk = OpenAI(api_key='test-only',http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(llm,'make_client',lambda:sdk)
    result = llm.ask_with_tools('まだの作業は？')
    assert result['answer'] == '確認した回答'
    assert result['input_tokens'] == 24
    assert result['output_tokens'] == 12
    assert 'tools' in requests[0]
    final_input = requests[-1]['input']
    assert final_input[0]['content'] == 'まだの作業は？'
    result_item = final_input[-1]
    assert result_item['call_id'] == 'call_test'
    assert len(json.loads(result_item['output'])) == 3
    assert 'tools' not in requests[-1]


def test_keyword_app_sends_documents(load_app, monkeypatch):
    main, _ = load_app('sample-app/keyword-app')
    llm = importlib.import_module('llm')
    requests = []
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,json=response_json([message('確認した回答')]))
    sdk = OpenAI(api_key='test-only',http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(llm,'make_client',lambda:sdk)
    result = llm.ask_with_documents('質問です', main.documents[:2])
    assert result == {'answer': '確認した回答', 'input_tokens': 12, 'output_tokens': 6}
    assert requests[0]['store'] is False
    assert '[資料1]' in requests[0]['input']
    assert '[資料2]' in requests[0]['input']
    assert requests[0]['input'].endswith('質問:\n質問です')


def test_api_errors_and_incomplete(load_app, monkeypatch):
    main, _ = load_app('sample-app/keyword-app')
    llm = importlib.import_module('llm')
    question = {'question': 'SQLiteに保存するには？'}
    incomplete = SimpleNamespace(status='incomplete', output_text='途中')
    client_stub = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: incomplete))
    original_make_client = llm.make_client
    monkeypatch.setattr(llm, 'make_client', lambda: client_stub)
    with pytest.raises(ValueError):
        llm.ask_with_documents('質問', main.documents[:1])
    monkeypatch.setattr(llm, 'make_client', original_make_client)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    assert TestClient(main.app).post('/api/ask', json=question).status_code == 400
    from openai import APITimeoutError
    def fail(question, documents):
        raise APITimeoutError(request=httpx.Request('POST','https://example.test'))
    monkeypatch.setattr(main,'ask_with_documents',fail)
    result = TestClient(main.app).post('/api/ask', json=question)
    assert result.status_code == 504
    assert 'example.test' not in result.text


@pytest.mark.parametrize('relative', ['sample-app/keyword-app', 'sample-app/progress-app', 'your-app'] + [
    f'session{i:02}/{kind}' for i in range(1, 9)
    for kind in ['exercise', 'solution']])
def test_settings_use_only_session_environment(tmp_path, monkeypatch, relative):
    import runpy
    directory = tmp_path / 'app'
    directory.mkdir()
    shutil.copy(ROOT / relative / 'settings.py', directory / 'settings.py')
    (directory / '.env').write_text(
        'OPENAI_API_KEY=file-key\nDEMO_MODE=false\nOPENAI_MODEL=file-model\n')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('DEMO_MODE', raising=False)
    monkeypatch.delenv('OPENAI_MODEL', raising=False)
    settings = runpy.run_path(str(directory / 'settings.py'))
    if relative != 'your-app':
        assert 'DEMO_MODE' not in settings
    else:
        assert settings['DEMO_MODE'] is True
    assert settings['MODEL'] == 'gpt-6-luna'
    assert settings['os'].getenv('OPENAI_API_KEY') is None
    monkeypatch.setenv('OPENAI_API_KEY', 'session-key')
    monkeypatch.setenv('DEMO_MODE', 'false')
    monkeypatch.setenv('OPENAI_MODEL', 'session-model')
    settings = runpy.run_path(str(directory / 'settings.py'))
    if relative != 'your-app':
        assert 'DEMO_MODE' not in settings
    else:
        assert settings['DEMO_MODE'] is False
    assert settings['MODEL'] == 'session-model'
    assert settings['os'].getenv('OPENAI_API_KEY') == 'session-key'


@pytest.mark.parametrize('kind', ['exercise', 'solution'])
def test_session02_api_path(load_app, kind):
    llm, _ = load_app(f'session02/{kind}')
    if kind == 'exercise':
        with pytest.raises(NotImplementedError, match='TODO'):
            llm.ask_plain('質問')
    else:
        assert llm.ask_plain('質問')['answer'] == 'テスト用のAPI回答'
