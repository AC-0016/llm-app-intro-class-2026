"""講師用。完成版をコピーし、未習の機能を削って各回を作る。
学生が編集したexerciseを上書きするため、--replaceを明示した場合だけ実行する。
"""
import argparse
import ast
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'sample-app'


def copy_app(destination):
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(SAMPLE, destination, ignore=shutil.ignore_patterns(
        '__pycache__', '*.db', '*.db-*', '.env', 'README.md'))


def remove_functions(path, names):
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    for node in reversed(ast.parse(text).body):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            del lines[node.lineno - 1:node.end_lineno]
    path.write_text(''.join(lines).rstrip() + '\n')


def make_stage(destination, stage):
    copy_app(destination)
    if stage == 1:
        return  # 初回は完成品を観察する。コードの実装は求めない。
    if stage == 2:
        for path in list(destination.iterdir()):
            if path.name not in ['settings.py', 'llm.py', 'one_shot.py']:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        remove_functions(destination / 'llm.py', ['build_context', 'ask_with_context'])
        return
    modes = ['plain']
    if stage >= 4: modes.append('context')
    if stage >= 5: modes.append('keyword')
    if stage >= 6: modes.append('vector')
    if stage >= 7: modes.append('tools')
    path = destination / 'main.py'
    text = path.read_text()
    # 未習のelif節をソースから削除する。実行時の授業番号分岐は作らない。
    text = re.sub(r"        elif request.mode == '(\w+)':\n.*?(?=        elif|    except)",
                  lambda m: m[0] if m[1] in modes else '', text, flags=re.S)
    text = text.replace("Literal['plain', 'context', 'keyword', 'vector', 'tools'] = 'keyword'",
                        'Literal[' + ', '.join(repr(m) for m in modes) + '] = ' + repr(modes[-1]))
    if stage < 8:
        text = re.sub(r'# BEGIN STAGE 8\n.*?# END STAGE 8\n', '', text, flags=re.S)
        text = text.replace('import threading\n', '').replace('    check_limit()\n', '')
    if stage < 7:
        text = text.replace('from assignment_tools import init_assignments, ask_assignments\n', '')
        text = text.replace('init_assignments()\n', '')
        (destination / 'assignment_tools.py').unlink()
        p = destination / 'init_db.py'
        p.write_text(p.read_text().replace('from assignment_tools import init_assignments\n', '').replace('    init_assignments()\n', ''))
    if stage < 6:
        text = text.replace('from embeddings import search_vector\n', '')
        (destination / 'embeddings.py').unlink()
        (destination / 'build_index.py').unlink()
    if stage < 5:
        text = text.replace('init_documents, all_chunks, search_keyword', 'init_documents, all_chunks')
        remove_functions(destination / 'knowledge.py', ['search_keyword', 'get_score'])
    if stage < 4:
        text = text.replace('from llm import ask_plain, ask_with_context, build_context', 'from llm import ask_plain')
        text = text.replace('from knowledge import init_documents, all_chunks\n', '')
        text = text.replace('# DBが無い初回だけ資料を登録。更新はサーバーを止めてinit_db.pyを実行する。\nif not DATABASE.exists():\n    init_documents()\n', '')
        text = text.replace("result['context'] = build_context(chunks)", "result['context'] = ''")
        remove_functions(destination / 'llm.py', ['build_context', 'ask_with_context'])
        (destination / 'knowledge.py').unlink()
        (destination / 'init_db.py').unlink()
        shutil.rmtree(destination / 'data')
    path.write_text(text)
    path = destination / 'static/index.html'
    html = path.read_text()
    html = re.sub(r'      <option value="(\w+)"[^>]*>.*?</option>\n',
                  lambda m: m[0].replace(' selected', '') if m[1] in modes else '', html)
    html = html.replace('value="' + modes[-1] + '"', 'value="' + modes[-1] + '" selected')
    if stage < 5: html = html.replace('id="search-options"', 'id="search-options" hidden')
    if stage < 4: html = html.replace('id="sources-section"', 'id="sources-section" hidden')
    path.write_text(html)


def hole(path, marker, description):
    text = path.read_text()
    prefix = '// ' if path.suffix == '.js' else '# '
    pattern = r'(?m)^([ ]*)' + re.escape(prefix) + 'BEGIN EXERCISE ' + marker + r'\n(.*?)^[ ]*' + re.escape(prefix) + 'END EXERCISE ' + marker + r'\n'
    def replace(match):
        indent = match[1]
        code = match[2]
        hints = ''
        for line in code.splitlines():
            hints += indent + prefix + line[len(indent):] + '\n'
        if path.suffix == '.js':
            stop = "throw new Error('TODO: " + description + "');"
        else:
            stop = "raise NotImplementedError('TODO: " + description + "')"
        return indent + prefix + 'TODO: ' + description + '\n' + hints + indent + stop + '\n'
    text, count = re.subn(pattern, replace, text, flags=re.S)
    assert count == 1, (path, marker, count)
    path.write_text(text)


def build():
    tasks = {2: ('llm.py', 'api', 'API呼び出しのコメントを外し、raiseを削除する'),
             3: ('static/app.js', 'fetch', 'POST通信のコメントを外し、throwを削除する'),
             4: ('llm.py', 'prompt', '指示文を復元し、根拠不足時の応答を確認する'),
             5: ('knowledge.py', 'keyword', '単語ごとの一致件数を加算する'),
             6: ('embeddings.py', 'cosine', '内積と各ベクトルの長さを計算する'),
             7: ('assignment_tools.py', 'sql', 'パラメータバインディングで課題を取得する')}
    for stage in range(1, 9):
        parent = ROOT / f'session{stage:02}'
        solution = parent / 'solution'
        exercise = parent / 'exercise'
        make_stage(solution, stage)
        if exercise.exists(): shutil.rmtree(exercise)
        shutil.copytree(solution, exercise)
        if stage in tasks:
            filename, marker, description = tasks[stage]
            hole(exercise / filename, marker, description)
        if stage == 8:
            path = exercise / 'main.py'
            text = path.read_text()
            text = text.replace('        if len(request_times) >= 10 or request_count >= 100:',
                "        # TODO: 1分10回または合計100回で制限する条件を書き、次のraiseを削除\n"
                "        raise HTTPException(status_code=501, detail='TODO: 利用上限の条件を実装してください。')\n"
                "        # ヒント: len(request_times) >= 10 or request_count >= 100\n"
                "        if False:")
            path.write_text(text)
    # 制作は第8回完成版から出発する。
    copy_app(ROOT / 'your-app')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    if not args.replace:
        parser.error('演習コードを上書きします。講師のみ --replace を指定してください。')
    build()
