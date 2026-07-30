import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, 
  Volume2, 
  VolumeX, 
  AlertTriangle, 
  HelpCircle, 
  FileText, 
  Settings, 
  Mic, 
  Square,
  Play,
  RotateCcw,
  CheckCircle,
  Activity
} from 'lucide-react';

// Preset profiles configuration
const PROFILE_PRESETS = [
  { id: 'general_adult', label: 'General Adult', desc: 'Plain language baseline, clear & balanced.', icon: 'standard' },
  { id: 'child', label: 'Child / Age-Appropriate', desc: 'Simple vocabulary, friendly framing, low density.', icon: 'child' },
  { id: 'anxious', label: 'Anxious / Low Load', desc: 'Reassuring, high safety, clear QA structure.', icon: 'anxiety' },
  { id: 'dyslexia_friendly', label: 'Dyslexia-Friendly', desc: 'Highly structured checklists, clean styling.', icon: 'dyslexia' },
  { id: 'caregiver', label: 'Caregiver / Family', desc: 'Action-oriented practical instructions.', icon: 'caregiver' },
  { id: 'clinician', label: 'Clinician / Expert', desc: 'Preserves technical precision and findings.', icon: 'expert' }
];

export default function App() {
  const [content, setContent] = useState('');
  const [selectedProfile, setSelectedProfile] = useState('general_adult');
  const [customProfile, setCustomProfile] = useState(false);
  const [role, setRole] = useState('general_adult');
  const [needs, setNeeds] = useState('standard');
  const [modality, setModality] = useState('text');
  
  const [multipleProfiles, setMultipleProfiles] = useState(false);
  const [enableExternal, setEnableExternal] = useState(false);
  const [generateTTS, setGenerateTTS] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTabIdx, setActiveTabIdx] = useState(0);
  
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [logs, setLogs] = useState('');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioEl, setAudioEl] = useState(null);
  
  const [urlInput, setUrlInput] = useState('');
  const [voiceNarration, setVoiceNarration] = useState('');
  const [isRecordingNarration, setIsRecordingNarration] = useState(false);
  const [voiceAssistant, setVoiceAssistant] = useState(false);

  const speakText = (text) => {
    if (!voiceAssistant) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
  };

  // STT / Recording State
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const audioChunks = useRef([]);
  
  // Physics simulation for Network Graph
  const svgRef = useRef(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [draggedNode, setDraggedNode] = useState(null);
  
  // API host determination (works inside docker, local dev, or custom env)
  const API_HOST = import.meta.env.VITE_API_URL || 
    (window.location.origin.includes('localhost:3000') ? 'http://localhost:8000' : '');

  const [isWakingUp, setIsWakingUp] = useState(true);
  const [wakeUpMessage, setWakeUpMessage] = useState('Connecting to backend services...');

  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_HOST}/api/v1/health`);
        if (res.ok) {
          if (active) {
            setIsWakingUp(false);
          }
        } else {
          throw new Error('Not ready');
        }
      } catch (e) {
        if (active) {
          setWakeUpMessage('Server is asleep (Render free tier cold start takes ~50s). Waking it up...');
          setTimeout(checkHealth, 3000);
        }
      }
    };
    checkHealth();
    return () => {
      active = false;
    };
  }, []);

  // Standard preset sample documents
  const loadSampleDoc = (type) => {
    if (type === 'admin') {
      setContent(
        "IMPORTANT NOTICE TO ALL TENANTS: ANNUAL SAFETY STANDARDS REGULATION UPDATE\n\n" +
        "Please be advised that pursuant to City Municipal Ordinance § 402.19, all residents are hereby required to grant access to authorized safety personnel for the purpose of the mandatory annual smoke detector and fire sprinkler integrity assessment. Said inspections are scheduled to commence on August 15, 2026, and will proceed continuously through August 22, 2026, during the standard operating hours of 9:00 AM to 5:00 PM.\n\n" +
        "Tenant presence is not strictly required if a written key-entry consent waiver is executed and submitted to the leasing office no later than 48 hours prior to the scheduled date. Failure to provide access or submit said waiver shall constitute a material breach of the lease agreement, and may result in the assessment of a non-compliance penalty fine of $150.00, or in extreme cases, the initiation of eviction proceedings. Please contact the leasing office manager at 555-0192 or safety@meridianapartments.com for scheduling adjustments. Do not leave keys under mats."
      );
    } else if (type === 'medical') {
      setContent(
        "CLINICAL DISCHARGE AND POST-OPERATIVE CARE DIRECTIVE\n\n" +
        "Patient: John Doe. Date of Procedure: July 30, 2026. Intervention: Laparoscopic Appendectomy.\n\n" +
        "Following discharge, the patient must strictly adhere to the following post-surgical recovery protocol. Physical activity is limited: do not lift objects exceeding 10 pounds (4.5 kg) for a minimum duration of 14 days post-discharge. The surgical incisions must be kept clean, dry, and intact. Showering is permitted after 48 hours; however, active scrubbing of the steri-strips is contraindicated, and bathing/immersion in water is prohibited until complete incisional closure is verified at the follow-up appointment.\n\n" +
        "Pharmacological management: Take Ibuprofen 400mg every 6 hours orally as needed for moderate discomfort. For severe, breakthrough pain, a prescription for Oxycodone-Acetaminophen (5/325mg) has been transmitted to your designated pharmacy; take 1 tablet every 4-6 hours only if necessary. Avoid driving or operating machinery while taking Oxycodone.\n\n" +
        "Vigilance for complications is required. The caregiver must monitor for and report the immediate onset of any of the following symptoms: pyrexia (fever exceeding 101°F / 38.3°C), persistent nausea or emesis, exacerbation of abdominal pain despite medication compliance, or purulent drainage/erythema surrounding the incision sites. Follow-up is scheduled with Dr. Sarah Smith on August 7, 2026, at 10:30 AM at the Surgical Suite."
      );
    }
  };

  // Run the adaptation pipeline
  const handleAdapt = async () => {
    if (!content.trim()) return;
    setLoading(true);
    setResult(null);
    setLogs('');
    setGraphData({ nodes: [], edges: [] });
    
    // Stop any playing audio
    if (audioEl) {
      audioEl.pause();
      setIsPlayingAudio(false);
    }

    const payload = {
      content: content,
      audience_profile: customProfile ? {
        role: role,
        domain_familiarity: "novice",
        cognitive_access_needs: needs,
        preferred_language: "en",
        modality: modality
      } : null,
      voice_narration: voiceNarration || null,
      options: {
        generate_multiple_profiles: multipleProfiles,
        profiles: multipleProfiles ? ['general_adult', 'anxious', 'child', 'clinician'] : [selectedProfile],
        include_fidelity_note: true,
        language: "en",
        enable_external_lookup: enableExternal,
        tts_output: generateTTS || !!voiceNarration
      }
    };
    
    // If not custom profile and not multiple, pass single profile dict
    if (!customProfile && !multipleProfiles) {
      const preset = PROFILE_PRESETS.find(p => p.id === selectedProfile);
      payload.audience_profile = {
        role: preset.id,
        domain_familiarity: preset.id === 'clinician' ? 'expert' : 'novice',
        cognitive_access_needs: preset.id === 'anxious' ? 'anxiety_aware' : (preset.id === 'dyslexia_friendly' ? 'dyslexia_friendly' : (preset.id === 'child' ? 'child_appropriate' : 'standard')),
        preferred_language: 'en',
        modality: preset.id === 'dyslexia_friendly' ? 'highly_structured' : 'text'
      };
    }

    try {
      const res = await fetch(`${API_HOST}/api/v1/adapt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult(data);
      setActiveTabIdx(0);
      
      // Fetch logs and graph
      fetchLogs(data.run_id);
      fetchGraph(data.run_id);
      
    } catch (err) {
      console.error(err);
      alert(`Adaptation pipeline failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Fetch execution logs
  const fetchLogs = async (runId) => {
    try {
      const res = await fetch(`${API_HOST}/api/v1/runs/${runId}/logs`);
      if (res.ok) {
        const text = await res.text();
        setLogs(text);
      }
    } catch (e) {
      console.error("Failed to load logs", e);
    }
  };

  // Fetch Neo4j graph data
  const fetchGraph = async (runId) => {
    try {
      const res = await fetch(`${API_HOST}/api/v1/runs/${runId}/graph`);
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
        
        // Initialize nodes for force simulation
        const initialNodes = data.nodes.map((node, i) => {
          const angle = (i / data.nodes.length) * 2 * Math.PI;
          return {
            ...node,
            x: 200 + 120 * Math.cos(angle),
            y: 200 + 120 * Math.sin(angle),
            vx: 0,
            vy: 0
          };
        });
        
        setNodes(initialNodes);
        setEdges(data.edges);
      }
    } catch (e) {
      console.error("Failed to load graph", e);
    }
  };

  // Drag handlers for the network graph
  const handleMouseDown = (nodeIndex, e) => {
    e.preventDefault();
    setDraggedNode(nodeIndex);
  };

  const handleMouseMove = (e) => {
    if (draggedNode === null || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    setNodes(prev => prev.map((node, idx) => {
      if (idx === draggedNode) {
        return { ...node, x: mouseX, y: mouseY, vx: 0, vy: 0 };
      }
      return node;
    }));
  };

  const handleMouseUp = () => {
    setDraggedNode(null);
  };

  // Simple spring-physics integration loop
  useEffect(() => {
    if (nodes.length === 0 || draggedNode !== null) return;
    
    let active = true;
    const tick = () => {
      if (!active) return;
      
      const k_spring = 0.04; // Edge attraction force
      const d_rest = 90;     // Rest length of spring
      const k_repel = 400;   // Repulsion charge between nodes
      const k_center = 0.02; // Pull to center
      const damping = 0.85;   // Velocity damping
      
      setNodes(prevNodes => {
        const updated = prevNodes.map(n => ({ ...n, fx: 0, fy: 0 }));
        
        // 1. Charge repulsion (all pairs)
        for (let i = 0; i < updated.length; i++) {
          for (let j = i + 1; j < updated.length; j++) {
            const dx = updated[j].x - updated[i].x;
            const dy = updated[j].y - updated[i].y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
            if (dist < 250) {
              const force = k_repel / (dist * dist);
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;
              
              updated[i].fx -= fx;
              updated[i].fy -= fy;
              updated[j].fx += fx;
              updated[j].fy += fy;
            }
          }
        }
        
        // 2. Spring attraction (connected nodes)
        edges.forEach(edge => {
          const sIdx = updated.findIndex(n => n.id === edge.from);
          const tIdx = updated.findIndex(n => n.id === edge.to);
          if (sIdx !== -1 && tIdx !== -1) {
            const dx = updated[tIdx].x - updated[sIdx].x;
            const dy = updated[tIdx].y - updated[sIdx].y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
            const displacement = dist - d_rest;
            const force = displacement * k_spring;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            
            updated[sIdx].fx += fx;
            updated[sIdx].fy += fy;
            updated[tIdx].fx -= fx;
            updated[tIdx].fy -= fy;
          }
        });
        
        // 3. Gravity center pull + Apply forces
        return updated.map(node => {
          const centerPullX = (200 - node.x) * k_center;
          const centerPullY = (200 - node.y) * k_center;
          
          const vx = (node.vx + node.fx + centerPullX) * damping;
          const vy = (node.vy + node.fy + centerPullY) * damping;
          
          // Clamp bounds
          let x = node.x + vx;
          let y = node.y + vy;
          x = Math.max(25, Math.min(375, x));
          y = Math.max(25, Math.min(375, y));
          
          return { ...node, x, y, vx, vy };
        });
      });
      
      requestAnimationFrame(tick);
    };
    
    const animId = requestAnimationFrame(tick);
    return () => {
      active = false;
      cancelAnimationFrame(animId);
    };
  }, [nodes.length, edges, draggedNode]);

  // STT recording handler
  const startRecording = async () => {
    if (!navigator.mediaDevices) {
      alert("Microphone recording not supported on this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunks.current = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };
      
      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('file', audioBlob, 'record.wav');
        
        setLoading(true);
        try {
          const res = await fetch(`${API_HOST}/api/v1/transcribe`, {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (data.text) {
            setContent(prev => (prev ? prev + "\n" + data.text : data.text));
          }
        } catch (e) {
          console.error(e);
          alert("Transcription failed.");
        } finally {
          setLoading(false);
        }
      };
      
      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (err) {
      console.error(err);
      alert("Failed to access microphone.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const startRecordingNarration = async () => {
    if (!navigator.mediaDevices) {
      alert("Microphone recording not supported on this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunks.current = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };
      
      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('file', audioBlob, 'narration.wav');
        
        setLoading(true);
        try {
          const res = await fetch(`${API_HOST}/api/v1/transcribe`, {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (data.text) {
            setVoiceNarration(data.text);
            speakText("Accessibility profile registered: " + data.text);
          }
        } catch (e) {
          console.error(e);
          alert("Transcription failed.");
        } finally {
          setLoading(false);
        }
      };
      
      recorder.start();
      setMediaRecorder(recorder);
      setIsRecordingNarration(true);
    } catch (err) {
      console.error(err);
      alert("Failed to access microphone.");
    }
  };

  const stopRecordingNarration = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecordingNarration(false);
    }
  };

  const handleFetchUrl = async () => {
    if (!urlInput.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_HOST}/api/v1/fetch-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput })
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (data.text) {
        setContent(data.text);
        speakText("Fetched document content successfully.");
      }
    } catch (e) {
      console.error(e);
      alert("Failed to fetch URL content.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    
    setLoading(true);
    try {
      const res = await fetch(`${API_HOST}/api/v1/upload-file`, {
        method: 'POST',
        body: formData
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (data.text) {
        setContent(data.text);
        speakText("Uploaded and parsed " + file.name + " successfully.");
      }
    } catch (e) {
      console.error(e);
      alert("Failed to upload and parse file.");
    } finally {
      setLoading(false);
    }
  };

  // Play audio version
  const playAudio = (url) => {
    if (isPlayingAudio && audioEl) {
      audioEl.pause();
      setIsPlayingAudio(false);
      return;
    }
    
    const audioUrl = `${API_HOST}${url}`;
    const audio = new Audio(audioUrl);
    audio.onended = () => setIsPlayingAudio(false);
    audio.play();
    setAudioEl(audio);
    setIsPlayingAudio(true);
  };

  // Node Color Helper
  const getNodeColor = (type) => {
    const map = {
      Claim: 'var(--color-claim)',
      Obligation: 'var(--color-obligation)',
      Right: 'var(--color-right)',
      Condition: 'var(--color-condition)',
      Action: 'var(--color-action)',
      Deadline: 'var(--color-deadline)',
      Gap: 'var(--color-gap)'
    };
    return map[type] || 'gray';
  };

  if (isWakingUp) {
    return (
      <div className="spinner-container" style={{ height: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
        <Shield style={{ color: 'var(--secondary-accent)', width: '60px', height: '60px', animation: 'pulse 1.5s infinite' }} size={48} />
        <div className="spinner" style={{ marginTop: '1.5rem' }}></div>
        <p className="loading-text" style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.95rem' }}>
          {wakeUpMessage}
        </p>
      </div>
    );
  }

  return (
    <div className="container">
      {/* Header */}
      <header className="app-header">
        <div className="brand">
          <Shield style={{ color: 'var(--secondary-accent)' }} size={32} />
          <div>
            <h1>Project Meridian</h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Faithful Semantic Adaptation & Audit Graph</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button 
            className={`btn ${voiceAssistant ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
            onClick={() => { setVoiceAssistant(!voiceAssistant); speakText("Voice Assistant Activated. Focus or hover on elements to read aloud."); }}
          >
            {voiceAssistant ? <Volume2 size={14} /> : <VolumeX size={14} />}
            {voiceAssistant ? "Voice Assistant On" : "Voice Assistant Off"}
          </button>
          <div className="system-badge">Production-Shaped System</div>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="layout-grid">
        {/* Left Input Panel */}
        <section className="panel glass">
          <h2>
            <FileText size={20} />
            Source Document
          </h2>

          {/* Voice Command Accessibility Card for Blind or Illiterate Users */}
          <div className="glass" style={{ padding: '1rem', border: '1px solid var(--primary-accent)', background: 'var(--primary-glow)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <h3 style={{ fontSize: '0.9rem', color: 'var(--secondary-accent)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Mic size={16} />
              Voice-Command Accessibility (For Blind or Illiterate Users)
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Click to speak who you are and what you need (e.g. "I am an anxious patient, read this notice to me").
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              {isRecordingNarration ? (
                <button className="btn btn-primary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }} onClick={stopRecordingNarration} onMouseEnter={() => speakText("Stop recording profile narration")}>
                  <Square size={12} /> Stop Recording
                </button>
              ) : (
                <button className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }} onClick={startRecordingNarration} onMouseEnter={() => speakText("Start recording profile narration")}>
                  <Mic size={12} /> Record My Profile
                </button>
              )}
              {voiceNarration && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-main)', flex: 1, padding: '0.3rem 0.5rem', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                  <strong>Narration:</strong> "{voiceNarration.slice(0, 45)}..."
                </div>
              )}
            </div>
          </div>
          
          <div className="form-group">
            <label onMouseEnter={() => speakText("Load Presets for Testing")}>Load Presets for Testing:</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }} onClick={() => loadSampleDoc('admin')} onMouseEnter={() => speakText("Button: Load Administrative Notice")}>Administrative Notice</button>
              <button className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }} onClick={() => loadSampleDoc('medical')} onMouseEnter={() => speakText("Button: Load Medical Discharge")}>Medical Discharge</button>
            </div>
          </div>

          {/* URL & File Upload Input Section */}
          <div style={{ display: 'flex', gap: '0.5rem', flexDirection: 'column' }}>
            <label style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Or Fetch Document Content:</label>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr', gap: '0.5rem', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '0.25rem', width: '100%' }}>
                <input 
                  type="text" 
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="Paste site/form URL link..."
                  style={{ flex: 1, padding: '0.5rem', background: '#0a0e1a', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', outline: 'none', fontSize: '0.85rem' }}
                />
                <button className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }} onClick={handleFetchUrl} onMouseEnter={() => speakText("Fetch content from URL")}>
                  Fetch
                </button>
              </div>
              <label className="btn btn-secondary" style={{ padding: '0.45rem', margin: 0, textAlign: 'center', cursor: 'pointer', fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }} onMouseEnter={() => speakText("Upload HTML or text document file")}>
                <FileText size={12} /> Upload File
                <input type="file" accept=".html,.htm,.txt" style={{ display: 'none' }} onChange={handleFileUpload} />
              </label>
            </div>
          </div>

          <div className="form-group" style={{ position: 'relative' }}>
            <label htmlFor="source-text" onMouseEnter={() => speakText("Source document input text. Currently has " + content.length + " characters.")}>Paste Source Content (HTML/Plain Text):</label>
            <textarea 
              id="source-text"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste contracts, forms, instructions, notices, etc..."
              onMouseEnter={() => speakText("Document text box. Paste here.")}
            />
            
            {/* STT trigger button */}
            <div style={{ position: 'absolute', bottom: '15px', right: '15px', zIndex: 10 }}>
              {isRecording ? (
                <button className="btn btn-primary" style={{ padding: '0.5rem', borderRadius: '50%' }} onClick={stopRecording} onMouseEnter={() => speakText("Stop voice dictation")}>
                  <Square size={16} />
                </button>
              ) : (
                <button className="btn btn-secondary" style={{ padding: '0.5rem', borderRadius: '50%' }} onClick={startRecording} onMouseEnter={() => speakText("Start voice dictation")}>
                  <Mic size={16} />
                </button>
              )}
            </div>
          </div>
          
          {isRecording && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'hsl(350, 80%, 55%)', fontSize: '0.875rem' }}>
              <div className="pulse-recording"></div>
              Recording... Speak now.
            </div>
          )}

          {/* Profile selector */}
          <div className="form-group">
            <label onMouseEnter={() => speakText("Adaptation Target Profile Preset. Choose the target audience profile.")}>Adaptation Target Profile Preset:</label>
            <div className="presets-grid">
              {PROFILE_PRESETS.map((preset) => (
                <button 
                  key={preset.id}
                  className={`preset-card ${selectedProfile === preset.id && !customProfile ? 'active' : ''}`}
                  onClick={() => { setSelectedProfile(preset.id); setCustomProfile(false); }}
                  onMouseEnter={() => speakText(`Preset option: ${preset.label}. Description: ${preset.desc}`)}
                >
                  <h3>{preset.label}</h3>
                  <p>{preset.desc}</p>
                </button>
              ))}
            </div>
          </div>
          
          {/* Options */}
          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }} onMouseEnter={() => speakText("Custom profile override settings")}>
              <Settings size={14} /> Custom Profile Overrides:
              <input 
                type="checkbox" 
                checked={customProfile} 
                onChange={(e) => setCustomProfile(e.target.checked)} 
                style={{ marginLeft: 'auto' }}
              />
            </label>
            
            {customProfile && (
              <div className="glass" style={{ padding: '1rem', marginTop: '0.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label onMouseEnter={() => speakText("Custom role dropdown")}>Role</label>
                  <select value={role} onChange={(e) => setRole(e.target.value)} style={{ padding: '0.5rem', background: '#0a0e1a', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px' }}>
                    <option value="patient">Patient</option>
                    <option value="caregiver">Caregiver</option>
                    <option value="clinician">Clinician</option>
                    <option value="child">Child</option>
                    <option value="general_adult">General Adult</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label onMouseEnter={() => speakText("Custom cognitive access needs dropdown")}>Access Needs</label>
                  <select value={needs} onChange={(e) => setNeeds(e.target.value)} style={{ padding: '0.5rem', background: '#0a0e1a', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px' }}>
                    <option value="standard">Standard</option>
                    <option value="low_cognitive_load">Low Cognitive Load</option>
                    <option value="dyslexia_friendly">Dyslexia Friendly</option>
                    <option value="anxiety_aware">Anxiety Aware</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          <div className="row-controls">
            <label className="checkbox-label" onMouseEnter={() => speakText("Checkbox: Generate 4 Presets simultaneously")}>
              <input 
                type="checkbox" 
                checked={multipleProfiles}
                onChange={(e) => setMultipleProfiles(e.target.checked)}
              />
              Generate 4 Presets Simultaneously
            </label>

            <label className="checkbox-label" onMouseEnter={() => speakText("Checkbox: Enable external search lookups")}>
              <input 
                type="checkbox" 
                checked={enableExternal}
                onChange={(e) => setEnableExternal(e.target.checked)}
              />
              Enable Tavily Web Lookups
            </label>
            
            <label className="checkbox-label" onMouseEnter={() => speakText("Checkbox: Generate audio version")}>
              <input 
                type="checkbox" 
                checked={generateTTS}
                onChange={(e) => setGenerateTTS(e.target.checked)}
              />
              Generate Audio Version (TTS)
            </label>
          </div>

          <button 
            className="btn btn-primary" 
            onClick={handleAdapt} 
            disabled={loading || !content.trim()}
            onMouseEnter={() => speakText("Generate adaptation button. Click to run the pipeline.")}
          >
            {loading ? 'Processing Pipeline...' : 'Generate Compliant Adaptation'}
          </button>
        </section>

        {/* Right Output Panel */}
        <section className="panel glass" style={{ minHeight: '600px' }}>
          <h2>
            <Activity size={20} />
            Compliant Adaptation Engine Output
          </h2>

          {loading && (
            <div className="spinner-container">
              <div className="spinner"></div>
              <p className="loading-text">Semantic Graphs being mapped in Neo4j, running verifier checks...</p>
            </div>
          )}

          {!loading && !result && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '350px', color: 'var(--text-muted)' }}>
              <Shield size={48} style={{ strokeWidth: 1, marginBottom: '1rem', color: 'var(--border-color)' }} />
              <p>Load a sample and trigger the adaptation model.</p>
            </div>
          )}

          {!loading && result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              
              {/* Badges of domain awareness */}
              <div className="badges-row">
                <span className="badge badge-domain">Domain: {result.domain}</span>
                <span className="badge badge-type">Doc Type: {result.document_type}</span>
                <span className="badge badge-risk">Risk: {result.risk_level}</span>
                <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)' }}>Fidelity Verified</span>
              </div>

              {/* Version Tabs selector */}
              {result.versions && result.versions.length > 1 && (
                <div className="tabs-container">
                  {result.versions.map((v, i) => (
                    <button 
                      key={v.profile} 
                      className={`tab ${activeTabIdx === i ? 'active' : ''}`}
                      onClick={() => setActiveTabIdx(i)}
                    >
                      {v.profile.replace('_', ' ').toUpperCase()}
                    </button>
                  ))}
                </div>
              )}

              {/* Active Version details */}
              {result.versions && result.versions[activeTabIdx] && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  
                  {/* Strategy Summary */}
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', padding: '0.5rem 1rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                    <strong>Adaptation Strategy:</strong> {result.versions[activeTabIdx].strategy_summary}
                  </div>

                  {/* Audio Controls */}
                  {result.versions[activeTabIdx].audio_url && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <button className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }} onClick={() => playAudio(result.versions[activeTabIdx].audio_url)}>
                        {isPlayingAudio ? <VolumeX size={14} /> : <Play size={14} />}
                        {isPlayingAudio ? 'Pause Speech' : 'Listen Aloud'}
                      </button>
                    </div>
                  )}

                  {/* Adapted Content */}
                  <div className="adapted-viewport">
                    {result.versions[activeTabIdx].adapted_content}
                  </div>

                  {/* Gaps Panel */}
                  {result.versions[activeTabIdx].gaps && result.versions[activeTabIdx].gaps.length > 0 && (
                    <div className="gaps-panel">
                      <h3>
                        <AlertTriangle size={16} style={{ display: 'inline', marginRight: '0.25rem', verticalAlign: 'text-bottom' }} />
                        Gaps & Uncertainties in Source Document
                      </h3>
                      <ul>
                        {result.versions[activeTabIdx].gaps.map((gap, i) => (
                          <li key={i}>{gap}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Optional Explanations (Grounding contexts) */}
                  {result.versions[activeTabIdx].explanations && (
                    <div className="explanations-section">
                      <h3>
                        <HelpCircle size={16} />
                        Definitions & Terminology Grounding
                      </h3>
                      <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', whiteSpace: 'pre-wrap' }}>
                        {result.versions[activeTabIdx].explanations}
                      </div>
                    </div>
                  )}

                  {/* Verifier compliance note */}
                  {result.versions[activeTabIdx].fidelity_note && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#34d399', fontSize: '0.8rem' }}>
                      <CheckCircle size={14} />
                      {result.versions[activeTabIdx].fidelity_note}
                    </div>
                  )}
                </div>
              )}

              {/* Neo4j extracted graph view */}
              {nodes.length > 0 && (
                <div>
                  <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Extracted Meaning Graph (Live Sandbox - Drag Nodes)</h3>
                  <div className="graph-container">
                    <span className="graph-instruction">Interactive Sandbox: Drag nodes to position</span>
                    <div className="legend">
                      <div className="legend-item"><div className="legend-color" style={{ background: 'var(--color-claim)' }}></div>Claim</div>
                      <div className="legend-item"><div className="legend-color" style={{ background: 'var(--color-obligation)' }}></div>Obligation</div>
                      <div className="legend-item"><div className="legend-color" style={{ background: 'var(--color-right)' }}></div>Right</div>
                      <div className="legend-item"><div className="legend-color" style={{ background: 'var(--color-condition)' }}></div>Condition</div>
                      <div className="legend-item"><div className="legend-color" style={{ background: 'var(--color-action)' }}></div>Action</div>
                      <div className="legend-item"><div className="legend-color" style={{ background: 'var(--color-deadline)' }}></div>Deadline</div>
                      <div className="legend-item"><div className="legend-color" style={{ background: 'var(--color-gap)' }}></div>Gap</div>
                    </div>
                    <svg 
                      ref={svgRef} 
                      width="100%" 
                      height="100%" 
                      viewBox="0 0 400 400" 
                      onMouseMove={handleMouseMove} 
                      onMouseUp={handleMouseUp}
                      onMouseLeave={handleMouseUp}
                    >
                      {/* Draw Links */}
                      {edges.map((edge, i) => {
                        const sourceNode = nodes.find(n => n.id === edge.from);
                        const targetNode = nodes.find(n => n.id === edge.to);
                        if (!sourceNode || !targetNode) return null;
                        return (
                          <line 
                            key={i} 
                            x1={sourceNode.x} 
                            y1={sourceNode.y} 
                            x2={targetNode.x} 
                            y2={targetNode.y} 
                            stroke="rgba(255,255,255,0.15)" 
                            strokeWidth="1.5" 
                            markerEnd="url(#arrow)"
                          />
                        );
                      })}
                      
                      {/* Draw Nodes */}
                      {nodes.map((node, i) => (
                        <g 
                          key={node.id} 
                          transform={`translate(${node.x},${node.y})`}
                          onMouseDown={(e) => handleMouseDown(i, e)}
                          style={{ cursor: 'grab' }}
                        >
                          <circle 
                            r="12" 
                            fill={getNodeColor(node.type)} 
                            stroke="#fff" 
                            strokeWidth="1.5" 
                            boxShadow="0 0 10px rgba(255,255,255,0.5)"
                          />
                          <text 
                            y="-18" 
                            textAnchor="middle" 
                            fill="#fff" 
                            fontSize="8" 
                            fontWeight="bold"
                            style={{ pointerEvents: 'none', background: 'black' }}
                          >
                            {node.id}
                          </text>
                          <title>{`${node.type}: ${node.text}`}</title>
                        </g>
                      ))}
                    </svg>
                  </div>
                </div>
              )}

              {/* Log stream browser */}
              {logs && (
                <div>
                  <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Fidelity Audit & Agent logs (logs/agent_run_{result.run_id}.md)</h3>
                  <div className="log-browser">
                    {logs}
                  </div>
                </div>
              )}
              
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
