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

const TRANSLATIONS = {
  en: {
    title: "IntelliX",
    subtitle: "Faithful Semantic Adaptation & Audit Graph",
    sourceDoc: "Source Document",
    presets: "Load Presets for Testing:",
    pasteLabel: "Paste Source Content (HTML/Plain Text):",
    fetchLabel: "Or Fetch Document Content:",
    urlPlaceholder: "Paste site/form URL link...",
    fetchBtn: "Fetch",
    uploadBtn: "Upload File",
    presetsTitle: "Adaptation Target Profile Preset:",
    customOverrides: "Custom Profile Overrides:",
    roleLabel: "Role",
    needsLabel: "Access Needs",
    generateBtn: "Generate Compliant Adaptation",
    processing: "Processing Pipeline...",
    wakingUp: "Connecting to backend services...",
    wakingUpDetail: "Server is asleep (Render free tier cold start takes ~50s). Waking it up...",
    voiceAssistant: "Voice Assistant On",
    voiceAssistantOff: "Voice Assistant Off",
    voiceControlTitle: "Voice Assistant & Controller",
    voiceControlDesc: "Click the mic and speak to control or translate the app.",
    voiceControlPrompt: "Voice Control / command",
    detectedLangModal: "Language Change Detected",
    detectedLangPrompt: "We detected you spoke in {lang}. Would you like to translate the application interface to {lang}?",
    yes: "Yes, Translate",
    no: "No, Keep English",
    listenBtn: "Read Aloud",
    stopBtn: "Stop Speaking",
    outputTitle: "Fidelity Adaptation Result",
    tabAdapted: "Adapted Content",
    tabFidelity: "Fidelity Report",
    tabLogs: "Execution Audit Logs",
    tabGraph: "Interactive Graph",
    riskLevel: "Risk Level",
    domain: "Domain",
    gapsTitle: "Gaps & Uncertainties"
  },
  hi: {
    title: "प्रोजेक्ट मेरिडियन",
    subtitle: "सटीक अर्थ प्रतिपादन और ऑडिट ग्राफ",
    sourceDoc: "स्रोत दस्तावेज़",
    presets: "जांच के लिए सैंपल लोड करें:",
    pasteLabel: "स्रोत सामग्री पेस्ट करें (HTML/सादा पाठ):",
    fetchLabel: "या दस्तावेज़ सामग्री प्राप्त करें:",
    urlPlaceholder: "वेबसाइट या फॉर्म का लिंक पेस्ट करें...",
    fetchBtn: "प्राप्त करें",
    uploadBtn: "फ़ाइल अपलोड करें",
    presetsTitle: "अनुकूलन लक्ष्य प्रोफ़ाइलPreset:",
    customOverrides: "कस्टम प्रोफ़ाइल ओवरराइड:",
    roleLabel: "भूमिका",
    needsLabel: "पहुंच आवश्यकताएं",
    generateBtn: "अनुकूलित अनुवाद बनाएं",
    processing: "प्रसंस्करण चल रहा है...",
    wakingUp: "बैकएंड सेवाओं से जुड़ रहा है...",
    wakingUpDetail: "सर्वर बंद है (रेंडर शुरू होने में ~50s लग सकते हैं)...",
    voiceAssistant: "आवाज़ सहायक चालू",
    voiceAssistantOff: "आवाज़ सहायक बंद",
    voiceControlTitle: "आवाज सहायक और नियंत्रक",
    voiceControlDesc: "ऐप को नियंत्रित करने या अनुवाद करने के लिए माइक दबाकर बोलें।",
    voiceControlPrompt: "आवाज़ नियंत्रण / आदेश",
    detectedLangModal: "भाषा परिवर्तन का पता चला",
    detectedLangPrompt: "हमें पता चला कि आपने {lang} में बात की। क्या आप स्क्रीन की भाषा बदलकर {lang} करना चाहते हैं?",
    yes: "हां, बदलें",
    no: "नहीं, अंग्रेजी रखें",
    listenBtn: "सुनें (बोलकर पढ़ें)",
    stopBtn: "बोलना बंद करें",
    outputTitle: "सटीकता अनुकूलन परिणाम",
    tabAdapted: "अनुकूलित सामग्री",
    tabFidelity: "विश्वसनीयता रिपोर्ट",
    tabLogs: "ऑडिट लॉग्स",
    tabGraph: "इंटरैक्टिव ग्राफ",
    riskLevel: "जोखिम स्तर",
    domain: "कार्यक्षेत्र",
    gapsTitle: "कमियां और अनिश्चितताएं"
  },
  es: {
    title: "IntelliX",
    subtitle: "Adaptación Semántica y Gráfico de Auditoría",
    sourceDoc: "Documento de Origen",
    presets: "Cargar muestras de prueba:",
    pasteLabel: "Pegar contenido de origen (HTML/Texto plano):",
    fetchLabel: "O descargar contenido de URL:",
    urlPlaceholder: "Pegar enlace de sitio o formulario...",
    fetchBtn: "Descargar",
    uploadBtn: "Subir archivo",
    presetsTitle: "Perfil de audiencia objetivo:",
    customOverrides: "Ajustes de perfil personalizados:",
    roleLabel: "Rol",
    needsLabel: "Necesidades de acceso",
    generateBtn: "Generar adaptación compatible",
    processing: "Procesando...",
    wakingUp: "Conectando al servidor...",
    wakingUpDetail: "El servidor está inactivo. Despertándolo...",
    voiceAssistant: "Asistente de voz activo",
    voiceAssistantOff: "Asistente de voz apagado",
    voiceControlTitle: "Asistente y control por voz",
    voiceControlDesc: "Haga clic en el micrófono y hable para controlar o traducir.",
    voiceControlPrompt: "Control de voz / comando",
    detectedLangModal: "Cambio de idioma detectado",
    detectedLangPrompt: "¿Detectamos que habla {lang}. ¿Quiere cambiar el idioma de la pantalla a {lang}?",
    yes: "Sí, traducir",
    no: "No, mantener inglés",
    listenBtn: "Escuchar",
    stopBtn: "Detener voz",
    outputTitle: "Resultado de la adaptación",
    tabAdapted: "Contenido adaptado",
    tabFidelity: "Reporte de fidelidad",
    tabLogs: "Líneas de auditoría",
    tabGraph: "Gráfico interactivo",
    riskLevel: "Nivel de riesgo",
    domain: "Dominio",
    gapsTitle: "Brechas y omisiones"
  },
  fr: {
    title: "IntelliX",
    subtitle: "Adaptation Sémantique & Graphe d'Audit",
    sourceDoc: "Document Source",
    presets: "Charger des échantillons de test:",
    pasteLabel: "Coller le contenu source (HTML/Texte brut):",
    fetchLabel: "Ou récupérer le contenu d'une URL:",
    urlPlaceholder: "Coller le lien du site ou du formulaire...",
    fetchBtn: "Récupérer",
    uploadBtn: "Téléverser un fichier",
    presetsTitle: "Profil du public cible:",
    customOverrides: "Surcharges de profil personnalisées:",
    roleLabel: "Rôle",
    needsLabel: "Besoins d'accès",
    generateBtn: "Générer l'adaptation conforme",
    processing: "Traitement en cours...",
    wakingUp: "Connexion aux services backend...",
    wakingUpDetail: "Le serveur dort. Réveil en cours...",
    voiceAssistant: "Assistant vocal activé",
    voiceAssistantOff: "Assistant vocal désactivé",
    voiceControlTitle: "Assistant vocal & Contrôleur",
    voiceControlDesc: "Cliquez sur le micro et parlez pour contrôler ou traduire.",
    voiceControlPrompt: "Contrôle vocal / commande",
    detectedLangModal: "Changement de langue détecté",
    detectedLangPrompt: "Nous avons détecté que vous parlez en {lang}. Voulez-vous changer la langue de l'écran en {lang}?",
    yes: "Oui, traduire",
    no: "Non, garder l'anglais",
    listenBtn: "Écouter",
    stopBtn: "Arrêter la lecture",
    outputTitle: "Résultat de l'adaptation conforme",
    tabAdapted: "Contenu adapté",
    tabFidelity: "Rapport de fidélité",
    tabLogs: "Log d'audit d'exécution",
    tabGraph: "Graphe interactif",
    riskLevel: "Niveau de risque",
    domain: "Domaine",
    gapsTitle: "Lacunes & Incertitudes"
  }
};


export default function App() {
  const [content, setContent] = useState('');
  const [selectedProfile, setSelectedProfile] = useState('general_adult');
  const [customProfile, setCustomProfile] = useState(false);
  const [role, setRole] = useState('general_adult');
  const [needs, setNeeds] = useState('standard');
  const [modality, setModality] = useState('text');
  
  const [multipleProfiles, setMultipleProfiles] = useState(false);
  const [enableExternal, setEnableExternal] = useState(true);
  const [generateTTS, setGenerateTTS] = useState(true);
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTabIdx, setActiveTabIdx] = useState(0);
  
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [logs, setLogs] = useState('');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioEl, setAudioEl] = useState(null);
  
  const [urlInput, setUrlInput] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [activeInputMode, setActiveInputMode] = useState('text');
  const [voiceNarration, setVoiceNarration] = useState('');
  const [isRecordingNarration, setIsRecordingNarration] = useState(false);
  const [voiceAssistant, setVoiceAssistant] = useState(true);

  const [uiLanguage, setUiLanguage] = useState('en');
  const t = (key) => {
    const dict = TRANSLATIONS[uiLanguage] || TRANSLATIONS['en'];
    return dict[key] || TRANSLATIONS['en'][key] || key;
  };

  const speakText = (text) => {
    if (!voiceAssistant) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const langLocales = {
      hi: 'hi-IN',
      bn: 'bn-IN',
      mr: 'mr-IN',
      te: 'te-IN',
      ta: 'ta-IN',
      gu: 'gu-IN',
      ur: 'ur-IN',
      kn: 'kn-IN',
      or: 'or-IN',
      ml: 'ml-IN',
      pa: 'pa-IN',
      es: 'es-ES',
      fr: 'fr-FR',
      en: 'en-US'
    };
    utterance.lang = langLocales[uiLanguage] || 'en-US';
    window.speechSynthesis.speak(utterance);
  };

  const startSilenceDetection = (stream, recorder, stopCallback) => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const SILENCE_THRESHOLD = 15;
      const SILENCE_DURATION = 1500;
      let lastSoundTime = Date.now();

      const checkAudio = () => {
        if (recorder.state !== "recording") {
          audioContext.close();
          stream.getTracks().forEach(track => track.stop());
          return;
        }

        analyser.getByteFrequencyData(dataArray);
        let maxVolume = 0;
        for (let i = 0; i < bufferLength; i++) {
          if (dataArray[i] > maxVolume) {
            maxVolume = dataArray[i];
          }
        }

        if (maxVolume > SILENCE_THRESHOLD) {
          lastSoundTime = Date.now();
        } else {
          const silenceMs = Date.now() - lastSoundTime;
          if (silenceMs > SILENCE_DURATION) {
            console.log("Silence detected. Auto-stopping recorder...");
            stopCallback();
            audioContext.close();
            stream.getTracks().forEach(track => track.stop());
            return;
          }
        }

        requestAnimationFrame(checkAudio);
      };

      checkAudio();
    } catch (e) {
      console.error("Silence detection initialization failed:", e);
    }
  };

  // Voice controller (Right Pane Mic)
  const [isRecordingVoiceControl, setIsRecordingVoiceControl] = useState(false);
  const [voiceControlFeedback, setVoiceControlFeedback] = useState('');
  const [detectedLangCode, setDetectedLangCode] = useState(null);
  const [showLangModal, setShowLangModal] = useState(false);
  const voiceControlChunks = useRef([]);
  const [voiceControlRecorder, setVoiceControlRecorder] = useState(null);

  const startRecordingVoiceControl = async () => {
    if (!navigator.mediaDevices) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      voiceControlChunks.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) voiceControlChunks.current.push(e.data);
      };
      recorder.onstop = async () => {
        const audioBlob = new Blob(voiceControlChunks.current, { type: 'audio/wav' });
        const formData = new FormData();
        const filename = uiLanguage === 'hi' || uiLanguage === 'en' ? 'command_hindi.wav' : 'command.wav';
        formData.append('file', audioBlob, filename);
        setLoading(true);
        try {
          const res = await fetch(`${API_HOST}/api/v1/transcribe`, {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (data.text) {
            setVoiceControlFeedback(data.text);
            const lang = data.language || 'en';
            
            if (lang !== 'en' && lang !== uiLanguage) {
              setUiLanguage(lang);
              const langNames = {
                hi: 'हिंदी (Hindi)',
                bn: 'বাংলা (Bengali)',
                mr: 'मराठी (Marathi)',
                te: 'తెలుగు (Telugu)',
                ta: 'தமிழ் (Tamil)',
                gu: 'ગુજરાતી (Gujarati)',
                ur: 'اردو (Urdu)',
                kn: 'ಕನ್ನಡ (Kannada)',
                or: 'ଓଡ଼ିଆ (Odia)',
                ml: 'മലയാളം (Malayalam)',
                pa: 'ਪੰਜਾਬੀ (Punjabi)',
                es: 'Español (Spanish)',
                fr: 'Français (French)'
              };
              const targetLangName = langNames[lang] || lang;
              speakText(`Detected ${targetLangName}. Translating interface and content.`);
              if (content.trim()) {
                handleAdapt(content, lang);
              }
            } else {
              handleVoiceCommand(data.text);
            }
          }
        } catch (e) {
          console.error(e);
        } finally {
          setLoading(false);
        }
      };
      recorder.start();
      setVoiceControlRecorder(recorder);
      setIsRecordingVoiceControl(true);
      speakText("Listening to voice command");
      
      startSilenceDetection(stream, recorder, () => {
        recorder.stop();
        setIsRecordingVoiceControl(false);
      });
    } catch (e) {
      console.error(e);
    }
  };

  const stopRecordingVoiceControl = () => {
    if (voiceControlRecorder) {
      voiceControlRecorder.stop();
      setIsRecordingVoiceControl(false);
    }
  };

  const handleVoiceCommand = (commandText) => {
    const txt = commandText.toLowerCase();
    if (txt.includes('read') || txt.includes('सुनो') || txt.includes('पढ़ो') || txt.includes('leer') || txt.includes('lire')) {
      if (result && result.versions && result.versions.length > 0) {
        speakText(result.versions[activeTabIdx]?.adapted_content || "No text generated");
      } else {
        speakText("No adapted text available to read.");
      }
    } else if (txt.includes('hindi') || txt.includes('हिंदी')) {
      setUiLanguage('hi');
      speakText("स्क्रीन की भाषा अब हिंदी है।");
      if (content.trim()) handleAdapt(content, 'hi');
    } else if (txt.includes('english') || txt.includes('अंग्रेजी')) {
      setUiLanguage('en');
      speakText("Screen language is now English.");
      if (content.trim()) handleAdapt(content, 'en');
    } else if (txt.includes('spanish') || txt.includes('स्पैनिश') || txt.includes('español')) {
      setUiLanguage('es');
      speakText("Idioma de pantalla cambiado a español.");
      if (content.trim()) handleAdapt(content, 'es');
    } else if (txt.includes('french') || txt.includes('फ्रेंच') || txt.includes('français')) {
      setUiLanguage('fr');
      speakText("Langue d'affichage changée en français.");
      if (content.trim()) handleAdapt(content, 'fr');
    } else {
      if (content.trim()) {
        speakText(uiLanguage === 'hi' ? "आपकी आवाज़ का अनुरोध प्राप्त हुआ, दस्तावेज़ पर काम कर रहे हैं..." : "Processing your spoken request on the document...");
        setVoiceNarration(commandText);
        handleAdapt(content, uiLanguage, selectedProfile, commandText);
      } else {
        speakText(uiLanguage === 'hi' ? "कृपया पहले दस्तावेज़ सामग्री अपलोड करें या पेस्ट करें।" : "Please upload or paste document content first.");
      }
    }
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

  // Dynamically styled viewport matching selected profile's access needs
  const getViewportStyle = () => {
    switch (selectedProfile) {
      case 'dyslexia_friendly':
        return {
          fontFamily: 'system-ui, sans-serif',
          lineHeight: '2.2',
          letterSpacing: '0.15em',
          wordSpacing: '0.3em',
          fontSize: '1.1rem',
          padding: '1.5rem',
          background: 'rgba(245, 158, 11, 0.05)',
          borderLeft: '4px solid #f59e0b',
          borderRadius: '8px',
          color: '#f3f4f6'
        };
      case 'child':
        return {
          fontSize: '1.25rem',
          lineHeight: '1.8',
          letterSpacing: '0.02em',
          color: '#e0e7ff',
          padding: '1.5rem',
          background: 'rgba(99, 102, 241, 0.05)',
          borderLeft: '4px solid #6366f1',
          borderRadius: '8px'
        };
      case 'anxious':
        return {
          fontSize: '1.05rem',
          lineHeight: '1.7',
          color: '#ecfeff',
          padding: '1.5rem',
          background: 'rgba(6, 182, 212, 0.05)',
          borderLeft: '4px solid #06b6d4',
          borderRadius: '8px'
        };
      case 'clinician':
        return {
          fontFamily: 'monospace',
          fontSize: '0.9rem',
          lineHeight: '1.5',
          color: '#e2e8f0',
          padding: '1.25rem',
          background: 'rgba(0, 0, 0, 0.25)',
          borderLeft: '4px solid #10b981',
          borderRadius: '4px'
        };
      default:
        return {
          fontSize: '0.95rem',
          lineHeight: '1.6',
          color: 'var(--text-main)',
          padding: '1rem',
          background: 'rgba(255,255,255,0.01)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px'
        };
    }
  };

  // Standard preset sample documents
  const loadSampleDoc = (type) => {
    setUploadedFileName('');
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
  const handleAdapt = async (forcedContent, targetLang, targetProfile, voiceNarrationText) => {
    const contentToUse = typeof forcedContent === 'string' ? forcedContent : content;
    if (!contentToUse.trim()) return;
    setLoading(true);
    setResult(null);
    setLogs('');
    setGraphData({ nodes: [], edges: [] });
    
    // Stop any playing audio
    if (audioEl) {
      audioEl.pause();
      setIsPlayingAudio(false);
    }

    const langToUse = targetLang || uiLanguage;
    const profileToUse = targetProfile || selectedProfile;
    const narrationToUse = voiceNarrationText || voiceNarration || null;

    const payload = {
      content: contentToUse,
      audience_profile: customProfile ? {
        role: role,
        domain_familiarity: "novice",
        cognitive_access_needs: needs,
        preferred_language: langToUse,
        modality: modality
      } : null,
      voice_narration: narrationToUse,
      options: {
        generate_multiple_profiles: multipleProfiles,
        profiles: multipleProfiles ? ['general_adult', 'anxious', 'child', 'clinician'] : [profileToUse],
        include_fidelity_note: true,
        language: langToUse,
        enable_external_lookup: enableExternal,
        tts_output: generateTTS || !!narrationToUse
      }
    };
    
    // If not custom profile and not multiple, pass single profile dict
    if (!customProfile && !multipleProfiles) {
      const preset = PROFILE_PRESETS.find(p => p.id === selectedProfile);
      payload.audience_profile = {
        role: preset.id,
        domain_familiarity: preset.id === 'clinician' ? 'expert' : 'novice',
        cognitive_access_needs: preset.id === 'anxious' ? 'anxiety_aware' : (preset.id === 'dyslexia_friendly' ? 'dyslexia_friendly' : (preset.id === 'child' ? 'child_appropriate' : 'standard')),
        preferred_language: langToUse,
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
            setContent(data.text);
            const lang = data.language || 'en';
            if (lang !== 'en' && lang !== uiLanguage) {
              setUiLanguage(lang);
            }
            speakText("Speech transcribed. Commencing adaptation.");
            await handleAdapt(data.text, lang);
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
      
      startSilenceDetection(stream, recorder, () => {
        recorder.stop();
        setIsRecording(false);
      });
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
      
      startSilenceDetection(stream, recorder, () => {
        recorder.stop();
        setIsRecordingNarration(false);
      });
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
    setUploadedFileName('');
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
        speakText("Fetched document content. Commencing adaptation.");
        await handleAdapt(data.text);
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
        setUploadedFileName(file.name);
        setContent(data.text);
        speakText("Uploaded and parsed file. Commencing adaptation.");
        await handleAdapt(data.text);
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
            <h1>{t("title")}</h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t("subtitle")}</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <select 
            value={uiLanguage} 
            onChange={(e) => { 
              const newLang = e.target.value;
              setUiLanguage(newLang); 
              speakText(newLang === 'hi' ? "भाषा बदलकर हिंदी की गई है।" : "Language changed."); 
              if (content.trim()) {
                handleAdapt(content, newLang);
              }
            }}
            style={{ 
              padding: '0.4rem 0.8rem', 
              borderRadius: '6px', 
              border: '1px solid var(--border-color)', 
              background: '#0a0e1a', 
              color: '#ffffff', 
              fontSize: '0.8rem', 
              cursor: 'pointer' 
            }}
          >
            <option value="en" style={{ background: '#0a0e1a', color: '#ffffff' }}>English</option>
            <option value="hi" style={{ background: '#0a0e1a', color: '#ffffff' }}>हिंदी (Hindi)</option>
            <option value="bn" style={{ background: '#0a0e1a', color: '#ffffff' }}>বাংলা (Bengali)</option>
            <option value="mr" style={{ background: '#0a0e1a', color: '#ffffff' }}>मराठी (Marathi)</option>
            <option value="te" style={{ background: '#0a0e1a', color: '#ffffff' }}>తెలుగు (Telugu)</option>
            <option value="ta" style={{ background: '#0a0e1a', color: '#ffffff' }}>தமிழ் (Tamil)</option>
            <option value="gu" style={{ background: '#0a0e1a', color: '#ffffff' }}>ગુજરાતી (Gujarati)</option>
            <option value="kn" style={{ background: '#0a0e1a', color: '#ffffff' }}>ಕನ್ನಡ (Kannada)</option>
            <option value="ml" style={{ background: '#0a0e1a', color: '#ffffff' }}>മലയാളം (Malayalam)</option>
            <option value="pa" style={{ background: '#0a0e1a', color: '#ffffff' }}>ਪੰਜਾਬੀ (Punjabi)</option>
            <option value="or" style={{ background: '#0a0e1a', color: '#ffffff' }}>ଓଡ଼ିଆ (Odia)</option>
            <option value="ur" style={{ background: '#0a0e1a', color: '#ffffff' }}>اردو (Urdu)</option>
            <option value="es" style={{ background: '#0a0e1a', color: '#ffffff' }}>Español (Spanish)</option>
            <option value="fr" style={{ background: '#0a0e1a', color: '#ffffff' }}>Français (French)</option>
          </select>
          <button 
            className={`btn ${voiceAssistant ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
            onClick={() => { setVoiceAssistant(!voiceAssistant); speakText("Voice Assistant Activated."); }}
          >
            {voiceAssistant ? <Volume2 size={14} /> : <VolumeX size={14} />}
            {voiceAssistant ? t("voiceAssistant") : t("voiceAssistantOff")}
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
          
          <div className="form-group">
            <label onMouseEnter={() => speakText("Load Presets for Testing")}>Load Presets for Testing:</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }} onClick={() => loadSampleDoc('admin')} onMouseEnter={() => speakText("Button: Load Administrative Notice")}>Administrative Notice</button>
              <button className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }} onClick={() => loadSampleDoc('medical')} onMouseEnter={() => speakText("Button: Load Medical Discharge")}>Medical Discharge</button>
            </div>
          </div>

          {/* Segment/Tab Switcher for Inputs (Task 2 request) */}
          <div className="tabs-container" style={{ margin: '1rem 0', display: 'flex', gap: '0.25rem', padding: '2px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
            <button 
              className={`tab ${activeInputMode === 'text' ? 'active' : ''}`}
              style={{ flex: 1, padding: '0.5rem', fontSize: '0.8rem', borderRadius: '6px' }}
              onClick={() => { setActiveInputMode('text'); speakText("Switched to Paste Text mode"); }}
            >
              {uiLanguage === 'hi' ? 'टेक्स्ट लिखें/पेस्ट करें' : 'Write / Paste Text'}
            </button>
            <button 
              className={`tab ${activeInputMode === 'url' ? 'active' : ''}`}
              style={{ flex: 1, padding: '0.5rem', fontSize: '0.8rem', borderRadius: '6px' }}
              onClick={() => { setActiveInputMode('url'); speakText("Switched to URL Fetch mode"); }}
            >
              {uiLanguage === 'hi' ? 'वेब / फॉर्म लिंक' : 'Web / Form URL Link'}
            </button>
            <button 
              className={`tab ${activeInputMode === 'file' ? 'active' : ''}`}
              style={{ flex: 1, padding: '0.5rem', fontSize: '0.8rem', borderRadius: '6px' }}
              onClick={() => { setActiveInputMode('file'); speakText("Switched to File Upload mode"); }}
            >
              {uiLanguage === 'hi' ? 'फ़ाइल अपलोड करें' : 'Upload Document File'}
            </button>
          </div>

          {activeInputMode === 'text' && (
            <div className="form-group" style={{ position: 'relative' }}>
              <label htmlFor="source-text" onMouseEnter={() => speakText("Source document input text. Currently has " + content.length + " characters.")}>
                {t("pasteLabel")}
              </label>
              <textarea 
                id="source-text"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={uiLanguage === 'hi' ? "यहां अनुबंध, फॉर्म, निर्देश, नोटिस आदि पेस्ट करें..." : "Paste contracts, forms, instructions, notices, etc..."}
                style={{ minHeight: '220px' }}
                onMouseEnter={() => speakText("Document text box. Paste here.")}
              />
            </div>
          )}

          {activeInputMode === 'url' && (
            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.5rem' }}>
              <label>{t("fetchLabel")}</label>
              <div style={{ display: 'flex', gap: '0.5rem', width: '100%' }}>
                <input 
                  type="text" 
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder={t("urlPlaceholder")}
                  style={{ flex: 1, padding: '0.6rem', background: '#0a0e1a', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', outline: 'none', fontSize: '0.85rem' }}
                />
                <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }} onClick={handleFetchUrl} onMouseEnter={() => speakText("Fetch and adapt content from URL")}>
                  {t("fetchBtn")}
                </button>
              </div>
            </div>
          )}

          {activeInputMode === 'file' && (
            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.5rem' }}>
              <label>{t("uploadBtn")}</label>
              <div 
                className="glass" 
                style={{ border: '2px dashed var(--border-color)', padding: '2rem', borderRadius: '8px', textAlign: 'center', cursor: 'pointer', background: 'rgba(255,255,255,0.01)' }}
                onClick={() => document.getElementById('file-upload-input').click()}
                onMouseEnter={() => speakText("File drag and drop area. Click to select HTML or text file")}
              >
                <FileText size={36} style={{ color: 'var(--secondary-accent)', marginBottom: '0.75rem' }} />
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  {uiLanguage === 'hi' ? 'फ़ाइल चुनने के लिए यहाँ क्लिक करें (HTML, HTM, TXT, PDF)' : 'Click to select and upload document (HTML, HTM, TXT, PDF)'}
                </p>
                <input 
                  type="file" 
                  accept=".html,.htm,.txt,.pdf" 
                  style={{ display: 'none' }} 
                  id="file-upload-input"
                  onChange={handleFileUpload} 
                />
              </div>

              {uploadedFileName && (
                <div style={{ marginTop: '0.75rem', padding: '0.5rem 0.75rem', background: 'rgba(59, 130, 246, 0.15)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '6px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#60a5fa' }}>
                  <span>📄 Loaded File: <strong>{uploadedFileName}</strong></span>
                  <button 
                    onClick={() => { setUploadedFileName(''); setContent(''); speakText("Cleared file"); }} 
                    style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 'bold' }}
                  >
                    Clear
                  </button>
                </div>
              )}
            </div>
          )}

          <button 
            className="btn btn-primary" 
            onClick={() => handleAdapt()} 
            disabled={loading || !content.trim()}
            onMouseEnter={() => speakText("Generate adaptation button. Click to run the pipeline.")}
          >
            {loading ? t("processing") : t("generateBtn")}
          </button>
        </section>

        {/* Right Output Panel */}
        <section className="panel glass" style={{ minHeight: '600px' }}>
          <h2>
            <Activity size={20} />
            {t("outputTitle")}
          </h2>

          {/* Reader Profile Selection Tabs (as requested above voice assistant control) */}
          <div className="glass" style={{ padding: '1.25rem', border: '1px solid var(--border-color)', marginBottom: '1.25rem', borderRadius: '8px' }}>
            <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 0.75rem 0', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Settings size={14} style={{ color: 'var(--secondary-accent)' }} />
              {uiLanguage === 'hi' ? 'पाठक की भूमिका / आवश्यकता चुनें:' : 'Target Reader Profile / Access Needs:'}
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
              {PROFILE_PRESETS.map((preset) => {
                const isActive = selectedProfile === preset.id;
                return (
                  <button
                    key={preset.id}
                    className={`tab ${isActive ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedProfile(preset.id);
                      speakText(uiLanguage === 'hi' ? `${preset.label} के लिए अनुकूलन कर रहे हैं` : `Adapting for ${preset.label}`);
                      if (content.trim()) {
                        handleAdapt(content, uiLanguage, preset.id);
                      }
                    }}
                    style={{
                      padding: '0.5rem 0.25rem',
                      fontSize: '0.7rem',
                      textAlign: 'center',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      background: isActive ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(147, 51, 234, 0.2))' : 'rgba(255,255,255,0.02)',
                      border: isActive ? '1px solid var(--secondary-accent)' : '1px solid var(--border-color)',
                      color: isActive ? '#ffffff' : 'var(--text-muted)',
                      fontWeight: isActive ? '600' : 'normal',
                      boxShadow: isActive ? '0 0 10px rgba(147, 51, 234, 0.15)' : 'none',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}
                    onMouseEnter={() => speakText(`${preset.label}: ${preset.desc}`)}
                  >
                    {preset.id === 'general_adult' ? (uiLanguage === 'hi' ? 'वयस्क' : 'Adult') : 
                     preset.id === 'child' ? (uiLanguage === 'hi' ? 'बच्चा' : 'Child') : 
                     preset.id === 'anxious' ? (uiLanguage === 'hi' ? 'चिंतित' : 'Anxious') : 
                     preset.id === 'dyslexia_friendly' ? (uiLanguage === 'hi' ? 'डिस्लेक्सिया' : 'Dyslexic') : 
                     preset.id === 'caregiver' ? (uiLanguage === 'hi' ? 'देखभालकर्ता' : 'Caregiver') : 
                     (uiLanguage === 'hi' ? 'विशेषज्ञ' : 'Expert')}
                  </button>
                );
              })}
            </div>
            
            {/* Active profile description details */}
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.75rem', background: 'rgba(0,0,0,0.15)', padding: '0.5rem 0.75rem', borderRadius: '4px', borderLeft: '3px solid var(--secondary-accent)' }}>
              <strong>{PROFILE_PRESETS.find(p => p.id === selectedProfile)?.label}:</strong> {PROFILE_PRESETS.find(p => p.id === selectedProfile)?.desc}
            </div>
          </div>

          {/* Circular Voice Assistant Mic for Right Panel */}
          <div className="glass" style={{ padding: '1.5rem', border: '1px solid var(--primary-accent)', background: 'var(--primary-glow)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', marginBottom: '1.5rem', borderRadius: '8px' }}>
            <h3 style={{ fontSize: '0.9rem', color: 'var(--secondary-accent)', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <Volume2 size={16} />
              {t("voiceControlTitle")}
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0 0 0.5rem 0', textAlign: 'center' }}>
              {t("voiceControlDesc")}
            </p>
            
            {isRecordingVoiceControl ? (
              <button 
                className="btn btn-primary animate-pulse" 
                style={{ 
                  width: '64px', 
                  height: '64px', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  background: 'hsl(350, 80%, 55%)',
                  boxShadow: '0 0 20px hsl(350, 80%, 55%)',
                  border: 'none',
                  cursor: 'pointer'
                }} 
                onClick={stopRecordingVoiceControl}
                onMouseEnter={() => speakText("Stop recording voice command")}
              >
                <Square size={24} style={{ color: 'white' }} />
              </button>
            ) : (
              <button 
                className="btn" 
                style={{ 
                  width: '64px', 
                  height: '64px', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  background: 'linear-gradient(135deg, var(--primary-accent), var(--secondary-accent))', 
                  boxShadow: '0 0 15px var(--primary-accent)',
                  border: 'none',
                  cursor: 'pointer'
                }} 
                onClick={startRecordingVoiceControl}
                onMouseEnter={() => speakText("Click to speak to the voice assistant")}
              >
                <Mic size={24} style={{ color: 'white' }} />
              </button>
            )}
            
            {isRecordingVoiceControl ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'hsl(350, 80%, 55%)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                <div className="pulse-recording" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'hsl(350, 80%, 55%)' }}></div>
                {uiLanguage === 'hi' ? 'बोलें, सिस्टम अपने आप रुक जाएगा...' : 'Speaking... stop talking to auto-process'}
              </div>
            ) : (
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '500', marginTop: '0.25rem' }}>
                {uiLanguage === 'hi' ? 'सहायक से बात करने के लिए दबाएं' : 'Click to Speak & Control'}
              </span>
            )}

            {voiceControlFeedback && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-main)', width: '100%', maxWidth: '280px', textAlign: 'center', padding: '0.4rem 0.6rem', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', border: '1px solid var(--border-color)', marginTop: '0.5rem' }}>
                <strong>Command:</strong> "{voiceControlFeedback}"
              </div>
            )}
          </div>

          {/* Detected Language Switcher Modal */}
          {showLangModal && (
            <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
              <div className="glass" style={{ padding: '2rem', maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '1.5rem', border: '1px solid var(--primary-accent)', borderRadius: '12px' }}>
                <h3 style={{ margin: 0, color: 'var(--secondary-accent)' }}>{t("detectedLangModal")}</h3>
                <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.4' }}>
                  {t("detectedLangPrompt")
                    .replace(/{lang}/g, detectedLangCode === 'hi' ? 'हिंदी (Hindi)' : (detectedLangCode === 'es' ? 'Español (Spanish)' : (detectedLangCode === 'fr' ? 'Français (French)' : detectedLangCode)))}
                </p>
                <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                  <button className="btn btn-secondary" style={{ padding: '0.5rem 1rem' }} onClick={() => setShowLangModal(false)}>
                    {t("no")}
                  </button>
                  <button className="btn btn-primary" style={{ padding: '0.5rem 1rem' }} onClick={() => { setUiLanguage(detectedLangCode); setShowLangModal(false); speakText("Translated interface."); if (content.trim()) { handleAdapt(content, detectedLangCode); } }}>
                    {t("yes")}
                  </button>
                </div>
              </div>
            </div>
          )}

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
                        {isPlayingAudio ? t("stopBtn") : t("listenBtn")}
                      </button>
                    </div>
                  )}

                  {/* Adapted Content with profile-specific accessibility styling */}
                  <div className="adapted-viewport" style={getViewportStyle()}>
                    {result.versions[activeTabIdx].adapted_content}
                  </div>

                  {/* Gaps Panel */}
                  {result.versions[activeTabIdx].gaps && result.versions[activeTabIdx].gaps.length > 0 && (
                    <div className="gaps-panel">
                      <h3>
                        <AlertTriangle size={16} style={{ display: 'inline', marginRight: '0.25rem', verticalAlign: 'text-bottom' }} />
                        {t("gapsTitle")}
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
