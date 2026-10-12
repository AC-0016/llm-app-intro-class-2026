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
MODULES = ['settings', 'main', 'llm', 'knowledge', 'embeddings', 'assignment_tools']


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
                    output = [{'type': 'function_call', 'id': 'fc_test', 'call_id': 'call_test',
                               'name': 'get_assignments', 'arguments': '{"status":"pending"}'}]
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


@pytest.mark.parametrize('relative,stage', [('sample-app',8), ('your-app',8)] +
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
    if stage >= 6:
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


def test_search_rebuild_and_tools(load_app):
    main, directory = load_app('sample-app')
    knowledge = importlib.import_module('knowledge')
    vectors = importlib.import_module('embeddings')
    functions = importlib.import_module('assignment_tools')
    assert len(knowledge.all_chunks()) == 10
    assert knowledge.search_keyword('zzzz-no-match', 3) == []
    found = knowledge.search_keyword('SQLite 保存', 3)
    assert found[0]['score'] == 2
    assert len(found) <= 3
    assert vectors.cosine_similarity([1,0],[1,0]) == 1
    assert vectors.cosine_similarity([1,0],[0,1]) == 0
    assert vectors.cosine_similarity([0,0],[1,0]) == 0
    vectors.build_embeddings()
    assert vectors.search_vector('SQLite 保存', 3)
    knowledge.init_documents()
    with pytest.raises(ValueError, match='ベクトル'):
        vectors.search_vector('SQLite',3)
    assert len(functions.get_assignments('pending')) == 2
    assert len(functions.get_assignments('done')) == 1
    assert len(functions.get_assignments('all')) == 3
    for name,args in [('delete_all','{}'), ('get_assignments','{"status":"bad"}'),
                      ('get_assignments','{"status":"all","sql":"DROP TABLE"}'),
                      ('get_assignments','[]')]:
        with pytest.raises(ValueError): functions.execute_tool(name,args)
    (directory/'data/03-api.md').unlink()
    knowledge.init_documents()
    assert len(knowledge.all_chunks()) == 7


def test_rate_limit(load_app):
    main, _ = load_app('sample-app')
    client = TestClient(main.app)
    for i in range(10):
        assert client.post('/api/ask',json={'question':'a','mode':'plain'}).status_code == 200
    assert client.post('/api/ask',json={'question':'a','mode':'plain'}).status_code == 429
    main.request_times.clear()
    main.request_count = 100
    assert client.post('/api/ask',json={'question':'a','mode':'plain'}).status_code == 429


@pytest.mark.parametrize('stage,mode',[(5,'keyword'),(6,'vector'),(7,'tools'),(8,'plain')])
def test_exercises_fail_explicitly_until_completed(load_app, stage, mode):
    main, _ = load_app(f'session{stage:02}/exercise')
    if stage == 6:
        importlib.import_module('embeddings').build_embeddings()
    response = TestClient(main.app).post('/api/ask',json={
        'question':'SQLite 保存','mode':mode,'search_text':'SQLite 保存'})
    assert response.status_code == 501
    assert 'TODO' in response.json()['detail']


def response_json(output, response_id='resp_test'):
    return {'id':response_id,'object':'response','created_at':0,'model':'gpt-6-luna',
            'status':'completed','output':output,
            'usage':{'input_tokens':12,'output_tokens':6,'total_tokens':18},
            'parallel_tool_calls':False,'tool_choice':'auto','tools':[]}


def message(text):
    return {'type':'message','id':'msg_test','role':'assistant','status':'completed',
            'content':[{'type':'output_text','text':text,'annotations':[]}]}


def test_real_sdk_request_and_function_roundtrip(load_app, monkeypatch):
    main, _ = load_app('sample-app')
    llm = importlib.import_module('llm')
    funcs = importlib.import_module('assignment_tools')
    requests = []
    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        assert body['model'] == 'gpt-6-luna'
        assert body['reasoning'] == {'effort':'none'}
        assert body['store'] is False
        if 'tools' in body:
            output = [{'type':'function_call','id':'fc_test','call_id':'call_test',
                       'name':'get_assignments','arguments':'{"status":"pending"}'}]
        else:
            output = [message('確認した回答')]
        return httpx.Response(200,json=response_json(output))
    sdk = OpenAI(api_key='test-only',http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(llm,'make_client',lambda:sdk)
    monkeypatch.setattr(funcs,'make_client',lambda:sdk)
    assert llm.ask_plain('質問')['answer'] == '確認した回答'
    result = funcs.ask_assignments('未提出は？')
    assert result['input_tokens'] == 24
    assert result['output_tokens'] == 12
    final_input = requests[-1]['input']
    result_item = final_input[-1]
    assert result_item['call_id'] == 'call_test'
    assert len(json.loads(result_item['output'])) == 2
    assert 'tools' not in requests[-1]


def test_api_errors_and_incomplete(load_app, monkeypatch):
    main, _ = load_app('sample-app')
    llm = importlib.import_module('llm')
    with pytest.raises(ValueError):
        llm.response_result(SimpleNamespace(status='incomplete',output_text='途中'))
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    assert TestClient(main.app).post('/api/ask',json={'question':'a','mode':'plain'}).status_code == 400
    from openai import APITimeoutError
    def fail(question):
        raise APITimeoutError(request=httpx.Request('POST','https://example.test'))
    monkeypatch.setattr(main,'ask_plain',fail)
    result = TestClient(main.app).post('/api/ask',json={'question':'a','mode':'plain'})
    assert result.status_code == 504
    assert 'example.test' not in result.text


@pytest.mark.parametrize('relative', ['sample-app', 'your-app'] + [
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
