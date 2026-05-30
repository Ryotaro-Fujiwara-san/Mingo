import { useState } from 'react'//画面に状態を保存させたいため、useStateでその変化する情報をReactに覚えさせる道具を取り出す

function App() {//画面一個分の部品であり、この関数が返した見た目がそのまま画面になる。
  const [started, setStarted] = useState(false)//startedが今の状態（false)であり、setStartedが状態を変化させるボタンとなる
  const [health, setHealth] = useState('まだ確認していません')
  const [wsReply, setWsReply] = useState('まだ送ってません')
  const [micStatus, setMicstatus] = useState('マイクはまだOFF')
  const [volume, setVolume] = useState(0)
  const [question, setQuestion] = useState('')//入力欄に打った質問の文字を覚えておく箱
  const [aiAnswer, setAiAnswer] = useState('')//AIの返答を覚えておく箱

  async function checkHealth() {
    try {//通信をまずやってみる
      const response = await fetch('http://127.0.0.1:8000/health')//この住所で返事をもらう
      const data = await response.json()
      setHealth(data.status)
    } catch (error) {
      setHealth('バックエンド未接続')
    }
  }

  //WebSocketでつなぐ
  function sendWebSocket() {
    const ws = new WebSocket('ws://127.0.0.1:8000/ws')
    ws.onopen = () => {//繋がったらこの言葉を送る
      ws.send('こんにちは、サーバー')
    }
    ws.onmessage = (event) => {//メッセージが届いたらその中身を箱に入れる
      setWsReply(event.data)
    }
    ws.onerror = () => {
      setWsReply('未接続')
    }
  }

  async function startMic() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })//ブラウザに「マイクを使わせて」と要求
      setMicstatus('マイクON(' + stream.getAudioTracks()[0].label + ')')//マイクの種類を表示
      const audioContext = new AudioContext()//音を扱う音響処理システムを作る
      const source = audioContext.createMediaStreamSource(stream)//マイクの音を工場の入り口につなぐ部品
      const analyser = audioContext.createAnalyser()//音の強さを測る計測器を作る
      source.connect(analyser)//入口と計測器をパイプでつなぐ
      const data = new Uint8Array(analyser.frequencyBinCount)//frequencyBinCountで周波数の棒数を分け、Uint8Arrayは0〜255の数字だけを入れられる箱
      function tick() {//測って画面に高速で出力する
        analyser.getByteFrequencyData(data)//今の音をdataに書き込む
        let sum = 0//合計を入れる（最初は０）
        for (let i = 0; i < data.length; i++) {
          sum += data[i]//一個ずつsumに足す
        }
        setVolume(Math.round(sum / data.length))//平均を出して画面に渡す
        requestAnimationFrame(tick)//次に画面を書き直すタイミングでもう一回tickを呼ぶ
      }
      tick()//最初の１回をスタート
    } catch (error) {
      setMicstatus('マイクが使えませんでした（許可が必要です）')
    }
  }

  //AIに質問を送る（POST）
  async function askAI() {
    setAiAnswer('考え中...')//返事が来るまでの表示
    try {
      const response = await fetch('http://127.0.0.1:8000/ask', {
        method: 'POST',//データを送りつけるタイプ
        headers: { 'Content-Type': 'application/json' },//中身はJSONだと伝える札
        body: JSON.stringify({ message: question }),//質問を文字に変換して送る
      })
      const data = await response.json()
      setAiAnswer(data.answer)//AIの答えを箱に入れる→画面に出る
    } catch (error) {
      setAiAnswer('エラー：バックエンドは起動してる？')
    }
  }

  return (
    <div style={{ textAlign: 'center', marginTop: '4rem', fontFamily: 'sans-serif' }}>{/*中央寄せ・上に余白・フォント指定*/}
      <h1>Mingo</h1>{/*見出し */}
      <p>AIと会話して言語学習を支援します。</p>

      <button onClick={() => setStarted(!started)}>{/*押すたびに started が反転して表示が切り替わる*/}
        {started ? '会話中...' : '会話を始める'}{/*条件 ? 真のとき : 偽のとき*/}
      </button>
      {started && <p>マイクの準備をしています...</p>}{/* started が true のときだけ表示*/}

      <hr style={{ margin: '2rem 0' }} />{/*横線*/}
      <button onClick={checkHealth}>サーバーの状態を確認</button>
      <p>バックエンドの返事:{health}</p>{/*healthの中身を表示*/}

      <hr style={{ margin: '2rem 0' }} />
      <button onClick={sendWebSocket}>WebSocketで送る</button>
      <p>サーバーからの返事: {wsReply}</p>

      <hr style={{ margin: '2rem 0' }} />
      <button onClick={startMic}>マイクをON</button>
      <p>{micStatus}</p>
      <p>音量: {volume}</p>
      <div style={{ height: '20px', width: volume * 3 + 'px', background: 'limegreen', margin: '0 auto' }} />{/*声で伸びる緑バー*/}

      <hr style={{ margin: '2rem 0' }} />
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="AIに質問を入力"
        style={{ width: '60%', padding: '0.5rem' }}
      />
      <button onClick={askAI}>AIに質問</button>
      <p>AIの答え: {aiAnswer}</p>
    </div>
  )
}

export default App//このAppを他のファイルから使えるように外に出す
