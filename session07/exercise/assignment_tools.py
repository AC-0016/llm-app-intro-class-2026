"""第7回: LLMが提案した関数を、Pythonが検証して実行する。"""
import json
import sqlite3
from settings import MODEL, DATABASE
from llm import make_client, response_result

TOOLS = [{
    'type': 'function',
    'name': 'get_assignments',
    'description': '教材用の架空の課題の提出状況を調べる。',
    'parameters': {
        'type': 'object',
        'properties': {'status': {'type': 'string', 'enum': ['all', 'pending', 'done']}},
        'required': ['status'],
        'additionalProperties': False,
    },
    'strict': True,
}]


def init_assignments():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY, title TEXT, status TEXT
    )''')
    # 再起動で変更済みの提出状況を上書きしない。
    cursor.executemany('INSERT OR IGNORE INTO assignments VALUES (?, ?, ?)', [
        (1, '第2回 API呼び出しレポート', 'done'),
        (2, '第5回 検索結果の比較', 'pending'),
        (3, '第8回 評価シート', 'pending'),
    ])
    conn.commit()
    conn.close()


def get_assignments(status):
    if status not in ['all', 'pending', 'done']:
        raise ValueError('提出状況の指定が不正です。')
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # TODO: パラメータバインディングで課題を取得する
    # if status == 'all':
    #     cursor.execute('SELECT id, title, status FROM assignments ORDER BY id')
    # else:
    #     cursor.execute('SELECT id, title, status FROM assignments WHERE status = ? ORDER BY id', (status,))
    raise NotImplementedError('TODO: パラメータバインディングで課題を取得する')
    rows = cursor.fetchall()
    conn.close()
    assignments = []
    for row in rows:
        assignments.append({'id': row[0], 'title': row[1], 'status': row[2]})
    return assignments


def execute_tool(name, arguments):
    # eval()、exec()、自由なSQL生成は使わない。
    if name != 'get_assignments':
        raise ValueError('許可していない関数です。')
    args = json.loads(arguments)
    if not isinstance(args, dict) or set(args.keys()) != {'status'}:
        raise ValueError('引数の形式が不正です。')
    if not isinstance(args['status'], str):
        raise ValueError('statusは文字列で指定してください。')
    return get_assignments(args['status'])


def ask_assignments(question):
    client = make_client()
    history = [{'role': 'user', 'content': question}]
    instructions = '課題の提出状況は必ずget_assignmentsの結果だけで答えてください。日本語で回答してください。'
    first = client.responses.create(
        model=MODEL, reasoning={'effort': 'none'}, instructions=instructions, input=history, tools=TOOLS,
        parallel_tool_calls=False, max_output_tokens=600, store=False,
    )
    if first.status != 'completed':
        raise ValueError('関数選択が完了しませんでした。')
    # 関数呼び出し項目を含め、モデルの出力を次の入力に引き継ぐ。
    history.extend(first.output)
    tool_results = []
    for item in first.output:
        if item.type == 'function_call':
            rows = execute_tool(item.name, item.arguments)
            tool_results.append({'name': item.name, 'arguments': item.arguments, 'rows': rows})
            history.append({'type': 'function_call_output', 'call_id': item.call_id,
                            'output': json.dumps(rows, ensure_ascii=False)})
    if not tool_results:
        result = response_result(first)
    else:
        # 2回目にはtoolsを渡さず、追加の呼び出しを許可しない。
        second = client.responses.create(
            model=MODEL, reasoning={'effort': 'none'}, instructions=instructions, input=history,
            max_output_tokens=600, store=False,
        )
        result = response_result(second)
        result['input_tokens'] += first.usage.input_tokens
        result['output_tokens'] += first.usage.output_tokens
    result['tool_results'] = tool_results
    return result
