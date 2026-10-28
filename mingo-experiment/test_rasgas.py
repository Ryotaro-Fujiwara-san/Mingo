#APIキーを使うため、osと文字化け対策
import ast
import os,sys
import sqlite3
import tempfile
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

#APIキー読み込み
from dotenv import load_dotenv
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
load_dotenv(BACKEND_DIR / ".env")
EVALUATION_DB_DIR = tempfile.TemporaryDirectory(prefix="mingo-evaluation-")
os.environ["MEMO_DB_PATH"] = str(Path(EVALUATION_DB_DIR.name) / "memo.db")
sys.path.insert(0, str(BACKEND_DIR))

#RAGAS本体
from ragas import evaluate,EvaluationDataset,SingleTurnSample#evaluateは採点を実行する関数、EvaluationDatasetは採点対象をまとめたデータセットの型、SingleTurnSampleは1件分の採点データ
from ragas.metrics import LLMContextPrecisionWithoutReference, LLMContextRecall, Faithfulness, ResponseRelevancy

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper#RAGASは独自の内部インターフェースを持つので、LangChainのモデルを、RAGASが使える形に変換する“変換プラグ”を用意する
from langchain_openai import ChatOpenAI, OpenAIEmbeddings#ChatOpenAI / OpenAIEmbeddingsはLangChain製のOpenAI窓口

llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

#oa_clientを定義
from openai import OpenAI

#JSONをインポート
import json
from fastapi.testclient import TestClient
import main as backend_main

memo_script = ast.parse(
    (Path(__file__).resolve().parent / "test_memo.py").read_text(encoding="utf-8")
)
memo_assignment = next(
    (
        statement
        for statement in memo_script.body
        if isinstance(statement, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "memos"
            for target in statement.targets
        )
    ),
    None,
)
if memo_assignment is None:
    raise RuntimeError("Could not find the memos list in test_memo.py.")
test_memos = ast.literal_eval(memo_assignment.value)
if not isinstance(test_memos, list) or not all(
    isinstance(memo, str) for memo in test_memos
):
    raise ValueError("The memos list in test_memo.py must contain only strings.")

backend_main.init_memo_db()
memo_vectors = backend_main.embed_texts(test_memos)
if len(memo_vectors) != len(test_memos):
    raise RuntimeError("Embedding count does not match the test memos count.")
with sqlite3.connect(os.environ["MEMO_DB_PATH"]) as conn:
    conn.executemany(
        "INSERT INTO memo_item(user_id,type,text,vector) VALUES(?,?,?,?)",
        [
            ("naturalness-evaluation", "expression", memo, vector)
            for memo, vector in zip(test_memos, memo_vectors)
        ],
    )


#テスト用の質問（AIの発言）

test_queries = [
    "What did you do last weekend?",
    "How was your day today?",
    "What are your plans for the weekend?",
    "Tell me about your morning.",
    "What did you have for lunch?",
]

#実際の/hintを呼んで「選んだ表現」と「作った例文」を取得
samples = []
def local_test_user():
    with sqlite3.connect(os.environ["MEMO_DB_PATH"]) as conn:
        row = conn.execute("SELECT user_id FROM memo_item LIMIT 1").fetchone()
    return {"sub": row[0] if row else "naturalness-evaluation"}

backend_main.app.dependency_overrides[backend_main.limited_user] = local_test_user

with TestClient(backend_main.app) as client:
    for q in test_queries:
        res = client.post("/hint", json={"query": q})
        res.raise_for_status()
        data = res.json()
        hints = [h["text"] for h in data["hints"]]   #選んだ表現
        example = data["example"]                     #作った例文
        print(f"[{q}]  表現:{hints}  例文:{example}")
        samples.append(SingleTurnSample(
            user_input=q,
            retrieved_contexts=hints,
            response=example,
        ))
dataset = EvaluationDataset(samples=samples)#複数サンプルをまとめる


#指標を用意
metrics = [
    ResponseRelevancy(),                 #例文：質問文に関連しているか
]

oa_client = OpenAI()#OPENAI_API_KEYを環境から自動で使う

##==メモの表現を実際に例文に使ったか計測する関数 ==##
def expression_usage_rate(expressions,example):
    if not expressions:
        return None
    prompt = (
        "例文が、次の表現リストの各表現を実際に使っているか判定して。活用形・言い換えも「使った」とみなす。"
        "必ずJSONだけで返す:\n"
        '{"used":["実際に使われた表現",...]}\n'
        f"表現リスト:{expressions}\n"
        f"例文:{example}"
    )
    res = oa_client.chat.completions.create(#oa_clientでapi_keyを書かなくても環境変数OPENAI_API_KEY（.envから読み込み済み）を自動で使う。
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        response_format={"type":"json_object"},#JSONで返させる
        temperature=0.2,
    )
    used = json.loads(res.choices[0].message.content).get("used",[])#res.choicesで返答候補のリストを返し、res.choices[0]でその一個目を返します。さらにres.choices[0].message.contentでモデルが書いた本文を取り出し、.get("used", [])でその辞書からusedのリストを取り出し、無ければ空のリスト[]を返します。
    return len(used)/len(expressions)#使用率


##==例文の自然さを1~10で採点する関数 ==##
def naturalness_score(example):
    prompt = (
        "次の英文が、ネイティブから見て自然な一文か1〜10で採点して（10=非常に自然, 1=不自然）。"
        "必ずJSONだけで返す:\n"
        '{"score":整数, "reason":"理由"}\n'
        f"例文:{example}"
    )
    res = oa_client.chat.completions.create(#oa_clientでapi_keyを書かなくても環境変数OPENAI_API_KEY（.envから読み込み済み）を自動で使う。
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        response_format={"type":"json_object"},#JSONで返させる
        temperature=0.2,
    )
    return json.loads(res.choices[0].message.content)


#採点を実行（llmとembeddingsを渡すと全指標がそれを使う）
result = evaluate(dataset=dataset, metrics=metrics, llm=llm, embeddings=embeddings)
print(result)#各指標のスコア（0〜1、高いほど良い）
rates = [expression_usage_rate(s.retrieved_contexts, s.response) for s in samples]
rates =  [expression_usage_rate(s.retrieved_contexts, s.response) for s in samples]#使用率を全サンプルで計算して平均
print("expression_usage_rate:", sum(rates)/len(rates))#使用率の平均値
#自然さを全サンプルで採点して平均
nat_scores = [naturalness_score(s.response)["score"] for s in samples]
print("naturalness_score :", sum(nat_scores)/len(nat_scores))
EVALUATION_DB_DIR.cleanup()
