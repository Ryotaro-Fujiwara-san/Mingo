import { useState, useEffect, useRef } from "react";
import { WavRecorder,WavStreamPlayer } from "wavtools";
//== 言語選択におけるオブジェクトをリストに並べたもの ==//
const LANGUAGE =[
  {code:'en',label:'英語'},
  {code:'ja',label:'日本語'},
  {code:'ru',label:'ロシア語'},
]


//== ボタンの設定を保存する項目 ==//
function App(){
  const[role,setRole] = useState('')//AIの属性を決定する。ここではテキスト入力を想定し初期状態は0にする
  const[situation,setSituation] =  useState('')//AIのシチュエーションを決定する。ここではテキスト入力を想定し初期状態は0にする
  const[targetLang,setTargetLang] = useState('en')//学習言語を設定する。初期状態は英語
  const[explainLang,setExplainLang] =  useState('ja')//説明に使用する言語を設定する。初期状態は日本語
  const[speed,setSpeed] = useState(0)//スレイダー式で速度を変更する。この時初期状態は0
  const[micOn,setMicOn] = useState(true)//マイクをオンにする。初期状態はON
  const[messages,setMessages] = useState<{who:string,text:string}[]>([]);//会話の履歴を保存
  const playerRef = useRef<WavStreamPlayer | null>(null);//再生機
  const wsRef = useRef<WebSocket | null>(null);        // 接続(ws)を保存する箱
  const recorderRef = useRef<any>(null);               // マイク録音器を保存する箱

//== 確定ボタンを押したら初期設定が送信される関数 ==//
  function startConversation(){
    const config = {role,situation,targetLang,explainLang,speed};
    const ws = new WebSocket("ws://localhost:8000/realtime");
    wsRef.current = ws;                                 // 確定したらwsを保存
    ws.onopen = () =>{
      ws.send(JSON.stringify(config));
    }

    if(!playerRef.current){
      playerRef.current = new WavStreamPlayer({sampleRate:24000});//再生機が無ければ再生機を準備
      playerRef.current.connect();//スピーカーに接続
    }
    ws.onmessage = (e) => {//メッセージが届き次第実行する
      const msg = JSON.parse(e.data);//parseは文字列をオブジェクトに変更する
      
      if(msg.type === "response.output_audio.delta"){//AIの音声
        const buf = base64ToArrayBuffer(msg.delta);//声を音声データに戻したもの
        playerRef.current.add16BitPCM(buf);//再生機にその音声データを渡してその場で再生する
      }

      if(msg.type === "conversation.item.input_audio_transcription.completed"){//自分の発言
        setMessages(prev => [...prev,{who:"You",text:msg.transcript}]);
      }

      if(msg.type === "response.output_audio_transcript.done"){//AIの発言
        setMessages(prev => [...prev,{who:"AI",text:msg.transcript}]);
      }

    }
  }
  
//==録音をする関数 ==//
async  function startRecording(){//関数内でawaitを使うため、asyncを使う
    if(!recorderRef.current){
      recorderRef.current = new WavRecorder({sampleRate:24000});//録音機が無ければ録音機を作成する
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
      recorderRef.current = new WavRecorder({sampleRate:24000});//録音機が無ければ録音機を作成する
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


//== マイクの状態により、録音を送信・停止する項目 ==//
useEffect(() => {
  if(micOn) startRecording();
  else stopRecording();
},[micOn]);

//== UI ==//
return(
  <div>

<input value={role} onChange = {(e) => setRole(e.target.value)} placeholder = "AIの属性"/>
<input value={situation} onChange = {(e) => setSituation(e.target.value)} placeholder = "シチュエーション"/>

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
  会話速度
  <input
    type = "range"
    min={-2}
    max={2}
    step={0.5}
    value={speed}
    onChange={(e) => setSpeed(Number(e.target.value))}//Numberで文字を数値に直す
    />
</label>

<label>
  マイク:
  <button onClick={() => setMicOn(!micOn)}>
    {micOn ? 'ON':'OFF'}
  </button>
</label>
<button onClick={startConversation}>確定</button>
<button onClick={() => setMessages([])}>履歴を削除</button>
<div style = {{display:"flex",flexDirection:"column",gap:"8px",maxWidth:"500px"}}>
  {messages.map((m,i) => (
    <div key={i} style={{
      alignSelf:m.who === "You"?"flex-end":"flex-start",
      background:m.who === "You"?"#cce5ff":"#eeeeee",
      padding:"8px 12px",
      borderRadius:"12px",
    }}>
      {m.text}
    </div>
    ))}
    </div>
    </div>
)
}
export default App