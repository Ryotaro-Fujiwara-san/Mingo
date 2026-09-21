import { useState, useEffect, useRef } from "react";
import { WavRecorder,WavStreamPlayer } from "wavtools";
//== 言語選択におけるオブジェクトをリストに並べたもの ==//
const LANGUAGE =[
  {code:'en',label:'英語'},
  {code:'ja',label:'日本語'},
  {code:'ru',label:'ロシア語'},
]

const ROLE_COLOR:Record<string,string> = {//文法検索の際、文字（S,Vなど）と色のコードが対応するようにする
  S:"#1e6bff",    //主語=青
  V:"#e53935",    //動詞=赤
  O:"#fb8c00",    //目的語=橙
  C:"#2e9e44",    //補語=緑
  idiom:"#8e24aa",//慣用句=紫
}

//==文法検索結果を描く関数==//
function SentenceBlock({sentence,targetLang,explainLang}:{sentence:any,targetLang:string,explainLang:string}){
  const[open,setOpen] = useState<Record<number,any>>({})
  useEffect(()=>{setOpen({})},[sentence])//文[sentence]が変わったらetOpen({})でopenをリセットする
  async function tapClause(i:number,clauseText:string) {
    const res = await fetch("http://localhost:8000/grammar_search",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text:clauseText,targetLang,explainLang,context:sentence.text}),
    })
    const data = await res.json()
    setOpen({...open,[i]:data})
  }
  return(
    <div>
      {/* 色と□の表示*/}
      {sentence.segments.map((seg:any,i:number)=>(
        seg.role==="clause"
          ? <span key={i} onClick={()=>tapClause(i,seg.text)} //□をタップすると解析が始まる
          style={{border:"1.5px solid #555",borderRadius:"6px",padding:"1px 5px",margin:"0 2px"}}>{seg.text} </span>
        :<span key={i} style={{color:ROLE_COLOR[seg.role]}}>{seg.text+" "}</span>
      ))}

      {/* 解説（下にまとめて） */}
      <div style={{fontSize:"13px",marginTop:"4px"}}>
        <div>意味：{sentence.sub_meaning}</div>
        {sentence.segments.map((seg:any,i:number)=>(
          <div key={i}>・{seg.text}（{seg.role}）：{seg.meaning} ／ {seg.caseInflection}</div>
        ))}
      </div>

      {/* □タップで下に：総合解説＋その節を再帰表示 */}
      {sentence.segments.map((seg:any,i:number)=>
        open[i] && <div key={"o"+i} style={{marginLeft:"14px",borderLeft:"2px solid #ccc",paddingLeft:"10px"}}><div>{open[i].all_meaning}</div>
        {open[i].sentences.map((s:any,j:number)=>
        <SentenceBlock key={j} sentence={s} targetLang={targetLang} explainLang={explainLang}/>//Reactで関数を使う時はタグで書く
        )}
        </div>
      )}
    </div>
  )
}

//== ボタンの設定を保存する項目 ==//
function App(){
  const[role,setRole] = useState('')//AIの属性を決定する。ここではテキスト入力を想定し初期状態は0にする
  const[situation,setSituation] =  useState('')//AIのシチュエーションを決定する。ここではテキスト入力を想定し初期状態は0にする
  const[targetLang,setTargetLang] = useState('en')//学習言語を設定する。初期状態は英語
  const[explainLang,setExplainLang] =  useState('ja')//説明に使用する言語を設定する。初期状態は日本語
  const[micOn,setMicOn] = useState(true)//マイクをオンにする。初期状態はON
  const[liveAI,setLiveAI] = useState("");//今流れているAIの文字
  const[messages,setMessages] = useState<{who:string,text:string,grammar?:any,pron?:any,id?:string,code?:string}[]>([]);//会話の履歴を保存
  const[memoText,setMemoText] = useState('')//メモ表現を入力する。
  const[watchPath,setWatchPath] =useState('')//監視するフォルダのパスを入力する。
  const[example,setExample] = useState("");//ヒントの表現を保存し、表示する。
  const[view,setView] =useState("main");//メモの進捗ダッシュボードタブと会話タブを切り替える
  const[dash,setDash] = useState<any>(null);//ダッシュボードのデータ
  const playerRef = useRef<WavStreamPlayer | null>(null);//再生機
  const wsRef = useRef<WebSocket | null>(null);        // 接続(ws)を保存する箱
  const recorderRef = useRef<any>(null);               // マイク録音器を保存する箱
  const shownHintsRef = useRef<string[]>([]);//ヒントで見せた表現を保存する
  const lastYouRef = useRef<string|null>(null);//最後に処理したYou発言のid
  const trackIdRef = useRef("t0");//AI音声のトラック
  const pendingCodeRef = useRef("");//コードを一時的に保存する
  const [grammarInput,setGrammarInput] = useState('')//文法検索の入力文
  const [grammarResult,setGrammarResult] = useState<any>(null)//文法検索の解析結果
  const[pronInput,setPronInput] = useState('')//発音検索の入力文
  const[pronSpeed,setPronSpeed] = useState(1)//読み上げ速度
 
//== 確定ボタンを押したら初期設定が送信される関数 ==//
  function startConversation(){
    const config = {role,situation,targetLang,explainLang,speed,watchPath};
    const ws = new WebSocket("ws://localhost:8000/realtime");
    wsRef.current = ws;                                 // 確定したらwsを保存
    ws.onopen = () =>{
      ws.send(JSON.stringify(config));
    }

    if(!playerRef.current){
      playerRef.current = new WavStreamPlayer({sampleRate:24000});//Gemini出力は24kHz
      playerRef.current.connect();//スピーカーに接続
    }
    ws.onmessage = (e) => {//メッセージが届き次第実行する
      const msg = JSON.parse(e.data);//parseは文字列をオブジェクトに変更する
      
      if(msg.type === "code_analysis"){//コード分析が必要な時
         setMessages(prev => [...prev,{who:"AI",text:"Code",code:msg.code}]);
      }

      if(msg.type === "response.output_audio.delta"){//AIの音声
        const buf = base64ToArrayBuffer(msg.delta);//声を音声データに戻したもの
        playerRef.current.add16BitPCM(buf,trackIdRef.current);//再生機にその音声データを渡してその場で再生する
      }

      if(msg.type === "conversation.item.input_audio_transcription.completed"){//自分の発言
        setMessages(prev => [...prev,{who:"You",text:msg.transcript,id:msg.id}]);
      }

      if(msg.type === "response.output_audio_transcript.done"){//AIの発言
       setLiveAI(msg.transcript);//随時更新表示される
      }

      if(msg.type === "response.output_audio_transcript.finish"){//AIの発言が完了したら、リアルタイムの文字起こしを履歴に保存し、リアルタイム表示をリセットする
               setMessages(prev => [...prev,{who:"AI",text:msg.transcript}]);//AIの会話履歴をコード以外保存する
       setLiveAI("");//リアルタイムの文字起こしをリセットする
      }

      if(msg.type === "grammar_feedback"){//文法チェックが必要な時
        const result = JSON.parse(msg.result);//オブジェクトにJSONを変換する
        setMessages(prev =>prev.map(m => m.id === msg.id ? {...m,grammar:result}:m));
      }

      if(msg.type === "pronunciation_feedback"){//発音チェックが必要な時
        const result = JSON.parse(msg.result);//オブジェクトにJSONを変換する
        setMessages(prev =>prev.map(m => m.id === msg.id ? {...m,pron:result}:m));
      }

      if(msg.type === "interrupted"){//割り込んだ時
        playerRef.current ?. interrupt()//correntがnullなら何もしないが、それ以外なら溜まった音声を捨てる
        trackIdRef.current = "t" + Date.now();//更新のたびに時間を更新して入力し、新しいトラックにする
        if(msg.transcript){//途中までAI音声が何かしゃべっていたら
          setMessages(prev => [...prev,{who:"AI",text:msg.transcript}]);//履歴に保存する
        }
        setLiveAI("");//リアルタイムの文字起こしをリセットする
      }
    }
  }


//==発音検索で入力文をTTSで音声で再生する関数 ==//
async function playPronunciation() {
  const res = await fetch("http://localhost:8000/pronounce",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({text:pronInput,targetLang,speed:pronSpeed}),
  })
  const blob = await res.blob()          //返ってきた音声をblobとして受け取る
  const url = URL.createObjectURL(blob)  //そのblobを再生できる一時URLに変換
  new Audio(url).play()                  //音声を再生
}

//==文法検索で入力文を解析する関数 ==//
async function searchGrammar() {
  const res = await fetch("http://localhost:8000/grammar_search",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({text:grammarInput,targetLang,explainLang}),
  })
  setGrammarResult(await res.json())
}

//==メモを送信する関数 ==//
async function saveMemo() {
  if(!memoText)return;//メモが空なら実行しない
  await fetch("http://localhost:8000/memo",{
    method:"POST",//どの操作か
    headers:{"Content-Type": "application/json"},//JSONで送ると指定
    body:JSON.stringify({text:memoText}),//送るデータ本体
  });
  setMemoText("");//メモの内容を空にする
}

//==ヒントを呼び出す関数 ==//
async function getHint() {
  const aiMessages = messages.filter(m => m.who ==="AI");
  const lastAI = aiMessages[aiMessages.length-1];//最新のAIの発言
  if(!lastAI) return;//もしまだAIの発言が無ければ返信しない
  const res = await fetch("http://localhost:8000/hint",{
    method:"POST",//どの操作か
    headers:{"Content-Type": "application/json"},//JSONで送ると指定
    body:JSON.stringify({query:lastAI.text}),//送るデータ本体
  });
  const data = await res.json();//LLMが返答するまで待つ
  shownHintsRef.current = data.hints.map((h:any) => h.text);
  setExample(data.example);
}

//==ヒント表現を更新する関数 ==//
async function recordInteraction(utterance:string){
  await fetch("http://localhost:8000/interaction",{
    method:"POST",//どの操作か
    headers:{"Content-Type": "application/json"},//JSONで送ると指定
    body:JSON.stringify({utterance,shown:shownHintsRef.current}),//送るデータ本体
  });
  shownHintsRef.current = [];//ヒントで見せた表現の内容を空にする
}


//==ダッシュボードのデータを取得する関数 ==//
async function getDashboard() {
  const res = await fetch("http://localhost:8000/dashboard");
  const data = await res.json();
  setDash(data);//ダッシュボードのデータを随時更新し変数を表示する
}

//==ダッシュボードのデータを削除する関数 ==//
async function deleteMemo(id:number) {
  await fetch("http://localhost:8000/delete",{
    method:"DELETE",//どの操作か
    headers:{"Content-Type": "application/json"},//JSONで送ると指定
    body:JSON.stringify({id}),//送るid
  });
  getDashboard();//ダッシュボードのデータを更新する
}




//==録音をする関数 ==//
async  function startRecording(){//関数内でawaitを使うため、asyncを使う
    if(!recorderRef.current){
      recorderRef.current = new WavRecorder({sampleRate:16000});//録音機が無ければ録音機を作成する
    }
      const recorder = recorderRef.current;
    if(recorder.getStatus()==="ended"){//録音機の状態が終了したいたら、録音機をスタートする
        await recorder.begin();
    }

    if(recorder.getStatus()!== "recording"){
        await recorder.record((data)=>{
          sendAudio(data.mono);//monoはチャンネル数は１本とすることを明示し、音の塊を送る
        });
    }
  }



 //==録音を停止する関数 ==//
 function stopRecording(){
    if(!recorderRef.current){
      recorderRef.current = new WavRecorder({sampleRate:16000});//録音機が無ければ録音機を作成する
    }
      const recorder = recorderRef.current;
    if(recorder&&recorder.getStatus() === "recording"){
      recorder.pause();
    }
  }

//==録音を送信する関数 ==//
function sendAudio(pcm16){
  const ws = wsRef.current;//接続(ws)を保存する箱から接続を取り出す

  const isConnected = ws && ws.readyState === WebSocket.OPEN;//接続が存在しない、または開いていないならここで終了
  if(!isConnected)return;
  const base64 = pcm16TOBase64(pcm16);//音をbase64にする

  const message = {
    type:"input_audio_buffer.append",
    audio:base64,
  };

  ws.send(JSON.stringify(message));

}

//==音をbase64にする関数 ==//
function pcm16TOBase64(buffer: ArrayBuffer){
  const bytes = new Uint8Array(buffer);//ArrayBufferをバイトの並びとして見る（.bufferは付けない）
  let binary = "";//空の文字列を用意
  for(let i = 0; i<bytes.length;i++)
    binary += String.fromCharCode(bytes[i]);//各バイトを文字にしてためる
  return btoa(binary);//文字列をbase64にして返す
}

//==base64を文字列にする関数 ==//
function base64ToArrayBuffer(base64:string){
  const binary = atob(base64);//base64を文字列に戻す
  const bytes = new Uint8Array(binary.length);
  for(let i = 0; i<bytes.length;i++)
    bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}


//== ユーザーが話したらヒントの重みを更新する項目 ==//
useEffect(() => {
  const youMessages = messages.filter(m => m.who === "You");//自分の発言のみを切り出し
  const lastYou = youMessages[youMessages.length-1];//直近の自分の発言
  if(lastYou && (lastYou.id !== lastYouRef.current)){//直近で自分の発言があり、直近の発言のIDが新しければ（新しい発言ならば）
    lastYouRef.current = lastYou.id ?? null;//lastYouRef.current を lastYou.idで更新する。もしIDがなければ少なくともnullが入る
    recordInteraction(lastYou.text); 
  }
},[messages])//新しいYou発言（messages）が増えたら動く

//== マイクの状態により、録音を送信・停止する項目 ==//
useEffect(() => {
  if(micOn) startRecording();
  else stopRecording();
},[micOn]);//micOn（マイクがON）なら動く

//== UI ==//
return(
<div>
  {view === "main" &&(//会話画面
  <div>

<input value={role} onChange = {(e) => setRole(e.target.value)} placeholder = "AIの属性"/>
<input value={situation} onChange = {(e) => setSituation(e.target.value)} placeholder = "シチュエーション"/>
<input value={watchPath} onChange = {(e) => setWatchPath(e.target.value)} placeholder = "作業・監視したいパス"/>



<label>
学習言語:
  <select value={targetLang} onChange = {(e) => setTargetLang(e.target.value)}>
    <option value = "en">英語</option>
    <option value = "ja">日本語</option>
    <option value = "ru">ロシア語</option>
  </select>
</label>

<label>
母国語:
  <select value={explainLang} onChange = {(e) => setExplainLang(e.target.value)}>
    <option value = "en">英語</option>
    <option value = "ja">日本語</option>
    <option value = "ru">ロシア語</option>
  </select>
</label>



<label>
  マイク:
  <button onClick={() => setMicOn(!micOn)}>
    {micOn ? 'ON':'OFF'}
  </button>
</label>
<button onClick={startConversation}>確定</button>
<button onClick={() => setMessages([])}>履歴を削除</button>
  <div style = {{display:"flex",flexDirection:"column",gap:"8px",width:"100%"}}>
    {messages.map((m,i) => (
    <div key={i} style={{
      alignSelf:m.who === "You"?"flex-end":"flex-start",//Youなら右寄せ（flex-start）、それ以外（AI）なら左寄せ（flex-end）
      background:m.who === "You"?"#cce5ff":"#eeeeee",//Youなら青、AIなら灰色
      maxWidth:"50%",//広がりすぎを防止する
      padding:"8px 12px",//上下8px,左右12px
      borderRadius:"12px",//角を丸く
    }}>
      {m.text}
      {m.code &&(
       <pre style={{margin:"4px 0 0",overflowX:"auto",whiteSpace:"pre-wrap",fontSize:"13px"}}>{m.code}</pre>
      )}
      {m.grammar && (
        <div style={{marginTop:"4px",fontSize:"13px"}}>
          {m.grammar.correct
          ?"文法問題無し"
        :<span>{m.grammar.corrected}<br/>{m.grammar.explanation}</span>}
        </div>
      )}
      {m.pron && (
        <div style={{marginTop:"4px",fontSize:"13px"}}>
          {(m.pron.advice && m.pron.advice.length > 0)?(
            <div>
              {m.pron.advice.map((a:any,j:number)=>(
                <div key = {j}>・{a.target}:{a.tip}</div>
              ))}
              </div>
          ):(
            "発音問題無し"
          )}
          </div>
      )}
    </div>
      ))}
    {liveAI && (<div style={{
    alignSelf:"flex-start",//左寄せ（AIなので）
    background:"#eeeeee",//AIなので灰色
    padding:"8px 12px",//上下8px,左右12px
    maxWidth:"60%",//広がりすぎを防止する
    borderRadius:"12px",//角を丸く
    }}>{liveAI}</div>)}
  </div>
  <div style ={{marginTop:"24px",borderTop:"2px solid #ccc",paddingTop:"12px"}}>
    <h3>メモ</h3>
    <input  value={memoText} onChange = {(e) => setMemoText(e.target.value)} placeholder = "メモする表現"/>
    <button onClick={saveMemo}>メモを保存</button>
    <button onClick={getHint}>ヒントを表示する</button>
    <button onClick={()=>{setView("dashboard");getDashboard();}}>進捗ダッシュボード画面を確認</button>
    <button onClick={()=>setView("grammar")}>文法発音検索</button>
    {example &&(
      <div style={{marginTop:"24px",borderTop:"2px solid #ccc",paddingTop:"12px"}}>
        <b>ヒント例文</b>
        <div>{example}</div>
      </div>
    )}
  </div>
  </div>
  )}
  {view === "dashboard" &&(//進捗ダッシュボード画面
  <div>
    <button onClick={() => setView("main")}>会話に戻る</button>
    <h2>進捗ダッシュボード</h2>
    {dash &&(//dashがまだデータが来ていない時は、まだ描写しないようにする
      <div>
        <div>習得済み:{dash.mastered_count}個</div>
        <div>学習中:{dash.learning.length}個</div>
        {dash.learning.map((it:any)=>(
          <div key = {it.id}>
            [{it.type}]{it.text}(ヒント無し成功:{it.hint_free_success})
            <button onClick = {() => deleteMemo(it.id)}>削除する</button>
          </div>
        ))}
      </div>
    )}
  </div>
  )}
  {view === "grammar" &&(
    <div>
      <button onClick={() => setView("main")}>会話に戻る</button>
      <h2>発音検索機能</h2>
       <input value={pronInput} onChange={(e)=>setPronInput(e.target.value)} placeholder="読み上げる文章"/>
       <label>
      速度 {pronSpeed}倍
      <input type="range" min={0.5} max={2} step={0.25} value={pronSpeed} onChange={(e)=>setPronSpeed(Number(e.target.value))}/>
      <button onClick={playPronunciation}>再生</button>
    </label>
      <h2>文法検索機能</h2>
      <input value={grammarInput} onChange = {(e) => setGrammarInput(e.target.value)} placeholder = "検索したい文章を入力"/>
      <button onClick = {searchGrammar}>検索</button>
      {grammarResult && grammarResult.sentences.map((s:any,i:number)=>(
        <SentenceBlock key={i} sentence={s} targetLang={targetLang} explainLang={explainLang}/>
      ))}
  </div>
  )}
</div>
)
}
export default App


