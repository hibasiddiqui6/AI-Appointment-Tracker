(function(){
  const logEl = document.getElementById('log');
  const nameEl = document.getElementById('name');
  const roomEl = document.getElementById('room');
  const startBtn = document.getElementById('startBtn');
  const leaveBtn = document.getElementById('leaveBtn');

  /** helpers */
  const log = (m)=>{ if(logEl){ logEl.textContent += m + "\n"; logEl.scrollTop = logEl.scrollHeight; } console.log(m); };
  // Backend API base (token service)
  const apiBase = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : location.origin.replace(/\/$/, '');

  let room;

  async function getToken(participantName, roomName){
    const body = {
      participant_name: participantName || 'Guest',
      room_name: roomName || 'demo',
      can_publish: true,
      can_subscribe: true,
      can_publish_data: true
    };
    const res = await fetch(apiBase + '/generate-token', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if(!res.ok){ throw new Error('Token request failed: ' + res.status); }
    return res.json();
  }

  async function createMicrophoneTrack(){
    const { createLocalAudioTrack } = LivekitClient;
    const micTrack = await createLocalAudioTrack({
      echoCancellation: true,
      noiseSuppression: false,
      autoGainControl: true,
      sampleRate: 48000,
      channelCount: 1
    });
    const s = micTrack.mediaStreamTrack.getSettings();
    log('Microphone settings: ' + JSON.stringify({ deviceId: s.deviceId, sampleRate: s.sampleRate, echoCancellation: s.echoCancellation, noiseSuppression: s.noiseSuppression, autoGainControl: s.autoGainControl }));
    return micTrack;
  }

  async function startCall(){
    startBtn.disabled = true;
    try{
      const participantName = nameEl.value || 'Guest';
      const roomName = roomEl.value || 'demo';
      log('Requesting token...');
      const t = await getToken(participantName, roomName);
      log('Connecting to LiveKit room: ' + t.livekit_url);

      room = new LivekitClient.Room();

      room.on('connected', () => { log('Room connected'); leaveBtn.disabled = false; });
      room.on('disconnected', () => { log('Room disconnected'); leaveBtn.disabled = true; startBtn.disabled = false; });
      // Listen for backend END_CALL signal (sent when silence threshold finalizes audio)
      room.on('dataReceived', async (payload, participant, kind) => {
        try{
          const text = typeof payload === 'string' ? payload : new TextDecoder().decode(payload);
          if(text === 'END_CALL'){
            log('Received END_CALL from backend; leaving room');
            await leave();
          }
        }catch(e){ /* ignore */ }
      });
      room.on('participantConnected', (p) => log('Participant connected: ' + p.identity));
      room.on('participantDisconnected', (p) => log('Participant disconnected: ' + p.identity));
      room.on('trackSubscribed', (_track, pub, p) => log('Track subscribed: ' + pub.kind + ' from ' + (p?.identity||'unknown')));

      await room.connect(t.livekit_url, t.token);
      log('Connected to room');

      const mic = await createMicrophoneTrack();
      await room.localParticipant.publishTrack(mic);
      log('Published microphone');

    }catch(e){
      log('Error: ' + (e?.message||e));
      startBtn.disabled = false;
    }
  }

  async function leave(){
    try{ if(room){ await room.disconnect(); } }catch{} finally{ leaveBtn.disabled = true; startBtn.disabled = false; }
  }

  startBtn.addEventListener('click', startCall);
  leaveBtn.addEventListener('click', leave);
})();
