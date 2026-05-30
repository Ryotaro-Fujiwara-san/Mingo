import { useState, useRef } from 'react'//useState=画面に出す値の箱／useRef=画面に出さない裏方の箱


// ===== 音声変換の道具（部品なので、画面の部品(App)の外に置く）=====

// マイクの音(Float32) → 16bitのPCM → base64文字 に変換（OpenAIへ送る形）
function floatToBase64(float32: Float32Array) {
  const int16 = new Int16Array(float32.length)//16bit整数を入れる箱
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]))//-1〜1の範囲に収める
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff//小数を16bit整数(-32768〜32767)に変換
  }
  const bytes = new Uint8Array(int16.buffer)//整数の並びを「バイトの並び」として見る
  let binary = ''
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i])//1バイトずつ文字にする
  return btoa(binary)//バイト列を base64 文字に変換（btoa=binary to ascii）
}

// OpenAIの音声(base64文字) → 16bit → Float32 に変換（再生できる形）
function base64ToFloat32(b64: string) {
  const binary = atob(b64)//base64 を元のバイト列(文字)に戻す（atob=ascii to binary）
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)//1文字ずつ数値(バイト)に
  const int16 = new Int16Array(bytes.buffer)//バイトの並びを16bit整数として見る
  const float32 = new Float32Array(int16.length)
  for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 0x8000//整数を-1〜1の小数に戻す
  return float32
}


function App() {//画面一個分の部品
  const [started, setStarted] = useState(false)//startedが今の状態（false)であり、setStartedが状態を変化させるボタンとなる
  const [health, setHealth] = useState('まだ確認していません')
  const [wsReply, setWsReply] = useState('まだ送ってません')
  const [micStatus, setMicstatus] = useState('マイクはまだOFF')
  const [volume, setVolume] = useState(0)
  const [question, setQuestion] = useState('')//入力欄に打った質問の文字を覚えておく箱
  const [aiAnswer, setAiAnswer] = useState('')//AIの返答を覚えておく箱
  const [talking, setTalking] = useState(false)//会話中かどうか
  const [aiText, setAiText] = useState('')//AIが今しゃべっている内容(文字)

  const wsRef = useRef<WebSocket | null>(null)//OpenAIへの中継回線（裏方）
  const audioCtxRef = useRef<AudioContext | null>(null)//音の工場（裏方）
  const playTimeRef = useRef(0)//次に音を再生する時刻（裏方）
  const sourcesRef = useRef<AudioBufferSourceNode[]>([])//再生中の音の一覧（割り込みで止める用）

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

  // ===== ここからリアルタイム音声会話　=====

  //受け取った音声のかけらを、途切れないように順番に再生する
  function playChunk(float32: Float32Array) {
    const ctx = audioCtxRef.current
    if (!ctx) return//工場が無ければ何もしない
    const buffer = ctx.createBuffer(1, float32.length, 24000)//1ch・24kHzの「音の器」を作る
    buffer.getChannelData(0).set(float32)//器に音の中身を流し込む
    const src = ctx.createBufferSource()//音を鳴らす再生機
    src.buffer = buffer
    src.connect(ctx.destination)//スピーカーへつなぐ
    const startAt = Math.max(ctx.currentTime, playTimeRef.current)//前のかけらの続きの時刻から鳴らす
    src.start(startAt)
    playTimeRef.current = startAt + buffer.duration//次のかけらの開始時刻を更新（=途切れない）
    sourcesRef.current.push(src)//割り込みで止められるよう記録
    src.onended = () => {//鳴り終わったら一覧から外す
      sourcesRef.current = sourcesRef.current.filter((s) => s !== src)
    }
  }

  //割り込み：再生中の音を全部止める
  function stopPlayback() {
    for (const s of sourcesRef.current) {
      try {
        s.stop()
      } catch (e) {
        //もう止まっている場合は無視
      }
    }
    sourcesRef.current = []//一覧を空に
    if (audioCtxRef.current) playTimeRef.current = audioCtxRef.current.currentTime//再生時刻をリセット
  }

  //会話スタート：中継につなぐ→マイク送信→受信した音を再生
  async function startConversation() {
    setTalking(true)
    setAiText('')

    //1) バックエンドの中継(/realtime)につなぐ
    const ws = new WebSocket('ws://127.0.0.1:8000/realtime')
    wsRef.current = ws

    //2) 音の工場を24kHzで作る（送受信ともこのレートで統一）
    const ctx = new AudioContext({ sampleRate: 24000 })
    audioCtxRef.current = ctx
    playTimeRef.current = 0

    //3) OpenAIから来たメッセージを処理
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)//届いたJSON文字を中身に戻す
      if (data.type === 'response.output_audio.delta') {
        playChunk(base64ToFloat32(data.delta))//音声のかけら→再生
      } else if (data.type === 'response.output_audio_transcript.delta') {
        setAiText((prev) => prev + data.delta)//AIの発話テキストをどんどん追記
      } else if (data.type === 'input_audio_buffer.speech_started') {
        stopPlayback()//自分が話し始めたらAIの音を止める(割り込み)
        setAiText('')
      }
    }

    //4) マイクを取得して、音を送り続ける
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const source = ctx.createMediaStreamSource(stream)//マイクを工場入口へ
    const processor = ctx.createScriptProcessor(4096, 1, 1)//音を小分けで受け取る部品
    source.connect(processor)
    processor.connect(ctx.destination)//これが無いと processor が動かない（出力は無音）
    processor.onaudioprocess = (e) => {//音が一定量たまるたびに呼ばれる
      if (ws.readyState !== WebSocket.OPEN) return//まだ繋がってなければ送らない
      const input = e.inputBuffer.getChannelData(0)//マイクのFloat32(24kHz)
      const b64 = floatToBase64(input)//送れる形に変換
      ws.send(JSON.stringify({ type: 'input_audio_buffer.append', audio: b64 }))//OpenAIへ音を送る
    }
  }

  //会話ストップ：全部止めて片付ける
  function stopConversation() {
    setTalking(false)
    stopPlayback()
    if (wsRef.current) wsRef.current.close()//中継を切る
    if (audioCtxRef.current) audioCtxRef.current.close()//工場を閉じる（マイクも止まる）
    wsRef.current = null
    audioCtxRef.current = null
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

      <hr style={{ margin: '2rem 0' }} />
      <button onClick={talking ? stopConversation : startConversation}>{/*会話中なら止める、そうでなければ始める*/}
        {talking ? '■ 会話を終わる' : 'AIと声で話す'}
      </button>
      <p>AIの発話: {aiText}</p>
    </div>
  )
}

export default App//このAppを他のファイルから使えるように外に出す
